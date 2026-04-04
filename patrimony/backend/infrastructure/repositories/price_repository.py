"""Repository implementation for price data.

Handles fetching current prices from external APIs and
caching price data in the database.
"""

import logging
import time
from datetime import datetime, timedelta

import polars as pl

from ...domain.interfaces import MarketDataProvider
from ...domain.repositories import PriceRepository
from ..database.connection import DatabaseConnection

logger = logging.getLogger(__name__)

# How many tickers to process before pausing during bulk sync.
_SYNC_BATCH_SIZE: int = 5
# Seconds to sleep between batches during sync_price_history.
_SYNC_BATCH_DELAY_S: float = 2.0


class PriceRepositoryImpl(PriceRepository):
    """Concrete implementation of PriceRepository.

    Integrates external market data provider with local caching.
    """

    def __init__(
        self,
        connection: DatabaseConnection,
        market_data_provider: MarketDataProvider,
    ):
        self._conn = connection
        self._market_data = market_data_provider

    def get_current_price(self, ticker: str) -> float:
        """Fetch current price, using cache when available."""
        cached_price = self.get_cached_price(ticker, max_age_minutes=15)
        if cached_price:
            return cached_price

        price = self._market_data.get_current_price(ticker)
        if price:
            self.cache_price(ticker, price, datetime.now())
        else:
            logger.debug("No price returned for %s", ticker)

        return price

    def cache_price(self, ticker: str, price: float, timestamp: datetime) -> None:
        """Cache a price in the database."""
        self._conn.execute(
            """
            INSERT OR REPLACE INTO price_cache
            (ticker, current_price, last_updated)
            VALUES (?, ?, ?)
            """,
            [ticker.upper(), price, timestamp],
        )

    def get_cached_price(self, ticker: str, max_age_minutes: int = 15) -> float:
        """Get cached price if available and not stale."""
        result = self._conn.execute(
            f"""
            SELECT current_price, last_updated
            FROM price_cache
            WHERE ticker = ?
            AND last_updated > current_timestamp - INTERVAL '{max_age_minutes}' MINUTE
            ORDER BY last_updated DESC
            LIMIT 1
            """,
            [ticker.upper()],
        ).fetchone()

        return result[0] if result else None

    def get_price_history(
        self,
        tickers: list[str],
        start_date: datetime,
        end_date: datetime,
        period: str = "1d",
    ) -> pl.DataFrame:
        """Get stored price history for tickers within a date range."""
        if not tickers:
            return pl.DataFrame(
                schema={
                    "ticker": pl.Utf8,
                    "date": pl.Datetime,
                    "close_price": pl.Float64,
                }
            )

        placeholders = ", ".join(["?"] * len(tickers))
        return self._conn.execute(
            f"""
            SELECT ticker, date, close_price
            FROM price_history
            WHERE ticker IN ({placeholders})
            AND date >= ? AND date <= ?
            AND period = ?
            ORDER BY date
            """,
            [t.upper() for t in tickers] + [start_date, end_date, period],
        ).pl()

    def _store_price_history(
        self, ticker: str, df: pl.DataFrame, period: str = "1d"
    ) -> None:
        """Insert new price history rows in bulk, ignoring duplicates."""
        if df.is_empty():
            return
        try:
            insert_df = df.select(
                pl.lit(ticker).alias("ticker"),
                pl.col("date"),
                pl.col("close_price"),
                pl.lit(period).alias("period"),
            )
            self._conn.connection.register("insert_df", insert_df)
            try:
                with self._conn.transaction():
                    self._conn.execute(
                        "INSERT OR IGNORE INTO price_history "
                        "(ticker, date, close_price, period, last_updated) "
                        "SELECT ticker, date, close_price, period, CURRENT_TIMESTAMP "
                        "FROM insert_df",
                    )
            finally:
                self._conn.connection.unregister("insert_df")
        except Exception as e:
            logger.warning("Error bulk-storing price history for %s: %s", ticker, e)

    def sync_price_history(
        self, tickers: list[str], start_date: datetime, period: str = "1d"
    ) -> None:
        """Fetch and store only missing price history data.

        Tickers are sorted by staleness (oldest-updated first) and
        processed in batches with a short delay between batches to
        avoid hitting Yahoo Finance rate limits.
        """
        if not tickers:
            return

        today = datetime.now()
        upper_tickers = [t.upper() for t in tickers]

        # Order tickers by staleness (oldest last_updated first).
        # Tickers absent from cache sort to the front so they get fetched first.
        placeholders = ", ".join(["?"] * len(upper_tickers))
        rows = self._conn.execute(
            f"""
            SELECT ticker, last_updated
            FROM price_cache
            WHERE ticker IN ({placeholders})
            """,
            upper_tickers,
        ).fetchall()
        staleness = {r[0]: r[1] for r in rows}
        epoch = datetime(1970, 1, 1)
        ordered = sorted(upper_tickers, key=lambda t: staleness.get(t, epoch))

        for idx, ticker in enumerate(ordered):
            if idx > 0 and idx % _SYNC_BATCH_SIZE == 0:
                logger.debug("Rate-limit pause after %d/%d tickers", idx, len(ordered))
                time.sleep(_SYNC_BATCH_DELAY_S)

            try:
                self._sync_single_ticker(ticker, start_date, today, period)
            except Exception as e:
                logger.warning("Skipping price sync for %s: %s", ticker, e)

    def _sync_single_ticker(
        self,
        ticker: str,
        start_date: datetime,
        today: datetime,
        period: str,
    ) -> None:
        """Fetch and store missing price history for a single ticker."""
        # Check what date range we already have stored
        result = self._conn.execute(
            """
            SELECT MIN(date), MAX(date) FROM price_history
            WHERE ticker = ? AND period = ?
            """,
            [ticker, period],
        ).fetchone()

        min_date = result[0] if result and result[0] else None
        max_date = result[1] if result and result[1] else None

        # No data at all — fetch full range
        if min_date is None:
            df = self._market_data.get_price_history(
                ticker, start_date=start_date, end_date=today
            )
            if df is not None and not df.is_empty():
                self._store_price_history(ticker, df, period)
            return

        # Fill missing early data if start_date is before our earliest
        if start_date.date() < (min_date - timedelta(days=1)).date():
            df = self._market_data.get_price_history(
                ticker,
                start_date=start_date,
                end_date=min_date - timedelta(days=1),
            )
            if df is not None and not df.is_empty():
                self._store_price_history(ticker, df, period)

        # Fill missing recent data if latest date is before yesterday
        if max_date.date() < (today - timedelta(days=1)).date():
            df = self._market_data.get_price_history(
                ticker,
                start_date=max_date + timedelta(days=1),
                end_date=today,
            )
            if df is not None and not df.is_empty():
                self._store_price_history(ticker, df, period)

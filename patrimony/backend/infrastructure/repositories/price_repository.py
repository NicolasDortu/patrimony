"""Repository implementation for price data.

Handles fetching current prices from external APIs and
caching price data in the database.
"""

import logging
from datetime import datetime

import polars as pl

from ...domain.interfaces import MarketDataProvider
from ...domain.repositories import PriceRepository
from ..database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


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

    def store_price_history(
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

    def get_stored_date_range(
        self, ticker: str, period: str = "1d"
    ) -> tuple[datetime | None, datetime | None]:
        """Return (min_date, max_date) of stored price history for a ticker."""
        result = self._conn.execute(
            """
            SELECT MIN(date), MAX(date) FROM price_history
            WHERE ticker = ? AND period = ?
            """,
            [ticker.upper(), period],
        ).fetchone()
        min_date = result[0] if result and result[0] else None
        max_date = result[1] if result and result[1] else None
        return min_date, max_date

    def get_cache_timestamps(self, tickers: list[str]) -> dict[str, datetime]:
        """Return {ticker: last_updated} for tickers present in price cache."""
        if not tickers:
            return {}
        upper_tickers = [t.upper() for t in tickers]
        placeholders = ", ".join(["?"] * len(upper_tickers))
        rows = self._conn.execute(
            f"""
            SELECT ticker, last_updated
            FROM price_cache
            WHERE ticker IN ({placeholders})
            """,
            upper_tickers,
        ).fetchall()
        return {r[0]: r[1] for r in rows}

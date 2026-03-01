"""Repository implementation for price data.

Handles fetching current prices from external APIs and
caching price data in the database.
"""

from datetime import datetime, timedelta

import polars as pl

from ...domain.repositories import PriceRepository, MarketDataProvider
from ..database.connection import DatabaseConnection


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
        self, tickers: list[str], start_date: datetime, end_date: datetime
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
            AND period = '1d'
            ORDER BY date
            """,
            [t.upper() for t in tickers] + [start_date, end_date],
        ).pl()

    def _store_price_history(self, ticker: str, df: pl.DataFrame) -> None:
        """Insert new price history rows, ignoring duplicates."""
        for row in df.iter_rows(named=True):
            try:
                self._conn.execute(
                    """
                    INSERT OR IGNORE INTO price_history
                    (ticker, date, close_price, period, last_updated)
                    VALUES (?, ?, ?, '1d', CURRENT_TIMESTAMP)
                    """,
                    [ticker, row["date"], row["close_price"]],
                )
            except Exception:
                print("error while storing price history for", ticker, row["date"])

    def sync_price_history(self, tickers: list[str], start_date: datetime) -> None:
        """Fetch and store only missing price history data."""
        today = datetime.now()

        for ticker in tickers:
            ticker = ticker.upper()

            # Check what date range we already have stored
            result = self._conn.execute(
                """
                SELECT MIN(date), MAX(date) FROM price_history
                WHERE ticker = ? AND period = '1d'
                """,
                [ticker],
            ).fetchone()

            min_date = result[0] if result and result[0] else None
            max_date = result[1] if result and result[1] else None

            # No data at all — fetch full range
            if min_date is None:
                df = self._market_data.get_price_history(
                    ticker, start_date=start_date, end_date=today
                )
                if df is not None and not df.is_empty():
                    self._store_price_history(ticker, df)
                continue

            # Fill missing early data if start_date is before our earliest
            if start_date.date() < (min_date - timedelta(days=1)).date():
                df = self._market_data.get_price_history(
                    ticker,
                    start_date=start_date,
                    end_date=min_date - timedelta(days=1),
                )
                if df is not None and not df.is_empty():
                    self._store_price_history(ticker, df)

            # Fill missing recent data if latest date is before yesterday
            if max_date.date() < (today - timedelta(days=1)).date():
                df = self._market_data.get_price_history(
                    ticker,
                    start_date=max_date + timedelta(days=1),
                    end_date=today,
                )
                if df is not None and not df.is_empty():
                    self._store_price_history(ticker, df)

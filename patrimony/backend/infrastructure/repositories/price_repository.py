"""Repository implementation for price data.

Handles caching and retrieving price data from the database.
"""

import logging
from datetime import datetime

import polars as pl

from ...domain.repositories import PriceRepository
from ..database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class PriceRepositoryImpl(PriceRepository):
    """Concrete implementation of PriceRepository."""

    def __init__(
        self,
        connection: DatabaseConnection,
    ):
        self._conn = connection

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
        """Insert new price history rows in bulk"""
        if df.is_empty():
            return
        try:
            insert_df = df.select(["date", "close_price"]).with_columns(
                pl.lit(ticker).alias("ticker"),
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

    def get_cached_prices(
        self, tickers: list[str], max_age_minutes: int = 15
    ) -> dict[str, float]:
        """Return cached prices that are still fresh (within max_age_minutes)."""
        if not tickers:
            return {}

        upper_tickers = [t.upper() for t in tickers]
        placeholders = ", ".join(["?"] * len(upper_tickers))

        rows = self._conn.execute(
            f"""
            SELECT ticker, current_price
            FROM price_cache
            WHERE ticker IN ({placeholders})
            AND last_updated > current_timestamp - INTERVAL '{max_age_minutes}' MINUTE
            """,
            upper_tickers,
        ).fetchall()

        return {r[0]: r[1] for r in rows if r[1] is not None}

    def get_last_known_prices(self, tickers: list[str]) -> dict[str, float]:
        """Return the most recent stored historical close price per ticker.

        Only returns strictly positive prices.
        """
        if not tickers:
            return {}
        upper_tickers = [t.upper() for t in tickers]
        placeholders = ", ".join(["?"] * len(upper_tickers))
        rows = self._conn.execute(
            f"""
            SELECT ticker, close_price
            FROM price_history
            WHERE ticker IN ({placeholders})
              AND close_price > 0
              AND (ticker, date) IN (
                  SELECT ticker, MAX(date)
                  FROM price_history
                  WHERE ticker IN ({placeholders}) AND close_price > 0
                  GROUP BY ticker
              )
            """,
            upper_tickers + upper_tickers,
        ).fetchall()
        return {r[0]: r[1] for r in rows if r[1] and r[1] > 0}

    def store_intraday_prices(self, ticker: str, df: pl.DataFrame) -> None:
        """Replace stored intraday prices for a ticker with fresh data."""
        if df.is_empty():
            return
        upper = ticker.upper()
        try:
            insert_df = df.select(["date", "close_price"]).with_columns(
                pl.lit(upper).alias("ticker"),
            )
            self._conn.connection.register("intraday_insert_df", insert_df)
            try:
                with self._conn.transaction():
                    self._conn.execute(
                        "DELETE FROM intraday_prices WHERE ticker = ?", [upper]
                    )
                    self._conn.execute(
                        "INSERT INTO intraday_prices "
                        "(ticker, date, close_price, last_updated) "
                        "SELECT ticker, date, close_price, CURRENT_TIMESTAMP "
                        "FROM intraday_insert_df",
                    )
            finally:
                self._conn.connection.unregister("intraday_insert_df")
        except Exception as e:
            logger.warning("Error storing intraday prices for %s: %s", upper, e)

    def get_intraday_prices(self, tickers: list[str]) -> pl.DataFrame:
        """Get today's intraday price data for the given tickers."""
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
            FROM intraday_prices
            WHERE ticker IN ({placeholders})
            ORDER BY date
            """,
            [t.upper() for t in tickers],
        ).pl()

    def get_intraday_last_updated(self, ticker: str) -> "datetime | None":
        """Return the most recent last_updated timestamp for a ticker's intraday data."""
        result = self._conn.execute(
            "SELECT MAX(last_updated) FROM intraday_prices WHERE ticker = ?",
            [ticker.upper()],
        ).fetchone()
        return result[0] if result and result[0] else None

    def get_latest_intraday_prices(
        self, tickers: list[str], max_age_minutes: int = 15
    ) -> dict[str, float]:
        """Return the latest intraday close price per ticker if data is fresh."""
        if not tickers:
            return {}
        upper_tickers = [t.upper() for t in tickers]
        placeholders = ", ".join(["?"] * len(upper_tickers))
        rows = self._conn.execute(
            f"""
            SELECT ticker, close_price
            FROM intraday_prices
            WHERE ticker IN ({placeholders})
            AND last_updated > current_timestamp - INTERVAL '{max_age_minutes}' MINUTE
            AND (ticker, date) IN (
                SELECT ticker, MAX(date)
                FROM intraday_prices
                WHERE ticker IN ({placeholders})
                GROUP BY ticker
            )
            """,
            upper_tickers + upper_tickers,
        ).fetchall()
        return {r[0]: r[1] for r in rows if r[1] is not None and r[1] > 0}

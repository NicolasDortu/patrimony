from typing import Optional

import polars as pl

from ...database.connection import DatabaseConnection


class PriceCacheOperations:
    """Database operations for price caching."""

    def __init__(self, conn: DatabaseConnection) -> None:
        self.conn = conn

    def get_cached_price(self, ticker: str) -> Optional[float]:
        """Get cached price for a ticker."""
        result = self.conn.execute(
            "SELECT current_price FROM price_cache WHERE ticker = ?",
            [ticker.upper()],
        ).fetchone()
        return result[0] if result else None

    def get_all_cached_prices(self) -> pl.DataFrame:
        """Get all cached prices as a DataFrame."""
        return self.conn.execute(
            "SELECT ticker, current_price, last_updated FROM price_cache"
        ).pl()

    def upsert_price(self, ticker: str, price: float) -> None:
        """Insert or update cached price for a ticker."""
        self.conn.execute(
            """
            INSERT INTO price_cache (ticker, current_price, last_updated)
            VALUES ($1, $2, now())
            ON CONFLICT (ticker) DO UPDATE SET
                current_price = $2,
                last_updated = now()
            """,
            [ticker.upper(), price],
        )

    def delete_cached_price(self, ticker: str) -> None:
        """Delete cached price for a ticker."""
        self.conn.execute("DELETE FROM price_cache WHERE ticker = ?", [ticker.upper()])


class PriceHistoryOperations:
    """Database operations for price history caching."""

    def __init__(self, conn: DatabaseConnection) -> None:
        self.conn = conn

    def get_cached_history(self, ticker: str, period: str) -> pl.DataFrame:
        """Get cached price history for a ticker and period."""
        return self.conn.execute(
            """
            SELECT date, close_price as close
            FROM price_history
            WHERE ticker = ? AND period = ?
            ORDER BY date
            """,
            [ticker.upper(), period],
        ).pl()

    def get_last_cached_date(self, ticker: str, period: str):
        """Get the most recent cached date for a ticker and period."""
        result = self.conn.execute(
            """
            SELECT MAX(date) FROM price_history
            WHERE ticker = ? AND period = ?
            """,
            [ticker.upper(), period],
        ).fetchone()
        return result[0] if result and result[0] else None

    def upsert_history(
        self, ticker: str, period: str, history_df: pl.DataFrame
    ) -> None:
        """Insert or update price history for a ticker and period.

        Only inserts new records that don't already exist to avoid
        unnecessary updates of immutable historical data.
        """
        ticker_upper = ticker.upper()
        last_cached = self.get_last_cached_date(ticker_upper, period)

        # Filter to only new data if we have cached data
        if last_cached is not None:
            # Convert to timezone-naive for comparison (yfinance returns tz-aware dates)
            history_df = history_df.with_columns(
                pl.col("date").dt.replace_time_zone(None).alias("date_naive")
            )
            history_df = history_df.filter(pl.col("date_naive") > last_cached).drop(
                "date_naive"
            )

        if history_df.is_empty():
            return

        # Deduplicate by date (keep last occurrence)
        history_df = history_df.unique(subset=["date"], keep="last")

        for row in history_df.iter_rows(named=True):
            self.conn.execute(
                """
                INSERT INTO price_history (ticker, date, close_price, period, last_updated)
                VALUES ($1, $2, $3, $4, now())
                ON CONFLICT (ticker, date, period) DO UPDATE SET
                    close_price = $3,
                    last_updated = now()
                """,
                [ticker_upper, row["date"], row["close"], period],
            )

    def delete_history(self, ticker: str, period: str = None) -> None:
        """Delete cached history for a ticker, optionally filtered by period."""
        if period:
            self.conn.execute(
                "DELETE FROM price_history WHERE ticker = ? AND period = ?",
                [ticker.upper(), period],
            )
        else:
            self.conn.execute(
                "DELETE FROM price_history WHERE ticker = ?", [ticker.upper()]
            )

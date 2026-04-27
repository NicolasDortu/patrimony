"""Repository implementation for dividends.

Tickers are normalized to upper-case at the application layer
(``dividend_use_cases``); repos trust the input.
"""

from datetime import datetime
import polars as pl

from ...domain.repositories import DividendRepository
from ..database.connection import DatabaseConnection


class DividendRepositoryImpl(DividendRepository):
    """Concrete implementation of DividendRepository using DuckDB."""

    def __init__(self, connection: DatabaseConnection):
        self._conn = connection

    def add_dividend(
        self,
        ticker: str,
        amount: float,
        date: datetime,
    ) -> int:
        """Add a new dividend to the database."""
        result = self._conn.execute(
            """
            INSERT INTO dividends (ticker, amount, date)
            VALUES (?, ?, ?)
            RETURNING id
            """,
            [ticker, amount, date],
        )
        return result.fetchone()[0]

    def get_by_ticker(self, ticker: str) -> pl.DataFrame:
        """Get all dividends for a specific ticker."""
        return self._conn.execute(
            "SELECT * FROM dividends WHERE ticker = ? ORDER BY date DESC",
            [ticker],
        ).pl()

    def get_total_amount(self) -> float:
        """Return the total amount of all dividends (raw, no currency conversion)."""
        result = self._conn.execute("SELECT COALESCE(SUM(amount), 0) FROM dividends")
        return result.fetchone()[0]

    def get_totals_by_ticker(self) -> dict[str, float]:
        """Return ``{ticker: total_amount}`` for all dividends in native currency."""
        rows = self._conn.execute(
            "SELECT ticker, COALESCE(SUM(amount), 0) FROM dividends GROUP BY ticker"
        ).fetchall()
        return {r[0]: float(r[1]) for r in rows if r[1]}

    def get_by_id(self, id: int) -> pl.DataFrame:
        """Get a dividend by ID."""
        return self._conn.execute("SELECT * FROM dividends WHERE id = ?", [id]).pl()

    def get_all(self) -> pl.DataFrame:
        """Get all dividends."""
        return self._conn.execute("SELECT * FROM dividends ORDER BY date DESC").pl()

    def delete(self, id: int) -> None:
        """Delete a dividend by ID."""
        self._conn.execute("DELETE FROM dividends WHERE id = ?", [id])

    def update_dividend(
        self,
        id: int,
        ticker: str,
        amount: float,
        date: datetime,
    ) -> None:
        """Update an existing dividend by ID."""
        self._conn.execute(
            """
            UPDATE dividends
            SET ticker = ?, amount = ?, date = ?
            WHERE id = ?
            """,
            [ticker, amount, date, id],
        )

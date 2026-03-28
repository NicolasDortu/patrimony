"""Repository implementation for dividends."""

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
            [ticker.upper(), amount, date],
        )
        return result.fetchone()[0]

    def get_by_ticker(self, ticker: str) -> pl.DataFrame:
        """Get all dividends for a specific ticker."""
        return self._conn.execute(
            "SELECT * FROM dividends WHERE ticker = ? ORDER BY date DESC",
            [ticker.upper()],
        ).pl()

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
            [ticker.upper(), amount, date, id],
        )

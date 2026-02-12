"""Repository implementation for cash accounts.

Concrete implementation of CashRepository interface handling
all database operations for cash accounts.
"""

from datetime import datetime
import polars as pl

from ...domain.repositories import CashRepository
from ...domain.entities import Currency
from ..database.connection import DatabaseConnection


class CashRepositoryImpl(CashRepository):
    """Concrete implementation of CashRepository using DuckDB."""

    def __init__(self, connection: DatabaseConnection):
        self._conn = connection

    def add_cash(
        self,
        bank: str,
        account_number: str,
        currency: Currency,
        balance: float,
        last_updated: datetime,
    ) -> int:
        """Add a new cash account."""
        result = self._conn.execute(
            """
            INSERT INTO cash
            (bank, account_number, currency, balance, last_updated)
            VALUES (?, ?, ?, ?, ?)
            RETURNING id
            """,
            [bank, account_number, currency.value, balance, last_updated],
        )
        return result.fetchone()[0]

    def update_cash(
        self,
        id: int,
        bank: str,
        account_number: str,
        currency: Currency,
        balance: float,
        last_updated: datetime,
    ) -> None:
        """Update an existing cash account."""
        self._conn.execute(
            """
            UPDATE cash
            SET bank = ?, account_number = ?, currency = ?, balance = ?, last_updated = ?
            WHERE id = ?
            """,
            [bank, account_number, currency.value, balance, last_updated, id],
        )

    def get_by_bank(self, bank: str) -> pl.DataFrame:
        """Get all cash accounts for a specific bank."""
        return self._conn.execute("SELECT * FROM cash WHERE bank = ?", [bank]).pl()

    def get_by_id(self, id: int) -> pl.DataFrame:
        """Get cash account by ID."""
        return self._conn.execute("SELECT * FROM cash WHERE id = ?", [id]).pl()

    def delete(self, id: int) -> None:
        """Delete a cash account by ID."""
        self._conn.execute("DELETE FROM cash WHERE id = ?", [id])

    def get_all(self) -> pl.DataFrame:
        """Get all cash accounts."""
        return self._conn.execute("SELECT * FROM cash").pl()

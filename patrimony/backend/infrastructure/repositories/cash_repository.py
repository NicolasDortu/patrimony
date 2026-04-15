"""Repository implementation for cash accounts.

Concrete implementation of CashRepository interface handling
all database operations for cash accounts.
"""

from datetime import datetime
import polars as pl

from ...domain.repositories import (
    CashOperationRepository,
    CashRepository,
)
from ...domain.entities import Currency, EntryType
from ..database.connection import DatabaseConnection


class CashOperationRepositoryImpl(CashOperationRepository):
    """Concrete implementation of CashOperationRepository using DuckDB."""

    def __init__(self, connection: DatabaseConnection):
        self._conn = connection

    def add_operation_balance(
        self,
        account_number: str,
        amount: float,
        title: str,
        operation_date: datetime,
        entry_type: EntryType,
        category: str = "Uncategorized",
    ) -> int:
        """Record a cash operation on the balance and return the operation ID."""
        with self._conn.transaction():
            result = self._conn.execute(
                """
                INSERT INTO balance_operations
                (account_number, amount, balance, rank, title, category, operation_date, entry_type)
                VALUES (?, ?, 0, 0, ?, ?, ?, ?)
                RETURNING id
                """,
                [
                    account_number,
                    amount,
                    title,
                    category,
                    operation_date,
                    entry_type.value,
                ],
            )
            op_id = result.fetchone()[0]
            self.recalculate_balances(account_number)
        return op_id

    def get_operations_by_account(self, account_number: str) -> pl.DataFrame:
        """Get all balance operations for a specific account."""
        result = self._conn.execute(
            """
            SELECT * FROM balance_operations
            WHERE account_number = ?
            ORDER BY rank DESC
            """,
            [account_number],
        )
        return result.pl()

    def get_all_operations(self) -> pl.DataFrame:
        """Get all balance operations."""
        result = self._conn.execute(
            """
            SELECT * FROM balance_operations
            ORDER BY rank DESC
            """
        )
        return result.pl()

    def get_cash_balance_history(self) -> pl.DataFrame:
        """Get cash balance history ordered by date for building a cash timeline."""
        result = self._conn.execute(
            """
            SELECT operation_date, account_number, balance
            FROM balance_operations
            ORDER BY rank ASC
            """
        )
        return result.pl()

    def delete_operation_by_id(self, id: int) -> None:
        """Delete a balance operation by ID and recalculate ranks/balances."""
        with self._conn.transaction():
            result = self._conn.execute(
                "SELECT account_number FROM balance_operations WHERE id = ?",
                [id],
            )
            row = result.fetchone()
            if row is None:
                raise ValueError(f"Operation {id} not found")
            account_number = row[0]
            self._conn.execute("DELETE FROM balance_operations WHERE id = ?", [id])
            self.recalculate_balances(account_number)

    def update_operation_by_id(
        self,
        id: int,
        amount: float,
        title: str,
        operation_date: datetime,
        entry_type: EntryType,
        category: str = "Uncategorized",
    ) -> None:
        """Update a balance operation by ID and recalculate ranks/balances."""
        with self._conn.transaction():
            result = self._conn.execute(
                "SELECT account_number FROM balance_operations WHERE id = ?",
                [id],
            )
            row = result.fetchone()
            if row is None:
                raise ValueError(f"Operation {id} not found")
            account_number = row[0]
            self._conn.execute(
                """
                UPDATE balance_operations
                SET amount = ?, title = ?, category = ?, operation_date = ?, entry_type = ?
                WHERE id = ?
                """,
                [amount, title, category, operation_date, entry_type.value, id],
            )
            self.recalculate_balances(account_number)

    def recalculate_balances(self, account_number: str) -> None:
        """Recalculate ranks and running balances for all operations of an account.

        Uses a single UPDATE with window functions instead of per-row updates.
        """
        self._conn.execute(
            """
            UPDATE balance_operations AS bo
            SET rank = sub.new_rank, balance = sub.running_balance
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER w AS new_rank,
                       SUM(amount) OVER w AS running_balance
                FROM balance_operations
                WHERE account_number = ?
                WINDOW w AS (ORDER BY operation_date ASC, id ASC)
            ) AS sub
            WHERE bo.id = sub.id
            """,
            [account_number],
        )


class CashRepositoryImpl(CashRepository):
    """Concrete implementation of CashRepository using DuckDB.

    Delegates operation methods to an internal CashOperationRepositoryImpl.
    """

    def __init__(self, connection: DatabaseConnection):
        self._conn = connection
        self._operations = CashOperationRepositoryImpl(connection)

    # ── Delegate operation methods to _operations ──
    def add_operation_balance(self, *args, **kwargs):
        return self._operations.add_operation_balance(*args, **kwargs)

    def get_operations_by_account(self, account_number):
        return self._operations.get_operations_by_account(account_number)

    def get_all_operations(self):
        return self._operations.get_all_operations()

    def get_cash_balance_history(self):
        return self._operations.get_cash_balance_history()

    def delete_operation_by_id(self, id):
        return self._operations.delete_operation_by_id(id)

    def update_operation_by_id(self, *args, **kwargs):
        return self._operations.update_operation_by_id(*args, **kwargs)

    def recalculate_balances(self, account_number):
        return self._operations.recalculate_balances(account_number)

    def add_cash(
        self,
        bank: str,
        account_number: str,
        currency: Currency,
        last_updated: datetime,
        entry_type: EntryType = EntryType.MANUAL,
    ) -> str:
        """Add a new cash account."""
        result = self._conn.execute(
            """
            INSERT INTO cash
            (bank, account_number, currency, last_updated, entry_type)
            VALUES (?, ?, ?, ?, ?)
            RETURNING account_number
            """,
            [
                bank,
                account_number,
                currency.value,
                last_updated,
                entry_type.value,
            ],
        )
        return result.fetchone()[0]

    def update_cash(
        self,
        bank: str,
        account_number: str,
        currency: Currency,
        last_updated: datetime,
    ) -> None:
        """Update an existing cash account."""
        self._conn.execute(
            """
            UPDATE cash
            SET bank = ?, currency = ?, last_updated = ?
            WHERE account_number = ?
            """,
            [bank, currency.value, last_updated, account_number],
        )

    def get_balance(self, account_number: str) -> float:
        """Get the current balance of a cash account."""
        result = self._conn.execute(
            """
            SELECT balance FROM cash_balance
            WHERE account_number = ?
            """,
            [account_number],
        )
        row = result.fetchone()
        return row[0] if row is not None else 0.0

    def get_total_balance(self) -> float:
        """Return the total balance across all cash accounts (raw, no currency conversion)."""
        result = self._conn.execute(
            "SELECT COALESCE(SUM(balance), 0) FROM cash_balance"
        )
        return result.fetchone()[0]

    def delete(self, account_number: str) -> None:
        """Delete a cash account by account number. And also delete all related balance operations."""
        with self._conn.transaction():
            self._conn.execute(
                "DELETE FROM balance_operations WHERE account_number = ?",
                [account_number],
            )
            self._conn.execute(
                "DELETE FROM cash WHERE account_number = ?", [account_number]
            )

    def get_all(self) -> pl.DataFrame:
        """Get all cash accounts with their current balance."""
        return self._conn.execute(
            """
            SELECT c.*, COALESCE(cb.balance, 0.0) AS balance
            FROM cash c
            LEFT JOIN cash_balance cb
                ON c.account_number = cb.account_number
            """
        ).pl()

    def get_by_id(self, account_number: str) -> pl.DataFrame:
        """Get cash account by account number with its current balance."""
        return self._conn.execute(
            """
            SELECT c.*, COALESCE(cb.balance, 0.0) AS balance
            FROM cash c
            LEFT JOIN cash_balance cb
                ON c.account_number = cb.account_number
            WHERE c.account_number = ?
            """,
            [account_number],
        ).pl()

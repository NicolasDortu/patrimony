"""Repository implementation for cash accounts.

Concrete implementation of CashRepository interface handling
all database operations for cash accounts.
"""

from datetime import datetime
import polars as pl

from ...domain.repositories import CashRepository
from ...domain.entities import Currency, EntryType
from ..database.connection import DatabaseConnection


class CashRepositoryImpl(CashRepository):
    """Concrete implementation of CashRepository using DuckDB."""

    def __init__(self, connection: DatabaseConnection):
        self._conn = connection

    def _recalculate_ranks_and_balances(self, account_number: str) -> None:
        """Recalculate ranks and running balances for all operations of an account.

        Orders operations by operation_date ASC, id ASC, then assigns
        sequential ranks and recomputes the cumulative balance.
        """
        rows = self._conn.execute(
            """
            SELECT id, amount
            FROM balance_operations
            WHERE account_number = ?
            ORDER BY operation_date ASC, id ASC
            """,
            [account_number],
        ).fetchall()

        running_balance = 0.0
        for rank, (op_id, amount) in enumerate(rows, start=1):
            running_balance += amount
            self._conn.execute(
                """
                UPDATE balance_operations
                SET rank = ?, balance = ?
                WHERE id = ?
                """,
                [rank, running_balance, op_id],
            )

    def _create_initial_balance_operation(
        self,
        account_number: str,
        balance: float,
        entry_type: EntryType,
    ) -> None:
        """Create an initial balance operation for a new cash account."""
        self._conn.execute(
            """
            INSERT INTO balance_operations
            (account_number, amount, balance, rank, title, operation_date, entry_type)
            VALUES (?, ?, ?, 1, ?, CURRENT_TIMESTAMP, ?)
            """,
            [
                account_number,
                balance,
                balance,
                "Initial balance",
                entry_type.value,
            ],
        )

    def add_cash(
        self,
        bank: str,
        account_number: str,
        currency: Currency,
        balance: float,
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
        # also create the initial balance operation
        self._create_initial_balance_operation(account_number, balance, entry_type)
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
            SET bank = ?, account_number = ?, currency = ?, last_updated = ?
            WHERE account_number = ?
            """,
            [bank, account_number, currency.value, last_updated, account_number],
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

    ## Operations methods ##
    def add_operation_balance(
        self,
        account_number: str,
        amount: float,
        title: str,
        operation_date: datetime,
        entry_type: EntryType,
    ) -> str:
        """Record a cash operation on the balance and return the operation ID."""
        with self._conn.transaction():
            result = self._conn.execute(
                """
                INSERT INTO balance_operations
                (account_number, amount, balance, rank, title, operation_date, entry_type)
                VALUES (?, ?, 0, 0, ?, ?, ?)
                RETURNING account_number
                """,
                [
                    account_number,
                    amount,
                    title,
                    operation_date,
                    entry_type.value,
                ],
            )
            op_id = result.fetchone()[0]
            self._recalculate_ranks_and_balances(account_number)
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
            account_number = result.fetchone()[0]
            self._conn.execute("DELETE FROM balance_operations WHERE id = ?", [id])
            self._recalculate_ranks_and_balances(account_number)

    def update_operation_by_id(
        self,
        id: int,
        amount: float,
        title: str,
        operation_date: datetime,
        entry_type: EntryType,
    ) -> None:
        """Update a balance operation by ID and recalculate ranks/balances."""
        with self._conn.transaction():
            result = self._conn.execute(
                "SELECT account_number FROM balance_operations WHERE id = ?",
                [id],
            )
            account_number = result.fetchone()[0]
            self._conn.execute(
                """
                UPDATE balance_operations
                SET amount = ?, title = ?, operation_date = ?, entry_type = ?
                WHERE id = ?
                """,
                [amount, title, operation_date, entry_type.value, id],
            )
            self._recalculate_ranks_and_balances(account_number)

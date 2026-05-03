"""Repository implementation for cash accounts."""

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
    ) -> None:
        """Record a cash operation on the balance."""
        with self._conn.transaction():
            self._conn.execute(
                """
                INSERT INTO balance_operations
                (account_number, amount, balance, rank, title, category, operation_date, entry_type)
                VALUES (?, ?, 0, 0, ?, ?, ?, ?)
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
            self.recalculate_balances(account_number)

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


class CashRepositoryImpl(CashOperationRepositoryImpl, CashRepository):
    """Concrete implementation of CashRepository using DuckDB.

    Inherits all balance-operation methods from
    :class:`CashOperationRepositoryImpl` and adds account-level operations.
    """

    def __init__(self, connection: DatabaseConnection):
        super().__init__(connection)

    def add_cash(
        self,
        bank: str,
        account_number: str,
        currency: Currency,
        last_updated: datetime,
        entry_type: EntryType = EntryType.MANUAL,
    ) -> None:
        """Add a new cash account."""
        self._conn.execute(
            """
            INSERT INTO cash
            (bank, account_number, currency, last_updated, entry_type)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                bank,
                account_number,
                currency.value,
                last_updated,
                entry_type.value,
            ],
        )

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
        """Delete a cash account and its balance operations.

        DuckDB's FK enforcement does not fully respect MVCC, so deleting
        the children and the parent inside the same transaction trips the
        FK constraint. We therefore commit the child delete first, then
        the parent. If the process crashes between the two commits the
        cash row remains with no operations, which is recoverable
        (re-running ``delete`` is idempotent).
        """
        with self._conn.transaction():
            self._conn.execute(
                "DELETE FROM balance_operations WHERE account_number = ?",
                [account_number],
            )
        with self._conn.transaction():
            self._conn.execute(
                "DELETE FROM cash WHERE account_number = ?", [account_number]
            )

    def rename_account(self, old_account_number: str, new_account_number: str) -> None:
        """Atomically rename an account, cascading to balance_operations.

        DuckDB doesn't support deferred FKs, so we update the child rows
        first (pointing them at the new key, which doesn't exist yet)
        then the parent. Wrapping in a transaction makes the temporary
        FK violation invisible to other readers.
        """
        if old_account_number == new_account_number:
            return
        with self._conn.transaction():
            # Insert the new parent first so the FK target exists.
            self._conn.execute(
                """
                INSERT INTO cash (bank, account_number, currency, last_updated, entry_type)
                SELECT bank, ?, currency, last_updated, entry_type
                FROM cash WHERE account_number = ?
                """,
                [new_account_number, old_account_number],
            )
            self._conn.execute(
                "UPDATE balance_operations SET account_number = ? WHERE account_number = ?",
                [new_account_number, old_account_number],
            )
            self._conn.execute(
                "DELETE FROM cash WHERE account_number = ?", [old_account_number]
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

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

    def _create_initial_balance_operation(
        self,
        account_number: str,
        currency: Currency,
        balance: float,
        entry_type: EntryType,
    ) -> None:
        """Create an initial balance operation for a new cash account."""
        self._conn.execute(
            """
            INSERT INTO balance_operations
            (account_number, currency, amount, balance,title, operation_date, entry_type)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
            """,
            [
                account_number,
                currency.value,
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
    ) -> int:
        """Add a new cash account."""
        result = self._conn.execute(
            """
            INSERT INTO cash
            (bank, account_number, currency, last_updated, entry_type)
            VALUES (?, ?, ?, ?, ?)
            RETURNING id
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
        self._create_initial_balance_operation(
            account_number, currency, balance, entry_type
        )
        return result.fetchone()[0]

    def update_cash(
        self,
        id: int,
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
            WHERE id = ?
            """,
            [bank, account_number, currency.value, last_updated, id],
        )

    def get_balance(self, account_number: str, currency: Currency) -> float:
        """Get the current balance of a cash account."""
        result = self._conn.execute(
            """
            SELECT balance FROM cash_balance
            WHERE account_number = ? AND currency = ?
            """,
            [account_number, currency.value],
        )
        return result.fetchone()[0]

    def delete(self, id: int) -> None:
        """Delete a cash account by ID. And also delete all related balance operations."""
        with self._conn.transaction():
            self._conn.execute(
                "DELETE FROM balance_operations WHERE account_number = (SELECT account_number FROM cash WHERE id = ?)",
                [id],
            )
            self._conn.execute("DELETE FROM cash WHERE id = ?", [id])

    def get_all(self) -> pl.DataFrame:
        """Get all cash accounts with their current balance."""
        return self._conn.execute(
            """
            SELECT c.*, COALESCE(cb.balance, 0.0) AS balance
            FROM cash c
            LEFT JOIN cash_balance cb
                ON c.account_number = cb.account_number
                AND c.currency = cb.currency
            """
        ).pl()

    def get_by_id(self, id: int) -> pl.DataFrame:
        """Get cash account by ID with its current balance."""
        return self._conn.execute(
            """
            SELECT c.*, COALESCE(cb.balance, 0.0) AS balance
            FROM cash c
            LEFT JOIN cash_balance cb
                ON c.account_number = cb.account_number
                AND c.currency = cb.currency
            WHERE c.id = ?
            """,
            [id],
        ).pl()

    ## Operations methods ##
    def operation_balance(
        self,
        account_number: str,
        currency: Currency,
        amount: float,
        title: str,
        operation_date: datetime,
        entry_type: EntryType,
    ) -> list[bool, str]:
        """Record a cash operation on the balance."""
        balance = self.get_balance(account_number, currency)
        try:
            result = self._conn.execute(
                """
                INSERT INTO balance_operations
                (account_number, currency, amount, balance, title, operation_date, entry_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                [
                    account_number,
                    currency.value,
                    amount,
                    balance + amount,
                    title,
                    operation_date,
                    entry_type.value,
                ],
            )
            return [True, f"Operation successful, id: {result.fetchone()[0]}"]
        except Exception as e:
            return [False, f"Operation failed: {str(e)}"]

    def get_operations_by_account(self, account_number: str) -> pl.DataFrame:
        """Get all balance operations for a specific account."""
        result = self._conn.execute(
            """
            SELECT * FROM balance_operations
            WHERE account_number = ?
            ORDER BY operation_date DESC
            """,
            [account_number],
        )
        return result.pl()

    def get_all_operations(self) -> pl.DataFrame:
        """Get all balance operations."""
        result = self._conn.execute(
            """
            SELECT * FROM balance_operations
            ORDER BY operation_date DESC
            """
        )
        return result.pl()

    def get_cash_balance_history(self) -> pl.DataFrame:
        """Get cash balance history ordered by date for building a cash timeline."""
        result = self._conn.execute(
            """
            SELECT operation_date, account_number, currency, balance
            FROM balance_operations
            ORDER BY operation_date ASC, id ASC
            """
        )
        return result.pl()

    def delete_operation_by_id(self, id: int) -> bool:
        """Delete a balance operation by ID. And also update the balance of the account accordingly."""
        with self._conn.transaction():
            # step1 : get the previous amount and balance of the operation
            result = self._conn.execute(
                "SELECT amount, account_number, currency FROM balance_operations WHERE id = ?",
                [id],
            )
            previous_amount, account_number, currency = result.fetchone()
            # step2 : delete the operation
            self._conn.execute("DELETE FROM balance_operations WHERE id = ?", [id])
            # step3 : update the balance for all the operations with a bigger ID to remove the amount of the deleted operation
            self._conn.execute(
                """
                UPDATE balance_operations
                SET balance = balance - ?
                WHERE account_number = ? AND currency = ? AND id > ?
                """,
                [previous_amount, account_number, currency, id],
            )
            return True

    def update_operation_by_id(
        self,
        id: int,
        amount: float,
        title: str,
        operation_date: datetime,
        entry_type: EntryType,
    ) -> bool:
        """Update a balance operation by ID."""
        with self._conn.transaction():
            # step1 : get the previous amount and balance of the operation
            result = self._conn.execute(
                "SELECT amount, account_number, currency FROM balance_operations WHERE id = ?",
                [id],
            )
            # step2 : calculate the difference between the previous amount and the new amount
            previous_amount, account_number, currency = result.fetchone()
            difference = amount - previous_amount
            # step3 : update the operation with the new amount, title, operation_date and entry_type
            self._conn.execute(
                """
                UPDATE balance_operations
                SET amount = ?, title = ?, operation_date = ?, entry_type = ?
                WHERE id = ?
                """,
                [amount, title, operation_date, entry_type.value, id],
            )
            # step4 : update the balance of the operation with the new amount as well as all the other operations with a bigger ID to add the difference to the balance
            self._conn.execute(
                """
                UPDATE balance_operations
                SET balance = balance + ?
                WHERE account_number = ? AND currency = ? AND id >= ?
                """,
                [difference, account_number, currency, id],
            )
            return True

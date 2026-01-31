from dataclasses import dataclass

import polars as pl

from ...shared.models.assets import Cash
from ..database.connection import DatabaseConnection
from ..database.queries.cash import CashOperations


@dataclass
class CashOperationResult:
    """Result of a cash operation."""

    success: bool
    message: str


class CashService:
    """Service layer for cash operations."""

    def __init__(self):
        self._conn = DatabaseConnection().get_connection()
        self._cash_ops = CashOperations(self._conn)

    def add_cash(self, cash: Cash) -> CashOperationResult:
        """
        Add a new cash entry.

        Returns:
            CashOperationResult with success status and message
        """
        try:
            self._cash_ops.add_cash(
                bank=cash.bank,
                account_number=cash.account_number,
                currency=cash.currency.value,
                balance=cash.balance,
                last_updated=cash.last_updated,
            )
            return CashOperationResult(
                success=True,
                message=f"Added {cash.currency.value} {cash.balance:.2f} to {cash.bank} ({cash.account_number})",
            )
        except Exception as e:
            return CashOperationResult(
                success=False,
                message=f"Error adding cash: {str(e)}",
            )

    def update_cash(self, id: int, cash: Cash) -> CashOperationResult:
        """
        Update an existing cash entry.

        Returns:
            CashOperationResult with success status and message
        """
        try:
            self._cash_ops.update_cash(
                id=id,
                bank=cash.bank,
                account_number=cash.account_number,
                currency=cash.currency.value,
                balance=cash.balance,
                last_updated=cash.last_updated,
            )
            return CashOperationResult(
                success=True,
                message=f"Updated cash entry {id}",
            )
        except Exception as e:
            return CashOperationResult(
                success=False,
                message=f"Error updating cash: {str(e)}",
            )

    def delete_cash(self, id: int) -> CashOperationResult:
        """Delete a cash entry by ID."""
        try:
            self._cash_ops.delete_cash(id=id)
            return CashOperationResult(
                success=True,
                message=f"Deleted cash entry with ID {id}.",
            )
        except Exception as e:
            return CashOperationResult(
                success=False,
                message=f"Error deleting cash entry: {str(e)}",
            )

    def get_all_cash(self) -> pl.DataFrame:
        """Retrieve all cash entries from the database."""
        return self._cash_ops.get_cash()

    def get_cash_by_bank(self, bank: str) -> pl.DataFrame:
        """Retrieve all cash entries for a specific bank from the database."""
        return self._cash_ops.get_cash_by_bank(bank=bank)

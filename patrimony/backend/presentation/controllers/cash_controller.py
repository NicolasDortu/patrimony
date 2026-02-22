from datetime import datetime
from typing import Optional

from ...domain.entities import Currency
from .operation_result import OperationResult
from ..di_container import container


class CashController:
    """Controller for cash account operations."""

    @property
    def _cash_repo(self):
        """Get cash repository from DI container."""
        return container.cash_repository()

    def add_cash(
        self,
        bank: str,
        account_number: str,
        currency: Currency,
        balance: float,
        last_updated: Optional[datetime] = None,
    ) -> OperationResult:
        """Add new cash account.

        Args:
            bank: Bank name
            account_number: Account identifier
            currency: Currency enum
            balance: Current balance
            last_updated: Last update timestamp (defaults to now)

        Returns:
            CashOperationResult with success status and new ID
        """
        try:
            if last_updated is None:
                last_updated = datetime.now()

            cash_id = self._cash_repo.add_cash(
                bank=bank,
                account_number=account_number,
                currency=currency,
                balance=balance,
                last_updated=last_updated,
            )

            return OperationResult(
                success=True,
                message="Bank account added successfully",
                data={"id": cash_id},
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to add bank account: {str(e)}",
            )

    def update_cash(
        self,
        id: int,
        bank: str,
        account_number: str,
        currency: Currency,
        balance: float,
        last_updated: Optional[datetime] = None,
    ) -> OperationResult:
        """Update existing cash account.

        Args:
            id: Cash account ID
            bank: Bank name
            account_number: Account identifier
            currency: Currency enum
            balance: Current balance
            last_updated: Last update timestamp (defaults to now)

        Returns:
            OperationResult with success status
        """
        try:
            if last_updated is None:
                last_updated = datetime.now()

            self._cash_repo.update_cash(
                id=id,
                bank=bank,
                account_number=account_number,
                currency=currency,
                balance=balance,
                last_updated=last_updated,
            )

            return OperationResult(
                success=True,
                message=f"Account {id} updated successfully",
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to update account {id}: {str(e)}",
            )

    def delete_cash(self, id: int) -> OperationResult:
        """Delete cash account by ID.

        Args:
            id: Cash account ID

        Returns:
            OperationResult with success status
        """
        try:
            self._cash_repo.delete(id)
            return OperationResult(
                success=True,
                message=f"Account {id} deleted successfully",
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to delete account {id}: {str(e)}",
            )

    def get_all_cash(self) -> list[dict]:
        """Get all cash accounts.

        Returns:
            List of cash account dictionaries
        """
        df = self._cash_repo.get_all()
        return df.to_dicts() if df is not None else []

    def get_cash_by_id(self, id: int) -> Optional[dict]:
        """Get single cash account by ID.

        Args:
            id: Cash account ID

        Returns:
            Cash account dictionary or None if not found
        """
        df = self._cash_repo.get_by_id(id)
        if df is not None:
            return df.to_dicts()[0]
        return None

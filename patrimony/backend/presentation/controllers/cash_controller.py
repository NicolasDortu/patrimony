from datetime import datetime
from typing import Optional

from ...domain.entities import Currency, EntryType
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
        last_updated: Optional[datetime] = None,
    ) -> OperationResult:
        """Update existing cash account.

        Args:
            id: Cash account ID
            bank: Bank name
            account_number: Account identifier
            currency: Currency enum
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

    def post_operation_balance(
        self,
        account_number: str,
        currency: Currency,
        amount: float,
        title: str,
        operation_date: datetime,
        entry_type: EntryType,
    ) -> OperationResult:
        """Record a cash operation on the balance."""
        try:
            operation = self._cash_repo.operation_balance(
                account_number=account_number,
                currency=currency,
                amount=amount,
                title=title,
                operation_date=operation_date,
                entry_type=entry_type,
            )
            if operation[0]:
                return OperationResult(success=True, message=operation[1])
            else:
                return OperationResult(
                    success=False,
                    message=operation[1],
                )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to record cash operation: {str(e)}",
            )

    def get_operations_by_account(self, account_number: str) -> list[dict]:
        """Get all balance operations for a specific account."""
        try:
            df = self._cash_repo.get_operations_by_account(account_number)
            return df.to_dicts() if df is not None else []
        except Exception as e:
            print(f"Failed to get operations for account {account_number}: {str(e)}")
            return []

    def get_all_operations(self) -> list[dict]:
        """Get all balance operations."""
        try:
            df = self._cash_repo.get_all_operations()
            return df.to_dicts() if df is not None else []
        except Exception as e:
            print(f"Failed to get all operations: {str(e)}")
            return []

    def get_balance(self, account_number: str, currency: Currency) -> float:
        """Get current balance for specific account and currency."""
        try:
            balance = self._cash_repo.get_balance(account_number, currency)
            return balance if balance is not None else 0.0
        except Exception as e:
            print(f"Failed to get balance for account {account_number}: {str(e)}")
            return 0.0

    def update_operation_by_id(
        self,
        id: int,
        amount: float,
        title: str,
        operation_date: datetime,
        entry_type: EntryType,
    ) -> OperationResult:
        """Update a balance operation by ID."""
        try:
            result = self._cash_repo.update_operation_by_id(
                id=id,
                amount=amount,
                title=title,
                operation_date=operation_date,
                entry_type=entry_type,
            )
            if result:
                return OperationResult(
                    success=True, message="Operation updated successfully"
                )
            else:
                return OperationResult(
                    success=False,
                    message="Failed to update operation",
                )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to update cash operation {id}: {str(e)}",
            )

    def delete_operation_by_id(self, id: int) -> OperationResult:
        """Delete a balance operation by ID."""
        try:
            result = self._cash_repo.delete_operation_by_id(id)
            if result:
                return OperationResult(
                    success=True, message="Operation deleted successfully"
                )
            else:
                return OperationResult(
                    success=False,
                    message="Failed to delete operation",
                )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to delete cash operation {id}: {str(e)}",
            )

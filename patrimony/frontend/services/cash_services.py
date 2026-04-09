"""Frontend services for cash operations."""

import logging
from datetime import datetime
from typing import Optional

from ...backend.domain.entities import Currency, EntryType
from ...backend.presentation.di_container import container
from .models import OperationResult

logger = logging.getLogger(__name__)


class CashService:
    """Frontend service for cash operations."""

    @staticmethod
    def add_cash(
        bank: str,
        account_number: str,
        currency: Currency,
        balance: float,
        last_updated: Optional[datetime] = None,
    ) -> OperationResult:
        """Add new cash account."""
        try:
            if last_updated is None:
                last_updated = datetime.now()
            repo = container.cash_repository()
            cash_id = repo.add_cash(
                bank=bank,
                account_number=account_number,
                currency=currency,
                last_updated=last_updated,
            )
            if balance:
                repo.add_operation_balance(
                    account_number=account_number,
                    amount=balance,
                    title="Initial balance",
                    operation_date=last_updated,
                    entry_type=EntryType.MANUAL,
                )
            return OperationResult(
                success=True,
                message="Bank account added successfully",
                data={"id": cash_id},
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to add bank account: {e}",
            )

    @staticmethod
    def update_cash(
        bank: str,
        account_number: str,
        currency: Currency,
        last_updated: Optional[datetime] = None,
    ) -> OperationResult:
        """Update existing cash account."""
        try:
            if last_updated is None:
                last_updated = datetime.now()
            container.cash_repository().update_cash(
                bank=bank,
                account_number=account_number,
                currency=currency,
                last_updated=last_updated,
            )
            return OperationResult(
                success=True,
                message=f"Account {account_number} updated successfully",
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to update account {account_number}: {e}",
            )

    @staticmethod
    def delete_cash(id: int) -> OperationResult:
        """Delete cash account."""
        try:
            container.cash_repository().delete(id)
            return OperationResult(
                success=True,
                message=f"Account {id} deleted successfully",
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to delete account {id}: {e}",
            )

    @staticmethod
    def get_all_cash() -> list[dict]:
        """Get all cash accounts."""
        df = container.cash_repository().get_all()
        return df.to_dicts() if df is not None else []

    @staticmethod
    def add_operation_balance(
        account_number: str,
        amount: float,
        title: str,
        operation_date: datetime,
        entry_type: EntryType = EntryType.MANUAL,
        category: str = "Uncategorized",
    ) -> OperationResult:
        """Make an operation on cash balance."""
        try:
            op_id = container.cash_repository().add_operation_balance(
                account_number=account_number,
                amount=amount,
                title=title,
                operation_date=operation_date,
                entry_type=entry_type,
                category=category,
            )
            return OperationResult(
                success=True,
                message=f"Operation successful, id: {op_id}",
                data={"id": op_id},
            )
        except Exception as e:
            logger.error("Failed to record cash operation: %s", e)
            return OperationResult(
                success=False,
                message=f"Failed to record cash operation: {e}",
            )

    @staticmethod
    def get_operations_by_account(account_number: str) -> list[dict]:
        """Get balance operations for specific account."""
        try:
            df = container.cash_repository().get_operations_by_account(account_number)
            return df.to_dicts() if df is not None else []
        except Exception as e:
            logger.error(
                "Failed to get operations for account %s: %s", account_number, e
            )
            return []

    @staticmethod
    def get_all_operations() -> list[dict]:
        """Get all balance operations."""
        try:
            df = container.cash_repository().get_all_operations()
            return df.to_dicts() if df is not None else []
        except Exception as e:
            logger.error("Failed to get all operations: %s", e)
            return []

    @staticmethod
    def update_operation_by_id(
        id: int,
        amount: float,
        title: str,
        operation_date: datetime,
        entry_type: EntryType,
        category: str = "Uncategorized",
    ) -> OperationResult:
        """Update a balance operation by ID."""
        try:
            container.cash_repository().update_operation_by_id(
                id=id,
                amount=amount,
                title=title,
                operation_date=operation_date,
                entry_type=entry_type,
                category=category,
            )
            return OperationResult(
                success=True, message="Operation updated successfully"
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to update cash operation {id}: {e}",
            )

    @staticmethod
    def delete_operation_by_id(id: int) -> OperationResult:
        """Delete a balance operation by ID."""
        try:
            container.cash_repository().delete_operation_by_id(id)
            return OperationResult(
                success=True, message="Operation deleted successfully"
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to delete cash operation {id}: {e}",
            )

    @staticmethod
    def get_balance(account_number: str) -> float:
        """Get current balance for specific account."""
        try:
            balance = container.cash_repository().get_balance(account_number)
            return balance if balance is not None else 0.0
        except Exception as e:
            logger.error("Failed to get balance for account %s: %s", account_number, e)
            return 0.0

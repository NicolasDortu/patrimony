"""Frontend services for cash operations."""

import logging
from datetime import datetime
from typing import Optional

from ...backend.domain.entities import Currency, EntryType
from ...backend.application import container
from .models import operation_result, safe_query

logger = logging.getLogger(__name__)


class CashService:
    """Frontend service for cash operations."""

    @staticmethod
    @operation_result(
        failure="Failed to add bank account", success="Bank account added successfully"
    )
    def add_cash(
        bank: str,
        account_number: str,
        currency: Currency,
        balance: float,
        last_updated: Optional[datetime] = None,
    ):
        return container.cash_use_cases().add_cash(
            bank=bank,
            account_number=account_number,
            currency=currency,
            balance=balance,
            last_updated=last_updated,
        )

    @staticmethod
    @operation_result(
        failure="Failed to update account", success="Account updated successfully"
    )
    def update_cash(
        bank: str,
        account_number: str,
        currency: Currency,
        last_updated: Optional[datetime] = None,
    ):
        container.cash_use_cases().update_cash(
            bank=bank,
            account_number=account_number,
            currency=currency,
            last_updated=last_updated,
        )

    @staticmethod
    @operation_result(
        failure="Failed to delete account", success="Account deleted successfully"
    )
    def delete_cash(id: int):
        container.cash_use_cases().delete_cash(id)

    @staticmethod
    @safe_query([])
    def get_all_cash() -> list[dict]:
        return container.cash_use_cases().get_all_cash()

    @staticmethod
    @operation_result(
        failure="Failed to record cash operation",
        success="Operation recorded successfully",
    )
    def add_operation_balance(
        account_number: str,
        amount: float,
        title: str,
        operation_date: datetime,
        entry_type: EntryType = EntryType.MANUAL,
        category: str = "Uncategorized",
    ):
        return container.cash_use_cases().add_operation_balance(
            account_number=account_number,
            amount=amount,
            title=title,
            operation_date=operation_date,
            entry_type=entry_type,
            category=category,
        )

    @staticmethod
    @safe_query([])
    def get_operations_by_account(account_number: str) -> list[dict]:
        return container.cash_use_cases().get_operations_by_account(account_number)

    @staticmethod
    @safe_query([])
    def get_all_operations() -> list[dict]:
        return container.cash_use_cases().get_all_operations()

    @staticmethod
    @operation_result(
        failure="Failed to update cash operation",
        success="Operation updated successfully",
    )
    def update_operation_by_id(
        id: int,
        amount: float,
        title: str,
        operation_date: datetime,
        entry_type: EntryType,
        category: str = "Uncategorized",
    ):
        container.cash_use_cases().update_operation_by_id(
            id=id,
            amount=amount,
            title=title,
            operation_date=operation_date,
            entry_type=entry_type,
            category=category,
        )

    @staticmethod
    @operation_result(
        failure="Failed to delete cash operation",
        success="Operation deleted successfully",
    )
    def delete_operation_by_id(id: int):
        container.cash_use_cases().delete_operation_by_id(id)

    @staticmethod
    @safe_query(0.0)
    def get_balance(account_number: str) -> float:
        return container.cash_use_cases().get_balance(account_number)

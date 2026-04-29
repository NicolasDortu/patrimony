"""Use cases for cash operations."""

from datetime import datetime

from ..domain.entities import Currency, EntryType
from ..domain.repositories import CashRepository


class CashUseCases:
    """Application use cases for cash account CRUD and balance operations."""

    def __init__(self, cash_repo: CashRepository):
        self._repo = cash_repo

    def add_cash(
        self,
        bank: str,
        account_number: str,
        currency: Currency,
        balance: float,
        last_updated: datetime | None = None,
    ) -> None:
        """Add a new cash account with optional initial balance."""
        if last_updated is None:
            last_updated = datetime.now()
        self._repo.add_cash(
            bank=bank,
            account_number=account_number,
            currency=currency,
            last_updated=last_updated,
        )
        if balance:
            self._repo.add_operation_balance(
                account_number=account_number,
                amount=balance,
                title="Initial balance",
                operation_date=last_updated,
                entry_type=EntryType.MANUAL,
            )

    def update_cash(
        self,
        bank: str,
        account_number: str,
        currency: Currency,
        last_updated: datetime | None = None,
    ) -> None:
        if last_updated is None:
            last_updated = datetime.now()
        self._repo.update_cash(
            bank=bank,
            account_number=account_number,
            currency=currency,
            last_updated=last_updated,
        )

    def rename_account(self, old_account_number: str, new_account_number: str) -> None:
        self._repo.rename_account(old_account_number, new_account_number)

    def delete_cash(self, id: int) -> None:
        self._repo.delete(id)

    def get_all_cash(self) -> list[dict]:
        df = self._repo.get_all()
        return df.to_dicts()

    def add_operation_balance(
        self,
        account_number: str,
        amount: float,
        title: str,
        operation_date: datetime,
        entry_type: EntryType = EntryType.MANUAL,
        category: str = "Uncategorized",
    ) -> None:
        """Record a cash operation."""
        self._repo.add_operation_balance(
            account_number=account_number,
            amount=amount,
            title=title,
            operation_date=operation_date,
            entry_type=entry_type,
            category=category,
        )

    def get_operations_by_account(self, account_number: str) -> list[dict]:
        df = self._repo.get_operations_by_account(account_number)
        return df.to_dicts()

    def get_all_operations(self) -> list[dict]:
        df = self._repo.get_all_operations()
        return df.to_dicts()

    def update_operation_by_id(
        self,
        id: int,
        amount: float,
        title: str,
        operation_date: datetime,
        entry_type: EntryType,
        category: str = "Uncategorized",
    ) -> None:
        self._repo.update_operation_by_id(
            id=id,
            amount=amount,
            title=title,
            operation_date=operation_date,
            entry_type=entry_type,
            category=category,
        )

    def delete_operation_by_id(self, id: int) -> None:
        self._repo.delete_operation_by_id(id)

    def get_balance(self, account_number: str) -> float:
        balance = self._repo.get_balance(account_number)
        return balance if balance is not None else 0.0

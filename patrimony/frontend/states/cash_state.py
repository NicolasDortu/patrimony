from datetime import datetime
from typing import Union

import reflex as rx

from ..services import CashService, Currency


class CashTableState(rx.State):
    """State for the cash table."""

    items: list[dict] = []

    search_value: str = ""
    sort_value: str = ""
    sort_reverse: bool = False

    total_items: int = 0
    offset: int = 0
    limit: int = 12  # Number of rows per page

    # Edit dialog state
    edit_id: int = 0
    edit_bank: str = ""
    edit_account_number: str = ""
    edit_currency: str = "EUR"
    edit_balance: float = 0.0

    @rx.event
    def set_search_value(self, value: str) -> None:
        self.search_value = value

    @rx.event
    def set_sort_value(self, value: str) -> None:
        self.sort_value = value

    @rx.var
    def filtered_sorted_items(self) -> list[dict]:
        items = self.items

        # Filter items based on selected sort column
        if self.sort_value:
            if self.sort_value == "balance":
                items = sorted(
                    items,
                    key=lambda item: float(item.get(self.sort_value, 0)),
                    reverse=self.sort_reverse,
                )
            else:
                items = sorted(
                    items,
                    key=lambda item: str(item.get(self.sort_value, "")).lower(),
                    reverse=self.sort_reverse,
                )

        # Filter items based on search value
        if self.search_value:
            search_value = self.search_value.lower()
            items = [
                item
                for item in items
                if any(
                    search_value in str(item.get(attr, "")).lower()
                    for attr in ["bank", "account_number", "currency"]
                )
            ]

        return items

    @rx.var
    def page_number(self) -> int:
        return (self.offset // self.limit) + 1

    @rx.var
    def total_pages(self) -> int:
        return max(
            1,
            (self.total_items // self.limit)
            + (1 if self.total_items % self.limit else 0),
        )

    @rx.var(initial_value=[])
    def get_current_page(self) -> list[dict]:
        start_index = self.offset
        end_index = start_index + self.limit
        return self.filtered_sorted_items[start_index:end_index]

    def prev_page(self) -> None:
        if self.page_number > 1:
            self.offset -= self.limit

    def next_page(self) -> None:
        if self.page_number < self.total_pages:
            self.offset += self.limit

    def first_page(self) -> None:
        self.offset = 0

    def last_page(self) -> None:
        self.offset = (self.total_pages - 1) * self.limit

    @rx.event
    def load_entries(self) -> None:
        """Load all cash entries from the database."""
        cash_entries = CashService.get_all_cash()
        # Enrich each entry with its current balance
        for entry in cash_entries:
            try:
                currency_str = entry.get("currency", "EUR")
                try:
                    currency = Currency[currency_str]
                except KeyError:
                    currency = Currency.EUR
                balance = CashService.get_balance(
                    entry.get("account_number", ""),
                    currency,
                )
                entry["balance"] = balance if balance is not None else 0.0
            except Exception as e:
                print(
                    f"Failed to get balance for account {entry.get('account_number', '')}: {e}"
                )
                entry["balance"] = 0.0
        self.items = cash_entries
        self.total_items = len(self.items)

    def toggle_sort(self) -> None:
        self.sort_reverse = not self.sort_reverse
        self.load_entries()

    @rx.event
    def add_cash_entry(self, form_data: dict) -> None:
        """Add a new cash entry from form data."""
        currency_str = form_data.get("currency", "EUR")
        try:
            currency = Currency[currency_str]
        except KeyError:
            currency = Currency.EUR

        result = CashService.add_cash(
            bank=form_data.get("bank", ""),
            account_number=form_data.get("account_number", ""),
            currency=currency,
            balance=float(form_data.get("balance", 0)),
            last_updated=datetime.now(),
        )

        if result.success:
            self.load_entries()
            return rx.toast.success(result.message, position="top-center")
        else:
            return rx.toast.error(result.message, position="top-center")

    @rx.event
    def open_edit_dialog(self, item: dict) -> None:
        """Open the edit dialog with the item's current values."""
        self.edit_id = item.get("id", 0)
        self.edit_bank = item.get("bank", "")
        self.edit_account_number = item.get("account_number", "")
        self.edit_currency = item.get("currency", "EUR")
        self.edit_balance = float(item.get("balance", 0))

    @rx.event
    def set_edit_balance(self, value: str) -> None:
        """Set the edit balance value."""
        try:
            self.edit_balance = float(value) if value else 0.0
        except ValueError:
            self.edit_balance = 0.0

    @rx.event
    def update_cash_entry(self, form_data: dict) -> None:
        """Update an existing cash entry."""
        currency_str = form_data.get("currency", self.edit_currency)
        try:
            currency = Currency[currency_str]
        except KeyError:
            currency = Currency.EUR

        result = CashService.update_cash(
            id=self.edit_id,
            bank=form_data.get("bank", self.edit_bank),
            account_number=form_data.get("account_number", self.edit_account_number),
            currency=currency,
            last_updated=datetime.now(),
        )

        if result.success:
            self.load_entries()
            return rx.toast.success(result.message, position="top-center")
        else:
            return rx.toast.error(result.message, position="top-center")

    @rx.event
    def delete_cash_entry(self, id: Union[int, dict]) -> None:
        """Delete a cash entry by ID."""
        if isinstance(id, dict):
            id = id.get("id", 0)

        result = CashService.delete_cash(id)

        if result.success:
            self.load_entries()
            return rx.toast.success(result.message, position="top-center")
        else:
            return rx.toast.error(result.message, position="top-center")

    @rx.event
    def open_operations_view(self, account_number: str, currency: str):
        """Navigate to the cash operations page for a specific account."""
        return rx.redirect(
            f"/cash_operations?account_number={account_number}&currency={currency}"
        )

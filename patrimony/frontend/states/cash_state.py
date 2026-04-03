import logging
from datetime import datetime
from typing import Union

import reflex as rx

from ..services import CashService, Currency
from ..utils import export_csv
from ..utils import get_pie_color
from .aggregation_helpers import (
    aggregate_expenses_by_category,
    aggregate_monthly_income_expense,
)
from .mixins import PaginationMixin, SearchSortMixin, apply_sort_and_search
from .spreadsheet_mixin import SpreadsheetMixin

logger = logging.getLogger(__name__)


class CashTableState(SpreadsheetMixin, SearchSortMixin, PaginationMixin, rx.State):
    """State for the cash table."""

    items: list[dict] = []
    is_loading: bool = False

    @rx.var
    def filtered_sorted_items(self) -> list[dict]:
        return apply_sort_and_search(
            self.items,
            self.sort_value,
            self.sort_reverse,
            self.search_value,
            numeric_sort_fields=["balance"],
            search_fields=["bank", "account_number", "currency"],
        )

    @rx.var(initial_value=[])
    def get_current_page(self) -> list[dict]:
        return self.filtered_sorted_items[self.offset : self.offset + self.limit]

    @rx.event
    async def on_page_load(self):
        """Handle page load with loading indicator."""
        self.is_loading = True
        yield
        self.load_entries()
        self.is_loading = False

    @rx.event
    def load_entries(self) -> None:
        """Load all cash entries from the database."""
        cash_entries = CashService.get_all_cash()
        # Enrich each entry with its current balance
        for entry in cash_entries:
            try:
                balance = CashService.get_balance(entry.get("account_number", ""))
                entry["balance"] = balance if balance is not None else 0.0
            except Exception as e:
                logger.warning(
                    "Failed to get balance for account %s: %s",
                    entry.get("account_number", ""),
                    e,
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
    def export_csv(self):
        """Export cash entries to CSV."""
        columns = ["bank", "account_number", "currency", "balance"]
        return export_csv(self.items, columns, "cash.csv")

    @rx.event
    def open_operations_view(self, account_number: str, currency: str):
        """Navigate to the cash operations page for a specific account."""
        return rx.redirect(
            f"/cash_operations?account_number={account_number}&currency={currency}"
        )

    @rx.var
    def all_operations_expense_data(self) -> list[dict]:
        """Aggregate all operations across all accounts into monthly income vs expense."""
        return aggregate_monthly_income_expense(CashService.get_all_operations())

    @rx.var
    def all_operations_category_data(self) -> list[dict]:
        """Aggregate expenses by category across all accounts."""
        return aggregate_expenses_by_category(CashService.get_all_operations())

    @rx.var
    def balance_by_account_data(self) -> list[dict]:
        """Balance distribution across all accounts for pie chart."""
        return [
            {
                "name": f"{item.get('bank', '')} - {item.get('account_number', '')}",
                "value": round(float(item.get("balance", 0)), 2),
                "fill": get_pie_color(i),
            }
            for i, item in enumerate(self.items)
            if float(item.get("balance", 0)) > 0
        ]

    # ── Spreadsheet mode ──

    @rx.var
    def spreadsheet_columns(self) -> list[dict]:
        return [
            {"title": "Bank", "type": "str"},
            {"title": "Account Number", "type": "str"},
            {"title": "Currency", "type": "str"},
            {"title": "Balance", "type": "float", "editable": False},
        ]

    def _load_spreadsheet_rows(self) -> tuple[list[list], list]:
        cash_entries = CashService.get_all_cash()
        for entry in cash_entries:
            try:
                balance = CashService.get_balance(entry.get("account_number", ""))
                entry["balance"] = balance if balance is not None else 0.0
            except Exception:
                entry["balance"] = 0.0
        data = [
            [
                e.get("bank", ""),
                e.get("account_number", ""),
                e.get("currency", "EUR"),
                e.get("balance", 0.0),
            ]
            for e in cash_entries
        ]
        ids = [e.get("account_number", "") for e in cash_entries]
        return data, ids

    def _save_spreadsheet_row(self, row, index, rid, is_new):
        bank = str(row[0]).strip()
        account_number = str(row[1]).strip()
        currency_str = str(row[2]).strip().upper() or "EUR"
        if not account_number:
            return "skip"
        try:
            currency = Currency[currency_str]
        except KeyError:
            currency = Currency.EUR
        if is_new:
            CashService.add_cash(
                bank=bank,
                account_number=account_number,
                currency=currency,
                balance=0.0,
                last_updated=datetime.now(),
            )
        else:
            CashService.update_cash(
                bank=bank,
                account_number=account_number,
                currency=currency,
                last_updated=datetime.now(),
            )
        return None

    def _delete_spreadsheet_row(self, rid):
        if rid:
            CashService.delete_cash(rid)

    async def _after_spreadsheet_save(self):
        self.load_entries()

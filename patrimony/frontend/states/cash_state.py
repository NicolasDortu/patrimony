from datetime import datetime
from typing import Union

import reflex as rx

from ..services import CashService, Currency
from .mixins import PaginationMixin
from .spreadsheet_mixin import SpreadsheetMixin

# Distinct color palette for pie chart slices
_PIE_COLORS = [
    "var(--blue-9)",
    "var(--orange-9)",
    "var(--green-9)",
    "var(--purple-9)",
    "var(--red-9)",
    "var(--cyan-9)",
    "var(--yellow-9)",
    "var(--pink-9)",
    "var(--teal-9)",
    "var(--indigo-9)",
    "var(--lime-9)",
    "var(--amber-9)",
]


class CashTableState(SpreadsheetMixin, PaginationMixin, rx.State):
    """State for the cash table."""

    items: list[dict] = []

    search_value: str = ""
    sort_value: str = ""
    sort_reverse: bool = False

    # Chart view
    chart_view: bool = False

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

    @rx.var(initial_value=[])
    def get_current_page(self) -> list[dict]:
        start_index = self.offset
        end_index = start_index + self.limit
        return self.filtered_sorted_items[start_index:end_index]

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

    @rx.event
    def toggle_chart_view(self):
        self.chart_view = not self.chart_view

    @rx.var
    def all_operations_expense_data(self) -> list[dict]:
        """Aggregate all operations across all accounts into monthly income vs expense."""
        all_ops = CashService.get_all_operations()
        monthly: dict[str, dict[str, float]] = {}
        for op in all_ops:
            date_str = str(op.get("operation_date", ""))[:7]
            if not date_str:
                continue
            if date_str not in monthly:
                monthly[date_str] = {"month": date_str, "income": 0.0, "expense": 0.0}
            amount = float(op.get("amount", 0))
            if amount >= 0:
                monthly[date_str]["income"] += amount
            else:
                monthly[date_str]["expense"] += abs(amount)
        result = sorted(monthly.values(), key=lambda x: x["month"])
        return [
            {
                "month": m["month"],
                "income": round(m["income"], 2),
                "expense": round(m["expense"], 2),
            }
            for m in result
        ]

    @rx.var
    def all_operations_category_data(self) -> list[dict]:
        """Aggregate expenses by category across all accounts."""
        all_ops = CashService.get_all_operations()
        categories: dict[str, float] = {}
        for op in all_ops:
            amount = float(op.get("amount", 0))
            if amount >= 0:
                continue
            cat = op.get("category", "Uncategorized") or "Uncategorized"
            categories[cat] = categories.get(cat, 0.0) + abs(amount)
        return [
            {"name": k, "value": round(v, 2), "fill": _PIE_COLORS[i % len(_PIE_COLORS)]}
            for i, (k, v) in enumerate(
                sorted(categories.items(), key=lambda x: x[1], reverse=True)
            )
        ]

    @rx.var
    def balance_by_account_data(self) -> list[dict]:
        """Balance distribution across all accounts for pie chart."""
        return [
            {
                "name": f"{item.get('bank', '')} - {item.get('account_number', '')}",
                "value": round(float(item.get("balance", 0)), 2),
                "fill": _PIE_COLORS[i % len(_PIE_COLORS)],
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

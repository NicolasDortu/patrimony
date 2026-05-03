"""State management for cash operations (deposits/expenses per account)."""

import reflex as rx

from ..services import CashService, EntryType
from ..utils import export_csv, parse_form_date
from .aggregation_helpers import (
    aggregate_expenses_by_category,
    aggregate_monthly_income_expense,
)
from .mixins import (
    AddDialogMixin,
    PaginationMixin,
    SearchSortMixin,
    apply_sort_and_search,
)
from .spreadsheet_helpers import cell_float, cell_iso_datetime, cell_str, fmt_date_cell
from .spreadsheet_mixin import SpreadsheetMixin


class CashOperationsState(
    SpreadsheetMixin, SearchSortMixin, PaginationMixin, AddDialogMixin, rx.State
):
    """State for cash operations table (per-account view)."""

    items: list[dict] = []
    account_number: str = ""
    account_currency: str = "EUR"
    is_loading: bool = False

    @rx.event
    async def on_page_load(self):
        """Handle page load - get account_number from URL and load operations."""
        self.is_loading = True
        yield
        account_number = self.router.url.query_parameters.get("account_number", "")
        currency = self.router.url.query_parameters.get("currency", "EUR")
        self.account_number = account_number
        self.account_currency = currency
        self.load_entries()
        self.is_loading = False

    @rx.event
    def set_account_number(self, account_number: str) -> None:
        """Set the account number for detail view navigation."""
        self.account_number = account_number

    @rx.var
    def filtered_sorted_items(self) -> list[dict]:
        return apply_sort_and_search(
            self.items,
            self.sort_value,
            self.sort_reverse,
            self.search_value,
            numeric_sort_fields=["amount", "balance"],
            search_fields=["title", "operation_date", "amount"],
        )

    @rx.var(initial_value=[])
    def get_current_page(self) -> list[dict]:
        return self.filtered_sorted_items[self.offset : self.offset + self.limit]

    @rx.var
    def expense_earning_data(self) -> list[dict]:
        """Aggregate operations into income vs expense totals by month."""
        return aggregate_monthly_income_expense(self.items)

    @rx.var
    def category_expense_data(self) -> list[dict]:
        """Aggregate expenses by category for pie chart."""
        return aggregate_expenses_by_category(self.items)

    @rx.event
    def load_entries(self) -> None:
        """Load all operations for the current account."""
        operations = CashService.get_operations_by_account(self.account_number)
        for op in operations:
            d = op.get("operation_date")
            if d is not None:
                # Trim microseconds from "2026-04-18 12:11:05.107074".
                op["operation_date"] = str(d).split(".", 1)[0]
        self.items = operations
        self.total_items = len(self.items)

    def toggle_sort(self) -> None:
        self.sort_reverse = not self.sort_reverse
        self.load_entries()

    @rx.event
    def add_operation(self, form_data: dict) -> None:
        """Add a new cash operation from form data."""
        amount = float(form_data.get("amount", 0))
        title = form_data.get("title", "")
        category = form_data.get("category", "Uncategorized")
        operation_date_str = form_data.get("operation_date", "")
        operation_date = parse_form_date(operation_date_str)

        result = CashService.add_operation_balance(
            account_number=self.account_number,
            amount=amount,
            title=title,
            operation_date=operation_date,
            entry_type=EntryType.MANUAL,
            category=category,
        )

        if result.success:
            self.load_entries()
            self.add_dialog_open = False
            return rx.toast.success(result.message, position="top-center")
        else:
            return rx.toast.error(result.message, position="top-center")

    @rx.event
    def delete_operation(self, id: int) -> None:
        """Delete a cash operation by ID."""
        result = CashService.delete_operation_by_id(id)
        if result.success:
            self.load_entries()
            return rx.toast.success(result.message, position="top-center")
        else:
            return rx.toast.error(result.message, position="top-center")

    @rx.event
    def export_csv(self):
        """Export operations to CSV."""
        operations = CashService.get_operations_by_account(self.account_number)
        if not operations:
            return rx.toast.error("No operations to export", position="top-center")

        columns = [
            "id",
            "account_number",
            "currency",
            "amount",
            "balance",
            "title",
            "operation_date",
            "entry_type",
        ]
        return export_csv(
            operations,
            columns,
            f"operations_{self.account_number}.csv",
        )

    # ── Spreadsheet mode ──

    @rx.var
    def spreadsheet_columns(self) -> list[dict]:
        return [
            {"title": "Title", "type": "str", "grow": 1},
            {"title": "Amount", "type": "float", "grow": 1},
            {"title": "Date", "type": "str", "grow": 1},
            {"title": "Category", "type": "str", "grow": 1},
            {"title": "Balance", "type": "float", "editable": False, "grow": 1},
        ]

    def _load_spreadsheet_rows(self) -> tuple[list[list], list]:
        operations = CashService.get_operations_by_account(self.account_number)
        data = [
            [
                op.get("title", ""),
                op.get("amount", 0.0),
                fmt_date_cell(op.get("operation_date", "")),
                op.get("category", "Uncategorized"),
                op.get("balance", 0.0),
            ]
            for op in operations
        ]
        ids = [op.get("id") for op in operations]
        return data, ids

    def _save_spreadsheet_row(self, row, index, rid, is_new):
        title = cell_str(row[0], default="Operation")
        amount = cell_float(row[1])
        category = cell_str(row[3], default="Uncategorized")
        operation_date = cell_iso_datetime(row[2])
        if is_new:
            if amount == 0.0 and title == "Operation":
                return "skip"
            CashService.add_operation_balance(
                account_number=self.account_number,
                amount=amount,
                title=title,
                operation_date=operation_date,
                entry_type=EntryType.MANUAL,
                category=category,
            )
        else:
            CashService.update_operation_by_id(
                id=rid,
                amount=amount,
                title=title,
                operation_date=operation_date,
                entry_type=EntryType.MANUAL,
                category=category,
            )
        return None

    def _delete_spreadsheet_row(self, rid):
        CashService.delete_operation_by_id(rid)

    async def _after_spreadsheet_save(self):
        self.load_entries()

"""State management for cash operations (deposits/expenses per account)."""

from datetime import datetime

import reflex as rx

from ..services import CashService, EntryType
from .mixins import PaginationMixin
from .spreadsheet_mixin import SpreadsheetMixin

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


class CashOperationsState(SpreadsheetMixin, PaginationMixin, rx.State):
    """State for cash operations table (per-account view)."""

    items: list[dict] = []
    account_number: str = ""
    account_currency: str = "EUR"

    search_value: str = ""
    sort_value: str = ""
    sort_reverse: bool = False

    # Chart view
    chart_view: bool = False

    @rx.event
    def on_page_load(self) -> None:
        """Handle page load - get account_number from URL and load operations."""
        account_number = self.router.url.query_parameters.get("account_number", "")
        currency = self.router.url.query_parameters.get("currency", "EUR")
        self.account_number = account_number
        self.account_currency = currency
        self.load_entries()

    @rx.event
    def set_account_number(self, account_number: str) -> None:
        """Set the account number for detail view navigation."""
        self.account_number = account_number

    @rx.event
    def set_search_value(self, value: str) -> None:
        self.search_value = value

    @rx.event
    def set_sort_value(self, value: str) -> None:
        self.sort_value = value

    @rx.var
    def filtered_sorted_items(self) -> list[dict]:
        items = self.items

        # Sort items based on selected column
        if self.sort_value:
            if self.sort_value in ["amount", "balance"]:
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
                    for attr in ["title", "operation_date", "amount"]
                )
            ]

        return items

    @rx.var(initial_value=[])
    def get_current_page(self) -> list[dict]:
        start_index = self.offset
        end_index = start_index + self.limit
        return self.filtered_sorted_items[start_index:end_index]

    @rx.event
    def toggle_chart_view(self):
        self.chart_view = not self.chart_view

    @rx.var
    def expense_earning_data(self) -> list[dict]:
        """Aggregate operations into income vs expense totals by month."""
        monthly: dict[str, dict[str, float]] = {}
        for op in self.items:
            date_str = str(op.get("operation_date", ""))[:7]  # YYYY-MM
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
    def category_expense_data(self) -> list[dict]:
        """Aggregate expenses by category for pie chart."""
        categories: dict[str, float] = {}
        for op in self.items:
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

    @rx.event
    def load_entries(self) -> None:
        """Load all operations for the current account."""
        operations = CashService.get_operations_by_account(self.account_number)
        self.items = operations
        self.total_items = len(self.items)

    def toggle_sort(self) -> None:
        self.sort_reverse = not self.sort_reverse
        self.load_entries()

    @rx.event
    def add_operation(self, form_data: dict) -> None:
        """Add a new cash operation from form data."""
        try:
            amount = float(form_data.get("amount", 0))
            title = form_data.get("title", "")
            category = form_data.get("category", "Uncategorized")
            operation_date_str = form_data.get("operation_date", "")

            if operation_date_str:
                operation_date = datetime.fromisoformat(operation_date_str)
            else:
                operation_date = datetime.now()

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
                return rx.toast.success(result.message, position="top-center")
            else:
                return rx.toast.error(result.message, position="top-center")
        except Exception as e:
            return rx.toast.error(
                f"Failed to add operation: {str(e)}", position="top-center"
            )

    @rx.event
    def delete_operation(self, id: int) -> None:
        """Delete a cash operation by ID."""
        try:
            result = CashService.delete_operation_by_id(id)
            if result.success:
                self.load_entries()
                return rx.toast.success(result.message, position="top-center")
            else:
                return rx.toast.error(result.message, position="top-center")
        except Exception as e:
            return rx.toast.error(
                f"Failed to delete operation: {str(e)}", position="top-center"
            )

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

        header = ",".join(columns)
        rows = [",".join(str(op.get(col, "")) for col in columns) for op in operations]

        data = str(header + "\n" + "\n".join(rows))
        return rx.download(
            data=data,
            filename=f"operations_{self.account_number}.csv",
        )

    # ── Spreadsheet mode ──

    @rx.var
    def spreadsheet_columns(self) -> list[dict]:
        return [
            {"title": "Title", "type": "str"},
            {"title": "Amount", "type": "float"},
            {"title": "Date", "type": "str"},
            {"title": "Category", "type": "str"},
            {"title": "Balance", "type": "float", "editable": False},
        ]

    def _load_spreadsheet_rows(self) -> tuple[list[list], list]:
        operations = CashService.get_operations_by_account(self.account_number)
        data = [
            [
                op.get("title", ""),
                op.get("amount", 0.0),
                str(op.get("operation_date", ""))[:10],
                op.get("category", "Uncategorized"),
                op.get("balance", 0.0),
            ]
            for op in operations
        ]
        ids = [op.get("id") for op in operations]
        return data, ids

    def _save_spreadsheet_row(self, row, index, rid, is_new):
        title = str(row[0]).strip() or "Operation"
        amount = float(row[1]) if row[1] != "" else 0.0
        date_str = str(row[2]).strip()
        category = str(row[3]).strip() or "Uncategorized"
        operation_date = (
            datetime.fromisoformat(date_str) if date_str else datetime.now()
        )
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

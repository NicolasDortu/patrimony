"""State management for cash operations (deposits/expenses per account)."""

from datetime import datetime

import reflex as rx

from ..services import CashService, EntryType
from .mixins import PaginationMixin


class CashOperationsState(PaginationMixin, rx.State):
    """State for cash operations table (per-account view)."""

    items: list[dict] = []
    account_number: str = ""
    account_currency: str = "EUR"

    search_value: str = ""
    sort_value: str = ""
    sort_reverse: bool = False

    # Edit dialog state
    edit_id: int = 0
    edit_title: str = ""
    edit_amount: float = 0.0
    edit_operation_date: str = ""

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
    def open_edit_dialog(self, item: dict) -> None:
        """Open the edit dialog with the item's current values."""
        self.edit_id = item.get("id", 0)
        self.edit_title = item.get("title", "")
        self.edit_amount = float(item.get("amount", 0))
        self.edit_operation_date = item.get("operation_date", "")

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
    def update_operation(self, form_data: dict) -> None:
        """Update an existing cash operation from form data."""
        try:
            id = self.edit_id
            amount = float(form_data.get("amount", 0))
            title = form_data.get("title", "")
            operation_date_str = form_data.get("operation_date", "")

            if operation_date_str:
                operation_date = datetime.fromisoformat(operation_date_str)
            else:
                operation_date = datetime.now()

            result = CashService.update_operation_by_id(
                id=id,
                amount=amount,
                title=title,
                operation_date=operation_date,
                entry_type=EntryType.MANUAL,
            )

            if result.success:
                self.load_entries()
                return rx.toast.success(result.message, position="top-center")
            else:
                return rx.toast.error(result.message, position="top-center")
        except Exception as e:
            return rx.toast.error(
                f"Failed to update operation: {str(e)}", position="top-center"
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

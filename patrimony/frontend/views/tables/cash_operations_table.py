import reflex as rx

from .common import header_cell, table_row, table_toolbar
from .pagination import pagination_view
from ...states.cash_operations_state import CashOperationsState
from ...dialogs.cash_operation_dialog import open_add_operation_dialog


def _show_item(item: dict, index: int) -> rx.Component:
    return table_row(
        rx.table.row_header_cell(item["id"]),
        rx.table.cell(item["title"]),
        rx.table.cell(
            rx.cond(
                item["amount"].to(float) >= 0,
                rx.text(item["amount"], color=rx.color("grass", 9)),
                rx.text(item["amount"], color=rx.color("red", 9)),
            )
        ),
        rx.table.cell(item["balance"]),
        rx.table.cell(item["category"]),
        rx.table.cell(item["operation_date"]),
        rx.table.cell(item["entry_type"]),
        index=index,
    )


def cash_operations_table() -> rx.Component:
    """Main cash operations table component."""
    return rx.box(
        table_toolbar(
            CashOperationsState,
            ["title", "amount", "balance", "operation_date"],
            add_button=open_add_operation_dialog(CashOperationsState.add_operation),
            default_sort_placeholder="Sort By: operation_date",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    header_cell("ID", "hash"),
                    header_cell("Title", "text"),
                    header_cell("Amount", "dollar-sign"),
                    header_cell("Balance", "wallet"),
                    header_cell("Category", "folder"),
                    header_cell("Date", "calendar"),
                    header_cell("Entry Type", "tag"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    CashOperationsState.get_current_page,
                    lambda item, index: _show_item(item, index),
                )
            ),
            variant="surface",
            size="3",
            width="100%",
        ),
        pagination_view(CashOperationsState),
        width="100%",
    )

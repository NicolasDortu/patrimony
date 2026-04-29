import reflex as rx

from .common import header_cell, table_row, table_toolbar
from .pagination import pagination_view
from ...states.cash_operations_state import CashOperationsState
from ...dialogs.cash_operation_dialog import open_add_operation_dialog
from ...templates import t


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
            [
                (t("label.title"), "title"),
                (t("label.amount"), "amount"),
                (t("label.balance"), "balance"),
                (t("label.date"), "operation_date"),
            ],
            add_button=open_add_operation_dialog(CashOperationsState.add_operation),
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    header_cell(t("label.id"), "hash"),
                    header_cell(t("label.title"), "text"),
                    header_cell(t("label.amount"), "dollar-sign"),
                    header_cell(t("label.balance"), "wallet"),
                    header_cell(t("label.category"), "folder"),
                    header_cell(t("label.date"), "calendar"),
                    header_cell(t("label.entry_type"), "tag"),
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

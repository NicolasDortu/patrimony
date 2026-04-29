import reflex as rx

from .common import header_cell, table_row, table_toolbar
from .pagination import pagination_view
from ...states.cash_state import CashTableState
from ...dialogs.cash_dialog import open_add_cash_dialog
from ...templates import t


def _show_item(item: dict, index: int) -> rx.Component:
    return table_row(
        rx.table.cell(item["bank"]),
        rx.table.cell(item["account_number"]),
        rx.table.cell(item["currency"]),
        rx.table.cell(f"{item['balance']:.2f}"),
        rx.table.cell(
            rx.icon_button(
                rx.icon("arrow_right_to_line", size=18),
                variant="ghost",
                on_click=lambda: CashTableState.open_operations_view(
                    item["account_number"], item["currency"]
                ),
            ),
        ),
        index=index,
    )


def cash_table() -> rx.Component:
    """Main cash table component."""
    return rx.box(
        table_toolbar(
            CashTableState,
            [
                (t("label.bank_name"), "bank"),
                (t("label.account_number"), "account_number"),
                (t("label.currency"), "currency"),
                (t("label.balance"), "balance"),
            ],
            add_button=open_add_cash_dialog(CashTableState.add_cash_entry),
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    header_cell(t("label.bank_name"), "landmark"),
                    header_cell(t("label.account_number"), "hash"),
                    header_cell(t("label.currency"), "badge-euro"),
                    header_cell(t("label.balance"), "wallet"),
                    header_cell("", "eye"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    CashTableState.get_current_page,
                    lambda item, index: _show_item(item, index),
                )
            ),
            variant="surface",
            size="3",
            width="100%",
        ),
        pagination_view(CashTableState),
        width="100%",
    )

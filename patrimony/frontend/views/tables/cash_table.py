import reflex as rx

from .common import header_cell, table_row
from .pagination import pagination_view
from .spreadsheet_view import spreadsheet_toggle_button
from ...states.cash_state import CashTableState
from ...dialogs.cash_dialog import open_add_cash_dialog


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
        rx.flex(
            rx.flex(
                open_add_cash_dialog(CashTableState.add_cash_entry),
                spreadsheet_toggle_button(CashTableState),
                align="center",
                spacing="3",
            ),
            rx.flex(
                rx.cond(
                    CashTableState.sort_reverse,
                    rx.icon(
                        "arrow-down-z-a",
                        size=28,
                        stroke_width=1.5,
                        cursor="pointer",
                        flex_shrink="0",
                        on_click=CashTableState.toggle_sort,
                    ),
                    rx.icon(
                        "arrow-down-a-z",
                        size=28,
                        stroke_width=1.5,
                        cursor="pointer",
                        flex_shrink="0",
                        on_click=CashTableState.toggle_sort,
                    ),
                ),
                rx.select(
                    ["bank", "account_number", "currency", "balance"],
                    placeholder="Sort By: bank",
                    size="3",
                    on_change=CashTableState.set_sort_value,
                ),
                rx.input(
                    rx.input.slot(rx.icon("search")),
                    rx.input.slot(
                        rx.icon("x"),
                        justify="end",
                        cursor="pointer",
                        on_click=CashTableState.set_search_value(""),
                        display=rx.cond(CashTableState.search_value, "flex", "none"),
                    ),
                    value=CashTableState.search_value,
                    placeholder="Search here...",
                    size="3",
                    max_width=["150px", "150px", "200px", "250px"],
                    width="100%",
                    variant="surface",
                    color_scheme="gray",
                    on_change=CashTableState.set_search_value,
                ),
                align="center",
                justify="end",
                spacing="3",
            ),
            spacing="3",
            justify="between",
            wrap="wrap",
            width="100%",
            padding_bottom="1em",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    header_cell("Bank", "landmark"),
                    header_cell("Account Number", "hash"),
                    header_cell("Currency", "badge-euro"),
                    header_cell("Balance", "wallet"),
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

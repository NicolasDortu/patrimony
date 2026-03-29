import reflex as rx

from .common import header_cell, table_row
from .pagination import pagination_view
from .spreadsheet_view import spreadsheet_toggle_button
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
        rx.flex(
            rx.flex(
                open_add_operation_dialog(CashOperationsState.add_operation),
                spreadsheet_toggle_button(CashOperationsState),
                rx.icon_button(
                    rx.icon("arrow-down-to-line", size=20),
                    variant="surface",
                    size="3",
                    on_click=CashOperationsState.export_csv,
                ),
                align="center",
                spacing="3",
            ),
            rx.flex(
                rx.cond(
                    CashOperationsState.sort_reverse,
                    rx.icon(
                        "arrow-down-z-a",
                        size=28,
                        stroke_width=1.5,
                        cursor="pointer",
                        flex_shrink="0",
                        on_click=CashOperationsState.toggle_sort,
                    ),
                    rx.icon(
                        "arrow-down-a-z",
                        size=28,
                        stroke_width=1.5,
                        cursor="pointer",
                        flex_shrink="0",
                        on_click=CashOperationsState.toggle_sort,
                    ),
                ),
                rx.select(
                    [
                        "title",
                        "amount",
                        "balance",
                        "operation_date",
                    ],
                    placeholder="Sort By: operation_date",
                    size="3",
                    on_change=CashOperationsState.set_sort_value,
                ),
                rx.input(
                    rx.input.slot(rx.icon("search")),
                    rx.input.slot(
                        rx.icon("x"),
                        justify="end",
                        cursor="pointer",
                        on_click=CashOperationsState.set_search_value(""),
                        display=rx.cond(
                            CashOperationsState.search_value, "flex", "none"
                        ),
                    ),
                    value=CashOperationsState.search_value,
                    placeholder="Search here...",
                    size="3",
                    max_width=["150px", "150px", "200px", "250px"],
                    width="100%",
                    variant="surface",
                    color_scheme="gray",
                    on_change=CashOperationsState.set_search_value,
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

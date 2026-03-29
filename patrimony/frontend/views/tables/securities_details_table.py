import reflex as rx

from .common import header_cell, table_row
from .pagination import pagination_view
from .spreadsheet_view import spreadsheet_toggle_button
from ...states.securities_details_state import TableStateDetails
from ...services import SecurityPosition
from ...dialogs import open_add_position_dialog
from ...templates import ThemeState


def _show_item(item: SecurityPosition, index: int) -> rx.Component:
    return table_row(
        rx.table.row_header_cell(item.id),
        rx.table.cell(item.ticker),
        rx.table.cell(ThemeState.currency_symbol + f"{item.price:.2f}"),
        rx.table.cell(item.quantity),
        rx.table.cell(item.date),
        index=index,
    )


def main_table() -> rx.Component:
    return rx.box(
        rx.flex(
            rx.flex(
                open_add_position_dialog(TableStateDetails.add_stock),
                spreadsheet_toggle_button(TableStateDetails),
                rx.icon_button(
                    rx.icon("arrow-down-to-line", size=20),
                    variant="surface",
                    size="3",
                    on_click=TableStateDetails.export_csv,
                ),
                align="center",
                spacing="3",
            ),
            rx.flex(
                rx.cond(
                    TableStateDetails.sort_reverse,
                    rx.icon(
                        "arrow-down-z-a",
                        size=28,
                        stroke_width=1.5,
                        cursor="pointer",
                        flex_shrink="0",
                        on_click=TableStateDetails.toggle_sort,
                    ),
                    rx.icon(
                        "arrow-down-a-z",
                        size=28,
                        stroke_width=1.5,
                        cursor="pointer",
                        flex_shrink="0",
                        on_click=TableStateDetails.toggle_sort,
                    ),
                ),
                rx.select(
                    [
                        "id",
                        "ticker",
                        "price",
                        "quantity",
                        "date",
                    ],
                    placeholder="Sort By: id",
                    size="3",
                    on_change=TableStateDetails.set_sort_value,
                ),
                rx.input(
                    rx.input.slot(rx.icon("search")),
                    rx.input.slot(
                        rx.icon("x"),
                        justify="end",
                        cursor="pointer",
                        on_click=TableStateDetails.set_search_value(""),
                        display=rx.cond(TableStateDetails.search_value, "flex", "none"),
                    ),
                    value=TableStateDetails.search_value,
                    placeholder="Search here...",
                    size="3",
                    max_width=["150px", "150px", "200px", "250px"],
                    width="100%",
                    variant="surface",
                    color_scheme="gray",
                    on_change=TableStateDetails.set_search_value,
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
                    header_cell("id", "user"),
                    header_cell("ticker", "notebook-pen"),
                    header_cell("price", "dollar-sign"),
                    header_cell("quantity", "notebook-pen"),
                    header_cell("date", "calendar"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    TableStateDetails.get_current_page,
                    lambda item, index: _show_item(item, index),
                )
            ),
            variant="surface",
            size="3",
            width="100%",
        ),
        pagination_view(TableStateDetails),
        width="100%",
    )

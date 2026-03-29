import reflex as rx

from .common import header_cell
from .pagination import pagination_view
from .spreadsheet_view import spreadsheet_toggle_button
from ...states.securities_total_state import TableStateTotal
from ...services import SecurityTotal
from ...dialogs import open_add_position_dialog
from ...templates import ThemeState


def _show_item(item: SecurityTotal, index: int) -> rx.Component:
    bg_color = rx.cond(
        index % 2 == 0,
        rx.color("gray", 1),
        rx.color("accent", 2),
    )
    hover_color = rx.cond(
        index % 2 == 0,
        rx.color("gray", 3),
        rx.color("accent", 3),
    )
    return rx.table.row(
        rx.table.cell(item.ticker),
        rx.table.cell(item.total_quantity),
        rx.table.cell(ThemeState.currency_symbol + f"{item.current_price:.2f}"),
        rx.table.cell(ThemeState.currency_symbol + f"{item.total_value:.2f}"),
        rx.table.cell(
            rx.icon_button(
                rx.icon("arrow_right_to_line", size=22),
                variant="ghost",
                on_click=lambda: TableStateTotal.open_detail_view(item.ticker),
            )
        ),
        style={"_hover": {"bg": hover_color}, "bg": bg_color},
        align="center",
    )


def main_table() -> rx.Component:
    return rx.box(
        rx.flex(
            rx.flex(
                open_add_position_dialog(TableStateTotal.add_stock),
                spreadsheet_toggle_button(TableStateTotal),
                rx.icon_button(
                    rx.icon("arrow-down-to-line", size=20),
                    variant="surface",
                    size="3",
                    on_click=TableStateTotal.export_csv,
                ),
                align="center",
                spacing="3",
            ),
            rx.flex(
                rx.cond(
                    TableStateTotal.sort_reverse,
                    rx.icon(
                        "arrow-down-z-a",
                        size=28,
                        stroke_width=1.5,
                        cursor="pointer",
                        flex_shrink="0",
                        on_click=TableStateTotal.toggle_sort,
                    ),
                    rx.icon(
                        "arrow-down-a-z",
                        size=28,
                        stroke_width=1.5,
                        cursor="pointer",
                        flex_shrink="0",
                        on_click=TableStateTotal.toggle_sort,
                    ),
                ),
                rx.select(
                    [
                        "ticker",
                        "total_quantity",
                        "current_price",
                        "total_value",
                    ],
                    placeholder="Sort By: ticker",
                    size="3",
                    on_change=TableStateTotal.set_sort_value,
                ),
                rx.input(
                    rx.input.slot(rx.icon("search")),
                    rx.input.slot(
                        rx.icon("x"),
                        justify="end",
                        cursor="pointer",
                        on_click=TableStateTotal.set_search_value(""),
                        display=rx.cond(TableStateTotal.search_value, "flex", "none"),
                    ),
                    value=TableStateTotal.search_value,
                    placeholder="Search here...",
                    size="3",
                    max_width=["150px", "150px", "200px", "250px"],
                    width="100%",
                    variant="surface",
                    color_scheme="gray",
                    on_change=TableStateTotal.set_search_value,
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
                    header_cell("ticker", "building"),
                    header_cell("total_quantity", "notebook-pen"),
                    header_cell("current_price", "dollar-sign"),
                    header_cell("total_value", "wallet"),
                    header_cell("", "chart_no_axes_combined"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    TableStateTotal.get_current_page,
                    lambda item, index: _show_item(item, index),
                )
            ),
            variant="surface",
            size="3",
            width="100%",
        ),
        pagination_view(TableStateTotal),
        width="100%",
    )

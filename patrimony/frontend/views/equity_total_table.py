import reflex as rx

from ..states.securities_total_state import TableStateTotal
from ..services import SecurityTotal
from ..dialogs import open_add_position_dialog


def _header_cell(text: str, icon: str) -> rx.Component:
    return rx.table.column_header_cell(
        rx.hstack(
            rx.icon(icon, size=18),
            rx.text(text),
            align="center",
            spacing="2",
        ),
    )


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
        rx.table.cell(f"${item.current_price:.2f}"),
        rx.table.cell(f"${item.total_value:.2f}"),
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


def _pagination_view() -> rx.Component:
    return (
        rx.hstack(
            rx.text(
                "Page ",
                rx.code(TableStateTotal.page_number),
                f" of {TableStateTotal.total_pages}",
                justify="end",
            ),
            rx.hstack(
                rx.icon_button(
                    rx.icon("chevrons-left", size=18),
                    on_click=TableStateTotal.first_page,
                    opacity=rx.cond(TableStateTotal.page_number == 1, 0.6, 1),
                    color_scheme=rx.cond(
                        TableStateTotal.page_number == 1, "gray", "accent"
                    ),
                    variant="soft",
                ),
                rx.icon_button(
                    rx.icon("chevron-left", size=18),
                    on_click=TableStateTotal.prev_page,
                    opacity=rx.cond(TableStateTotal.page_number == 1, 0.6, 1),
                    color_scheme=rx.cond(
                        TableStateTotal.page_number == 1, "gray", "accent"
                    ),
                    variant="soft",
                ),
                rx.icon_button(
                    rx.icon("chevron-right", size=18),
                    on_click=TableStateTotal.next_page,
                    opacity=rx.cond(
                        TableStateTotal.page_number == TableStateTotal.total_pages,
                        0.6,
                        1,
                    ),
                    color_scheme=rx.cond(
                        TableStateTotal.page_number == TableStateTotal.total_pages,
                        "gray",
                        "accent",
                    ),
                    variant="soft",
                ),
                rx.icon_button(
                    rx.icon("chevrons-right", size=18),
                    on_click=TableStateTotal.last_page,
                    opacity=rx.cond(
                        TableStateTotal.page_number == TableStateTotal.total_pages,
                        0.6,
                        1,
                    ),
                    color_scheme=rx.cond(
                        TableStateTotal.page_number == TableStateTotal.total_pages,
                        "gray",
                        "accent",
                    ),
                    variant="soft",
                ),
                align="center",
                spacing="2",
                justify="end",
            ),
            spacing="5",
            margin_top="1em",
            align="center",
            width="100%",
            justify="end",
        ),
    )


def main_table() -> rx.Component:
    return rx.box(
        rx.flex(
            open_add_position_dialog(TableStateTotal.add_stock),
            align="center",
            justify="start",
            spacing="4",
            padding_bottom="1.5em",
        ),
        rx.flex(
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
            rx.button(
                rx.icon("arrow-down-to-line", size=20),
                "Export",
                size="3",
                variant="surface",
                display=["none", "none", "none", "flex"],
                on_click=TableStateTotal.export_csv,
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
                    _header_cell("ticker", "building"),
                    _header_cell("total_quantity", "notebook-pen"),
                    _header_cell("current_price", "dollar-sign"),
                    _header_cell("total_value", "wallet"),
                    _header_cell("", "chart_no_axes_combined"),
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
        _pagination_view(),
        width="100%",
    )

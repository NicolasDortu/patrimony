import reflex as rx

from .common import header_cell
from ...states.securities_details_state import TableStateDetails
from ...services import SecurityPosition
from ...templates import ThemeState


def _show_item(item: SecurityPosition, index: int) -> rx.Component:
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
        rx.table.row_header_cell(item.id),
        rx.table.cell(item.ticker),
        rx.table.cell(ThemeState.currency_symbol + f"{item.price:.2f}"),
        rx.table.cell(item.quantity),
        rx.table.cell(item.date),
        rx.table.cell(
            rx.icon_button(
                rx.icon("trash", size=22),
                color_scheme="red",
                variant="ghost",
                on_click=lambda: TableStateDetails.delete_stock(item.id),
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
                rx.code(TableStateDetails.page_number),
                f" of {TableStateDetails.total_pages}",
                justify="end",
            ),
            rx.hstack(
                rx.icon_button(
                    rx.icon("chevrons-left", size=18),
                    on_click=TableStateDetails.first_page,
                    opacity=rx.cond(TableStateDetails.page_number == 1, 0.6, 1),
                    color_scheme=rx.cond(
                        TableStateDetails.page_number == 1, "gray", "accent"
                    ),
                    variant="soft",
                ),
                rx.icon_button(
                    rx.icon("chevron-left", size=18),
                    on_click=TableStateDetails.prev_page,
                    opacity=rx.cond(TableStateDetails.page_number == 1, 0.6, 1),
                    color_scheme=rx.cond(
                        TableStateDetails.page_number == 1, "gray", "accent"
                    ),
                    variant="soft",
                ),
                rx.icon_button(
                    rx.icon("chevron-right", size=18),
                    on_click=TableStateDetails.next_page,
                    opacity=rx.cond(
                        TableStateDetails.page_number == TableStateDetails.total_pages,
                        0.6,
                        1,
                    ),
                    color_scheme=rx.cond(
                        TableStateDetails.page_number == TableStateDetails.total_pages,
                        "gray",
                        "accent",
                    ),
                    variant="soft",
                ),
                rx.icon_button(
                    rx.icon("chevrons-right", size=18),
                    on_click=TableStateDetails.last_page,
                    opacity=rx.cond(
                        TableStateDetails.page_number == TableStateDetails.total_pages,
                        0.6,
                        1,
                    ),
                    color_scheme=rx.cond(
                        TableStateDetails.page_number == TableStateDetails.total_pages,
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
        _pagination_view(),
        width="100%",
    )

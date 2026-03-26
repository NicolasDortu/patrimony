import reflex as rx

from .common import header_cell
from ...states.dividends_state import DividendsState, Dividend
from ...templates import ThemeState


def _show_item(item: Dividend, index: int) -> rx.Component:
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
        rx.table.cell(ThemeState.currency_symbol + f"{item.amount:.2f}"),
        rx.table.cell(item.date),
        rx.table.cell(
            rx.icon_button(
                rx.icon("trash", size=22),
                color_scheme="red",
                variant="ghost",
                on_click=lambda: DividendsState.delete_dividend(item.id),
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
                rx.code(DividendsState.page_number),
                f" of {DividendsState.total_pages}",
                justify="end",
            ),
            rx.hstack(
                rx.icon_button(
                    rx.icon("chevrons-left", size=18),
                    on_click=DividendsState.first_page,
                    opacity=rx.cond(DividendsState.page_number == 1, 0.6, 1),
                    color_scheme=rx.cond(
                        DividendsState.page_number == 1, "gray", "accent"
                    ),
                    variant="soft",
                ),
                rx.icon_button(
                    rx.icon("chevron-left", size=18),
                    on_click=DividendsState.prev_page,
                    opacity=rx.cond(DividendsState.page_number == 1, 0.6, 1),
                    color_scheme=rx.cond(
                        DividendsState.page_number == 1, "gray", "accent"
                    ),
                    variant="soft",
                ),
                rx.icon_button(
                    rx.icon("chevron-right", size=18),
                    on_click=DividendsState.next_page,
                    opacity=rx.cond(
                        DividendsState.page_number == DividendsState.total_pages,
                        0.6,
                        1,
                    ),
                    color_scheme=rx.cond(
                        DividendsState.page_number == DividendsState.total_pages,
                        "gray",
                        "accent",
                    ),
                    variant="soft",
                ),
                rx.icon_button(
                    rx.icon("chevrons-right", size=18),
                    on_click=DividendsState.last_page,
                    opacity=rx.cond(
                        DividendsState.page_number == DividendsState.total_pages,
                        0.6,
                        1,
                    ),
                    color_scheme=rx.cond(
                        DividendsState.page_number == DividendsState.total_pages,
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


def dividends_table() -> rx.Component:
    return rx.box(
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    header_cell("id", "hash"),
                    header_cell("ticker", "notebook-pen"),
                    header_cell("amount", "dollar-sign"),
                    header_cell("date", "calendar"),
                    header_cell("", "settings"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    DividendsState.get_current_page,
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

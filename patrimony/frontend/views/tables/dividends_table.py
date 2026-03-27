import reflex as rx

from .common import header_cell
from .pagination import pagination_view
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
        pagination_view(DividendsState),
        width="100%",
    )

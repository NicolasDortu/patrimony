import reflex as rx

from .common import header_cell, table_row
from .pagination import pagination_view
from .spreadsheet_view import spreadsheet_toggle_button
from ...states.dividends_state import DividendsState, Dividend
from ...dialogs.dividend_dialog import open_add_dividend_dialog
from ...templates import ThemeState


def _show_item(item: Dividend, index: int) -> rx.Component:
    return table_row(
        rx.table.cell(ThemeState.currency_symbol + f"{item.amount:.2f}"),
        rx.table.cell(item.date),
        index=index,
    )


def dividends_table() -> rx.Component:
    return rx.box(
        rx.flex(
            rx.flex(
                open_add_dividend_dialog(DividendsState.add_dividend),
                spreadsheet_toggle_button(DividendsState),
                align="center",
                spacing="3",
            ),
            spacing="3",
            justify="start",
            wrap="wrap",
            width="100%",
            padding_bottom="1em",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    header_cell("Amount", "dollar-sign"),
                    header_cell("Date", "calendar"),
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

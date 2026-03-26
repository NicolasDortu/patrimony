"""The equity detail page."""

import reflex as rx

from ..components.card import card
from ..dialogs import open_add_position_dialog
from ..dialogs.dividend_dialog import open_add_dividend_dialog
from ..states.securities_details_state import TableStateDetails
from ..states.dividends_state import DividendsState
from ..templates import template, ThemeState
from ..views.tables.securities_details_table import main_table
from ..views.tables.dividends_table import dividends_table
from ..views.charts.stock_chart import stock_chart


class SecuritiesDetailState(rx.State):
    @rx.event
    def on_load(self):
        # Get ticker from URL query params
        ticker = self.router.page.params.get("ticker", "")
        if ticker:
            return TableStateDetails.set_ticker(ticker)


@template(
    route="/securities_detail",
    title="Securities Detail",
    on_load=[TableStateDetails.on_page_load],
)
def securities_detail() -> rx.Component:
    """The securities detail page.

    Returns:
        The UI for the securities detail page.
    """
    return rx.vstack(
        rx.heading(f"Details for {TableStateDetails.ticker}", size="5"),
        rx.flex(
            open_add_position_dialog(TableStateDetails.add_stock),
            rx.button(
                rx.icon("arrow-down-to-line", size=20),
                "Export",
                size="3",
                variant="surface",
                display=["none", "none", "none", "flex"],
                on_click=TableStateDetails.export_csv,
            ),
            justify="between",
            width="100%",
        ),
        card(stock_chart()),
        main_table(),
        # Dividends section
        rx.heading("Dividends", size="4", margin_top="1em"),
        rx.flex(
            open_add_dividend_dialog(),
            rx.text(
                "Total: ",
                ThemeState.currency_symbol,
                f"{DividendsState.total_dividends:.2f}",
                size="3",
                weight="bold",
            ),
            justify="between",
            align="center",
            width="100%",
        ),
        dividends_table(),
        spacing="5",
        width="100%",
    )

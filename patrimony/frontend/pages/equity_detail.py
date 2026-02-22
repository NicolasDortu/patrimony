"""The equity detail page."""

import reflex as rx

from ..components.card import card
from ..dialogs import open_add_position_dialog
from ..states.securities_details_state import TableStateDetails
from ..templates import template
from ..views.tables.equity_details_table import main_table
from ..views.charts.stock_chart import stock_chart


class EquityDetailState(rx.State):
    @rx.event
    def on_load(self):
        # Get ticker from URL query params
        ticker = self.router.page.params.get("ticker", "")
        if ticker:
            return TableStateDetails.set_ticker(ticker)


@template(
    route="/equity_detail",
    title="Equity Detail",
    on_load=[TableStateDetails.on_page_load],
)
def equity_detail() -> rx.Component:
    """The equity detail page.

    Returns:
        The UI for the equity detail page.
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
        spacing="5",
        width="100%",
    )

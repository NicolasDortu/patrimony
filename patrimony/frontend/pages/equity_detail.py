"""The equity detail page."""

import reflex as rx

from ..states.securities_details_state import TableStateDetails
from ..templates import template
from ..views.equity_details_table import main_table


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
        main_table(),
        spacing="5",
        width="100%",
    )

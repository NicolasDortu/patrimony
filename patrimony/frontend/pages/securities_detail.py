"""The equity detail page."""

import reflex as rx

from ..components.card import card
from ..states.securities_details_state import TableStateDetails
from ..states.dividends_state import DividendsState
from ..templates import template, ThemeState, t
from ..views.tables.securities_details_table import main_table
from ..views.tables.dividends_table import dividends_table
from ..views.tables.spreadsheet_view import spreadsheet_or_table
from ..views.charts.stock_chart import stock_chart


class SecuritiesDetailState(rx.State):
    @rx.event
    def on_load(self):
        # Get ticker from URL query params
        ticker = self.router.page.params.get("ticker", "")
        if ticker:
            return TableStateDetails.set_ticker(ticker)


def _header() -> rx.Component:
    """Page header with ticker name and current price."""
    return rx.hstack(
        rx.heading(TableStateDetails.ticker, size="5"),
        rx.badge(
            ThemeState.currency_symbol,
            f"{TableStateDetails.current_price:.2f}",
            size="3",
            variant="surface",
            color_scheme="grass",
        ),
        align="center",
        width="100%",
    )


def _positions_tab() -> rx.Component:
    """Positions tab content."""
    return rx.vstack(
        spreadsheet_or_table(TableStateDetails, main_table()),
        spacing="4",
        width="100%",
    )


def _dividends_tab() -> rx.Component:
    """Dividends tab content."""
    return rx.hstack(
        rx.vstack(
            spreadsheet_or_table(DividendsState, dividends_table()),
            spacing="4",
            flex="1",
        ),
        rx.text(
            t("label.total"),
            ": ",
            ThemeState.currency_symbol,
            f"{DividendsState.total_dividends:.2f}",
            size="3",
            weight="bold",
            white_space="nowrap",
        ),
        align="start",
        spacing="4",
        width="100%",
    )


@template(
    route="/securities_detail",
    title="Securities Detail",
    on_load=[TableStateDetails.on_page_load],
)
def securities_detail() -> rx.Component:
    """The securities detail page."""
    return rx.vstack(
        _header(),
        card(stock_chart()),
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger(t("tab.positions"), value="positions"),
                rx.tabs.trigger(t("tab.dividends"), value="dividends"),
            ),
            rx.tabs.content(_positions_tab(), value="positions"),
            rx.tabs.content(_dividends_tab(), value="dividends"),
            default_value="positions",
            width="100%",
        ),
        spacing="5",
        width="100%",
    )

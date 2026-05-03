"""The equity detail page."""

import reflex as rx

from ..components.card import card
from ..components.loading import loading_spinner
from ..states.securities_details_state import TableStateDetails
from ..states.dividends_state import DividendsState
from ..templates import template, ThemeState, t
from ..views.tables.securities_details_table import main_table
from ..views.tables.dividends_table import dividends_table
from ..views.tables.spreadsheet_view import spreadsheet_or_table
from ..views.charts.stock_chart import stock_chart


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
        rx.spacer(),
        rx.button(
            rx.icon("arrow-left", size=18),
            t("securities.back"),
            size="2",
            variant="soft",
            on_click=rx.redirect("/securities"),
        ),
        align="center",
        spacing="3",
        width="100%",
    )


def _positions_tab() -> rx.Component:
    """Positions tab content."""
    return rx.vstack(
        spreadsheet_or_table(TableStateDetails, main_table()),
        spacing="4",
        width="100%",
        padding_top="1rem",
    )


def _dividends_tab() -> rx.Component:
    """Dividends tab content.

    Dividend records have only two columns (amount, date), so we constrain
    the width to roughly half the page
    """
    # 220 + 220 column widths + ~50px Glide row-marker gutter ≈ 490px.
    _DIVIDEND_WIDTH = "490px"
    return rx.vstack(
        rx.box(
            spreadsheet_or_table(DividendsState, dividends_table()),
            width=_DIVIDEND_WIDTH,
            max_width="100%",
        ),
        width="100%",
        padding_top="1rem",
    )


@template(
    route="/securities_detail",
    title="Securities Detail",
    on_load=[TableStateDetails.on_page_load],
)
def securities_detail() -> rx.Component:
    """The securities detail page."""
    return rx.cond(
        TableStateDetails.is_loading,
        loading_spinner(),
        rx.vstack(
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
        ),
    )

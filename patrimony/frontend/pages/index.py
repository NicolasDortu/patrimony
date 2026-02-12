"""The overview page of the app."""

import reflex as rx

from ..components.card import card
from ..components.notification import notification
from ..templates import template
from ..states.portfolio_state import PortfolioState
from ..views.wealth_chart import wealth_chart
from ..views.portfolio_kpis import (
    portfolio_kpi_cards,
    top_performers_card,
    bottom_performers_card,
    allocation_card,
)


@template(route="/", title="Overview", on_load=PortfolioState.load_portfolio_data)
def index() -> rx.Component:
    """The overview page.

    Returns:
        The UI for the overview page.

    """
    return rx.vstack(
        rx.flex(
            rx.heading("Portfolio Overview", size="5"),
            rx.flex(
                notification("bell", "cyan", 12),
                notification("message-square-text", "plum", 6),
                spacing="4",
                width="100%",
                wrap="nowrap",
                justify="end",
            ),
            justify="between",
            align="center",
            width="100%",
        ),
        portfolio_kpi_cards(),
        card(wealth_chart()),
        rx.grid(
            top_performers_card(),
            bottom_performers_card(),
            allocation_card(),
            gap="1rem",
            grid_template_columns=[
                "1fr",
                "repeat(1, 1fr)",
                "repeat(2, 1fr)",
                "repeat(3, 1fr)",
                "repeat(3, 1fr)",
            ],
            width="100%",
        ),
        spacing="8",
        width="100%",
    )

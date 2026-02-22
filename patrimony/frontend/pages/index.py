"""The overview page of the app."""

import reflex as rx

from ..components.card import card
from ..components.notification import notification
from ..templates import template
from ..states.portfolio_state import PortfolioState
from ..views.charts.wealth_chart import wealth_chart
from ..views.kpis.portfolio_stats_card import portfolio_kpi_cards
from ..views.kpis.portfolio_performers import portfolio_performers_card
from ..views.kpis.portfolio_allocation import allocation_card


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
                notification("message-square-text", "plum", 0),
                spacing="4",
                width="100%",
                wrap="nowrap",
                justify="end",
            ),  # TODO: link notifications to connector status and other important events + color should be the accent color of user
            justify="between",
            align="center",
            width="100%",
        ),
        portfolio_kpi_cards(),
        card(wealth_chart()),
        rx.grid(
            portfolio_performers_card(),
            allocation_card(),
            gap="1rem",
            grid_template_columns=[
                "1fr",
                "1fr",
                "1fr 2fr",
                "1fr 2fr",
                "1fr 2fr",
            ],
            width="100%",
        ),
        spacing="8",
        width="100%",
    )

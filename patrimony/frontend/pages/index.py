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


def _empty_state() -> rx.Component:
    """Welcome page shown when the user has no data yet."""
    return rx.center(
        rx.vstack(
            rx.icon("wallet", size=64, color=rx.color("accent", 9)),
            rx.heading("Welcome to Patrimony!", size="6"),
            rx.text(
                "It looks like you don't have any assets yet. "
                "Start by importing data or adding positions manually.",
                size="3",
                color=rx.color("gray", 11),
                text_align="center",
                max_width="480px",
            ),
            rx.separator(size="4"),
            rx.hstack(
                rx.link(
                    rx.button(
                        rx.icon("plug", size=16),
                        "Import via Connector",
                        size="3",
                        variant="solid",
                    ),
                    href="/connectors",
                ),
                rx.link(
                    rx.button(
                        rx.icon("plus", size=16),
                        "Add Securities",
                        size="3",
                        variant="outline",
                    ),
                    href="/securities",
                ),
                rx.link(
                    rx.button(
                        rx.icon("landmark", size=16),
                        "Add Cash Account",
                        size="3",
                        variant="outline",
                    ),
                    href="/cash",
                ),
                spacing="3",
                wrap="wrap",
                justify="center",
            ),
            align="center",
            spacing="5",
            padding="4em",
        ),
        width="100%",
        min_height="60vh",
    )


def _dashboard() -> rx.Component:
    """The main dashboard shown when data exists."""
    return rx.vstack(
        rx.flex(
            rx.heading("Portfolio Overview", size="5"),
            rx.flex(
                notification("message-square-text", "plum", 0),
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


@template(route="/", title="Overview", on_load=PortfolioState.load_portfolio_data)
def index() -> rx.Component:
    """The overview page."""
    return rx.cond(
        PortfolioState.has_data,
        _dashboard(),
        _empty_state(),
    )

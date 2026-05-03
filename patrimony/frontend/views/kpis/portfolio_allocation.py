import reflex as rx

from ...components.card import card
from ...components.donut_chart import donut_pie_chart_with_legend
from ...states.portfolio_state import PortfolioState
from ...templates import t


def allocation_card() -> rx.Component:
    """Asset allocation card: donut on the left, full legend (% + amount) on the right."""
    return card(
        rx.vstack(
            rx.hstack(
                rx.icon("pie-chart", size=20),
                rx.text(
                    t("kpi.asset_allocation"),
                    size="4",
                    weight="medium",
                ),
                align="center",
                spacing="2",
            ),
            rx.cond(
                PortfolioState.allocation_data.length() > 0,
                donut_pie_chart_with_legend(
                    PortfolioState.allocation_data,
                    height=260,
                ),
                rx.text(
                    t("kpi.no_allocation_data"),
                    size="2",
                    color=rx.color("gray", 10),
                ),
            ),
            spacing="4",
            width="100%",
        ),
    )

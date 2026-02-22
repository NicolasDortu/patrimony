import reflex as rx

from ...components.card import card
from ...states.portfolio_state import PortfolioState


def allocation_pie_chart() -> rx.Component:
    """Pie chart showing asset allocation."""
    return rx.recharts.pie_chart(
        rx.recharts.pie(
            data=PortfolioState.allocation_data,
            data_key="value",
            name_key="name",
            cx="50%",
            cy="50%",
            label=True,
            inner_radius="100",
            outer_radius="120",
        ),
        rx.recharts.legend(),
        rx.recharts.graphing_tooltip(),
        width="100%",
        height=300,
    )


def allocation_breakdown() -> rx.Component:
    """Display allocation breakdown with percentages."""
    return rx.vstack(
        rx.foreach(
            PortfolioState.allocation_data,
            lambda item: rx.hstack(
                rx.box(
                    width="16px",
                    height="16px",
                    border_radius="4px",
                    background=item["fill"],
                ),
                rx.text(item["name"], size="3", weight="medium"),
                rx.spacer(),
                rx.vstack(
                    rx.text(
                        f"{item['percentage']}%",
                        size="3",
                        weight="bold",
                    ),
                    rx.text(
                        f"€{item['value']:,.2f}",
                        size="2",
                        color=rx.color("gray", 10),
                    ),
                    spacing="0",
                    align_items="end",
                ),
                width="100%",
                padding="0.5rem",
            ),
        ),
        spacing="2",
        width="100%",
    )


def allocation_card() -> rx.Component:
    """Display asset allocation card with pie chart and breakdown."""
    return card(
        rx.vstack(
            rx.hstack(
                rx.icon("pie-chart", size=20),
                rx.text("Asset Allocation", size="4", weight="medium"),
                align="center",
                spacing="2",
            ),
            rx.cond(
                PortfolioState.allocation_data.length() > 0,
                rx.vstack(
                    allocation_pie_chart(),
                    allocation_breakdown(),
                    spacing="4",
                    width="100%",
                ),
                rx.text(
                    "No allocation data available",
                    size="2",
                    color=rx.color("gray", 10),
                ),
            ),
            spacing="4",
            width="100%",
        ),
    )

"""Portfolio KPI components for displaying key metrics."""

import reflex as rx

from ..components.card import card
from ..states.portfolio_state import PortfolioState
from ..styles import styles


def portfolio_stats_card(
    stat_name: str,
    value_formatted: str,
    return_pct_var,
    return_formatted: str,
    icon: str,
) -> rx.Component:
    """Display a portfolio statistic with value and return percentage."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.badge(
                    rx.icon(tag=icon, size=34),
                    radius="full",
                    padding="0.7rem",
                ),
                rx.vstack(
                    rx.heading(
                        value_formatted,
                        size="6",
                        weight="bold",
                    ),
                    rx.text(stat_name, size="4", weight="medium"),
                    spacing="1",
                    height="100%",
                    align_items="start",
                    width="100%",
                ),
                height="100%",
                spacing="4",
                align="center",
                width="100%",
            ),
            rx.hstack(
                rx.hstack(
                    rx.cond(
                        return_pct_var >= 0,
                        rx.icon(
                            tag="trending-up",
                            size=24,
                            color=rx.color("grass", 9),
                        ),
                        rx.icon(
                            tag="trending-down",
                            size=24,
                            color=rx.color("tomato", 9),
                        ),
                    ),
                    rx.cond(
                        return_pct_var >= 0,
                        rx.text(
                            return_formatted,
                            size="3",
                            color=rx.color("grass", 9),
                            weight="medium",
                        ),
                        rx.text(
                            return_formatted,
                            size="3",
                            color=rx.color("tomato", 9),
                            weight="medium",
                        ),
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.text(
                    "total return",
                    size="2",
                    color=rx.color("gray", 10),
                ),
                align="center",
                width="100%",
            ),
            spacing="3",
        ),
        size="3",
        width="100%",
        box_shadow=styles.box_shadow_style,
    )


def portfolio_kpi_cards() -> rx.Component:
    """Display main portfolio KPI cards."""
    return rx.grid(
        portfolio_stats_card(
            stat_name="Total Portfolio",
            value_formatted=PortfolioState.total_value_formatted,
            return_pct_var=PortfolioState.total_return,
            return_formatted=PortfolioState.total_return_formatted,
            icon="wallet",
        ),
        portfolio_stats_card(
            stat_name="Stocks Value",
            value_formatted=PortfolioState.stocks_value_formatted,
            return_pct_var=PortfolioState.total_return,
            return_formatted=PortfolioState.total_return_formatted,
            icon="trending-up",
        ),
        portfolio_stats_card(
            stat_name="Cash Holdings",
            value_formatted=PortfolioState.cash_value_formatted,
            return_pct_var=PortfolioState.router.session.client_token.to(float) * 0,
            return_formatted="0.00%",
            icon="banknote",
        ),
        gap="1rem",
        grid_template_columns=[
            "1fr",
            "repeat(1, 1fr)",
            "repeat(2, 1fr)",
            "repeat(3, 1fr)",
            "repeat(3, 1fr)",
        ],
        width="100%",
    )


def performer_item(item: dict) -> rx.Component:
    """Display a single performer item."""
    return rx.hstack(
        rx.hstack(
            rx.match(
                item["icon"],
                ("trending-up", rx.icon("trending-up", size=20, color=rx.color(item["color"], 9))),
                ("trending-down", rx.icon("trending-down", size=20, color=rx.color(item["color"], 9))),
                rx.icon("trending-up", size=20, color=rx.color(item["color"], 9)),
            ),
            rx.text(item["ticker"], size="3", weight="bold"),
            spacing="2",
            align="center",
        ),
        rx.spacer(),
        rx.vstack(
            rx.text(
                item["return_formatted"],
                size="3",
                weight="medium",
                color=rx.color(item["color"], 9),
            ),
            rx.text(
                item["value_formatted"],
                size="2",
                color=rx.color("gray", 11),
            ),
            spacing="0",
            align_items="end",
        ),
        width="100%",
        padding="0.75rem",
        border_radius="8px",
        background=rx.color("gray", 2),
    )


def top_performers_card() -> rx.Component:
    """Display top performing assets."""
    return card(
        rx.vstack(
            rx.hstack(
                rx.icon("trophy", size=20),
                rx.text("Top Performers", size="4", weight="medium"),
                align="center",
                spacing="2",
            ),
            rx.cond(
                PortfolioState.top_performers.length() > 0,
                rx.vstack(
                    rx.foreach(
                        PortfolioState.top_performers,
                        performer_item,
                    ),
                    spacing="2",
                    width="100%",
                ),
                rx.text(
                    "No performance data available",
                    size="2",
                    color=rx.color("gray", 10),
                ),
            ),
            spacing="4",
            width="100%",
        ),
    )


def bottom_performers_card() -> rx.Component:
    """Display worst performing assets."""
    return card(
        rx.vstack(
            rx.hstack(
                rx.icon("triangle-alert", size=20),
                rx.text("Needs Attention", size="4", weight="medium"),
                align="center",
                spacing="2",
            ),
            rx.cond(
                PortfolioState.bottom_performers.length() > 0,
                rx.vstack(
                    rx.foreach(
                        PortfolioState.bottom_performers,
                        performer_item,
                    ),
                    spacing="2",
                    width="100%",
                ),
                rx.text(
                    "No performance data available",
                    size="2",
                    color=rx.color("gray", 10),
                ),
            ),
            spacing="4",
            width="100%",
        ),
    )


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
            inner_radius="60",
            outer_radius="80",
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

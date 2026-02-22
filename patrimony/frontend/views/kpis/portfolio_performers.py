import reflex as rx

from ...components.card import card
from ...states.portfolio_state import PortfolioState


def performer_item(item: dict) -> rx.Component:
    """Display a single performer item."""
    return rx.hstack(
        rx.hstack(
            rx.match(
                item["icon"],
                (
                    "trending-up",
                    rx.icon("trending-up", size=20, color=rx.color(item["color"], 9)),
                ),
                (
                    "trending-down",
                    rx.icon("trending-down", size=20, color=rx.color(item["color"], 9)),
                ),
                rx.icon("trending-up", size=20, color=rx.color(item["color"], 9)),
            ),
            rx.text(item["ticker"], size="3", weight="bold"),
            spacing="2",
            align="center",
        ),
        rx.spacer(),
        rx.vstack(
            rx.text(
                item["return"],
                size="3",
                weight="medium",
                color=rx.color(item["color"], 9),
            ),
            rx.text(
                item["value"],
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


def portfolio_performers_card() -> rx.Component:
    """Display top and bottom performers stacked vertically."""
    return rx.grid(
        top_performers_card(),
        bottom_performers_card(),
        gap="1rem",
        grid_template_columns="1fr",
        width="100%",
    )

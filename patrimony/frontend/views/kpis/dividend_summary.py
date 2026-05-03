"""Dividend summary card for the main dashboard."""

import reflex as rx

from ...components.card import card
from ...states.portfolio_state import PortfolioState
from ...templates import ThemeState, t


def _dividend_item(item: dict) -> rx.Component:
    """Single dividend entry as a compact card."""
    return rx.hstack(
        rx.text(item["ticker"], size="2", weight="bold"),
        rx.spacer(),
        rx.text(
            ThemeState.currency_symbol,
            item["amount"],
            size="2",
            color=rx.color("grass", 9),
        ),
        rx.text(item["date"], size="2", color=rx.color("gray", 10)),
        spacing="3",
        align="center",
        # Fixed-ish basis (don't grow): when the row wraps, items keep
        # their natural width instead of stretching to fill, so the
        # ticker on the left and amount/date on the right stay together.
        flex="0 1 220px",
        min_width="200px",
        max_width="320px",
        padding="0.5rem",
        border_radius="6px",
        background=rx.color("gray", 2),
    )


def dividend_summary_card() -> rx.Component:
    """Full-width card showing total dividends received and recent entries."""
    return card(
        rx.vstack(
            rx.hstack(
                rx.icon("coins", size=20),
                rx.text(t("kpi.dividends"), size="4", weight="medium"),
                rx.spacer(),
                rx.text(
                    ThemeState.currency_symbol,
                    PortfolioState.total_dividends_received,
                    size="4",
                    weight="bold",
                    color=rx.color("grass", 9),
                ),
                align="center",
                spacing="2",
                width="100%",
            ),
            rx.cond(
                PortfolioState.recent_dividends.length() > 0,
                rx.flex(
                    rx.foreach(
                        PortfolioState.recent_dividends,
                        _dividend_item,
                    ),
                    spacing="3",
                    width="100%",
                    wrap="wrap",
                    direction="row",
                ),
                rx.text(
                    t("kpi.no_dividend_data"),
                    size="2",
                    color=rx.color("gray", 10),
                ),
            ),
            spacing="4",
            width="100%",
        ),
    )

"""Dividend summary card for the main dashboard."""

import reflex as rx

from ...components.card import card
from ...states.portfolio_state import PortfolioState
from ...templates import ThemeState, t


def _dividend_item(item: dict) -> rx.Component:
    """Single dividend entry row."""
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
        width="100%",
        padding="0.5rem",
        border_radius="6px",
        background=rx.color("gray", 2),
    )


def dividend_summary_card() -> rx.Component:
    """KPI card showing total dividends received and recent entries."""
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
                rx.vstack(
                    rx.foreach(
                        PortfolioState.recent_dividends,
                        _dividend_item,
                    ),
                    spacing="2",
                    width="100%",
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

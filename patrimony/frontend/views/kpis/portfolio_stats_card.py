import reflex as rx

from ...components.card import stats_card
from ...states.portfolio_state import PortfolioState
from ...templates import ThemeState, t


def portfolio_kpi_cards() -> rx.Component:
    """Display main portfolio KPI cards."""
    return rx.grid(
        stats_card(
            stat_name=t("kpi.total_portfolio"),
            value=PortfolioState.total_value,
            return_pct=PortfolioState.total_return,
            icon="wallet",
            currency_symbol=ThemeState.currency_symbol,
        ),
        stats_card(
            stat_name=t("kpi.stocks_value"),
            value=PortfolioState.stocks_value,
            return_pct=PortfolioState.total_return,
            icon="trending-up",
            currency_symbol=ThemeState.currency_symbol,
        ),
        stats_card(
            stat_name=t("kpi.cash_holdings"),
            value=PortfolioState.cash_value,
            return_pct=0,
            icon="banknote",
            currency_symbol=ThemeState.currency_symbol,
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

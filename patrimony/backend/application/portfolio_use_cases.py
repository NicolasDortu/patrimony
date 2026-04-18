"""Use cases for portfolio operations."""

from ..domain.constants import DEFAULT_CURRENCY, DEFAULT_PERIOD
from ..domain.entities import PortfolioOverview
from ..domain.services import PortfolioService


class PortfolioUseCases:
    """Application use cases for portfolio overview and chart data."""

    def __init__(self, portfolio_service: PortfolioService):
        self._service = portfolio_service

    def get_portfolio_overview(
        self, user_currency: str = DEFAULT_CURRENCY
    ) -> PortfolioOverview:
        return self._service.get_overview(user_currency)

    def get_chart_data(
        self, period: str = DEFAULT_PERIOD, user_currency: str = DEFAULT_CURRENCY
    ) -> list[dict]:
        return self._service.get_chart_data(period, user_currency)

"""Use cases for portfolio operations."""

from ..domain.entities import PortfolioOverview
from ..domain.services import PortfolioService


class PortfolioUseCases:
    """Application use cases for portfolio overview and chart data."""

    def __init__(self, portfolio_service: PortfolioService):
        self._service = portfolio_service

    def get_portfolio_overview(self, user_currency: str = "EUR") -> PortfolioOverview:
        return self._service.get_overview(user_currency)

    def get_chart_data(
        self, period: str = "1M", user_currency: str = "EUR"
    ) -> list[dict]:
        return self._service.get_chart_data(period, user_currency)

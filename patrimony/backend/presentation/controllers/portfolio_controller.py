"""Portfolio Controller - Thin delegate to PortfolioService."""

from ...domain.entities import PortfolioOverview
from ...domain.services.portfolio_service import PortfolioService


class PortfolioController:
    """Controller for portfolio-wide operations and metrics."""

    def __init__(self, portfolio_service: PortfolioService):
        self._service = portfolio_service

    def get_portfolio_overview(self, user_currency: str = "EUR") -> PortfolioOverview:
        """Get complete portfolio overview with all metrics."""
        return self._service.get_overview(user_currency)

    def get_chart_data(
        self, period: str = "1M", user_currency: str = "EUR"
    ) -> list[dict]:
        """Build time-series chart data for the entire portfolio."""
        return self._service.get_chart_data(period, user_currency)

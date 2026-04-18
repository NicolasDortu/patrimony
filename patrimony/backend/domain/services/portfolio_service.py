"""Domain service for portfolio-wide overview and value metrics.

Orchestrates asset services to provide portfolio overview and chart data.
"""

import logging

from ..entities import PortfolioOverview
from .cash_service import CashService
from .chart_service import ChartService
from .property_service import PropertyService
from .securities_service import SecuritiesService

logger = logging.getLogger(__name__)


class PortfolioService:
    """Domain service for portfolio aggregation and overview."""

    def __init__(
        self,
        securities_service: SecuritiesService,
        cash_service: CashService,
        property_service: PropertyService,
        chart_service: ChartService,
    ):
        self._securities_service = securities_service
        self._cash_service = cash_service
        self._property_service = property_service
        self._chart_service = chart_service

    def get_overview(self, user_currency: str = "EUR") -> PortfolioOverview:
        """Build aggregated portfolio metrics."""
        total_invested, securities_value, total_return = (
            self._securities_service.calculate_metrics(user_currency)
        )
        cash_value = self._cash_service.get_total_balance(user_currency)
        properties_value = self._property_service.get_total_value(user_currency)

        return PortfolioOverview(
            total_value=securities_value + cash_value + properties_value,
            total_invested=total_invested,
            total_return=total_return,
            securities_value=securities_value,
            cash_value=cash_value,
            properties_value=properties_value,
        )

    def get_chart_data(
        self, period: str = "1M", user_currency: str = "EUR"
    ) -> list[dict]:
        """Build time-series chart data for the entire portfolio."""
        return self._chart_service.get_portfolio_chart_data(
            period=period,
            user_currency=user_currency,
            securities=self._build_securities_map(user_currency),
            current_cash=self._cash_service.get_total_balance(user_currency),
            properties_value=self._property_service.get_total_value(user_currency),
        )

    def _build_securities_map(self, user_currency: str) -> dict[str, dict]:
        """Transform enriched positions into {ticker: {quantity, asset_type}} for chart input."""
        df = self._securities_service.get_aggregated_positions(user_currency)
        if df is None or df.is_empty():
            return {}
        return {
            row["ticker"]: {
                "quantity": float(row["total_quantity"]),
                "asset_type": row["asset_type"],
            }
            for row in df.iter_rows(named=True)
        }

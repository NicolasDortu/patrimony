"""Domain service for portfolio-wide overview and value metrics.

Orchestrates securities, cash, prices, and currency conversion
to provide portfolio overview data. Delegates chart building to
PortfolioChartService.
"""

import logging
from typing import Optional

import polars as pl

from ..entities import PortfolioOverview
from ..repositories import (
    CashRepository,
    PriceRepository,
    PropertyRepository,
    SecuritiesRepository,
)
from .currency_service import CurrencyService
from .enrichment_utilities import (
    apply_currency_conversion,
    enrich_with_prices,
)
from .portfolio_chart_service import PortfolioChartService
from .price_sync_service import PriceSyncService

logger = logging.getLogger(__name__)


class PortfolioService:
    """Domain service for portfolio aggregation and overview."""

    def __init__(
        self,
        securities_repo: SecuritiesRepository,
        cash_repo: CashRepository,
        price_repo: PriceRepository,
        currency_service: CurrencyService,
        chart_service: PortfolioChartService,
        property_repo: PropertyRepository | None = None,
        price_sync: PriceSyncService | None = None,
    ):
        self._securities_repo = securities_repo
        self._cash_repo = cash_repo
        self._price_repo = price_repo
        self._currency_service = currency_service
        self._chart_service = chart_service
        self._property_repo = property_repo
        self._price_sync = price_sync

    # -- Portfolio Overview --------------------------------------------------

    def get_overview(self, user_currency: str = "EUR") -> PortfolioOverview:
        """Build a complete portfolio overview with metrics."""
        # Securities
        securities_df = self._securities_repo.get_aggregated_positions()
        if securities_df is not None and not securities_df.is_empty():
            securities_df = enrich_with_prices(securities_df, self._price_sync)
            securities_df = apply_currency_conversion(
                securities_df, self._currency_service, user_currency
            )

        total_invested, securities_value, total_return = (
            self._calculate_securities_metrics(securities_df)
        )

        # Cash
        cash_df = self._cash_repo.get_all()
        cash_value = self._calculate_cash_value(cash_df, user_currency)

        # Properties
        properties_value = self._calculate_properties_value(user_currency)

        return PortfolioOverview(
            securities_total=securities_df,
            cash_entries=cash_df,
            total_value=securities_value + cash_value + properties_value,
            total_invested=total_invested,
            total_return=total_return,
            securities_value=securities_value,
            cash_value=cash_value,
            properties_value=properties_value,
        )

    # -- Chart Data (delegated) ----------------------------------------------

    def get_chart_data(
        self, period: str = "1M", user_currency: str = "EUR"
    ) -> list[dict]:
        """Build time-series chart data for the entire portfolio."""
        securities = self._get_all_securities()
        current_cash = self._calculate_cash_value(
            self._cash_repo.get_all(), user_currency
        )
        properties_value = self._calculate_properties_value(user_currency)

        return self._chart_service.get_chart_data(
            period=period,
            user_currency=user_currency,
            securities=securities,
            current_cash=current_cash,
            properties_value=properties_value,
        )

    # -- Internal helpers ----------------------------------------------------

    def _calculate_securities_metrics(
        self, df: Optional[pl.DataFrame]
    ) -> tuple[float, float, float]:
        if df is None or df.is_empty():
            return 0.0, 0.0, 0.0

        valid_df = df.filter(
            pl.col("current_price").is_not_null()
            & pl.col("total_quantity").is_not_null()
            & (pl.col("total_quantity") > 0)
        )
        if valid_df.is_empty():
            return 0.0, 0.0, 0.0

        return PortfolioService._calculate_metrics(
            quantities=valid_df["total_quantity"].to_list(),
            buy_prices=valid_df["avg_price"].to_list(),
            current_prices=valid_df["current_price"].to_list(),
        )

    @staticmethod
    def _calculate_metrics(
        quantities: list[float],
        buy_prices: list[float],
        current_prices: list[float],
    ) -> tuple[float, float, float]:
        """Calculate total invested, current value, and return percentage."""
        import math

        total_invested = math.fsum(q * p for q, p in zip(quantities, buy_prices))
        total_value = math.fsum(q * p for q, p in zip(quantities, current_prices))
        return_percentage = (
            ((total_value - total_invested) / total_invested * 100)
            if total_invested > 0
            else 0.0
        )
        return total_invested, total_value, return_percentage

    def _sum_with_currency(
        self,
        df: Optional[pl.DataFrame],
        value_col: str,
        user_currency: str,
    ) -> float:
        """Sum a value column, converting each row's currency to user_currency."""
        if df is None or df.is_empty():
            return 0.0
        if "currency" not in df.columns:
            return float(df[value_col].sum())
        total = 0.0
        rate_cache: dict[str, float] = {}
        for row in df.iter_rows(named=True):
            curr = row.get("currency", "EUR") or "EUR"
            if curr not in rate_cache:
                rate_cache[curr] = self._currency_service.get_exchange_rate(
                    curr, user_currency
                )
            total += row[value_col] * rate_cache[curr]
        return total

    def _calculate_cash_value(
        self, df: Optional[pl.DataFrame], user_currency: str
    ) -> float:
        return self._sum_with_currency(df, "balance", user_currency)

    def _calculate_properties_value(self, user_currency: str) -> float:
        """Sum property values converted to user currency."""
        if not self._property_repo:
            return 0.0
        df = self._property_repo.get_total_by_currency()
        return self._sum_with_currency(df, "total_value", user_currency)

    def _get_all_securities(self) -> dict[str, dict]:
        df = self._securities_repo.get_aggregated_positions()
        if df is None or df.is_empty():
            return {}
        df = df.filter(pl.col("total_quantity") > 0)
        if df.is_empty():
            return {}
        return {
            t: {"quantity": float(q), "asset_type": at}
            for t, q, at in zip(
                df["ticker"].to_list(),
                df["total_quantity"].to_list(),
                df["asset_type"].to_list(),
            )
        }

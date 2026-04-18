"""Domain service for securities-specific business logic.

Handles price enrichment, currency conversion, and metrics for positions.
"""

import math
from typing import Optional

import polars as pl

from ..repositories import SecuritiesRepository
from .currency_service import CurrencyService
from .price_sync_service import PriceSyncService


class SecuritiesService:
    """Domain service for securities enrichment."""

    def __init__(
        self,
        securities_repo: SecuritiesRepository,
        currency_service: CurrencyService,
        price_sync: PriceSyncService,
    ):
        self._securities_repo = securities_repo
        self._currency_service = currency_service
        self._price_sync = price_sync

    def get_aggregated_positions(
        self, user_currency: str = "EUR"
    ) -> Optional[pl.DataFrame]:
        """Get aggregated positions enriched with current prices and currency-converted."""
        df = self._securities_repo.get_aggregated_positions()
        if df is None or df.is_empty():
            return None

        df = self._enrich_with_prices(df)
        df = self._currency_service.apply_conversion(df, user_currency)
        return df

    def _enrich_with_prices(self, df: pl.DataFrame) -> pl.DataFrame:
        """Add current_price (and total_value if applicable) columns."""
        if df is None or df.is_empty() or "ticker" not in df.columns:
            return df

        tickers = df["ticker"].to_list()
        bulk_prices = self._price_sync.get_current_prices(tickers)
        prices = [bulk_prices.get(t, 0.0) or 0.0 for t in tickers]

        df = df.with_columns(pl.Series("current_price", prices))
        if "total_quantity" in df.columns:
            df = df.with_columns(
                (pl.col("current_price") * pl.col("total_quantity")).alias(
                    "total_value"
                )
            )
        return df

    def calculate_metrics(
        self, user_currency: str = "EUR"
    ) -> tuple[float, float, float]:
        """Compute (total_invested, securities_value, return_pct)."""
        df = self.get_aggregated_positions(user_currency)
        if df is None or df.is_empty():
            return 0.0, 0.0, 0.0

        valid = df.filter(
            pl.col("current_price").is_not_null()
            & pl.col("total_quantity").is_not_null()
            & (pl.col("total_quantity") > 0)
        )
        if valid.is_empty():
            return 0.0, 0.0, 0.0

        quantities = valid["total_quantity"].to_list()
        buy_prices = valid["avg_price"].to_list()
        current_prices = valid["current_price"].to_list()

        invested = math.fsum(q * p for q, p in zip(quantities, buy_prices))
        value = math.fsum(q * p for q, p in zip(quantities, current_prices))
        return_pct = ((value - invested) / invested * 100) if invested > 0 else 0.0
        return invested, value, return_pct

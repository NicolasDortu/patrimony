"""Domain service for securities-specific business logic.

Handles price enrichment, currency conversion, and metrics for positions.
"""

import math
from bisect import bisect_right

import polars as pl

from ..constants import DEFAULT_CURRENCY
from ..repositories import SecuritiesRepository
from .currency_service import CurrencyService
from .date_utils import normalize_date
from .price_service import PriceService


class SecuritiesService:
    """Domain service for securities enrichment."""

    def __init__(
        self,
        securities_repo: SecuritiesRepository,
        currency_service: CurrencyService,
        price_sync: PriceService,
    ):
        self._securities_repo = securities_repo
        self._currency_service = currency_service
        self._price_sync = price_sync

    def get_aggregated_positions(
        self, user_currency: str = DEFAULT_CURRENCY
    ) -> pl.DataFrame:
        """Get aggregated positions enriched with current prices and currency-converted.

        Returns an empty DataFrame when no positions exist.
        """
        df = self._securities_repo.get_aggregated_positions()
        if df.is_empty():
            return df

        df = self._enrich_with_prices(df)
        df = self._currency_service.apply_conversion(df, user_currency)
        return df

    def _enrich_with_prices(self, df: pl.DataFrame) -> pl.DataFrame:
        """Add current_price (and total_value if applicable) columns."""
        if "ticker" not in df.columns:
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
        self, user_currency: str = DEFAULT_CURRENCY
    ) -> tuple[float, float, float]:
        """Compute (total_invested, securities_value, return_pct)."""
        df = self.get_aggregated_positions(user_currency)
        if df.is_empty():
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
        fees = (
            valid["total_fees"].to_list()
            if "total_fees" in valid.columns
            else [0.0] * len(quantities)
        )

        gross_invested = math.fsum(q * p for q, p in zip(quantities, buy_prices))
        invested = gross_invested + math.fsum(f or 0.0 for f in fees)
        value = math.fsum(q * p for q, p in zip(quantities, current_prices))
        return_pct = ((value - invested) / invested * 100) if invested > 0 else 0.0
        return invested, value, return_pct

    def build_quantity_timeline(self) -> dict[str, list[tuple]]:
        """Build per-ticker cumulative quantity timeline from individual positions.

        Returns a dict mapping ticker -> sorted list of (date, cumulative_quantity).
        """
        df = self._securities_repo.get_all()
        if df.is_empty():
            return {}

        df = df.sort("date").with_columns(
            pl.col("quantity").cum_sum().over("ticker").alias("cum_qty"),
            pl.col("date").cast(pl.Date).alias("norm_date"),
        )

        timeline: dict[str, list[tuple]] = {}
        for partition in df.partition_by("ticker", as_dict=True).items():
            key, ticker_df = partition
            ticker = key[0] if isinstance(key, tuple) else key
            timeline[ticker] = list(
                zip(ticker_df["norm_date"].to_list(), ticker_df["cum_qty"].to_list())
            )
        return timeline

    @staticmethod
    def get_quantity_at_date(
        quantity_timeline: dict[str, list[tuple]], ticker: str, dt
    ) -> float:
        """Get the cumulative quantity held for a ticker at a given date."""
        entries = quantity_timeline.get(ticker, [])
        if not entries:
            return 0.0
        dt_date = normalize_date(dt)
        idx = bisect_right(entries, dt_date, key=lambda e: e[0])
        return entries[idx - 1][1] if idx > 0 else 0.0

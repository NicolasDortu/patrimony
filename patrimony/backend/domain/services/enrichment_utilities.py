"""Shared enrichment utilities for securities DataFrames.

Provides price enrichment, currency conversion, quantity timeline,
and sync cooldown logic used across domain services.
"""

import logging
from bisect import bisect_right
from datetime import date, datetime

import polars as pl

from ..repositories import PriceRepository, SecuritiesRepository
from .currency_service import CurrencyService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sync cooldown mixin
# ---------------------------------------------------------------------------


class SyncCooldownMixin:
    """Mixin providing per-ticker cooldown tracking for sync services.

    Subclasses must set ``_cooldown_seconds`` (int) as a class attribute.
    """

    _cooldown_seconds: int  # must be set by subclass

    def _init_cooldown(self) -> None:
        self._synced_tickers: set[str] = set()
        self._last_sync_time: datetime | None = None

    def _apply_cooldown(self, tickers: list[str]) -> list[str]:
        """Filter out tickers that were recently synced.

        When the cooldown has not yet expired, only tickers that have
        never been synced in this session are returned.  When the
        cooldown expires (or on the very first call), all tickers pass
        through.
        """
        if (
            self._last_sync_time is None
            or (datetime.now() - self._last_sync_time).total_seconds()
            >= self._cooldown_seconds
        ):
            return tickers

        new_tickers = [t for t in tickers if t not in self._synced_tickers]
        if new_tickers:
            logger.debug(
                "Sync cooldown active, processing %d new ticker(s) only",
                len(new_tickers),
            )
        return new_tickers

    def _mark_synced(self, ticker: str) -> None:
        self._synced_tickers.add(ticker)

    def _finish_sync(self) -> None:
        self._last_sync_time = datetime.now()


def enrich_with_prices(df: pl.DataFrame, price_repo: PriceRepository) -> pl.DataFrame:
    """Add current_price (and total_value if applicable) columns to a DataFrame of positions."""
    if df is None or df.is_empty() or "ticker" not in df.columns:
        return df

    tickers = df["ticker"].to_list()
    bulk_prices = price_repo.get_current_prices(tickers)
    prices = [bulk_prices.get(t.upper(), 0.0) or 0.0 for t in tickers]

    df = df.with_columns(pl.Series("current_price", prices))
    if "total_quantity" in df.columns:
        df = df.with_columns(
            (pl.col("current_price") * pl.col("total_quantity")).alias("total_value")
        )
    return df


def apply_currency_conversion(
    df: pl.DataFrame, currency_service: CurrencyService, user_currency: str
) -> pl.DataFrame:
    """Convert current_price and avg_price to user_currency, recompute total_value."""
    tickers = df["ticker"].to_list()
    rates = currency_service.get_rates_for_tickers(tickers, user_currency)
    rate_list = pl.Series("_rate", [rates.get(t, 1.0) for t in tickers])
    df = df.with_columns(
        (pl.col("current_price") * rate_list).alias("current_price"),
        (pl.col("avg_price") * rate_list).alias("avg_price"),
    )
    return df.with_columns(
        (pl.col("current_price") * pl.col("total_quantity")).alias("total_value")
    )


def normalize_date(dt) -> date:
    """Normalize a datetime or date value to a plain date object."""
    if isinstance(dt, datetime):
        return dt.date()
    if hasattr(dt, "date") and callable(dt.date):
        return dt.date()
    return dt


def forward_fill_prices(prices: dict, sorted_dates: list) -> None:
    """Fill missing/invalid prices in-place using the last valid price.

    A price is considered invalid if it is None, NaN, or <= 0.
    """
    last_valid = None
    for dt in sorted_dates:
        price = prices.get(dt)
        if price is not None and price == price and price > 0:
            last_valid = price
        elif last_valid is not None:
            prices[dt] = last_valid


def build_quantity_timeline(
    securities_repo: SecuritiesRepository,
) -> dict[str, list[tuple]]:
    """Build per-ticker cumulative quantity timeline from individual positions.

    Returns a dict mapping ticker -> sorted list of (date, cumulative_quantity).
    """
    df = securities_repo.get_all()
    if df is None or df.is_empty():
        return {}

    df = df.sort("date").with_columns(
        pl.col("quantity").cum_sum().over("ticker").alias("cum_qty"),
        pl.col("date")
        .map_elements(normalize_date, return_dtype=pl.Date)
        .alias("norm_date"),
    )

    timeline: dict[str, list[tuple]] = {}
    for ticker in df["ticker"].unique().to_list():
        ticker_df = df.filter(pl.col("ticker") == ticker)
        timeline[ticker] = list(
            zip(ticker_df["norm_date"].to_list(), ticker_df["cum_qty"].to_list())
        )
    return timeline


def get_quantity_at_date(
    quantity_timeline: dict[str, list[tuple]], ticker: str, dt
) -> float:
    """Get the cumulative quantity held for a ticker at a given date."""
    entries = quantity_timeline.get(ticker.upper(), [])
    if not entries:
        entries = quantity_timeline.get(ticker, [])
    if not entries:
        return 0.0
    dt_date = normalize_date(dt)
    idx = bisect_right(entries, dt_date, key=lambda e: e[0])
    return entries[idx - 1][1] if idx > 0 else 0.0

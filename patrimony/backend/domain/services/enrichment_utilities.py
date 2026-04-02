"""Shared enrichment utilities for securities DataFrames.

Provides price enrichment and currency conversion logic
used by both PortfolioService and SecuritiesService.
"""

import logging
from datetime import date, datetime

import polars as pl

from ..repositories import PriceRepository
from .currency_service import CurrencyService

logger = logging.getLogger(__name__)


def enrich_with_prices(df: pl.DataFrame, price_repo: PriceRepository) -> pl.DataFrame:
    """Add current_price (and total_value if applicable) columns to a DataFrame of positions."""
    if df is None or df.is_empty() or "ticker" not in df.columns:
        return df

    tickers = df["ticker"].to_list()
    prices = []
    for ticker in tickers:
        try:
            prices.append(price_repo.get_current_price(ticker))
        except Exception as e:
            logger.error("Error fetching price for %s: %s", ticker, e)
            prices.append(None)

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

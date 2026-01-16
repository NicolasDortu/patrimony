"""Portfolio analysis and market data fetching."""

import polars as pl
from typing import Optional

from ..database.queries import PriceCacheOperations, PriceHistoryOperations
from ..infrastructure.market_data_provider import (
    fetch_current_price,
    fetch_price_history,
)


def fetch_and_cache_price(
    ticker: str, price_cache: PriceCacheOperations
) -> Optional[float]:
    """Fetch price from API and store in cache."""
    price = fetch_current_price(ticker)
    if price is not None:
        price_cache.upsert_price(ticker, price)
    return price


def get_price_with_cache(
    ticker: str, price_cache: PriceCacheOperations, force_refresh: bool = False
) -> Optional[float]:
    """Get price from cache, or fetch if not available or forced refresh."""
    if not force_refresh:
        cached_price = price_cache.get_cached_price(ticker)
        if cached_price is not None:
            return cached_price
    return fetch_and_cache_price(ticker, price_cache)


def fetch_and_cache_history(
    ticker: str, period: str, history_cache: PriceHistoryOperations
) -> pl.DataFrame:
    """Fetch history from API and store in cache."""
    history = fetch_price_history(ticker, period)
    if not history.is_empty():
        history_cache.upsert_history(ticker, period, history)
    return history


def get_history_with_cache(
    ticker: str,
    period: str,
    history_cache: PriceHistoryOperations,
    force_refresh: bool = False,
) -> pl.DataFrame:
    """Get price history from cache, fetching only new data since last update.

    This function implements incremental updates:
    - If force_refresh: fetches full history and replaces cache
    - Otherwise: fetches from API but only inserts new records after last cached date
    """
    if force_refresh:
        history_cache.delete_history(ticker, period)
        return fetch_and_cache_history(ticker, period, history_cache)

    # Always try to fetch new data - upsert_history will only insert new records
    history = fetch_price_history(ticker, period)
    if not history.is_empty():
        history_cache.upsert_history(ticker, period, history)

    # Return full cached history
    return history_cache.get_cached_history(ticker, period)


def refresh_all_prices(
    tickers: list[str], price_cache: PriceCacheOperations
) -> dict[str, Optional[float]]:
    """Refresh prices for all tickers from API and update cache."""
    prices = {}
    for ticker in tickers:
        prices[ticker] = fetch_and_cache_price(ticker, price_cache)
    return prices

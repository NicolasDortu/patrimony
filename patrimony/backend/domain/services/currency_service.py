"""Domain service for currency resolution and exchange rate conversion."""

import logging
from typing import Optional

import polars as pl

from ..interfaces import MarketDataProvider
from ..repositories import CurrencyRepository

logger = logging.getLogger(__name__)


class CurrencyService:
    """Domain service for currency resolution and exchange rate conversion."""

    def __init__(
        self,
        currency_repo: CurrencyRepository,
        market_data_provider: MarketDataProvider,
    ):
        self._currency_repo = currency_repo
        self._market_data = market_data_provider

    def get_ticker_currency(self, ticker: str) -> str:
        """Get the native currency of a ticker from cache if available or fetch from market data."""
        cached = self._currency_repo.get_ticker_currency(ticker)
        if cached:
            return cached

        currency = self._market_data.get_ticker_currency(ticker)
        if currency:
            self._currency_repo.set_ticker_currency(ticker, currency)
            return currency

        logger.warning(
            "Could not fetch currency for ticker %s, defaulting to EUR", ticker
        )

        return "EUR"  # Default to EUR

    def get_exchange_rate(self, from_currency: str, to_currency: str) -> float:
        """Get exchange rate to convert from from_currency to to_currency."""
        if from_currency == to_currency:
            return 1.0

        cached = self._currency_repo.get_exchange_rate(from_currency, to_currency)
        if cached is not None:
            return cached

        rate = self._market_data.get_exchange_rate(from_currency, to_currency)

        if rate and rate > 0:
            self._currency_repo.set_exchange_rate(from_currency, to_currency, rate)
            return rate

        logger.warning(
            "Could not fetch exchange rate %s -> %s, using 1.0",
            from_currency,
            to_currency,
        )
        return 1.0

    def get_rates_for_tickers(
        self, tickers: list[str], user_currency: str
    ) -> dict[str, float]:
        """Get exchange rates for all tickers to convert to user's currency.

        Returns:
            dict[ticker, rate] where value_in_user_currency = value_in_native * rate.
        """
        rates: dict[str, float] = {}
        rate_cache: dict[str, float] = {}

        for ticker in tickers:
            ticker_curr = self.get_ticker_currency(ticker)
            if ticker_curr == user_currency:
                rates[ticker] = 1.0
            else:
                if ticker_curr not in rate_cache:
                    rate_cache[ticker_curr] = self.get_exchange_rate(
                        ticker_curr, user_currency
                    )
                rates[ticker] = rate_cache[ticker_curr]

        return rates

    def apply_conversion(self, df: pl.DataFrame, user_currency: str) -> pl.DataFrame:
        """Convert current_price and avg_price to user_currency, recompute total_value."""
        tickers = df["ticker"].to_list()
        rates = self.get_rates_for_tickers(tickers, user_currency)
        rate_list = pl.Series("_rate", [rates.get(t, 1.0) for t in tickers])
        df = df.with_columns(
            (pl.col("current_price") * rate_list).alias("current_price"),
            (pl.col("avg_price") * rate_list).alias("avg_price"),
        )
        return df.with_columns(
            (pl.col("current_price") * pl.col("total_quantity")).alias("total_value")
        )

    def sum_with_conversion(
        self,
        df: Optional[pl.DataFrame],
        value_col: str,
        target_currency: str,
    ) -> float:
        """Sum a DataFrame column, converting each row's currency to target_currency."""
        if df is None or df.is_empty():
            return 0.0
        if "currency" not in df.columns:
            return float(df[value_col].sum())
        total = 0.0
        rate_cache: dict[str, float] = {}
        for row in df.iter_rows(named=True):
            curr = row.get("currency", "EUR") or "EUR"
            if curr not in rate_cache:
                rate_cache[curr] = self.get_exchange_rate(curr, target_currency)
            total += row[value_col] * rate_cache[curr]
        return total

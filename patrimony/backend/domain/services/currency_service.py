"""Domain service for currency resolution and exchange rate conversion."""

import logging
import time

import polars as pl

from ..exceptions import CurrencyConversionError, TickerCurrencyUnknownError
from ..interfaces import MarketDataProvider
from ..repositories import CurrencyRepository

logger = logging.getLogger(__name__)

# ~30 days of staleness as a fallback when the live FX provider is unreachable.
_STALE_FX_MAX_AGE_MINUTES = 60 * 24 * 30
# In-process FX cache TTL — short enough that user sees fresh rates after a
# refresh, long enough to avoid hammering the repo on a single page render.
_PROCESS_CACHE_TTL_S = 15 * 60


class CurrencyService:
    """Domain service for currency resolution and exchange rate conversion."""

    def __init__(
        self,
        currency_repo: CurrencyRepository,
        market_data_provider: MarketDataProvider,
    ):
        self._currency_repo = currency_repo
        self._market_data = market_data_provider
        # (from, to) -> (rate, monotonic_timestamp)
        self._rate_cache: dict[tuple[str, str], tuple[float, float]] = {}
        # ticker -> currency (immutable per ticker, no TTL needed)
        self._ticker_currency_cache: dict[str, str] = {}

    def get_ticker_currency(self, ticker: str) -> str:
        """Resolve the native currency of a ticker."""
        if ticker in self._ticker_currency_cache:
            return self._ticker_currency_cache[ticker]

        cached = self._currency_repo.get_ticker_currency(ticker)
        if cached:
            self._ticker_currency_cache[ticker] = cached
            return cached

        try:
            currency = self._market_data.get_ticker_currency(ticker)
        except Exception as e:
            logger.warning("Provider error fetching currency for %s: %s", ticker, e)
            currency = None

        if currency:
            self._currency_repo.set_ticker_currency(ticker, currency)
            self._ticker_currency_cache[ticker] = currency
            return currency

        raise TickerCurrencyUnknownError(ticker)

    def get_exchange_rate(self, from_currency: str, to_currency: str) -> float:
        """Resolve an exchange rate, preferring fresh data but accepting stale.

        Resolution order:
            1. Identity (same currency).
            2. In-process cache (< _PROCESS_CACHE_TTL_S).
            3. Fresh repo cache (< default repo TTL).
            4. Live provider (cache on success).
            5. Stale repo cache (up to ~30 days).
        """
        if from_currency == to_currency:
            return 1.0

        key = (from_currency, to_currency)
        cached_entry = self._rate_cache.get(key)
        if cached_entry is not None:
            rate, ts = cached_entry
            if time.monotonic() - ts < _PROCESS_CACHE_TTL_S:
                return rate

        cached = self._currency_repo.get_exchange_rate(from_currency, to_currency)
        if cached is not None and cached > 0:
            self._rate_cache[key] = (cached, time.monotonic())
            return cached

        try:
            rate = self._market_data.get_exchange_rate(from_currency, to_currency)
        except Exception as e:
            logger.warning(
                "Provider error fetching FX rate %s -> %s: %s",
                from_currency,
                to_currency,
                e,
            )
            rate = None

        if rate and rate > 0:
            self._currency_repo.set_exchange_rate(from_currency, to_currency, rate)
            self._rate_cache[key] = (rate, time.monotonic())
            return rate

        stale = self._currency_repo.get_exchange_rate(
            from_currency, to_currency, max_age_minutes=_STALE_FX_MAX_AGE_MINUTES
        )
        if stale is not None and stale > 0:
            logger.warning(
                "Using stale FX rate for %s -> %s (live provider unavailable)",
                from_currency,
                to_currency,
            )
            return stale

        raise CurrencyConversionError(from_currency, to_currency)

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
            try:
                ticker_curr = self.get_ticker_currency(ticker)
            except TickerCurrencyUnknownError as e:
                logger.error("%s; using rate=1.0 (values may be incorrect)", e)
                rates[ticker] = 1.0
                continue

            if ticker_curr == user_currency:
                rates[ticker] = 1.0
                continue

            if ticker_curr not in rate_cache:
                try:
                    rate_cache[ticker_curr] = self.get_exchange_rate(
                        ticker_curr, user_currency
                    )
                except CurrencyConversionError as e:
                    logger.error("%s; using rate=1.0 (values may be incorrect)", e)
                    rate_cache[ticker_curr] = 1.0
            rates[ticker] = rate_cache[ticker_curr]

        return rates

    def apply_conversion(self, df: pl.DataFrame, user_currency: str) -> pl.DataFrame:
        """Convert price columns to user_currency, recompute total_value.

        Converts ``current_price``, ``avg_price`` and ``total_fees`` (if present) from each position's native currency.
        """
        tickers = df["ticker"].to_list()
        rates = self.get_rates_for_tickers(tickers, user_currency)
        rate_list = pl.Series("_rate", [rates.get(t, 1.0) for t in tickers])
        new_cols = [
            (pl.col("current_price") * rate_list).alias("current_price"),
            (pl.col("avg_price") * rate_list).alias("avg_price"),
        ]
        if "total_fees" in df.columns:
            new_cols.append((pl.col("total_fees") * rate_list).alias("total_fees"))
        df = df.with_columns(new_cols)
        return df.with_columns(
            (pl.col("current_price") * pl.col("total_quantity")).alias("total_value")
        )

    def sum_with_conversion(
        self,
        df: pl.DataFrame,
        value_col: str,
        target_currency: str,
    ) -> float:
        """Sum a DataFrame column, converting each row's currency to target_currency."""
        if df.is_empty():
            return 0.0
        if "currency" not in df.columns:
            return float(df[value_col].sum())
        total = 0.0
        rate_cache: dict[str, float] = {}
        for row in df.iter_rows(named=True):
            curr = row.get("currency", target_currency) or target_currency
            if curr not in rate_cache:
                try:
                    rate_cache[curr] = self.get_exchange_rate(curr, target_currency)
                except CurrencyConversionError as e:
                    logger.error("%s; using rate=1.0 (values may be incorrect)", e)
                    rate_cache[curr] = 1.0
            total += row[value_col] * rate_cache[curr]
        return total

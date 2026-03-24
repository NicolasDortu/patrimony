"""Domain service for currency resolution and exchange rate conversion."""

import logging

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
        """Get the native currency of a ticker, caching the result."""
        cached = self._currency_repo.get_ticker_currency(ticker)
        if cached:
            return cached

        currency = self._market_data.get_ticker_currency(ticker)
        if currency:
            self._currency_repo.set_ticker_currency(ticker, currency)
            return currency.upper()

        return "USD"

    def get_exchange_rate(self, from_currency: str, to_currency: str) -> float:
        """Get exchange rate to convert from from_currency to to_currency."""
        if from_currency.upper() == to_currency.upper():
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

        Returns {ticker: rate} where value_in_user_currency = value_in_native * rate.
        """
        rates: dict[str, float] = {}
        rate_cache: dict[str, float] = {}

        for ticker in tickers:
            ticker_curr = self.get_ticker_currency(ticker)
            if ticker_curr.upper() == user_currency.upper():
                rates[ticker] = 1.0
            else:
                if ticker_curr not in rate_cache:
                    rate_cache[ticker_curr] = self.get_exchange_rate(
                        ticker_curr, user_currency
                    )
                rates[ticker] = rate_cache[ticker_curr]

        return rates

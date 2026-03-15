"""Currency Controller - Thin wrapper around CurrencyService."""

from ..di_container import container


class CurrencyController:
    """Controller for currency conversion operations."""

    @property
    def _currency_service(self):
        return container.currency_service()

    def get_ticker_currency(self, ticker: str) -> str:
        return self._currency_service.get_ticker_currency(ticker)

    def get_exchange_rate(self, from_currency: str, to_currency: str) -> float:
        return self._currency_service.get_exchange_rate(from_currency, to_currency)

    def get_rates_for_tickers(
        self, tickers: list[str], user_currency: str
    ) -> dict[str, float]:
        return self._currency_service.get_rates_for_tickers(tickers, user_currency)

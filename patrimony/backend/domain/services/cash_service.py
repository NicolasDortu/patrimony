"""Domain service for cash account business logic.

Handles balance aggregation, currency conversion, and historical timeline.
"""

from ..repositories import CashRepository
from .currency_service import CurrencyService


class CashService:
    """Domain service for cash accounts."""

    def __init__(
        self,
        cash_repo: CashRepository,
        currency_service: CurrencyService,
    ):
        self._cash_repo = cash_repo
        self._currency_service = currency_service

    def get_total_balance(self, user_currency: str) -> float:
        """Get total cash balance converted to user_currency."""
        return self._currency_service.sum_with_conversion(
            self._cash_repo.get_all(), "balance", user_currency
        )

    def get_balance_timeline(self, user_currency: str) -> dict:
        """Build a timeline of total cash balance keyed by date."""
        df = self._cash_repo.get_cash_balance_history()
        if df is None or df.is_empty():
            return {}

        account_currencies: dict[str, str] = {}
        all_cash = self._cash_repo.get_all()
        if all_cash is not None:
            for row in all_cash.iter_rows(named=True):
                account_currencies[row["account_number"]] = row.get("currency", "EUR")

        rate_cache: dict[str, float] = {}
        account_balances: dict[str, float] = {}
        timeline: dict = {}

        for row in df.iter_rows(named=True):
            key = row["account_number"]
            cash_curr = account_currencies.get(key, "EUR")
            if cash_curr not in rate_cache:
                rate_cache[cash_curr] = self._currency_service.get_exchange_rate(
                    cash_curr, user_currency
                )

            account_balances[key] = row["balance"] * rate_cache[cash_curr]
            timeline[row["operation_date"]] = sum(account_balances.values())

        return timeline

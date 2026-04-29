"""Domain service for property business logic.

Handles property value aggregation with currency conversion.
"""

from ..repositories import PropertyRepository
from .currency_service import CurrencyService


class PropertyService:
    """Domain service for physical properties."""

    def __init__(
        self,
        property_repo: PropertyRepository,
        currency_service: CurrencyService,
    ):
        self._property_repo = property_repo
        self._currency_service = currency_service

    def get_total_value(self, user_currency: str) -> float:
        """Get total property value converted to user_currency."""
        df = self._property_repo.get_total_value_by_currency()
        return self._currency_service.sum_with_conversion(
            df, "total_value", user_currency
        )

    def get_value_timeline(self, user_currency: str) -> dict:
        """Build a step-function timeline of total property value keyed by purchase date."""
        df = self._property_repo.get_all()
        if df.is_empty():
            return {}

        rate_cache: dict[str, float] = {}
        rows = sorted(df.iter_rows(named=True), key=lambda r: r["purchase_date"])

        timeline: dict = {}
        cumulative = 0.0
        for row in rows:
            currency = row.get("currency") or "EUR"
            if currency not in rate_cache:
                rate_cache[currency] = self._currency_service.get_exchange_rate(
                    currency, user_currency
                )
            cumulative += float(row["value"]) * rate_cache[currency]
            timeline[row["purchase_date"]] = cumulative

        return timeline

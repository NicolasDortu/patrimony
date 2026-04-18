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

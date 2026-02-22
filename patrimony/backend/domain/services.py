"""Domain services - Advanced business logic."""

from typing import Tuple


class MetricsCalculator:
    """Domain service for portfolio metrics calculation."""

    @staticmethod
    def calculate_metrics(
        quantities: list[float],
        buy_prices: list[float],
        current_prices: list[float],
    ) -> Tuple[float, float, float]:
        """Calculate total invested, current value, and return percentage across multiple positions."""
        total_invested = sum(q * p for q, p in zip(quantities, buy_prices))
        total_value = sum(q * p for q, p in zip(quantities, current_prices))
        return_percentage = (
            ((total_value - total_invested) / total_invested * 100)
            if total_invested > 0
            else 0.0
        )
        return total_invested, total_value, return_percentage

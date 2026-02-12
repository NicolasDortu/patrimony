"""Domain services - Business logic that doesn't fit in entities or repositories."""

import polars as pl
from typing import Tuple


class PortfolioCalculator:
    """Domain service for portfolio metrics calculation."""

    @staticmethod
    def calculate_metrics(positions: pl.DataFrame) -> Tuple[float, float, float]:
        """Calculate total invested, current value, and return percentage.

        Works with both individual positions and aggregated positions.
        - Individual: uses 'price', 'quantity', 'current_price'
        - Aggregated: uses 'avg_price', 'total_quantity', 'current_price'

        Args:
            positions: DataFrame with position data

        Returns:
            Tuple of (total_invested, total_value, return_percentage)
        """
        if positions.is_empty():
            return 0.0, 0.0, 0.0

        # Detect which columns are available
        has_aggregated = "total_quantity" in positions.columns
        quantity_col = "total_quantity" if has_aggregated else "quantity"
        price_col = "avg_price" if has_aggregated else "price"

        total_invested = (positions[price_col] * positions[quantity_col]).sum()
        total_value = (positions["current_price"] * positions[quantity_col]).sum()

        return_percentage = (
            ((total_value - total_invested) / total_invested * 100)
            if total_invested > 0
            else 0.0
        )

        return total_invested, total_value, return_percentage

    @staticmethod
    def calculate_position_pnl(
        quantity: float, entry_price: float, current_price: float
    ) -> Tuple[float, float]:
        """Calculate profit/loss for a single position.

        Args:
            quantity: Number of shares/units
            entry_price: Purchase price
            current_price: Current market price

        Returns:
            Tuple of (absolute_pnl, percentage_pnl)
        """
        invested = quantity * entry_price
        current_value = quantity * current_price
        absolute_pnl = current_value - invested
        percentage_pnl = (absolute_pnl / invested * 100) if invested > 0 else 0.0

        return absolute_pnl, percentage_pnl

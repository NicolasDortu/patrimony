import polars as pl


def calculate_portfolio_metrics(positions: pl.DataFrame) -> tuple[float, float, float]:
    """Calculate total invested, current value, and return."""
    total_invested = (positions["price"] * positions["quantity"]).sum()
    total_value = (positions["current_price"] * positions["quantity"]).sum()
    total_return = (
        ((total_value - total_invested) / total_invested * 100)
        if total_invested > 0
        else 0
    )
    return total_invested, total_value, total_return

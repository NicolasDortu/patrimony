"""State management for portfolio data and wealth visualization."""

import datetime
from typing import Literal

import reflex as rx

from ..services import PortfolioService


AssetFilter = Literal["all", "stocks", "cash"]


class PortfolioState(rx.State):
    """Manage portfolio data and visualization state."""

    asset_filter: AssetFilter = "all"
    chart_type: str = "area"

    # Raw data (stored as list[dict] from API)
    _stocks_total_data: list[dict] = []
    _cash_data: list[dict] = []

    # Chart data
    wealth_chart_data: list[dict] = []
    allocation_data: list[dict] = []

    # KPI metrics
    total_value: float = 0.0
    total_invested: float = 0.0
    total_return: float = 0.0
    stocks_value: float = 0.0
    cash_value: float = 0.0

    # Top/Bottom performers
    top_performers: list[dict] = []
    bottom_performers: list[dict] = []

    @rx.var
    def total_value_formatted(self) -> str:
        """Format total value for display."""
        return f"€{self.total_value:,.2f}"

    @rx.var
    def stocks_value_formatted(self) -> str:
        """Format stocks value for display."""
        return f"€{self.stocks_value:,.2f}"

    @rx.var
    def cash_value_formatted(self) -> str:
        """Format cash value for display."""
        return f"€{self.cash_value:,.2f}"

    @rx.var
    def total_return_formatted(self) -> str:
        """Format total return percentage for display."""
        return f"{abs(self.total_return):.2f}%"

    @rx.event
    async def load_portfolio_data(self):
        """Load all portfolio data from models service."""
        # Fetch aggregated data from service
        portfolio_data = PortfolioService.get_portfolio_overview()

        # Store raw data
        self._stocks_total_data = portfolio_data.securities_total
        self._cash_data = portfolio_data.cash_entries

        # Store calculated metrics
        self.total_value = portfolio_data.total_value
        self.total_invested = portfolio_data.total_invested
        self.total_return = portfolio_data.total_return
        self.stocks_value = portfolio_data.securities_value
        self.cash_value = portfolio_data.cash_value

        # Prepare UI data
        self._prepare_chart_data()
        self._calculate_performers()
        self._calculate_allocation()

    def _prepare_chart_data(self):
        """Prepare time-series data for wealth chart."""
        chart_data = []

        # Generate historical data for the last 30 days
        for i in range(30, -1, -1):
            date = (datetime.datetime.now() - datetime.timedelta(days=i)).strftime(
                "%m-%d"
            )

            # Simulate historical values with some variation
            # TODO: Display real data
            day_factor = 1 - (i * 0.01)  # Gradual growth simulation

            data_point = {"Date": date}

            if self.asset_filter == "all" or self.asset_filter == "stocks":
                stocks_val = self.stocks_value * day_factor
                data_point["Stocks"] = round(stocks_val, 2)

            if self.asset_filter == "all" or self.asset_filter == "cash":
                cash_val = self.cash_value * (0.98 + (i * 0.0005))
                data_point["Cash"] = round(cash_val, 2)

            if self.asset_filter == "all":
                data_point["Total"] = round(
                    data_point.get("Stocks", 0) + data_point.get("Cash", 0), 2
                )

            chart_data.append(data_point)

        self.wealth_chart_data = chart_data

    def _calculate_performers(self):
        """Calculate top and bottom performing assets."""
        if not self._stocks_total_data:
            self.top_performers = []
            self.bottom_performers = []
            return

        # Calculate return percentage for each position
        performers = []
        for stock in self._stocks_total_data:
            if (
                stock.get("current_price")
                and stock.get("avg_price")
                and stock.get("total_quantity")
            ):
                return_pct = (
                    (stock["current_price"] - stock["avg_price"])
                    / stock["avg_price"]
                    * 100
                )
                value = stock["current_price"] * stock["total_quantity"]

                performers.append(
                    {
                        "ticker": stock["ticker"],
                        "return": round(return_pct, 2),
                        "return_formatted": f"{return_pct:+.2f}%",
                        "value": round(value, 2),
                        "value_formatted": f"€{value:,.2f}",
                        "color": "grass" if return_pct >= 0 else "tomato",
                        "icon": "trending-up" if return_pct >= 0 else "trending-down",
                    }
                )

        # Sort by return percentage
        performers.sort(key=lambda x: x["return"], reverse=True)

        # Top 3 and bottom 3
        self.top_performers = performers[:3] if len(performers) >= 3 else performers
        self.bottom_performers = (
            list(reversed(performers[-3:])) if len(performers) >= 3 else []
        )

    def _calculate_allocation(self):
        """Calculate asset allocation for pie chart."""
        allocation = []

        if self.stocks_value > 0:
            allocation.append(
                {
                    "name": "Stocks",
                    "value": round(self.stocks_value, 2),
                    "percentage": round((self.stocks_value / self.total_value * 100), 2)
                    if self.total_value > 0
                    else 0,
                    "fill": "var(--blue-9)",
                }
            )

        if self.cash_value > 0:
            allocation.append(
                {
                    "name": "Cash",
                    "value": round(self.cash_value, 2),
                    "percentage": round((self.cash_value / self.total_value * 100), 2)
                    if self.total_value > 0
                    else 0,
                    "fill": "var(--green-9)",
                }
            )

        self.allocation_data = allocation

    @rx.event
    async def set_asset_filter(self, filter_value: str | list[str]):
        """Change asset type filter and refresh chart."""
        # Handle both single value and list from segmented control
        if isinstance(filter_value, list):
            filter_value = filter_value[0] if filter_value else "all"
        self.asset_filter = filter_value
        self._prepare_chart_data()

    @rx.event
    def toggle_chart_type(self):
        """Toggle between area and bar chart."""
        self.chart_type = "bar" if self.chart_type == "area" else "area"

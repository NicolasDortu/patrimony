"""State management for portfolio data and wealth visualization."""

from typing import Literal

import reflex as rx

from ..services import PortfolioService


AssetFilter = Literal["all", "stocks", "etfs", "crypto", "commodity", "cash"]


class PortfolioState(rx.State):
    """Manage portfolio data and visualization state."""

    # Filters
    asset_filter: AssetFilter = "all"
    chart_type: str = "area"
    selected_period: str = "1M"

    # Raw data (stored as list[dict] from API)
    _stocks_total_data: list[dict] = []
    _cash_data: list[dict] = []
    _chart_data: list[dict] = []

    # KPI metrics
    total_value: float = 0.0
    total_invested: float = 0.0
    total_return: float = 0.0
    stocks_value: float = 0.0
    cash_value: float = 0.0

    ####################
    ### Wealth Chart ###
    ####################
    def _load_chart_data(self):
        """Fetch price history and build chart data."""
        self._chart_data = PortfolioService.get_chart_data(self.selected_period)

    @rx.var
    def get_chart_data(self) -> list[dict]:
        """Get the wealth chart data."""
        return self._chart_data

    @rx.event
    async def set_asset_filter(self, filter_value: str | list[str]):
        """Change asset type filter and refresh chart display."""
        self.asset_filter = filter_value

    @rx.event
    async def set_period(self, period: str | list[str]):
        """Change time period and refresh chart data."""
        self.selected_period = period
        self._load_chart_data()

    @rx.event
    def toggle_chart_type(self):
        """Toggle between area and bar chart."""
        self.chart_type = "bar" if self.chart_type == "area" else "area"

    #######################
    ### Performers data ###
    #######################
    def _calculate_performer(self, stock: dict) -> dict | None:
        """Calculate performance metrics for a single stock."""
        if not all(
            stock.get(key) for key in ("current_price", "avg_price", "total_quantity")
        ):
            return None

        return_pct = (
            (stock["current_price"] - stock["avg_price"]) / stock["avg_price"] * 100
        )

        return {
            "ticker": stock["ticker"],
            "return": round(return_pct, 2),
            "value": round(stock["current_price"] * stock["total_quantity"], 2),
            "color": "grass" if return_pct >= 0 else "tomato",
            "icon": "trending-up" if return_pct >= 0 else "trending-down",
        }

    @rx.var
    def sorted_performers(self) -> list[dict]:
        """Helper to calculate and sort all performers."""
        if not self._stocks_total_data:
            return []

        performers = [
            performer
            for stock in self._stocks_total_data
            if (performer := self._calculate_performer(stock)) is not None
        ]

        return sorted(performers, key=lambda x: x["return"], reverse=True)

    @rx.var
    def top_performers(self) -> list[dict]:
        """Return top 3 performers."""
        return self.sorted_performers[:3]

    @rx.var
    def bottom_performers(self) -> list[dict]:
        """Return bottom 3 performers."""
        return self.sorted_performers[-3:][::-1]

    #######################
    ### Allocation data ###
    #######################
    def _calc_percentage(self, value: float) -> float:
        return round((value / self.total_value * 100), 2)

    @rx.var
    def allocation_data(self) -> list[dict]:
        """Calculate asset allocation for pie chart."""
        allocation = []

        if self.total_value > 0:
            # Group securities by asset_type
            asset_type_config = {
                "STOCK": ("Stocks", "var(--purple-9)"),
                "ETF": ("ETFs", "var(--orange-9)"),
                "CRYPTO": ("Crypto", "var(--yellow-9)"),
                "COMMODITY": ("Commodity", "var(--red-9)"),
            }
            asset_totals: dict[str, float] = {}
            for stock in self._stocks_total_data:
                at = stock.get("asset_type", "STOCK")
                val = stock.get("total_value") or 0.0
                if val > 0:
                    asset_totals[at] = asset_totals.get(at, 0.0) + val

            for at, total in asset_totals.items():
                label, fill = asset_type_config.get(at, (at, "var(--blue-9)"))
                allocation.append(
                    {
                        "name": label,
                        "value": round(total, 2),
                        "percentage": self._calc_percentage(total),
                        "fill": fill,
                    }
                )

            if self.cash_value > 0:
                allocation.append(
                    {
                        "name": "Cash",
                        "value": round(self.cash_value, 2),
                        "percentage": self._calc_percentage(self.cash_value),
                        "fill": "var(--green-9)",
                    }
                )
        else:
            allocation.append(
                {
                    "name": "No Data",
                    "value": 1,
                    "percentage": 100.0,
                    "fill": "var(--gray-5)",
                }
            )
        return allocation

    #################
    ### Load data ###
    #################
    @rx.event
    async def load_portfolio_data(self):
        """Load all portfolio data from models service."""
        portfolio_data = PortfolioService.get_portfolio_overview()

        self._stocks_total_data = portfolio_data.securities_total
        self._cash_data = portfolio_data.cash_entries

        self.total_value = portfolio_data.total_value
        self.total_invested = portfolio_data.total_invested
        self.total_return = portfolio_data.total_return
        self.stocks_value = portfolio_data.securities_value
        self.cash_value = portfolio_data.cash_value

        self._load_chart_data()

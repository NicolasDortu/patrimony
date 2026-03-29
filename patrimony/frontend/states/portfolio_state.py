"""State management for portfolio data and wealth visualization."""

from typing import Literal

import reflex as rx

from ..services import DividendService, PortfolioService, was_market_data_fetched
from ..templates import ThemeState


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
    _asset_colors: dict[str, str] = {}
    _dividends_data: list[dict] = []

    # Loading flag
    is_loaded: bool = False

    # KPI metrics
    total_value: float = 0.0
    total_invested: float = 0.0
    total_return: float = 0.0
    stocks_value: float = 0.0
    cash_value: float = 0.0

    ####################
    ### Asset types  ###
    ####################
    @rx.var
    def has_data(self) -> bool:
        return len(self._stocks_total_data) > 0 or self.cash_value > 0

    @rx.var
    def has_stocks(self) -> bool:
        return any(s.get("asset_type") == "STOCK" for s in self._stocks_total_data)

    @rx.var
    def has_etfs(self) -> bool:
        return any(s.get("asset_type") == "ETF" for s in self._stocks_total_data)

    @rx.var
    def has_crypto(self) -> bool:
        return any(s.get("asset_type") == "CRYPTO" for s in self._stocks_total_data)

    @rx.var
    def has_commodity(self) -> bool:
        return any(s.get("asset_type") == "COMMODITY" for s in self._stocks_total_data)

    @rx.var
    def has_cash(self) -> bool:
        return self.cash_value > 0

    # Expose asset color names for chart components
    @rx.var
    def stock_color(self) -> str:
        return self._asset_colors.get("STOCK", "purple")

    @rx.var
    def etf_color(self) -> str:
        return self._asset_colors.get("ETF", "orange")

    @rx.var
    def crypto_color(self) -> str:
        return self._asset_colors.get("CRYPTO", "yellow")

    @rx.var
    def commodity_color(self) -> str:
        return self._asset_colors.get("COMMODITY", "red")

    @rx.var
    def cash_color(self) -> str:
        return self._asset_colors.get("CASH", "green")

    @rx.var
    def available_filters(self) -> list[dict]:
        """Filter options based on owned asset types."""
        filters = [{"label": "All", "value": "all"}]
        type_config = [
            ("STOCK", "Stocks", "stocks"),
            ("ETF", "ETFs", "etfs"),
            ("CRYPTO", "Crypto", "crypto"),
            ("COMMODITY", "Commodity", "commodity"),
        ]
        owned = {s.get("asset_type") for s in self._stocks_total_data}
        for at, label, value in type_config:
            if at in owned:
                filters.append({"label": label, "value": value})
        if self.cash_value > 0:
            filters.append({"label": "Cash", "value": "cash"})
        return filters

    ####################
    ### Wealth Chart ###
    ####################
    async def _load_chart_data(self):
        """Fetch price history and build chart data."""
        theme_state = await self.get_state(ThemeState)
        self._chart_data = PortfolioService.get_chart_data(
            self.selected_period, theme_state.default_currency
        )

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
        await self._load_chart_data()

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

    def _get_asset_color_map(self) -> dict[str, str]:
        """Build asset_type -> CSS var color map from current color settings."""
        return {
            "STOCK": f"var(--{self._asset_colors.get('STOCK', 'purple')}-9)",
            "ETF": f"var(--{self._asset_colors.get('ETF', 'orange')}-9)",
            "CRYPTO": f"var(--{self._asset_colors.get('CRYPTO', 'yellow')}-9)",
            "COMMODITY": f"var(--{self._asset_colors.get('COMMODITY', 'red')}-9)",
            "CASH": f"var(--{self._asset_colors.get('CASH', 'green')}-9)",
            "NONE": "var(--gray-5)",
        }

    @rx.var
    def allocation_data(self) -> list[dict]:
        """Calculate asset allocation for pie chart."""
        allocation = []
        color_map = self._get_asset_color_map()

        if self.total_value > 0:
            # Group securities by asset_type
            asset_totals: dict[str, float] = {}
            for stock in self._stocks_total_data:
                at = stock.get("asset_type", "STOCK")
                val = stock.get("total_value") or 0.0
                if val > 0:
                    asset_totals[at] = asset_totals.get(at, 0.0) + val

            asset_type_labels = {
                "STOCK": "Stocks",
                "ETF": "ETFs",
                "CRYPTO": "Crypto",
                "COMMODITY": "Commodity",
            }

            for at, total in asset_totals.items():
                label = asset_type_labels.get(at, at)
                allocation.append(
                    {
                        "name": label,
                        "value": round(total, 2),
                        "percentage": self._calc_percentage(total),
                        "fill": color_map.get(at, "var(--blue-9)"),
                    }
                )

            if self.cash_value > 0:
                allocation.append(
                    {
                        "name": "Cash",
                        "value": round(self.cash_value, 2),
                        "percentage": self._calc_percentage(self.cash_value),
                        "fill": color_map.get("CASH", "var(--green-9)"),
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

    #####################
    ### Dividend data ###
    #####################
    @rx.var
    def total_dividends_received(self) -> str:
        """Total dividends received, formatted."""
        total = sum(d.get("amount", 0.0) for d in self._dividends_data)
        return f"{total:,.2f}"

    @rx.var
    def recent_dividends(self) -> list[dict]:
        """Return last 5 dividends sorted by date descending."""
        sorted_divs = sorted(
            self._dividends_data,
            key=lambda d: d.get("date", ""),
            reverse=True,
        )
        return [
            {
                "ticker": d.get("ticker", ""),
                "amount": f"{d.get('amount', 0.0):,.2f}",
                "date": str(d.get("date", ""))[:10],
            }
            for d in sorted_divs[:5]
        ]

    #################
    ### Load data ###
    #################
    @rx.event
    async def load_portfolio_data(self):
        """Load all portfolio data from models service."""
        self.is_loaded = False
        theme_state = await self.get_state(ThemeState)
        self._asset_colors = {
            "STOCK": theme_state.stock_color,
            "ETF": theme_state.etf_color,
            "CRYPTO": theme_state.crypto_color,
            "COMMODITY": theme_state.commodity_color,
            "CASH": theme_state.cash_color,
        }
        portfolio_data = PortfolioService.get_portfolio_overview(
            theme_state.default_currency
        )

        self._stocks_total_data = portfolio_data.securities_total
        self._cash_data = portfolio_data.cash_entries

        self.total_value = portfolio_data.total_value
        self.total_invested = portfolio_data.total_invested
        self.total_return = portfolio_data.total_return
        self.stocks_value = portfolio_data.securities_value
        self.cash_value = portfolio_data.cash_value

        await self._load_chart_data()
        self._dividends_data = DividendService.get_all_dividends()
        self.is_loaded = True
        if was_market_data_fetched():
            yield rx.toast.info("Market data refreshed", position="bottom-right")

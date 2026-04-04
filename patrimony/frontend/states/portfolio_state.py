"""State management for portfolio data and wealth visualization."""

import logging
from typing import Literal

import reflex as rx

from ..services import DividendService, PortfolioService, was_market_data_fetched
from ..templates import ThemeState

logger = logging.getLogger(__name__)


AssetFilter = Literal[
    "all", "stocks", "etfs", "crypto", "commodity", "cash", "properties"
]


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
    properties_value: float = 0.0
    _total_dividends: float = 0.0

    ####################
    ### Asset types  ###
    ####################
    @rx.var
    def has_data(self) -> bool:
        return (
            len(self._stocks_total_data) > 0
            or self.cash_value > 0
            or self.properties_value > 0
        )

    @rx.var
    def _owned_types(self) -> set[str]:
        return {s.get("asset_type") for s in self._stocks_total_data}

    @rx.var
    def has_stocks(self) -> bool:
        return "STOCK" in self._owned_types

    @rx.var
    def has_etfs(self) -> bool:
        return "ETF" in self._owned_types

    @rx.var
    def has_crypto(self) -> bool:
        return "CRYPTO" in self._owned_types

    @rx.var
    def has_commodity(self) -> bool:
        return "COMMODITY" in self._owned_types

    @rx.var
    def has_cash(self) -> bool:
        return self.cash_value > 0

    @rx.var
    def has_properties(self) -> bool:
        return self.properties_value > 0

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
    def property_color(self) -> str:
        return self._asset_colors.get("PROPERTY", "indigo")

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
        if self.properties_value > 0:
            filters.append({"label": "Properties", "value": "properties"})
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
    _ASSET_COLOR_DEFAULTS: dict[str, str] = {
        "STOCK": "purple",
        "ETF": "orange",
        "CRYPTO": "yellow",
        "COMMODITY": "red",
        "CASH": "green",
        "PROPERTY": "indigo",
    }

    def _calc_percentage(self, value: float) -> float:
        return round((value / self.total_value * 100), 2)

    def _get_asset_color_map(self) -> dict[str, str]:
        """Build asset_type -> CSS var color map from current color settings."""
        color_map = {
            at: f"var(--{self._asset_colors.get(at, default)}-9)"
            for at, default in self._ASSET_COLOR_DEFAULTS.items()
        }
        color_map["NONE"] = "var(--gray-5)"
        return color_map

    def _alloc_entry(self, name: str, value: float, fill: str) -> dict:
        """Build a single allocation entry."""
        return {
            "name": name,
            "value": round(value, 2),
            "percentage": self._calc_percentage(value),
            "fill": fill,
        }

    @rx.var
    def allocation_data(self) -> list[dict]:
        """Calculate asset allocation for pie chart."""
        if self.total_value <= 0:
            return [
                {
                    "name": "No Data",
                    "value": 1,
                    "percentage": 100.0,
                    "fill": "var(--gray-5)",
                }
            ]

        color_map = self._get_asset_color_map()
        allocation = []

        # Group securities by asset_type
        asset_totals: dict[str, float] = {}
        for stock in self._stocks_total_data:
            at = stock.get("asset_type", "STOCK")
            val = stock.get("total_value") or 0.0
            if val > 0:
                asset_totals[at] = asset_totals.get(at, 0.0) + val

        labels = {
            "STOCK": "Stocks",
            "ETF": "ETFs",
            "CRYPTO": "Crypto",
            "COMMODITY": "Commodity",
        }
        for at, total in asset_totals.items():
            allocation.append(
                self._alloc_entry(
                    labels.get(at, at), total, color_map.get(at, "var(--blue-9)")
                )
            )

        # Non-security assets
        for key, label, value in [
            ("CASH", "Cash", self.cash_value),
            ("PROPERTY", "Properties", self.properties_value),
        ]:
            if value > 0:
                allocation.append(self._alloc_entry(label, value, color_map[key]))

        return allocation

    #####################
    ### Dividend data ###
    #####################
    @rx.var
    def total_dividends_received(self) -> str:
        """Total dividends received, formatted."""
        return f"{self._total_dividends:,.2f}"

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
        try:
            theme_state = await self.get_state(ThemeState)
            self._asset_colors = {
                at: getattr(theme_state, f"{at.lower()}_color", default)
                for at, default in self._ASSET_COLOR_DEFAULTS.items()
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
            self.properties_value = portfolio_data.properties_value

            await self._load_chart_data()
            self._dividends_data = DividendService.get_all_dividends()
            self._total_dividends = DividendService.get_total_amount()
        except Exception as e:
            logger.error("Failed to load portfolio data: %s", e)
            yield rx.toast.error(
                f"Failed to load portfolio: {e}", position="top-center"
            )
        finally:
            self.is_loaded = True
        if was_market_data_fetched():
            yield rx.toast.info("Market data refreshed", position="bottom-right")

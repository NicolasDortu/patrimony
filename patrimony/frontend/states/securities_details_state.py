from typing import Union

import reflex as rx

from ..services import (
    SecuritiesService,
    SecurityPosition,
    EntryType,
    AssetType,
)
from ..templates import ThemeState
from .dividends_state import DividendsState
from .mixins import PaginationMixin


class TableStateDetails(PaginationMixin, rx.State):
    """The state class."""

    items: list[SecurityPosition] = []
    ticker: str = ""

    search_value: str = ""
    sort_value: str = ""
    sort_reverse: bool = False

    # Stock chart state
    selected_period: str = "6M"
    stock_chart_data: list[dict] = []

    @rx.event
    async def on_page_load(self) -> None:
        """Handle page load - get ticker from URL and load entries."""
        ticker = self.router.url.query_parameters.get("ticker", "")
        self.ticker = ticker
        self.load_entries()
        await self._load_chart_data()
        dividends_state = await self.get_state(DividendsState)
        dividends_state.ticker = ticker
        dividends_state.load_entries()

    @rx.event
    def set_ticker(self, ticker: str) -> None:
        """Set the ticker for detail view navigation from the total table."""
        self.ticker = ticker

    @rx.event
    def set_search_value(self, value: str) -> None:
        self.search_value = value

    @rx.event
    def set_sort_value(self, value: str) -> None:
        self.sort_value = value

    @rx.var
    def filtered_sorted_items(self) -> list[SecurityPosition]:
        items = self.items

        # Filter items based on selected item
        if self.sort_value:
            if self.sort_value in ["price"]:
                items = sorted(
                    items,
                    key=lambda item: float(getattr(item, self.sort_value)),
                    reverse=self.sort_reverse,
                )
            else:
                items = sorted(
                    items,
                    key=lambda item: str(getattr(item, self.sort_value)).lower(),
                    reverse=self.sort_reverse,
                )

        # Filter items based on search value
        if self.search_value:
            search_value = self.search_value.lower()
            items = [
                item
                for item in items
                if any(
                    search_value in str(getattr(item, attr)).lower()
                    for attr in [
                        "ticker",
                        "date",
                    ]
                )
            ]

        return items

    @rx.var(initial_value=[])
    def get_current_page(self) -> list[SecurityPosition]:
        start_index = self.offset
        end_index = start_index + self.limit
        return self.filtered_sorted_items[start_index:end_index]

    @rx.event
    def load_entries(self) -> None:
        positions = SecuritiesService.get_positions_by_ticker(self.ticker)
        self.items = [SecurityPosition(**pos) for pos in positions]
        self.total_items = len(self.items)

    def toggle_sort(self) -> None:
        self.sort_reverse = not self.sort_reverse
        self.load_entries()

    @rx.event
    def add_stock(self, form_data: dict) -> None:
        """Add a new stock position from form data."""
        result = SecuritiesService.add_position(
            ticker=form_data.get("ticker", "").upper(),
            price=float(form_data.get("price", 0)),
            quantity=float(form_data.get("quantity", 0)),
            entry_type=EntryType.MANUAL,
            asset_type=AssetType.STOCK,
            fees=float(form_data.get("fees", 0)),
        )

        if result.success:
            self.load_entries()
            return rx.toast.success(result.message, position="top-center")
        else:
            return rx.toast.error(result.message, position="top-center")

    @rx.event
    def delete_stock(self, id: Union[int, dict]) -> None:
        """Delete a stock position by ID
        args:
            id: The ID of the stock position to delete. Can be an int or a dict.
        """
        if isinstance(id, dict):
            id = id.get("id", "")

        result = SecuritiesService.delete_position(id)

        if result.success:
            self.load_entries()
            return rx.toast.success(result.message, position="top-center")
        else:
            return rx.toast.error(result.message, position="top-center")

    @rx.event
    def export_csv(self):
        positions = SecuritiesService.get_all_positions()
        columns = list(SecurityPosition.__dataclass_fields__.keys())

        header = ",".join(columns)
        rows = [",".join(str(pos[col]) for col in columns) for pos in positions]

        data = str(header + "\n" + "\n".join(rows))
        return rx.download(data=data, filename="positions.csv")

    async def _load_chart_data(self):
        """Fetch stock price history for the chart."""
        if self.ticker:
            theme_state = await self.get_state(ThemeState)
            self.stock_chart_data = SecuritiesService.get_chart_data_ticker(
                self.ticker, self.selected_period, theme_state.default_currency
            )
        else:
            self.stock_chart_data = []

    @rx.event
    async def set_chart_period(self, period: str | list[str]):
        """Change chart period and refresh data."""
        if isinstance(period, list):
            period = period[0] if period else "1Y"
        self.selected_period = period
        await self._load_chart_data()

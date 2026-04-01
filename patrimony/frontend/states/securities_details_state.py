from typing import Union

import reflex as rx

from datetime import datetime

from ..services import (
    SecuritiesService,
    SecurityPosition,
    EntryType,
    AssetType,
    was_market_data_fetched,
)
from ..templates import ThemeState
from ..utils import tauri_save_file
from .dividends_state import DividendsState
from .mixins import PaginationMixin, SearchSortMixin, apply_sort_and_search
from .spreadsheet_mixin import SpreadsheetMixin


class TableStateDetails(SpreadsheetMixin, SearchSortMixin, PaginationMixin, rx.State):
    """The state class."""

    items: list[SecurityPosition] = []
    ticker: str = ""
    is_loading: bool = False

    # Stock chart state
    selected_period: str = "6M"
    stock_chart_data: list[dict] = []

    # Current price from aggregated data
    current_price: float = 0.0

    @rx.event
    async def on_page_load(self):
        """Handle page load - get ticker from URL and load entries."""
        self.is_loading = True
        yield
        ticker = self.router.url.query_parameters.get("ticker", "")
        self.ticker = ticker
        self.load_entries()
        await self._load_chart_data()
        # Load current price from aggregated positions
        theme_state = await self.get_state(ThemeState)
        agg = SecuritiesService.get_aggregated_positions(theme_state.default_currency)
        for pos in agg:
            if pos.get("ticker", "").upper() == ticker.upper():
                self.current_price = pos.get("current_price", 0.0) or 0.0
                break
        dividends_state = await self.get_state(DividendsState)
        dividends_state.ticker = ticker
        dividends_state.load_entries()
        self.is_loading = False
        if was_market_data_fetched():
            yield rx.toast.info("Market data refreshed", position="bottom-right")

    @rx.event
    def set_ticker(self, ticker: str) -> None:
        """Set the ticker for detail view navigation from the total table."""
        self.ticker = ticker

    @rx.var
    def filtered_sorted_items(self) -> list[SecurityPosition]:
        return apply_sort_and_search(
            self.items,
            self.sort_value,
            self.sort_reverse,
            self.search_value,
            numeric_sort_fields=["price"],
            search_fields=["ticker", "date"],
            accessor="attr",
        )

    @rx.var(initial_value=[])
    def get_current_page(self) -> list[SecurityPosition]:
        return self.filtered_sorted_items[self.offset : self.offset + self.limit]

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
        return tauri_save_file(data, "positions.csv")

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

    # ── Spreadsheet mode ──

    @rx.var
    def spreadsheet_columns(self) -> list[dict]:
        return [
            {"title": "Price", "type": "float"},
            {"title": "Quantity", "type": "float"},
            {"title": "Fees", "type": "float"},
            {"title": "Date", "type": "str"},
        ]

    def _load_spreadsheet_rows(self) -> tuple[list[list], list]:
        positions = SecuritiesService.get_positions_by_ticker(self.ticker)
        data = [
            [
                p.get("price", 0.0),
                p.get("quantity", 1.0),
                p.get("fees", 0.0),
                str(p.get("date", ""))[:10],
            ]
            for p in positions
        ]
        ids = [p.get("id") for p in positions]
        return data, ids

    def _save_spreadsheet_row(self, row, index, rid, is_new):
        price = float(row[0]) if row[0] != "" else 0.0
        quantity = float(row[1]) if row[1] != "" else 1.0
        fees = float(row[2]) if row[2] != "" else 0.0
        date_str = str(row[3]).strip()
        date = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()
        if is_new:
            if price == 0.0 and quantity == 0.0:
                return "skip"
            SecuritiesService.add_position(
                ticker=self.ticker,
                price=price,
                quantity=quantity,
                entry_type=EntryType.MANUAL,
                asset_type=AssetType.STOCK,
                date=date,
                fees=fees,
            )
        else:
            SecuritiesService.update_position(
                id=rid,
                ticker=self.ticker,
                price=price,
                quantity=quantity,
                entry_type=EntryType.MANUAL,
                asset_type=AssetType.STOCK,
                date=date,
                fees=fees,
            )
        return None

    def _delete_spreadsheet_row(self, rid):
        SecuritiesService.delete_position(rid)

    async def _after_spreadsheet_save(self):
        self.load_entries()

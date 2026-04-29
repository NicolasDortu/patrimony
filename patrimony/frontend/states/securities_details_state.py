from typing import Union
import logging

import reflex as rx

from ..services import (
    DividendService,
    SecuritiesService,
    SecurityPosition,
    EntryType,
    AssetType,
    was_market_data_fetched,
)
from ..templates import ThemeState
from ..utils import export_csv
from .dividends_state import DividendsState
from .mixins import PaginationMixin, SearchSortMixin, apply_sort_and_search
from .securities_total_state import TableStateTotal
from .spreadsheet_helpers import cell_date, cell_float, fmt_date_cell
from .spreadsheet_mixin import SpreadsheetMixin

logger = logging.getLogger(__name__)


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
        try:
            ticker = self.router.url.query_parameters.get("ticker", "")
            if not ticker:
                # Also try page.params as fallback
                ticker = self.router.page.params.get("ticker", "")
            if not ticker:
                logger.warning("No ticker in URL, redirecting to securities list")
                self.is_loading = False
                yield rx.redirect("/securities")
                return
            self.ticker = ticker
            self.load_entries()
            await self._load_chart_data()
            # Load current price directly from price cache (avoids fetching all positions)
            theme_state = await self.get_state(ThemeState)
            prices = SecuritiesService.get_current_prices(
                [ticker], theme_state.default_currency
            )
            self.current_price = prices.get(ticker.upper(), 0.0) or 0.0
            dividends_state = await self.get_state(DividendsState)
            dividends_state.ticker = ticker
            DividendService.sync_dividends([ticker])
            dividends_state.load_entries()
            if was_market_data_fetched():
                yield rx.toast.info("Market data refreshed", position="bottom-right")
        except Exception as e:
            logger.error("Failed to load security details for %s: %s", self.ticker, e)
            yield rx.toast.error(str(e), position="bottom-right")
        finally:
            self.is_loading = False

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
    async def add_stock(self, form_data: dict) -> None:
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
            total_state = await self.get_state(TableStateTotal)
            total_state.add_dialog_open = False
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
        return export_csv(positions, columns, "positions.csv")

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
            {"title": "Price", "type": "float", "grow": 1},
            {"title": "Quantity", "type": "float", "grow": 1},
            {"title": "Fees", "type": "float", "grow": 1},
            {"title": "Date", "type": "str", "grow": 1},
        ]

    def _load_spreadsheet_rows(self) -> tuple[list[list], list]:
        positions = SecuritiesService.get_positions_by_ticker(self.ticker)
        data = [
            [
                p.get("price", 0.0),
                p.get("quantity", 1.0),
                p.get("fees", 0.0),
                fmt_date_cell(p.get("date", "")),
            ]
            for p in positions
        ]
        ids = [p.get("id") for p in positions]
        return data, ids

    def _save_spreadsheet_row(self, row, index, rid, is_new):
        price = cell_float(row[0])
        quantity = cell_float(row[1], default=1.0)
        fees = cell_float(row[2])
        date = cell_date(row[3])
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

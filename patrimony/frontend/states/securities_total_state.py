from typing import Union

import reflex as rx

from datetime import datetime

from ..services import (
    SecuritiesService,
    SecuritiesReferenceService,
    SecurityTotal,
    EntryType,
    AssetType,
    was_market_data_fetched,
)
from ..templates import ThemeState
from ..utils import export_csv
from .mixins import PaginationMixin, SearchSortMixin, apply_sort_and_search
from .spreadsheet_mixin import SpreadsheetMixin


class TableStateTotal(SpreadsheetMixin, SearchSortMixin, PaginationMixin, rx.State):
    """The state class."""

    items: list[SecurityTotal] = []
    is_loading: bool = False

    # Asset type filter for the table
    selected_asset_filter: str = "all"

    # Position form autocomplete state
    ticker_search: str = ""
    _ticker_suggestions: list[dict] = []
    show_suggestions: bool = False
    selected_asset_type: str = "STOCK"

    @rx.var
    def available_asset_filters(self) -> list[dict]:
        """Filter options based on owned asset types."""
        filters = [{"label": "All", "value": "all"}]
        type_config = [
            ("STOCK", "Stocks", "STOCK"),
            ("ETF", "ETFs", "ETF"),
            ("CRYPTO", "Crypto", "CRYPTO"),
            ("COMMODITY", "Commodity", "COMMODITY"),
        ]
        owned = {item.asset_type.upper() for item in self.items}
        for at, label, value in type_config:
            if at in owned:
                filters.append({"label": label, "value": value})
        return filters

    @rx.var
    def asset_type_allocation(self) -> list[dict]:
        """Group positions by asset type for pie chart with colors from settings."""
        groups: dict[str, float] = {}
        for item in self.items:
            at = item.asset_type or "STOCK"
            val = item.total_value or 0.0
            groups[at] = groups.get(at, 0.0) + val
        return [
            {
                "name": k,
                "value": round(v, 2),
                "fill": self._asset_colors.get(k, "var(--gray-9)"),
            }
            for k, v in sorted(groups.items())
        ]

    @rx.var
    def heatmap_data(self) -> list[dict]:
        """Position-level data for weighted heatmap (ticker, return %, value, weight %)."""
        result = []
        total = sum((item.total_value or 0.0) for item in self.items)
        for item in self.items:
            if not item.avg_price or item.avg_price == 0 or not item.current_price:
                continue
            ret_pct = round(
                (item.current_price - item.avg_price) / item.avg_price * 100, 2
            )
            val = round(item.total_value or 0.0, 2)
            weight = round(val / total * 100, 2) if total > 0 else 0.0
            result.append(
                {
                    "ticker": item.ticker,
                    "return_pct": ret_pct,
                    "value": val,
                    "weight": weight,
                }
            )
        return sorted(result, key=lambda x: x["value"], reverse=True)

    @rx.var
    def filtered_sorted_items(self) -> list[SecurityTotal]:
        items = self.items
        if self.selected_asset_filter != "all":
            items = [
                i
                for i in items
                if i.asset_type.upper() == self.selected_asset_filter.upper()
            ]
        return apply_sort_and_search(
            items,
            self.sort_value,
            self.sort_reverse,
            self.search_value,
            numeric_sort_fields=["price"],
            search_fields=["ticker", "date"],
            accessor="attr",
        )

    @rx.var(initial_value=[])
    def get_current_page(self) -> list[SecurityTotal]:
        return self.filtered_sorted_items[self.offset : self.offset + self.limit]

    # Asset type colors cached from ThemeState
    _asset_colors: dict[str, str] = {}

    @rx.event
    async def load_entries(self) -> None:
        theme_state = await self.get_state(ThemeState)
        self._asset_colors = {
            "STOCK": f"var(--{theme_state.stock_color}-9)",
            "ETF": f"var(--{theme_state.etf_color}-9)",
            "CRYPTO": f"var(--{theme_state.crypto_color}-9)",
            "COMMODITY": f"var(--{theme_state.commodity_color}-9)",
        }
        positions = SecuritiesService.get_aggregated_positions(
            theme_state.default_currency
        )
        self.items = [SecurityTotal(**pos) for pos in positions]
        self.total_items = len(self.items)

    @rx.event
    async def on_page_load(self):
        self.is_loading = True
        yield
        await self.load_entries()
        self.is_loading = False
        if was_market_data_fetched():
            yield rx.toast.info("Market data refreshed", position="bottom-right")

    async def toggle_sort(self) -> None:
        self.sort_reverse = not self.sort_reverse
        await self.load_entries()

    @rx.event
    async def set_asset_filter(self, value: str | list[str]) -> None:
        self.selected_asset_filter = value
        self.offset = 0
        await self.load_entries()

    # Autocomplete for position form
    @rx.event
    def search_ticker(self, query: str) -> None:
        self.ticker_search = query
        if len(query) >= 1:
            self._ticker_suggestions = SecuritiesReferenceService.search(query)
            self.show_suggestions = len(self._ticker_suggestions) > 0
        else:
            self._ticker_suggestions = []
            self.show_suggestions = False

    @rx.event
    def select_suggestion(self, ticker: str, asset_type: str) -> None:
        self.ticker_search = ticker
        self.selected_asset_type = asset_type.upper() if asset_type else "STOCK"
        self.show_suggestions = False

    @rx.event
    def set_selected_asset_type(self, value: str) -> None:
        self.selected_asset_type = value

    @rx.event
    def clear_ticker_search(self) -> None:
        self.ticker_search = ""
        self._ticker_suggestions = []
        self.show_suggestions = False
        self.selected_asset_type = "STOCK"

    @rx.var
    def ticker_suggestions(self) -> list[dict]:
        return self._ticker_suggestions

    @rx.event
    async def add_stock(self, form_data: dict) -> None:
        """Add a new position from form data."""
        ticker = form_data.get("ticker", self.ticker_search).upper()
        asset_type_str = form_data.get("asset_type", self.selected_asset_type)
        date_str = form_data.get("date", "")
        purchase_date = (
            datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()
        )
        result = SecuritiesService.add_position(
            ticker=ticker,
            price=float(form_data.get("price", 0)),
            quantity=float(form_data.get("quantity", 0)),
            entry_type=EntryType.MANUAL,
            asset_type=AssetType(asset_type_str),
            date=purchase_date,
            fees=float(form_data.get("fees", 0))
            if form_data.get("fees") and form_data.get("fees").isdigit()
            else 0.0,
        )

        self.ticker_search = ""
        self._ticker_suggestions = []
        self.show_suggestions = False
        self.selected_asset_type = "STOCK"

        if result.success:
            await self.load_entries()
            return rx.toast.success(result.message, position="top-center")
        else:
            return rx.toast.error(result.message, position="top-center")

    @rx.event
    async def delete_stock(self, id: Union[int, dict]) -> None:
        """Delete a stock position by ID
        args:
            id: The ID of the stock position to delete. Can be an int or a dict.
        """
        if isinstance(id, dict):
            id = id.get("id", "")

        result = SecuritiesService.delete_position(id)

        if result.success:
            await self.load_entries()
            return rx.toast.success(result.message, position="top-center")
        else:
            return rx.toast.error(result.message, position="top-center")

    @rx.event
    def export_csv(self):
        positions = SecuritiesService.get_aggregated_positions()
        columns = list(SecurityTotal.__dataclass_fields__.keys())
        return export_csv(positions, columns, "positions.csv")

    @rx.event
    def open_detail_view(self, ticker: str):
        return rx.redirect(f"/securities_detail?ticker={ticker}")

    # ── Spreadsheet mode ──

    _VALID_ASSET_TYPES: list[str] = [
        "STOCK",
        "ETF",
        "CRYPTO",
        "COMMODITY",
        "BOND",
        "CASH",
    ]

    @rx.var
    def spreadsheet_columns(self) -> list[dict]:
        return [
            {"title": "Ticker", "type": "str"},
            {"title": "Price", "type": "float"},
            {"title": "Quantity", "type": "float"},
            {"title": "Fees", "type": "float"},
            {"title": "Asset Type", "type": "str"},
            {"title": "Date", "type": "str"},
        ]

    @rx.event
    def on_spreadsheet_cell_edited(self, pos: tuple[int, int], cell: dict) -> None:
        """Override mixin to add ticker auto-resolve and asset type validation."""
        col, row = pos
        if row < 0 or row >= len(self._spreadsheet_data):
            return
        if col < 0 or col >= len(self._spreadsheet_data[row]):
            return

        value = cell.get("data", "")
        new_data = [r[:] for r in self._spreadsheet_data]

        if col == 0:
            # Ticker column — auto-resolve asset type from reference table
            ticker = str(value).strip().upper()
            new_data[row][col] = ticker
            if ticker:
                results = SecuritiesReferenceService.search(ticker, limit=1)
                if results and results[0].get("ticker", "").upper() == ticker:
                    new_data[row][4] = results[0].get("asset_type", "STOCK").upper()
        elif col == 4:
            # Asset type column — validate and auto-correct
            raw = str(value).strip().upper()
            matched = None
            for at in self._VALID_ASSET_TYPES:
                if at == raw:
                    matched = at
                    break
            if matched is None:
                for at in self._VALID_ASSET_TYPES:
                    if at.startswith(raw):
                        matched = at
                        break
            new_data[row][col] = matched if matched else new_data[row][col]
            if matched is None:
                self._spreadsheet_data = new_data
                return rx.toast.info(
                    f"Valid types: {', '.join(self._VALID_ASSET_TYPES)}",
                    position="top-center",
                )
        else:
            new_data[row][col] = value

        self._spreadsheet_data = new_data
        self._has_edits = True

    def _load_spreadsheet_rows(self) -> tuple[list[list], list]:
        positions = SecuritiesService.get_all_positions()
        data = [
            [
                p.get("ticker", ""),
                p.get("price", 0.0),
                p.get("quantity", 1.0),
                p.get("fees", 0.0),
                p.get("asset_type", "STOCK"),
                str(p.get("date", ""))[:10],
            ]
            for p in positions
        ]
        ids = [p.get("id") for p in positions]
        return data, ids

    def _save_spreadsheet_row(self, row, index, rid, is_new):
        ticker = str(row[0]).strip().upper()
        if is_new and not ticker:
            return "skip"
        price = float(row[1]) if row[1] != "" else 0.0
        quantity = float(row[2]) if row[2] != "" else 1.0
        fees = float(row[3]) if row[3] != "" else 0.0
        asset_type_str = str(row[4]).strip().upper() or "STOCK"
        date_str = str(row[5]).strip()
        date = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()
        if is_new:
            SecuritiesService.add_position(
                ticker=ticker,
                price=price,
                quantity=quantity,
                entry_type=EntryType.MANUAL,
                asset_type=AssetType(asset_type_str),
                date=date,
                fees=fees,
            )
        else:
            SecuritiesService.update_position(
                id=rid,
                ticker=ticker,
                price=price,
                quantity=quantity,
                entry_type=EntryType.MANUAL,
                asset_type=AssetType(asset_type_str),
                date=date,
                fees=fees,
            )
        return None

    def _delete_spreadsheet_row(self, rid):
        SecuritiesService.delete_position(rid)

    async def _after_spreadsheet_save(self):
        await self.load_entries()

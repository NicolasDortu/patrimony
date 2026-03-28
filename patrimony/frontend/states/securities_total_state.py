from typing import Union

import reflex as rx

from datetime import datetime

from ..services import (
    SecuritiesService,
    SecuritiesReferenceService,
    SecurityTotal,
    EntryType,
    AssetType,
)
from ..templates import ThemeState
from .mixins import PaginationMixin
from .spreadsheet_mixin import SpreadsheetMixin


class TableStateTotal(SpreadsheetMixin, PaginationMixin, rx.State):
    """The state class."""

    items: list[SecurityTotal] = []

    search_value: str = ""
    sort_value: str = ""
    sort_reverse: bool = False

    # Asset type filter for the table
    selected_asset_filter: str = "all"

    # Position form autocomplete state
    ticker_search: str = ""
    _ticker_suggestions: list[dict] = []
    show_suggestions: bool = False
    selected_asset_type: str = "STOCK"

    @rx.event
    def set_search_value(self, value: str) -> None:
        self.search_value = value

    @rx.event
    def set_sort_value(self, value: str) -> None:
        self.sort_value = value

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
    def filtered_sorted_items(self) -> list[SecurityTotal]:
        items = self.items

        # Filter by asset type
        if self.selected_asset_filter != "all":
            items = [
                item
                for item in items
                if item.asset_type.upper() == self.selected_asset_filter.upper()
            ]

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
    def get_current_page(self) -> list[SecurityTotal]:
        start_index = self.offset
        end_index = start_index + self.limit
        return self.filtered_sorted_items[start_index:end_index]

    @rx.event
    async def load_entries(self) -> None:
        theme_state = await self.get_state(ThemeState)
        positions = SecuritiesService.get_aggregated_positions(
            theme_state.default_currency
        )
        self.items = [SecurityTotal(**pos) for pos in positions]
        self.total_items = len(self.items)

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

        header = ",".join(columns)
        rows = [",".join(str(pos[col]) for col in columns) for pos in positions]

        data = str(header + "\n" + "\n".join(rows))
        return rx.download(data=data, filename="positions.csv")

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

    @rx.event
    def toggle_spreadsheet_mode(self) -> None:
        if not self.spreadsheet_mode:
            positions = SecuritiesService.get_all_positions()
            self._spreadsheet_data = [
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
            self._row_ids = [p.get("id") for p in positions]
            self._deleted_ids = []
            self._has_edits = False
            self.spreadsheet_mode = True
        else:
            self._exit_spreadsheet_mode()

    @rx.event
    async def save_spreadsheet_changes(self) -> None:
        errors: list[str] = []

        # Update existing rows
        for i, row in enumerate(self._spreadsheet_data):
            rid = self._row_ids[i]
            if rid is not None:
                try:
                    ticker = str(row[0]).strip().upper()
                    price = float(row[1]) if row[1] != "" else 0.0
                    quantity = float(row[2]) if row[2] != "" else 1.0
                    fees = float(row[3]) if row[3] != "" else 0.0
                    asset_type_str = str(row[4]).strip().upper() or "STOCK"
                    date_str = str(row[5]).strip()
                    date = (
                        datetime.strptime(date_str, "%Y-%m-%d")
                        if date_str
                        else datetime.now()
                    )
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
                except Exception as e:
                    errors.append(f"Row {i + 1}: {e}")

        # Add new rows
        for i, row in enumerate(self._spreadsheet_data):
            rid = self._row_ids[i]
            if rid is None:
                ticker = str(row[0]).strip().upper()
                if not ticker:
                    continue
                try:
                    price = float(row[1]) if row[1] != "" else 0.0
                    quantity = float(row[2]) if row[2] != "" else 1.0
                    fees = float(row[3]) if row[3] != "" else 0.0
                    asset_type_str = str(row[4]).strip().upper() or "STOCK"
                    date_str = str(row[5]).strip()
                    date = (
                        datetime.strptime(date_str, "%Y-%m-%d")
                        if date_str
                        else datetime.now()
                    )
                    SecuritiesService.add_position(
                        ticker=ticker,
                        price=price,
                        quantity=quantity,
                        entry_type=EntryType.MANUAL,
                        asset_type=AssetType(asset_type_str),
                        date=date,
                        fees=fees,
                    )
                except Exception as e:
                    errors.append(f"New row {i + 1}: {e}")

        # Delete removed rows
        for del_id in self._deleted_ids:
            SecuritiesService.delete_position(del_id)

        self._exit_spreadsheet_mode()
        await self.load_entries()

        if errors:
            return rx.toast.error(
                f"Saved with {len(errors)} error(s)", position="top-center"
            )
        return rx.toast.success("Changes saved", position="top-center")

from typing import Union

import reflex as rx

from ..services import (
    SecuritiesService,
    SecuritiesReferenceService,
    SecurityTotal,
    EntryType,
    AssetType,
)
from ..templates import ThemeState


class TableStateTotal(rx.State):
    """The state class."""

    items: list[SecurityTotal] = []

    search_value: str = ""
    sort_value: str = ""
    sort_reverse: bool = False

    total_items: int = 0
    offset: int = 0
    limit: int = 12  # Number of rows per page

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

    @rx.var
    def page_number(self) -> int:
        return (self.offset // self.limit) + 1

    @rx.var
    def total_pages(self) -> int:
        return (self.total_items // self.limit) + (
            1 if self.total_items % self.limit else 1
        )

    @rx.var(initial_value=[])
    def get_current_page(self) -> list[SecurityTotal]:
        start_index = self.offset
        end_index = start_index + self.limit
        return self.filtered_sorted_items[start_index:end_index]

    def prev_page(self) -> None:
        if self.page_number > 1:
            self.offset -= self.limit

    def next_page(self) -> None:
        if self.page_number < self.total_pages:
            self.offset += self.limit

    def first_page(self) -> None:
        self.offset = 0

    def last_page(self) -> None:
        self.offset = (self.total_pages - 1) * self.limit

    @rx.event
    async def load_entries(self) -> None:
        theme_state = await self.get_state(ThemeState)
        positions = SecuritiesService.get_aggregated_positions(
            theme_state.default_currency
        )
        self.items = [SecurityTotal(**pos) for pos in positions]
        self.total_items = len(self.items)

    def toggle_sort(self) -> None:
        self.sort_reverse = not self.sort_reverse
        self.load_entries()

    @rx.event
    def set_asset_filter(self, value: str | list[str]) -> None:
        self.selected_asset_filter = value
        self.offset = 0

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
        result = SecuritiesService.add_position(
            ticker=ticker,
            price=float(form_data.get("price", 0)),
            quantity=float(form_data.get("quantity", 0)),
            entry_type=EntryType.MANUAL,
            asset_type=AssetType(asset_type_str),
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

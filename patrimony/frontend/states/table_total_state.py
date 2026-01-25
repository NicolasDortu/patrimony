from typing import Union

import reflex as rx

from ...backend.api.stock_api import (
    delete_stock_position,
    get_all_stocks_total,
    add_stock_position,
)
from ...shared.models.assets import EquityTotal, Stock, EntryType, BuySell, Currency


class TableStateTotal(rx.State):
    """The state class."""

    items: list[EquityTotal] = []

    search_value: str = ""
    sort_value: str = ""
    sort_reverse: bool = False

    total_items: int = 0
    offset: int = 0
    limit: int = 12  # Number of rows per page

    @rx.event
    def set_search_value(self, value: str) -> None:
        self.search_value = value

    @rx.event
    def set_sort_value(self, value: str) -> None:
        self.sort_value = value

    @rx.var
    def filtered_sorted_items(self) -> list[EquityTotal]:
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

    @rx.var
    def page_number(self) -> int:
        return (self.offset // self.limit) + 1

    @rx.var
    def total_pages(self) -> int:
        return (self.total_items // self.limit) + (
            1 if self.total_items % self.limit else 1
        )

    @rx.var(initial_value=[])
    def get_current_page(self) -> list[EquityTotal]:
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
    def load_entries(self) -> None:
        stocks = get_all_stocks_total()
        self.items = [EquityTotal(**stock) for stock in stocks]
        self.total_items = len(self.items)

    def toggle_sort(self) -> None:
        self.sort_reverse = not self.sort_reverse
        self.load_entries()

    @rx.event
    def add_stock(self, form_data: dict) -> None:
        """Add a new stock position from form data."""
        stock = Stock(
            ticker=form_data.get("ticker", "").upper(),
            price=float(form_data.get("price", 0)),
            quantity=float(form_data.get("quantity", 0)),
            entry_type=EntryType.MANUAL,
            buy_sell=BuySell.BUY,
            currency=Currency.EUR,  # TODO: make dynamic later
        )
        result = add_stock_position(stock=stock)

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

        result = delete_stock_position(id)

        if result.success:
            self.load_entries()
            return rx.toast.success(result.message, position="top-center")
        else:
            return rx.toast.error(result.message, position="top-center")

    @rx.event
    def export_csv(self):
        stocks = get_all_stocks_total()
        columns = list(EquityTotal.__dataclass_fields__.keys())

        header = ",".join(columns)
        rows = [",".join(str(stock[col]) for col in columns) for stock in stocks]

        data = str(header + "\n" + "\n".join(rows))
        return rx.download(data=data, filename="positions.csv")

    @rx.event
    def open_detail_view(self, ticker: str):
        return rx.redirect(f"/equity_detail?ticker={ticker}")

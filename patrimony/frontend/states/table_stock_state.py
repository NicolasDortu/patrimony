from datetime import datetime
from dataclasses import dataclass

import reflex as rx

from ...backend.api.stock_api import (
    delete_stock_position,
    get_all_stocks,
    add_stock_position,
)


@dataclass
class Stock:
    """The stock table item class."""

    id: int
    ticker: str
    buy_price: float
    quantity: float
    buy_date: datetime


class TableState(rx.State):
    """The state class."""

    items: list[Stock] = []

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
    def filtered_sorted_items(self) -> list[Stock]:
        items = self.items

        # Filter items based on selected item
        if self.sort_value:
            if self.sort_value in ["buy_price"]:
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
                        "buy_date",
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
    def get_current_page(self) -> list[Stock]:
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
        stocks = get_all_stocks()
        self.items = [Stock(**stock) for stock in stocks]
        self.total_items = len(self.items)

    def toggle_sort(self) -> None:
        self.sort_reverse = not self.sort_reverse
        self.load_entries()

    @rx.event
    def add_stock(self, form_data: dict) -> None:
        """Add a new stock position from form data."""
        ticker = form_data.get("ticker", "").upper()
        buy_price = float(form_data.get("buy_price", 0))
        quantity = float(form_data.get("quantity", 0))

        result = add_stock_position(ticker, buy_price, quantity)

        if result.success:
            self.load_entries()

    @rx.event
    def delete_stock(self, form_data: dict) -> None:
        """Add a new stock position from form data."""
        id = form_data.get("id", "")

        result = delete_stock_position(id)

        if result.success:
            self.load_entries()

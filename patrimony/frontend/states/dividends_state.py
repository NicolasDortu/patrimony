from dataclasses import dataclass, field
from datetime import datetime
from typing import Union

import reflex as rx

from ..services import DividendService
from .mixins import PaginationMixin


@dataclass(slots=True)
class Dividend:
    """Frontend model for a dividend entry."""

    id: int = 0
    ticker: str = ""
    amount: float = 0.0
    date: datetime = field(default_factory=datetime.now)


class DividendsState(PaginationMixin, rx.State):
    """State for managing dividends on the securities detail page."""

    items: list[Dividend] = []
    ticker: str = ""

    @rx.var
    def total_dividends(self) -> float:
        return sum(item.amount for item in self.items)

    @rx.var(initial_value=[])
    def get_current_page(self) -> list[Dividend]:
        start_index = self.offset
        end_index = start_index + self.limit
        return self.items[start_index:end_index]

    @rx.event
    def set_ticker(self, ticker: str) -> None:
        self.ticker = ticker

    @rx.event
    def load_entries(self) -> None:
        if not self.ticker:
            self.items = []
            self.total_items = 0
            return
        dividends = DividendService.get_dividends_by_ticker(self.ticker)
        self.items = [Dividend(**d) for d in dividends]
        self.total_items = len(self.items)

    @rx.event
    def add_dividend(self, form_data: dict) -> None:
        """Add a new dividend from form data."""
        date_str = form_data.get("date", "")
        date = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()

        result = DividendService.add_dividend(
            ticker=self.ticker,
            amount=float(form_data.get("amount", 0)),
            date=date,
        )

        if result.success:
            self.load_entries()
            return rx.toast.success(result.message, position="top-center")
        else:
            return rx.toast.error(result.message, position="top-center")

    @rx.event
    def delete_dividend(self, id: Union[int, dict]) -> None:
        """Delete a dividend by ID."""
        if isinstance(id, dict):
            id = id.get("id", "")

        result = DividendService.delete_dividend(id)

        if result.success:
            self.load_entries()
            return rx.toast.success(result.message, position="top-center")
        else:
            return rx.toast.error(result.message, position="top-center")

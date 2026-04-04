from dataclasses import dataclass, field
from datetime import datetime
from typing import Union
import logging

import reflex as rx

from ..services import DividendService
from ..utils import parse_form_date
from .mixins import PaginationMixin
from .spreadsheet_mixin import SpreadsheetMixin

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Dividend:
    """Frontend model for a dividend entry."""

    id: int = 0
    ticker: str = ""
    amount: float = 0.0
    date: datetime = field(default_factory=datetime.now)


class DividendsState(SpreadsheetMixin, PaginationMixin, rx.State):
    """State for managing dividends on the securities detail page."""

    items: list[Dividend] = []
    ticker: str = ""

    @rx.var
    def total_dividends(self) -> float:
        return sum(item.amount for item in self.items)

    @rx.var(initial_value=[])
    def get_current_page(self) -> list[Dividend]:
        return self.items[self.offset : self.offset + self.limit]

    @rx.event
    def set_ticker(self, ticker: str) -> None:
        self.ticker = ticker

    @rx.event
    def load_entries(self) -> None:
        if not self.ticker:
            self.items = []
            self.total_items = 0
            return
        try:
            dividends = DividendService.get_dividends_by_ticker(self.ticker)
            self.items = [Dividend(**d) for d in dividends]
            self.total_items = len(self.items)
        except Exception as e:
            logger.error("Failed to load dividends for %s: %s", self.ticker, e)
            self.items = []
            self.total_items = 0

    @rx.event
    def add_dividend(self, form_data: dict) -> None:
        """Add a new dividend from form data."""
        date_str = form_data.get("date", "")
        date = parse_form_date(date_str)

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

    # ── Spreadsheet mode ──

    @rx.var
    def spreadsheet_columns(self) -> list[dict]:
        return [
            {"title": "Amount", "type": "float"},
            {"title": "Date", "type": "str"},
        ]

    def _load_spreadsheet_rows(self) -> tuple[list[list], list]:
        dividends = DividendService.get_dividends_by_ticker(self.ticker)
        data = [[d.get("amount", 0.0), str(d.get("date", ""))[:10]] for d in dividends]
        ids = [d.get("id") for d in dividends]
        return data, ids

    def _save_spreadsheet_row(self, row, index, rid, is_new):
        amount = float(row[0]) if row[0] != "" else 0.0
        date_str = str(row[1]).strip()
        date = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()
        if is_new:
            if amount == 0.0:
                return "skip"
            DividendService.add_dividend(ticker=self.ticker, amount=amount, date=date)
        else:
            DividendService.update_dividend(
                id=rid, ticker=self.ticker, amount=amount, date=date
            )
        return None

    def _delete_spreadsheet_row(self, rid):
        DividendService.delete_dividend(rid)

    async def _after_spreadsheet_save(self):
        self.load_entries()

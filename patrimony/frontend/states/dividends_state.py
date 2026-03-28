from dataclasses import dataclass, field
from datetime import datetime
from typing import Union

import reflex as rx

from ..services import DividendService
from .mixins import PaginationMixin
from .spreadsheet_mixin import SpreadsheetMixin


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

    # ── Spreadsheet mode ──

    @rx.var
    def spreadsheet_columns(self) -> list[dict]:
        return [
            {"title": "Amount", "type": "float"},
            {"title": "Date", "type": "str"},
        ]

    @rx.event
    def toggle_spreadsheet_mode(self) -> None:
        if not self.spreadsheet_mode:
            dividends = DividendService.get_dividends_by_ticker(self.ticker)
            self._spreadsheet_data = [
                [
                    d.get("amount", 0.0),
                    str(d.get("date", ""))[:10],
                ]
                for d in dividends
            ]
            self._row_ids = [d.get("id") for d in dividends]
            self._deleted_ids = []
            self._has_edits = False
            self.spreadsheet_mode = True
        else:
            self._exit_spreadsheet_mode()

    @rx.event
    def save_spreadsheet_changes(self) -> None:
        errors: list[str] = []

        for i, row in enumerate(self._spreadsheet_data):
            rid = self._row_ids[i]
            try:
                amount = float(row[0]) if row[0] != "" else 0.0
                date_str = str(row[1]).strip()
                date = (
                    datetime.strptime(date_str, "%Y-%m-%d")
                    if date_str
                    else datetime.now()
                )

                if rid is not None:
                    DividendService.update_dividend(
                        id=rid,
                        ticker=self.ticker,
                        amount=amount,
                        date=date,
                    )
                else:
                    if amount == 0.0:
                        continue
                    DividendService.add_dividend(
                        ticker=self.ticker,
                        amount=amount,
                        date=date,
                    )
            except Exception as e:
                errors.append(f"Row {i + 1}: {e}")

        for del_id in self._deleted_ids:
            DividendService.delete_dividend(del_id)

        self._exit_spreadsheet_mode()
        self.load_entries()

        if errors:
            return rx.toast.error(
                f"Saved with {len(errors)} error(s)", position="top-center"
            )
        return rx.toast.success("Changes saved", position="top-center")

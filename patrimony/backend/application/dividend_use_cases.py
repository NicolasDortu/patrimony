"""Use cases for dividend operations."""

from datetime import datetime
from typing import Optional

from ..domain.repositories import DividendRepository
from ..domain.services import DividendSyncService


class DividendUseCases:
    """Application use cases for dividend CRUD and sync."""

    def __init__(
        self,
        dividend_repo: DividendRepository,
        dividend_sync_service: DividendSyncService,
    ):
        self._repo = dividend_repo
        self._sync_service = dividend_sync_service

    def add_dividend(
        self,
        ticker: str,
        amount: float,
        date: Optional[datetime] = None,
    ) -> dict:
        """Add a new dividend. Returns {'id': int}."""
        if date is None:
            date = datetime.now()
        dividend_id = self._repo.add_dividend(
            ticker=ticker,
            amount=amount,
            date=date,
        )
        return {"id": dividend_id}

    def get_dividends_by_ticker(self, ticker: str) -> list[dict]:
        df = self._repo.get_by_ticker(ticker)
        return df.to_dicts() if df is not None else []

    def get_all_dividends(self) -> list[dict]:
        df = self._repo.get_all()
        return df.to_dicts() if df is not None else []

    def get_total_amount(self) -> float:
        return self._repo.get_total_amount()

    def delete_dividend(self, id: int) -> None:
        self._repo.delete(id)

    def update_dividend(
        self,
        id: int,
        ticker: str,
        amount: float,
        date: Optional[datetime] = None,
    ) -> None:
        if date is None:
            date = datetime.now()
        self._repo.update_dividend(
            id=id,
            ticker=ticker,
            amount=amount,
            date=date,
        )

    def sync_dividends(self, tickers: list[str] | None = None) -> dict:
        """Sync dividends from market data. Returns {'imported': int, 'skipped': int, 'errors': list}."""
        return self._sync_service.sync_dividends(tickers)

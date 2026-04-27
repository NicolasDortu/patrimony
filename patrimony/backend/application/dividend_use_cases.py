"""Use cases for dividend operations."""

import logging
from datetime import datetime
from typing import Optional

from ..domain.repositories import DividendRepository, SecuritiesRepository
from ..domain.services import DividendService

logger = logging.getLogger(__name__)


class DividendUseCases:
    """Application use cases for dividend CRUD and sync."""

    _SYNC_COOLDOWN_S: int = 3600  # 1 hour

    def __init__(
        self,
        dividend_repo: DividendRepository,
        securities_repo: SecuritiesRepository,
        dividend_sync_service: DividendService,
    ):
        self._repo = dividend_repo
        self._securities_repo = securities_repo
        self._sync_service = dividend_sync_service
        self._synced_tickers: set[str] = set()
        self._last_sync_time: datetime | None = None

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
            ticker=ticker.strip().upper(),
            amount=amount,
            date=date,
        )
        return {"id": dividend_id}

    def get_dividends_by_ticker(self, ticker: str) -> list[dict]:
        df = self._repo.get_by_ticker(ticker.strip().upper())
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
            ticker=ticker.strip().upper(),
            amount=amount,
            date=date,
        )

    def sync_dividends(self, tickers: list[str] | None = None) -> dict:
        """Sync dividends from market data.

        Resolves held tickers when *tickers* is None.  Applies a per-ticker
        cooldown so recently synced tickers are skipped.

        Returns {'imported': int, 'skipped': int, 'errors': list}.
        """
        if tickers is None:
            df = self._securities_repo.get_aggregated_positions()
            tickers = (
                df["ticker"].to_list() if df is not None and not df.is_empty() else []
            )
        tickers = self._filter_recently_synced(tickers)
        if not tickers:
            return {"imported": 0, "skipped": 0, "errors": []}

        result = self._sync_service.sync_dividends(tickers)
        self._synced_tickers.update(tickers)
        self._last_sync_time = datetime.now()
        return result

    def _filter_recently_synced(self, tickers: list[str]) -> list[str]:
        if (
            self._last_sync_time is None
            or (datetime.now() - self._last_sync_time).total_seconds()
            >= self._SYNC_COOLDOWN_S
        ):
            return tickers
        new = [t for t in tickers if t not in self._synced_tickers]
        if new:
            logger.debug("Sync cooldown active, processing %d new ticker(s)", len(new))
        return new

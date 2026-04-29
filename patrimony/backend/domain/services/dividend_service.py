"""Domain service for dividend history synchronization.

Fetches dividend data from external providers, computes total amounts
based on position quantities, and stores new dividends in the repository.
"""

import logging
from datetime import datetime

from ..exceptions import (
    CurrencyConversionError,
    DividendSyncError,
    TickerCurrencyUnknownError,
)
from ..interfaces import MarketDataProvider
from ..repositories import DividendRepository, SecuritiesRepository
from .currency_service import CurrencyService
from .date_utils import normalize_date
from .securities_service import SecuritiesService

logger = logging.getLogger(__name__)


class DividendService:
    """Synchronizes dividend history from external providers into the repository."""

    def __init__(
        self,
        dividend_repo: DividendRepository,
        securities_repo: SecuritiesRepository,
        securities_service: SecuritiesService,
        market_data: MarketDataProvider,
        currency_service: CurrencyService | None = None,
    ):
        self._dividend_repo = dividend_repo
        self._securities_repo = securities_repo
        self._securities_service = securities_service
        self._market_data = market_data
        self._currency_service = currency_service

    def get_total_in_currency(self, user_currency: str) -> float:
        """Sum all dividends, converting each ticker's native currency."""
        totals = self._dividend_repo.get_totals_by_ticker()
        if not totals:
            return 0.0
        if self._currency_service is None:
            return float(sum(totals.values()))

        grand_total = 0.0
        for ticker, amount in totals.items():
            try:
                native = self._currency_service.get_ticker_currency(ticker)
                rate = self._currency_service.get_exchange_rate(native, user_currency)
            except (TickerCurrencyUnknownError, CurrencyConversionError) as e:
                logger.error(
                    "Dividend conversion failed for %s: %s; counting at 1.0",
                    ticker,
                    e,
                )
                rate = 1.0
            grand_total += amount * rate
        return grand_total

    def sync_dividends(self, tickers: list[str]) -> dict:
        """Fetch and store dividends for the given tickers.

        Returns a summary dict: {imported: int, skipped: int, errors: list[str]}.
        """
        if not tickers:
            return {"imported": 0, "skipped": 0, "errors": []}

        quantity_timeline = self._securities_service.build_quantity_timeline()
        imported = 0
        skipped = 0
        errors: list[str] = []

        for ticker in tickers:
            try:
                result = self._sync_ticker_dividends(ticker, quantity_timeline)
                imported += result["imported"]
                skipped += result["skipped"]
            except DividendSyncError:
                raise
            except Exception as e:
                logger.warning("Error syncing dividends for %s: %s", ticker, e)
                errors.append(f"{ticker}: {e}")

        return {"imported": imported, "skipped": skipped, "errors": errors}

    def _sync_ticker_dividends(
        self, ticker: str, quantity_timeline: dict[str, list[tuple]]
    ) -> dict:
        """Sync dividends for a single ticker."""
        earliest = self._securities_repo.get_earliest_purchase_date(ticker)
        if earliest is None:
            return {"imported": 0, "skipped": 0}

        div_df = self._market_data.get_dividend_history(
            ticker, start_date=earliest, end_date=datetime.now()
        )
        if div_df is None or div_df.is_empty():
            return {"imported": 0, "skipped": 0}

        existing_df = self._dividend_repo.get_by_ticker(ticker)
        existing_dates: set = set()
        if not existing_df.is_empty():
            existing_dates = {normalize_date(d) for d in existing_df["date"].to_list()}

        imported = 0
        skipped = 0

        for row in div_df.iter_rows(named=True):
            div_date = normalize_date(row["date"])

            if div_date in existing_dates:
                skipped += 1
                continue

            qty = SecuritiesService.get_quantity_at_date(
                quantity_timeline, ticker, div_date
            )
            if qty <= 0:
                skipped += 1
                continue

            total_amount = row["amount_per_share"] * qty
            store_date = datetime.combine(div_date, datetime.min.time())
            try:
                self._dividend_repo.add_dividend(
                    ticker=ticker,
                    amount=round(total_amount, 4),
                    date=store_date,
                )
                imported += 1
                existing_dates.add(div_date)
            except Exception as e:
                logger.warning(
                    "Failed to store dividend for %s on %s: %s",
                    ticker,
                    div_date,
                    e,
                )
                skipped += 1

        return {"imported": imported, "skipped": skipped}

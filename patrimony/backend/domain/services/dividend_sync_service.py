"""Domain service for dividend history synchronization.

Fetches dividend data from external providers, computes total amounts
based on position quantities, and stores new dividends in the repository.
"""

import logging
import time
from bisect import bisect_right
from datetime import datetime

import polars as pl

from ..interfaces import MarketDataProvider
from ..repositories import DividendRepository, SecuritiesRepository
from .enrichment_utilities import normalize_date

logger = logging.getLogger(__name__)

_SYNC_BATCH_SIZE: int = 5
_SYNC_BATCH_DELAY_S: float = 2.0


class DividendSyncService:
    """Synchronizes dividend history from external providers into the repository."""

    def __init__(
        self,
        dividend_repo: DividendRepository,
        securities_repo: SecuritiesRepository,
        market_data: MarketDataProvider,
    ):
        self._dividend_repo = dividend_repo
        self._securities_repo = securities_repo
        self._market_data = market_data

    def sync_dividends(self, tickers: list[str] | None = None) -> dict:
        """Fetch and store dividends for the given tickers (or all held tickers).

        For each ticker, fetches the dividend history from the market data
        provider, multiplies per-share amounts by the quantity held at each
        ex-dividend date, and inserts new records that don't already exist.

        Returns a summary dict: {imported: int, skipped: int, errors: list[str]}.
        """
        if tickers is None:
            tickers = self._get_held_tickers()
        if not tickers:
            return {"imported": 0, "skipped": 0, "errors": []}

        quantity_timeline = self._build_quantity_timeline()
        imported = 0
        skipped = 0
        errors: list[str] = []

        for idx, ticker in enumerate(tickers):
            if idx > 0 and idx % _SYNC_BATCH_SIZE == 0:
                time.sleep(_SYNC_BATCH_DELAY_S)

            try:
                result = self._sync_ticker_dividends(ticker, quantity_timeline)
                imported += result["imported"]
                skipped += result["skipped"]
            except Exception as e:
                logger.warning("Error syncing dividends for %s: %s", ticker, e)
                errors.append(f"{ticker}: {e}")

        return {"imported": imported, "skipped": skipped, "errors": errors}

    def _sync_ticker_dividends(
        self, ticker: str, quantity_timeline: dict[str, list[tuple]]
    ) -> dict:
        """Sync dividends for a single ticker."""
        earliest = self._securities_repo.get_earliest_purchase_date(ticker)
        start_date = earliest if earliest else None

        div_df = self._market_data.get_dividend_history(
            ticker, start_date=start_date, end_date=datetime.now()
        )
        if div_df is None or div_df.is_empty():
            return {"imported": 0, "skipped": 0}

        # Get existing dividend dates to avoid duplicates
        existing_df = self._dividend_repo.get_by_ticker(ticker)
        existing_dates: set = set()
        if existing_df is not None and not existing_df.is_empty():
            existing_dates = {normalize_date(d) for d in existing_df["date"].to_list()}

        imported = 0
        skipped = 0

        for row in div_df.iter_rows(named=True):
            div_date = normalize_date(row["date"])

            if div_date in existing_dates:
                skipped += 1
                continue

            qty = self._get_quantity_at_date(quantity_timeline, ticker, div_date)
            if qty <= 0:
                skipped += 1
                continue

            total_amount = row["amount_per_share"] * qty
            try:
                self._dividend_repo.add_dividend(
                    ticker=ticker.upper(),
                    amount=round(total_amount, 4),
                    date=datetime.combine(div_date, datetime.min.time())
                    if not isinstance(div_date, datetime)
                    else div_date,
                )
                imported += 1
            except Exception as e:
                logger.warning(
                    "Failed to store dividend for %s on %s: %s", ticker, div_date, e
                )
                skipped += 1

        return {"imported": imported, "skipped": skipped}

    def _get_held_tickers(self) -> list[str]:
        """Return tickers that currently have a positive position."""
        df = self._securities_repo.get_aggregated_positions()
        if df is None or df.is_empty():
            return []
        held = df.filter(pl.col("total_quantity") > 0)
        return held["ticker"].to_list() if not held.is_empty() else []

    def _build_quantity_timeline(self) -> dict[str, list[tuple]]:
        """Build per-ticker cumulative quantity timeline."""
        df = self._securities_repo.get_all()
        if df is None or df.is_empty():
            return {}

        df = df.sort("date").with_columns(
            pl.col("quantity").cum_sum().over("ticker").alias("cum_qty"),
            pl.col("date")
            .map_elements(normalize_date, return_dtype=pl.Date)
            .alias("norm_date"),
        )

        timeline: dict[str, list[tuple]] = {}
        for ticker in df["ticker"].unique().to_list():
            ticker_df = df.filter(pl.col("ticker") == ticker)
            timeline[ticker] = list(
                zip(ticker_df["norm_date"].to_list(), ticker_df["cum_qty"].to_list())
            )
        return timeline

    @staticmethod
    def _get_quantity_at_date(
        quantity_timeline: dict[str, list[tuple]], ticker: str, dt
    ) -> float:
        """Get the cumulative quantity held for a ticker at a given date."""
        entries = quantity_timeline.get(ticker.upper(), [])
        if not entries:
            # Try original case
            entries = quantity_timeline.get(ticker, [])
        if not entries:
            return 0.0
        dt_date = normalize_date(dt)
        idx = bisect_right(entries, dt_date, key=lambda e: e[0])
        return entries[idx - 1][1] if idx > 0 else 0.0

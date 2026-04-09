"""Domain service for dividend history synchronization.

Fetches dividend data from external providers, computes total amounts
based on position quantities, and stores new dividends in the repository.
"""

import logging
import time
from datetime import datetime

import polars as pl

from ..constants import SYNC_BATCH_DELAY_S, SYNC_BATCH_SIZE
from ..exceptions import DividendSyncError
from ..interfaces import MarketDataProvider
from ..repositories import DividendRepository, SecuritiesRepository
from .enrichment_utilities import (
    SyncCooldownMixin,
    build_quantity_timeline,
    get_quantity_at_date,
    normalize_date,
)

logger = logging.getLogger(__name__)


class DividendSyncService(SyncCooldownMixin):
    """Synchronizes dividend history from external providers into the repository."""

    # Dividends change infrequently — longer cooldown than prices.
    _cooldown_seconds: int = 3600  # 60 minutes

    def __init__(
        self,
        dividend_repo: DividendRepository,
        securities_repo: SecuritiesRepository,
        market_data: MarketDataProvider,
    ):
        self._dividend_repo = dividend_repo
        self._securities_repo = securities_repo
        self._market_data = market_data
        self._init_cooldown()

    def sync_dividends(self, tickers: list[str] | None = None) -> dict:
        """Fetch and store dividends for the given tickers (or all held tickers).

        For each ticker, fetches the dividend history from the market data
        provider, multiplies per-share amounts by the quantity held at each
        ex-dividend date, and inserts new records that don't already exist.

        Recently synced tickers are skipped unless the cooldown has expired.
        New tickers (never synced in this session) are always processed.

        Returns a summary dict: {imported: int, skipped: int, errors: list[str]}.
        """
        if tickers is None:
            tickers = self._get_held_tickers()
        if not tickers:
            return {"imported": 0, "skipped": 0, "errors": []}

        upper_tickers = [t.upper() for t in tickers]
        upper_tickers = self._apply_cooldown(upper_tickers)
        if not upper_tickers:
            return {"imported": 0, "skipped": 0, "errors": []}

        quantity_timeline = build_quantity_timeline(self._securities_repo)
        imported = 0
        skipped = 0
        errors: list[str] = []

        for idx, ticker in enumerate(upper_tickers):
            if idx > 0 and idx % SYNC_BATCH_SIZE == 0:
                time.sleep(SYNC_BATCH_DELAY_S)

            try:
                result = self._sync_ticker_dividends(ticker, quantity_timeline)
                imported += result["imported"]
                skipped += result["skipped"]
                self._mark_synced(ticker)
            except DividendSyncError:
                raise
            except Exception as e:
                logger.warning("Error syncing dividends for %s: %s", ticker, e)
                errors.append(f"{ticker}: {e}")

        self._finish_sync()
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

        # Get existing dividend dates to avoid duplicates (normalize to date objects)
        existing_df = self._dividend_repo.get_by_ticker(ticker)
        existing_dates: set = set()
        if existing_df is not None and not existing_df.is_empty():
            for d in existing_df["date"].to_list():
                existing_dates.add(normalize_date(d))

        imported = 0
        skipped = 0

        for row in div_df.iter_rows(named=True):
            div_date = normalize_date(row["date"])

            if div_date in existing_dates:
                skipped += 1
                continue

            qty = get_quantity_at_date(quantity_timeline, ticker, div_date)
            if qty <= 0:
                skipped += 1
                continue

            total_amount = row["amount_per_share"] * qty
            # Normalize to midnight datetime for consistent storage
            store_date = datetime.combine(div_date, datetime.min.time())
            try:
                self._dividend_repo.add_dividend(
                    ticker=ticker.upper(),
                    amount=round(total_amount, 4),
                    date=store_date,
                )
                imported += 1
                existing_dates.add(div_date)
            except Exception as e:
                # UNIQUE constraint violation means duplicate — safe to skip
                if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                    skipped += 1
                else:
                    logger.warning(
                        "Failed to store dividend for %s on %s: %s",
                        ticker,
                        div_date,
                        e,
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

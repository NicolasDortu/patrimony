"""Domain service for price history synchronization.

Orchestrates fetching missing price data from external providers
and storing it via the price repository. Handles staleness ordering,
batch rate-limiting, gap-fill logic, and cooldown to avoid redundant calls.
"""

import logging
import time
from datetime import datetime, timedelta

from ..constants import SYNC_BATCH_DELAY_S, SYNC_BATCH_SIZE
from ..exceptions import PriceSyncError
from ..interfaces import MarketDataProvider
from ..repositories import PriceRepository
from .enrichment_utilities import SyncCooldownMixin

logger = logging.getLogger(__name__)


class PriceSyncService(SyncCooldownMixin):
    """Synchronizes price history from external providers into the repository."""

    _cooldown_seconds: int = 900  # 15 minutes

    def __init__(
        self,
        price_repo: PriceRepository,
        market_data: MarketDataProvider,
    ):
        self._price_repo = price_repo
        self._market_data = market_data
        self._init_cooldown()

    def sync_price_history(
        self, tickers: list[str], start_date: datetime, period: str = "1d"
    ) -> None:
        """Fetch and store only missing price history data.

        Tickers are sorted by staleness (oldest-updated first) and
        processed in batches with a short delay between batches to
        avoid hitting Yahoo Finance rate limits.

        Recently synced tickers are skipped unless the cooldown has
        expired.  New tickers (never synced in this session) are
        always processed immediately.
        """
        if not tickers:
            return

        today = datetime.now()
        upper_tickers = [t.upper() for t in tickers]

        # Determine which tickers actually need syncing
        upper_tickers = self._apply_cooldown(upper_tickers)
        if not upper_tickers:
            return

        # Order tickers by staleness (oldest last_updated first).
        # Tickers absent from cache sort to the front so they get fetched first.
        staleness = self._price_repo.get_cache_timestamps(upper_tickers)
        epoch = datetime(1970, 1, 1)
        ordered = sorted(upper_tickers, key=lambda t: staleness.get(t, epoch))

        for idx, ticker in enumerate(ordered):
            if idx > 0 and idx % SYNC_BATCH_SIZE == 0:
                logger.debug("Rate-limit pause after %d/%d tickers", idx, len(ordered))
                time.sleep(SYNC_BATCH_DELAY_S)

            try:
                self._sync_single_ticker(ticker, start_date, today, period)
                self._mark_synced(ticker)
            except Exception as e:
                logger.warning("%s", PriceSyncError(ticker, cause=e))

        self._finish_sync()

    def _sync_single_ticker(
        self,
        ticker: str,
        start_date: datetime,
        today: datetime,
        period: str,
    ) -> None:
        """Fetch and store missing price history for a single ticker."""
        min_date, max_date = self._price_repo.get_stored_date_range(ticker, period)

        # No data at all — fetch full range
        if min_date is None:
            df = self._market_data.get_price_history(
                ticker, start_date=start_date, end_date=today
            )
            if df is not None and not df.is_empty():
                self._price_repo.store_price_history(ticker, df, period)
            return

        # Fill missing early data if start_date is before our earliest
        if start_date.date() < (min_date - timedelta(days=1)).date():
            df = self._market_data.get_price_history(
                ticker,
                start_date=start_date,
                end_date=min_date - timedelta(days=1),
            )
            if df is not None and not df.is_empty():
                self._price_repo.store_price_history(ticker, df, period)

        # Fill missing recent data if latest date is before yesterday
        if max_date.date() < (today - timedelta(days=1)).date():
            df = self._market_data.get_price_history(
                ticker,
                start_date=max_date + timedelta(days=1),
                end_date=today,
            )
            if df is not None and not df.is_empty():
                self._price_repo.store_price_history(ticker, df, period)

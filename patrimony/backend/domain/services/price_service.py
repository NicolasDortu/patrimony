"""Domain service for price synchronization.

Orchestrates fetching missing price data from external providers and storing it via the price repository.
"""

import logging
from datetime import datetime, timedelta

from ..exceptions import PriceSyncError
from ..interfaces import MarketDataProvider
from ..repositories import PriceRepository

logger = logging.getLogger(__name__)


class PriceService:
    """Synchronizes price data from external providers into the repository."""

    def __init__(
        self,
        price_repo: PriceRepository,
        market_data: MarketDataProvider,
    ):
        self._price_repo = price_repo
        self._market_data = market_data

    def get_current_prices(
        self, tickers: list[str], max_age_minutes: int = 15
    ) -> dict[str, float]:
        """Return current prices, using intraday table, price cache, or API (in that order)."""
        if not tickers:
            return {}

        # 1. Try latest intraday prices (already fetched recently)
        prices = self._price_repo.get_latest_intraday_prices(tickers, max_age_minutes)

        # 2. Fill gaps from price_cache
        missing = [t for t in tickers if t not in prices]
        if missing:
            cached = self._price_repo.get_cached_prices(missing, max_age_minutes)
            prices.update(cached)

        # 3. Fetch remaining from API
        stale_tickers = [t for t in tickers if t not in prices]
        now = datetime.now()
        for ticker in stale_tickers:
            try:
                price = self._market_data.get_current_price(ticker)
                if price:
                    self._price_repo.cache_price(ticker, price, now)
                    prices[ticker] = price
                else:
                    self._price_repo.cache_price(ticker, 0.0, now)
            except Exception as e:
                logger.warning("Error fetching price for %s: %s", ticker, e)
                self._price_repo.cache_price(ticker, 0.0, now)

        return prices

    # == Timeline preparation ================================================

    @staticmethod
    def sort_and_forward_fill(
        ticker_data: dict[str, dict], all_dates_set: set
    ) -> tuple[dict[str, dict], list]:
        """Sort dates and forward-fill missing/invalid prices across all tickers.

        A price is considered invalid if it is None, NaN, or <= 0.
        Returns (ticker_data, sorted_dates) with gaps filled in-place.
        """
        sorted_dates = sorted(all_dates_set)
        for prices in ticker_data.values():
            last_valid = None
            for dt in sorted_dates:
                price = prices.get(dt)
                if price is not None and price == price and price > 0:
                    last_valid = price
                elif last_valid is not None:
                    prices[dt] = last_valid
        return ticker_data, sorted_dates

    def inject_today_prices(
        self, ticker_data: dict[str, dict], tickers: list[str], all_dates: list
    ) -> list:
        """Append today's price as the final chart point if not already present."""
        today = datetime.now().date()
        if today in all_dates:
            return all_dates
        cached = self.get_current_prices(tickers)
        for ticker in tickers:
            price = cached.get(ticker)
            if price and price > 0:
                ticker_data.setdefault(ticker, {})[today] = price
        all_dates.append(today)
        return all_dates

    # == Sync operations =====================================================

    def sync_intraday(
        self, tickers: list[str], interval: str = "5m", max_age_minutes: int = 15
    ) -> None:
        """Sync intraday prices, refreshing only when stored data is stale."""
        if not tickers:
            return
        for ticker in tickers:
            try:
                last_updated = self._price_repo.get_intraday_last_updated(ticker)
                if last_updated is not None:
                    age_minutes = (datetime.now() - last_updated).total_seconds() / 60
                    if age_minutes < max_age_minutes:
                        continue
                df = self._market_data.get_price_history(
                    ticker, interval=interval, period="1d"
                )
                if df is not None and not df.is_empty():
                    self._price_repo.store_intraday_prices(ticker, df)
            except Exception as e:
                logger.warning("%s", PriceSyncError(ticker, cause=e))

    def sync_price_history(
        self, tickers: list[str], start_date: datetime, period: str = "1d"
    ) -> None:
        """Fetch and store only missing price history data.

        Tickers are sorted by staleness (oldest-updated first) so the most
        out-of-date data is refreshed first.
        """
        if not tickers:
            return

        today = datetime.now()
        staleness = self._price_repo.get_cache_timestamps(tickers)
        ordered = sorted(tickers, key=lambda t: staleness.get(t, datetime.min))

        for ticker in ordered:
            try:
                min_date, max_date = self._price_repo.get_stored_date_range(
                    ticker, period
                )

                if min_date is None:
                    self._fetch_and_store(ticker, start_date, today, period)
                    continue

                # Fill early gap
                if start_date.date() < (min_date - timedelta(days=1)).date():
                    self._fetch_and_store(
                        ticker, start_date, min_date - timedelta(days=1), period
                    )

                # Fill recent gap (inject_today only handles live display, not DB persistence)
                if max_date.date() < (today - timedelta(days=1)).date():
                    self._fetch_and_store(
                        ticker, max_date + timedelta(days=1), today, period
                    )
            except Exception as e:
                logger.warning("%s", PriceSyncError(ticker, cause=e))

    def _fetch_and_store(
        self, ticker: str, start: datetime, end: datetime, period: str
    ) -> None:
        """Fetch price history from provider and store if non-empty."""
        df = self._market_data.get_price_history(ticker, start_date=start, end_date=end)
        if df is not None and not df.is_empty():
            self._price_repo.store_price_history(ticker, df, period)

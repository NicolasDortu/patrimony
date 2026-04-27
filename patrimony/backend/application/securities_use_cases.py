"""Use cases for securities operations."""

import logging
from datetime import datetime
from typing import Optional

from ..domain.constants import DEFAULT_CURRENCY, DEFAULT_PERIOD
from ..domain.entities import AssetType, EntryType
from ..domain.interfaces import MarketDataProvider
from ..domain.repositories import SecuritiesRepository
from ..domain.repositories.support_repositories import TickerInfoRepository
from ..domain.services import (
    ChartService,
    CurrencyService,
    PriceService,
    SecuritiesService,
)

logger = logging.getLogger(__name__)


class SecuritiesUseCases:
    """Application use cases for securities CRUD, aggregation, and chart data."""

    def __init__(
        self,
        securities_repo: SecuritiesRepository,
        securities_service: SecuritiesService,
        chart_service: ChartService,
        price_sync: PriceService,
        currency_service: CurrencyService,
        ticker_info_repo: TickerInfoRepository,
        market_data: MarketDataProvider,
    ):
        self._repo = securities_repo
        self._service = securities_service
        self._chart_service = chart_service
        self._price_sync = price_sync
        self._currency_service = currency_service
        self._info_repo = ticker_info_repo
        self._market_data = market_data

    def _enrich_ticker(self, ticker: str) -> None:
        """Best-effort: fetch and store ticker metadata if not already known.

        Failures are swallowed — the position is still saved, the user
        just won't see a company name until the next refresh.
        """
        if not ticker:
            return
        try:
            if self._info_repo.get_by_ticker(ticker):
                return
            info = self._market_data.resolve_ticker_info(ticker)
            if info:
                self._info_repo.upsert(info)
        except Exception as e:
            logger.warning("Could not enrich ticker info for %s: %s", ticker, e)

    def add_position(
        self,
        ticker: str,
        price: float,
        quantity: float,
        entry_type: EntryType,
        asset_type: AssetType,
        date: Optional[datetime] = None,
        fees: float = 0.0,
    ) -> dict:
        """Add a new position. Returns {'id': int}."""
        if date is None:
            date = datetime.now()
        # Normalize once at the application boundary; repos trust input.
        ticker = ticker.strip().upper()
        position_id = self._repo.add_position(
            ticker=ticker,
            price=price,
            quantity=quantity,
            entry_type=entry_type,
            asset_type=asset_type,
            date=date,
            fees=fees,
        )
        self._enrich_ticker(ticker)
        return {"id": position_id}

    def update_position(
        self,
        id: int,
        ticker: str,
        price: float,
        quantity: float,
        entry_type: EntryType,
        asset_type: AssetType,
        date: Optional[datetime] = None,
        fees: float = 0.0,
    ) -> None:
        if date is None:
            date = datetime.now()
        ticker = ticker.strip().upper()
        self._repo.update_position(
            id=id,
            ticker=ticker,
            price=price,
            quantity=quantity,
            entry_type=entry_type,
            asset_type=asset_type,
            date=date,
            fees=fees,
        )
        self._enrich_ticker(ticker)

    def delete_position(self, id: int) -> None:
        self._repo.delete(id)

    def get_all_positions(self) -> list[dict]:
        df = self._repo.get_all()
        if df is None:
            return []
        if "currency" in df.columns:
            df = df.drop("currency")
        return df.to_dicts()

    def get_positions_by_ticker(self, ticker: str) -> list[dict]:
        df = self._repo.get_by_ticker(ticker)
        if df is None:
            return []
        if "currency" in df.columns:
            df = df.drop("currency")
        return df.to_dicts()

    def get_aggregated_positions(
        self, user_currency: str = DEFAULT_CURRENCY
    ) -> list[dict]:
        df = self._service.get_aggregated_positions(user_currency)
        rows = df.to_dicts() if df is not None else []
        # Backfill ticker metadata for rows missing a name (one yfinance
        # call per ticker, cached forever after). Patch the result so
        # the user sees the name without waiting for the next reload.
        enriched_any = False
        for row in rows:
            if row.get("name"):
                continue
            ticker = row.get("ticker", "")
            self._enrich_ticker(ticker)
            info = self._info_repo.get_by_ticker(ticker) if ticker else None
            if info:
                row["name"] = info.name or ""
                if not row.get("isin"):
                    row["isin"] = info.isin or ""
                if not row.get("display_ticker"):
                    row["display_ticker"] = info.ticker or ticker
                enriched_any = True
        if enriched_any:
            logger.info(
                "Ticker info backfilled for %d position(s)",
                sum(1 for r in rows if r.get("name")),
            )
        return rows

    def get_chart_data_ticker(
        self,
        ticker: str,
        period: str = DEFAULT_PERIOD,
        user_currency: str = DEFAULT_CURRENCY,
    ) -> list[dict]:
        return self._chart_service.get_ticker_chart_data(ticker, period, user_currency)

    def get_current_prices(
        self, tickers: list[str], user_currency: str = DEFAULT_CURRENCY
    ) -> dict[str, float]:
        prices = self._price_sync.get_current_prices(tickers)
        rates = self._currency_service.get_rates_for_tickers(tickers, user_currency)
        return {t: (p or 0.0) * rates.get(t, 1.0) for t, p in prices.items()}

"""Use cases for securities operations."""

from datetime import datetime
from typing import Optional

from ..domain.entities import AssetType, EntryType
from ..domain.repositories import SecuritiesRepository
from ..domain.services.currency_service import CurrencyService
from ..domain.services.price_sync_service import PriceSyncService
from ..domain.services.securities_service import SecuritiesService


class SecuritiesUseCases:
    """Application use cases for securities CRUD, aggregation, and chart data."""

    def __init__(
        self,
        securities_repo: SecuritiesRepository,
        securities_service: SecuritiesService,
        price_sync: PriceSyncService,
        currency_service: CurrencyService,
    ):
        self._repo = securities_repo
        self._service = securities_service
        self._price_sync = price_sync
        self._currency_service = currency_service

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
        position_id = self._repo.add_position(
            ticker=ticker,
            price=price,
            quantity=quantity,
            entry_type=entry_type,
            asset_type=asset_type,
            date=date,
            fees=fees,
        )
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

    def get_aggregated_positions(self, user_currency: str = "EUR") -> list[dict]:
        df = self._service.get_aggregated_positions(user_currency)
        return df.to_dicts() if df is not None else []

    def get_chart_data_ticker(
        self, ticker: str, period: str = "1M", user_currency: str = "EUR"
    ) -> list[dict]:
        return self._service.get_chart_data_ticker(ticker, period, user_currency)

    def get_current_prices(
        self, tickers: list[str], user_currency: str = "EUR"
    ) -> dict[str, float]:
        prices = self._price_sync.get_current_prices(tickers)
        rates = self._currency_service.get_rates_for_tickers(tickers, user_currency)
        return {t: (p or 0.0) * rates.get(t, 1.0) for t, p in prices.items()}

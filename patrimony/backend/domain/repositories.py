from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

import polars as pl

from .entities import AssetType, Currency, EntryType
from .interfaces import CurrencyProvider, PriceProvider


class BaseRepository(ABC):
    """Base repository interface methods."""

    @abstractmethod
    def get_all(self) -> Optional[pl.DataFrame]:
        """Get all entities."""
        pass

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[pl.DataFrame]:
        """Retrieve entity by ID."""
        pass

    @abstractmethod
    def delete(self, id: int) -> None:
        """Delete entity by ID."""
        pass


### Repositories for specific domains (securities, cash, market data, etc.) ###
class SecuritiesRepository(BaseRepository, ABC):
    """Repository for securities (stocks, crypto, ETFs, bonds, ...).

    Extends base repository with security-specific operations.
    """

    @abstractmethod
    def add_position(
        self,
        ticker: str,
        price: float,
        quantity: float,
        entry_type: EntryType,
        asset_type: AssetType,
        date: datetime,
        fees: float = 0.0,
    ) -> int:
        """Add a new position and return its id."""
        pass

    @abstractmethod
    def update_position(
        self,
        id: int,
        ticker: str,
        price: float,
        quantity: float,
        entry_type: EntryType,
        asset_type: AssetType,
        date: datetime,
        fees: float = 0.0,
    ) -> None:
        """Update an existing position by ID."""
        pass

    @abstractmethod
    def get_by_ticker(self, ticker: str) -> Optional[pl.DataFrame]:
        """Get all positions for a specific ticker."""
        pass

    @abstractmethod
    def get_aggregated_positions(self) -> Optional[pl.DataFrame]:
        """Get aggregated positions (total quantities, avg prices)."""
        pass

    @abstractmethod
    def get_earliest_purchase_date(self, ticker: str | None = None) -> datetime | None:
        """Return the earliest purchase date, optionally filtered by ticker."""
        pass


class CashOperationRepository(ABC):
    """Cash Methods related to cash operations (deposits, withdrawals, transfers)."""

    @abstractmethod
    def add_operation_balance(
        self,
        account_number: str,
        amount: float,
        title: str,
        operation_date: datetime,
        entry_type: EntryType = EntryType.MANUAL,
        category: str = "Uncategorized",
    ) -> int:
        """Record a cash operation on the balance and return the operation ID."""
        pass

    @abstractmethod
    def get_operations_by_account(self, account_number: str) -> Optional[pl.DataFrame]:
        """Get all balance operations for a specific account."""
        pass

    @abstractmethod
    def get_all_operations(self) -> Optional[pl.DataFrame]:
        """Get all balance operations."""
        pass

    @abstractmethod
    def update_operation_by_id(
        self,
        id: int,
        amount: float,
        title: str,
        operation_date: datetime,
        entry_type: EntryType,
        category: str = "Uncategorized",
    ) -> None:
        """Update a balance operation by ID."""
        pass

    @abstractmethod
    def delete_operation_by_id(self, id: int) -> None:
        """Delete a balance operation by ID."""
        pass

    @abstractmethod
    def get_cash_balance_history(self) -> Optional[pl.DataFrame]:
        """Get cash balance history over time for all accounts by summing the operations."""
        pass


class CashRepository(BaseRepository, CashOperationRepository, ABC):
    """Repository for cash accounts."""

    @abstractmethod
    def add_cash(
        self,
        bank: str,
        account_number: str,
        currency: Currency,
        balance: float,
        last_updated: datetime,
    ) -> str:
        """Add a new cash account and return its account number."""
        pass

    @abstractmethod
    def update_cash(
        self,
        bank: str,
        account_number: str,
        currency: Currency,
        last_updated: datetime,
    ) -> None:
        """Update cash account."""
        pass

    @abstractmethod
    def get_balance(self, account_number: str) -> float:
        """Get the current balance of a cash account."""
        pass


class PriceRepository(PriceProvider, ABC):
    """Repository for asset price data."""

    @abstractmethod
    def cache_price(self, ticker: str, price: float, timestamp: datetime) -> None:
        """Cache a price for later use."""
        pass

    @abstractmethod
    def get_cached_price(self, ticker: str, max_age_minutes: int = 15) -> float:
        """Get cached price if available and not stale."""
        pass

    @abstractmethod
    def sync_price_history(
        self, tickers: list[str], start_date: datetime, period: str = "1d"
    ) -> None:
        """Fetch and store missing price history data for tickers."""
        pass


class CurrencyRepository(CurrencyProvider, ABC):
    """Repository for currency data (ticker currencies and exchange rates)."""

    @abstractmethod
    def set_ticker_currency(self, ticker: str, currency: str) -> None:
        """Cache a ticker's native currency."""
        pass

    @abstractmethod
    def get_exchange_rate(
        self, from_currency: str, to_currency: str, max_age_minutes: int = 60
    ) -> float | None:
        """Get cached exchange rate if fresh enough."""
        pass

    @abstractmethod
    def set_exchange_rate(
        self, from_currency: str, to_currency: str, rate: float
    ) -> None:
        """Cache an exchange rate."""
        pass


class ReferenceRepository(ABC):
    """Repository for securities reference data."""

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search securities by ticker or name (case-insensitive)."""
        pass


class DividendRepository(BaseRepository, ABC):
    """Repository for dividend records."""

    @abstractmethod
    def add_dividend(
        self,
        ticker: str,
        amount: float,
        date: datetime,
    ) -> int:
        """Add a new dividend and return its id."""
        pass

    @abstractmethod
    def update_dividend(
        self,
        id: int,
        ticker: str,
        amount: float,
        date: datetime,
    ) -> None:
        """Update an existing dividend by ID."""
        pass

    @abstractmethod
    def get_by_ticker(self, ticker: str) -> Optional[pl.DataFrame]:
        """Get all dividends for a specific ticker."""
        pass

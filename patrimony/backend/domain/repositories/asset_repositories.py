"""Repository interfaces for asset-related domain entities.

Covers securities, cash, prices, currencies, reference data,
dividends, and physical properties.
"""

from abc import ABC, abstractmethod
from datetime import datetime

import polars as pl

from ..constants import DEFAULT_CURRENCY
from ..entities import AssetType, Currency, EntryType
from ..interfaces import CurrencyProvider


class BaseRepository(ABC):
    """Base asset repository interface methods."""

    @abstractmethod
    def get_all(self) -> pl.DataFrame:
        """Get all entities."""
        pass

    @abstractmethod
    def get_by_id(self, id: int | str) -> pl.DataFrame:
        """Retrieve entity by ID."""
        pass

    @abstractmethod
    def delete(self, id: int | str) -> None:
        """Delete entity by ID."""
        pass


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
    def get_by_ticker(self, ticker: str) -> pl.DataFrame:
        """Get all positions for a specific ticker."""
        pass

    @abstractmethod
    def get_aggregated_positions(self, ticker: str | None = None) -> pl.DataFrame:
        """Get aggregated positions, optionally filtered by a single ticker."""
        pass

    @abstractmethod
    def get_earliest_purchase_date(self, ticker: str | None = None) -> datetime | None:
        """Return the earliest purchase date, optionally filtered by ticker.

        This is useful for determining how far back to fetch historical price data.
        """
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
    ) -> None:
        """Record a cash operation on the balance."""
        pass

    @abstractmethod
    def get_operations_by_account(self, account_number: str) -> pl.DataFrame:
        """Get all balance operations for a specific account."""
        pass

    @abstractmethod
    def get_all_operations(self) -> pl.DataFrame:
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
        category: str,
    ) -> None:
        """Update a balance operation by ID."""
        pass

    @abstractmethod
    def delete_operation_by_id(self, id: int) -> None:
        """Delete a balance operation by ID."""
        pass

    @abstractmethod
    def get_cash_balance_history(self) -> pl.DataFrame:
        """Get cash balance history over time for all accounts by summing the operations."""
        pass

    @abstractmethod
    def recalculate_balances(self, account_number: str) -> None:
        """Recalculate ranks and running balances for all operations of an account.

        This is useful after modifying or deleting past operations, to ensure subsequent balances are correct.
        """
        pass


class CashRepository(BaseRepository, CashOperationRepository, ABC):
    """Repository for cash accounts."""

    @abstractmethod
    def add_cash(
        self,
        bank: str,
        account_number: str,
        currency: Currency,
        last_updated: datetime,
        entry_type: EntryType = EntryType.MANUAL,
    ) -> None:
        """Add a new cash account."""
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
    def rename_account(self, old_account_number: str, new_account_number: str) -> None:
        """Rename a cash account, cascading to all referencing balance_operations.

        Both updates run in a single transaction so the foreign-key
        relationship is never broken.
        """
        pass

    @abstractmethod
    def get_balance(self, account_number: str) -> float:
        """Get the current balance of a cash account."""
        pass

    @abstractmethod
    def get_total_balance(self) -> float:
        """Return the total balance across all cash accounts (raw, no currency conversion)."""
        pass


class PriceRepository(ABC):
    """Repository for asset price data."""

    @abstractmethod
    def cache_price(self, ticker: str, price: float, timestamp: datetime) -> None:
        """Cache a price for later use."""
        pass

    @abstractmethod
    def store_price_history(
        self, ticker: str, df: pl.DataFrame, period: str = "1d"
    ) -> None:
        """Insert new price history rows in bulk, ignoring duplicates."""
        pass

    @abstractmethod
    def get_stored_date_range(
        self, ticker: str, period: str = "1d"
    ) -> tuple[datetime | None, datetime | None]:
        """Return (min_date, max_date) of stored price history for a ticker."""
        pass

    @abstractmethod
    def get_cache_timestamps(self, tickers: list[str]) -> dict[str, datetime]:
        """Return {ticker: last_updated} for tickers present in price cache."""
        pass

    @abstractmethod
    def get_cached_prices(
        self, tickers: list[str], max_age_minutes: int = 15
    ) -> dict[str, float]:
        """Return cached prices that are still fresh (within max_age_minutes)."""
        pass

    @abstractmethod
    def get_last_known_prices(self, tickers: list[str]) -> dict[str, float]:
        """Return the most recent stored historical close price per ticker."""
        pass

    @abstractmethod
    def store_intraday_prices(self, ticker: str, df: pl.DataFrame) -> None:
        """Insert or replace stored intraday prices for a ticker with fresh data."""
        pass

    @abstractmethod
    def get_intraday_prices(self, tickers: list[str]) -> pl.DataFrame:
        """Get today's intraday price data for the given tickers."""
        pass

    @abstractmethod
    def get_intraday_last_updated(self, ticker: str) -> datetime | None:
        """Return the most recent last_updated timestamp for a ticker's intraday data."""
        pass

    @abstractmethod
    def get_latest_intraday_prices(
        self, tickers: list[str], max_age_minutes: int = 15
    ) -> dict[str, float]:
        """Return the latest intraday close price per ticker if data is fresh."""
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


class DividendRepository(BaseRepository, ABC):
    """Repository for dividend records."""

    @abstractmethod
    def add_dividend(
        self,
        ticker: str,
        amount: float,
        date: datetime,
    ) -> None:
        """Add a new dividend."""
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
    def get_by_ticker(self, ticker: str) -> pl.DataFrame:
        """Get all dividends for a specific ticker."""
        pass

    @abstractmethod
    def get_total_amount(self) -> float:
        """Return the total amount of all dividends (raw, no currency conversion)."""
        pass

    @abstractmethod
    def get_totals_by_ticker(self) -> dict[str, float]:
        """Return ``{ticker: total_amount}`` for all dividends.

        Amounts are in each ticker's native currency; callers are responsible
        for currency conversion via ``CurrencyService``.
        """
        pass


class PropertyRepository(BaseRepository, ABC):
    """Repository for physical properties (real estate, valuables, etc.)."""

    @abstractmethod
    def add_property(
        self,
        name: str,
        value: float,
        purchase_date: datetime,
        description: str = "",
        category: str = "Other",
        currency: str = DEFAULT_CURRENCY,
        entry_type: EntryType = EntryType.MANUAL,
    ) -> None:
        """Add a new property."""
        pass

    @abstractmethod
    def update_property(
        self,
        id: int,
        name: str,
        value: float,
        purchase_date: datetime,
        description: str = "",
        category: str = "Other",
        currency: str = DEFAULT_CURRENCY,
    ) -> None:
        """Update an existing property by ID."""
        pass

    @abstractmethod
    def get_total_value_by_currency(self) -> pl.DataFrame:
        """Return aggregated property values grouped by currency.

        Returns a DataFrame with columns: currency, total_value.
        """
        pass

from abc import ABC, abstractmethod
from datetime import datetime

from .entities import AssetType, Currency, EntryType, TransactionType


### Base repository interfaces for data access abstraction. ###
class BaseRepository(ABC):
    """Base repository interface methods."""

    @abstractmethod
    def get_all(self) -> object:
        """Get all entities."""
        pass

    @abstractmethod
    def get_by_id(self, id: int) -> object:
        """Retrieve entity by ID."""
        pass

    @abstractmethod
    def delete(self, id: int) -> None:
        """Delete entity by ID."""
        pass


class BasePriceRepository(ABC):
    """Base repository for price data."""

    @abstractmethod
    def get_current_price(self, ticker: str) -> float:
        """Get current price for a ticker."""
        pass

    @abstractmethod
    def get_price_history(
        self,
        ticker: str,
        start_date: datetime = None,
        end_date: datetime = None,
        interval: str = "1d",
    ) -> object:
        """Fetch price history for a ticker.

        Args:
            ticker: Stock ticker symbol
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            interval: Data interval (e.g. '5m', '1d', '1wk')

        Returns:
            DataFrame with columns: date, close
        """
        pass


class BaseCurrencyRepository(ABC):
    """Base repository for currency data."""

    @abstractmethod
    def get_ticker_currency(self, ticker: str) -> float:
        """Get currency for a ticker."""
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
        transaction_type: TransactionType,
        date: datetime,
    ) -> int:
        """Add a new position and return its id."""
        pass

    @abstractmethod
    def get_by_ticker(self, ticker: str) -> object:
        """Get all positions for a specific ticker."""
        pass

    @abstractmethod
    def get_aggregated_positions(self) -> object:
        """Get aggregated positions (total quantities, avg prices)."""
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
    ) -> int:
        """Record a cash operation on the balance and return the operation ID."""
        pass

    @abstractmethod
    def get_operations_by_account(self, account_number: str) -> object:
        """Get all balance operations for a specific account."""
        pass

    @abstractmethod
    def get_all_operations(self) -> object:
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
    ) -> None:
        """Update a balance operation by ID."""
        pass

    @abstractmethod
    def delete_operation_by_id(self, id: int) -> None:
        """Delete a balance operation by ID."""
        pass

    @abstractmethod
    def get_cash_balance_history(self) -> object:
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


class MarketDataProvider(BasePriceRepository, BaseCurrencyRepository, ABC):
    """Interface for external market data providers.

    Generic abstraction for market data providers (Yahoo Finance, Alpha Vantage, etc.)
    """

    @abstractmethod
    def get_price_history_period(
        self,
        ticker: str,
        period: str = None,
        interval: str = "1d",
    ) -> object:
        """Fetch price history for a ticker using period instead of dates.

        Args:
            ticker: Stock ticker symbol
            period: yfinance period string (e.g. '1d', '1mo', '1y')
            interval: Data interval (e.g. '5m', '1d', '1wk')

        Returns:
            DataFrame with columns: date, close
        """
        pass


class PriceRepository(BasePriceRepository, ABC):
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


class CurrencyRepository(BaseCurrencyRepository, ABC):
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

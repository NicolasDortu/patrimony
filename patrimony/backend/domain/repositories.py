from abc import ABC, abstractmethod
from datetime import datetime

from .entities import AssetType, Currency, TransactionType, EntryType


class Repository(ABC):
    """Base repository interface following Repository Pattern."""

    @abstractmethod
    def get_by_id(self, id: int) -> object:
        """Retrieve entity by ID."""
        pass

    @abstractmethod
    def delete(self, id: int) -> None:
        """Delete entity by ID."""
        pass

    @abstractmethod
    def get_all(self) -> object:
        """Get all entities."""
        pass


class SecuritiesRepository(Repository, ABC):
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
        currency: Currency,
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


class CashRepository(Repository, ABC):
    """Repository for cash accounts.

    Specific interface for cash-related operations.
    """

    @abstractmethod
    def add_cash(
        self,
        bank: str,
        account_number: str,
        currency: Currency,
        balance: float,
        last_updated: datetime,
    ) -> int:
        """Add a new cash account and return its id."""
        # TODO: return success/failure instead
        pass

    @abstractmethod
    def update_cash(
        self,
        id: int,
        bank: str,
        account_number: str,
        currency: Currency,
        last_updated: datetime,
    ) -> None:
        """Update cash account."""
        pass

    @abstractmethod
    def get_balance(self, account_number: str, currency: Currency) -> float:
        """Get the current balance of a cash account."""
        pass

    @abstractmethod
    def operation_balance(
        self,
        account_number: str,
        currency: Currency,
        amount: float,
        title: str,
        operation_date: datetime,
        entry_type: EntryType = EntryType.MANUAL,
    ) -> list[bool, str]:
        """Record a cash operation on the balance and return success/failure and message."""
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
    def delete_operation_by_id(self, id: int) -> None:
        """Delete a balance operation by ID."""
        pass

    @abstractmethod
    def get_cash_balance_history(self) -> object:
        """Get cash balance history over time for all accounts."""
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


class MarketDataProvider(ABC):
    """Interface for external market data providers.

    Generic abstraction for market data providers (Yahoo Finance, Alpha Vantage, etc.)
    """

    @abstractmethod
    def get_current_price(self, ticker: str) -> float:
        """Fetch current price for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Current price or None if unavailable
        """
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


class PriceRepository(ABC):
    """Repository for asset price data."""

    @abstractmethod
    def get_current_price(self, ticker: str) -> float:
        """Get current price for a ticker."""
        pass

    @abstractmethod
    def cache_price(self, ticker: str, price: float, timestamp: datetime) -> None:
        """Cache a price for later use."""
        pass

    @abstractmethod
    def get_cached_price(self, ticker: str, max_age_minutes: int = 15) -> float:
        """Get cached price if available and not stale."""
        pass

    @abstractmethod
    def get_price_history(
        self, tickers: list[str], start_date: datetime, end_date: datetime
    ) -> object:
        """Get stored price history for tickers within a date range."""
        pass

    @abstractmethod
    def sync_price_history(self, tickers: list[str], start_date: datetime) -> None:
        """Fetch and store missing price history data for tickers."""
        pass

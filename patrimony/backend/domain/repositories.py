from abc import ABC, abstractmethod
from datetime import datetime
from typing import Generic, TypeVar
import polars as pl

from .entities import AssetType, Currency, TransactionType, EntryType

# Generic types for repository pattern
T = TypeVar("T")
ID = TypeVar("ID")


class Repository(ABC, Generic[T, ID]):
    """Base repository interface following Repository Pattern."""

    @abstractmethod
    def get_by_id(self, id: ID) -> T:
        """Retrieve entity by ID."""
        pass

    @abstractmethod
    def delete(self, id: ID) -> None:
        """Delete entity by ID."""
        pass

    @abstractmethod
    def get_all(self) -> pl.DataFrame:
        """Get all entities."""
        pass


class SecuritiesRepository(Repository[T, int], ABC):
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
        """Add a new position."""
        pass

    @abstractmethod
    def get_by_ticker(self, ticker: str) -> pl.DataFrame:
        """Get all positions for a specific ticker."""
        pass

    @abstractmethod
    def get_aggregated_positions(self) -> pl.DataFrame:
        """Get aggregated positions (total quantities, avg prices)."""
        pass


class CashRepository(Repository[T, int], ABC):
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
        """Add a new cash account."""
        pass

    @abstractmethod
    def update_cash(
        self,
        id: int,
        bank: str,
        account_number: str,
        currency: Currency,
        balance: float,
        last_updated: datetime,
    ) -> None:
        """Update cash account."""
        pass

    @abstractmethod
    def get_by_bank(self, bank: str) -> pl.DataFrame:
        """Get all cash accounts for a specific bank."""
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
    def get_price_history(self, ticker: str, period: str = "1mo") -> pl.DataFrame:
        """Fetch historical prices for a ticker.

        Args:
            ticker: Stock ticker symbol
            period: Time period (e.g., '1mo', '1y')

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

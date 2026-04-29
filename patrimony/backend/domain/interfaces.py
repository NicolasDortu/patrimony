"""Domain interfaces for external data providers.

These abstract interfaces define the contracts for fetching live data
from external sources (market data APIs, exchange rate services, etc.).
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import datetime
from typing import Protocol

import polars as pl

from .entities import ConnectorProfile, TickerInfo


class UnitOfWork(Protocol):
    """Provides transactional scope for grouping repository writes."""

    def transaction(self) -> AbstractContextManager[None]: ...


class PriceProvider(ABC):
    """Interface for fetching live price data from an external source."""

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
        *,
        period: str | None = None,
    ) -> pl.DataFrame | None:
        """Fetch price history for a ticker.

        Either supply (start_date, end_date) for a date range, or ``period``
        (e.g. '1d', '1mo', '1y') for a relative window.  When ``period`` is
        given, start_date/end_date are ignored.

        Returns:
            DataFrame with columns: date, close_price
        """
        pass


class CurrencyProvider(ABC):
    """Interface for fetching live currency data from an external source."""

    @abstractmethod
    def get_ticker_currency(self, ticker: str) -> float:
        """Get the native trading currency of a ticker."""
        pass


class MarketDataProvider(PriceProvider, CurrencyProvider, ABC):
    """Interface for external market data providers.

    Generic abstraction for market data providers (e.g., Yahoo Finance)
    Combines price and currency fetching capabilities with additional methods.
    """

    _provider_was_called: bool = False

    def check_provider_was_called(self) -> bool:
        """Check and reset whether any API call was made since last check."""
        result = self._provider_was_called
        self._provider_was_called = False
        return result

    @abstractmethod
    def get_exchange_rate(self, from_currency: str, to_currency: str) -> float | None:
        """Fetch the exchange rate from from_currency to to_currency."""
        pass

    @abstractmethod
    def get_dividend_history(
        self,
        ticker: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> pl.DataFrame | None:
        """Fetch dividend history for a ticker.

        Args:
            ticker: Stock ticker symbol
            start_date: Optional start of date range (inclusive)
            end_date: Optional end of date range (inclusive)

        Returns:
            DataFrame with columns: date, amount_per_share
        """
        pass

    @abstractmethod
    def resolve_ticker_info(self, identifier: str) -> TickerInfo | None:
        """Resolve an identifier (ISIN or ticker) to enriched metadata via a single API call.

        Returns a TickerInfo entity with resolved fields,
        or None if resolution failed.
        """
        pass


class FileConnector(ABC):
    """Interface for reading uploaded files into a raw DataFrame."""

    @abstractmethod
    def read_file(
        self,
        file_bytes: bytes,
        filename: str,
        delimiter: str = ",",
        encoding: str = "utf8",
    ) -> pl.DataFrame:
        """Parse an uploaded file into a raw DataFrame.

        Args:
            file_bytes: Raw bytes of the uploaded file.
            filename: Original filename (used to detect format).
            delimiter: CSV delimiter character (ignored for Excel).
            encoding: Text encoding for CSV files (ignored for Excel).

        Returns:
            A polars DataFrame with the raw file contents.
        """
        pass


class SiteConnector(ABC):
    """Interface for a site-specific data connector.

    Each site (broker or bank) implements this interface to fetch data
    and return it as a DataFrame. The implementation handles all details
    of data collection (browser automation, API calls, scraping, etc.).
    """

    @property
    @abstractmethod
    def site_id(self) -> str:
        """Unique identifier for this connector."""
        pass

    @property
    @abstractmethod
    def profile(self) -> ConnectorProfile:
        """Data mapping and import configuration."""
        pass

    @abstractmethod
    def fetch_data(
        self,
        credentials: dict[str, str],
        on_status: Callable[[str], None] | None = None,
        on_user_input: Callable[[str, str], str] | None = None,
        **options,
    ) -> pl.DataFrame:
        """Fetch data from the external source.

        Args:
            credentials: Dict with authentication keys.
            on_status: Optional callback receiving status messages.
            on_user_input: Optional callback to request input from the user.
                Signature: (prompt_type, message) -> user_response.
                prompt_type is "text" (input box) or "action" (confirm dialog).
            **options: Implementation-specific options (e.g. headless).

        Returns:
            A DataFrame with the fetched raw data.
        """
        pass

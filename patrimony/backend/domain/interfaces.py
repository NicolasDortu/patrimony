"""Domain interfaces for external data providers.

These abstract interfaces define the contracts for fetching live data
from external sources (market data APIs, exchange rate services, etc.).
"""

from abc import ABC, abstractmethod
from datetime import datetime

import polars as pl


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


class CurrencyProvider(ABC):
    """Interface for fetching live currency data from an external source."""

    @abstractmethod
    def get_ticker_currency(self, ticker: str) -> float:
        """Get the native trading currency of a ticker."""
        pass


class MarketDataProvider(PriceProvider, CurrencyProvider, ABC):
    """Interface for external market data providers.

    Generic abstraction for market data providers (Yahoo Finance, Alpha Vantage, etc.)
    Combines price and currency fetching capabilities with additional methods.
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

    @abstractmethod
    def get_exchange_rate(self, from_currency: str, to_currency: str) -> float | None:
        """Fetch the exchange rate from from_currency to to_currency."""
        pass


class FileConnector(ABC):
    """Interface for reading uploaded files into a raw DataFrame."""

    @abstractmethod
    def read_file(
        self, file_bytes: bytes, filename: str, delimiter: str = ","
    ) -> pl.DataFrame:
        """Parse an uploaded file into a raw DataFrame.

        Args:
            file_bytes: Raw bytes of the uploaded file.
            filename: Original filename (used to detect format).
            delimiter: CSV delimiter character (ignored for Excel).

        Returns:
            A Polars DataFrame with the raw file contents.
        """
        pass

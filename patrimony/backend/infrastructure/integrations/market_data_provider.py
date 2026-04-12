"""External market data provider implementations.

This module contains concrete implementations of the MarketDataProvider interface
for different data sources (Yahoo Finance, Alpha Vantage, etc.). Only Yfinance is implemented for now.
"""

import logging
import threading
import time
from datetime import datetime

import polars as pl
import yfinance as yf
from typing import Optional

from ...domain.interfaces import MarketDataProvider


logger = logging.getLogger(__name__)

# Minimum seconds between consecutive yfinance API calls.
_MIN_REQUEST_INTERVAL_S: float = 0.55

_EMPTY_HISTORY = pl.DataFrame({"date": [], "close_price": []})
_EMPTY_DIVIDENDS = pl.DataFrame({"date": [], "amount_per_share": []})


class YahooFinanceProvider(MarketDataProvider):
    """Market data provider using Yahoo Finance (yfinance library).

    This is the default provider - free, no API key required.
    Includes per-call throttling to avoid hitting Yahoo Finance rate limits.
    """

    def __init__(self) -> None:
        self._last_call: float = 0.0
        self._lock = threading.Lock()

    def _throttle(self) -> None:
        """Block until at least ``_MIN_REQUEST_INTERVAL_S`` has passed since the last call."""
        with self._lock:
            now = time.monotonic()
            wait = self._last_call + _MIN_REQUEST_INTERVAL_S - now
        if wait > 0:
            time.sleep(wait)
        with self._lock:
            self._last_call = time.monotonic()
            self._api_was_called = True

    @staticmethod
    def _parse_history_df(data) -> pl.DataFrame:
        """Convert a yfinance pandas history DataFrame into a polars DataFrame.

        Returns a DataFrame with columns: date, close_price.
        """
        data = data.reset_index()
        if "Datetime" in data.columns:
            date_col = "Datetime"
        elif "Date" in data.columns:
            date_col = "Date"
        else:
            date_col = data.columns[0]

        data = data.rename(columns={date_col: "date", "Close": "close_price"})
        return pl.from_pandas(data[["date", "close_price"]])

    def get_current_price(self, ticker: str) -> Optional[float]:
        """Fetch current price from Yahoo Finance."""
        try:
            self._throttle()
            stock = yf.Ticker(ticker)
            data = stock.history(period="1d")
            if not data.empty:
                return float(data["Close"].iloc[-1])
            else:
                logger.warning("No price data found for %s", ticker)
        except Exception as e:
            logger.warning("Error fetching price for %s: %s", ticker, e)
            return None
        return None

    def get_price_history(
        self,
        ticker: str,
        start_date: datetime = None,
        end_date: datetime = None,
        interval: str = "1d",
    ) -> pl.DataFrame:
        """Fetch price history from Yahoo Finance using date range."""
        try:
            self._throttle()
            stock = yf.Ticker(ticker)
            data = stock.history(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                interval=interval,
            )
            if not data.empty:
                return self._parse_history_df(data)
        except Exception as e:
            logger.warning("Error fetching price history for %s: %s", ticker, e)
        return _EMPTY_HISTORY.clone()

    def get_price_history_period(
        self,
        ticker: str,
        period: str = None,
        interval: str = "1d",
    ) -> pl.DataFrame:
        """Fetch price history from Yahoo Finance using period."""
        try:
            self._throttle()
            stock = yf.Ticker(ticker)
            data = stock.history(period=period, interval=interval)
            if not data.empty:
                return self._parse_history_df(data)
        except Exception as e:
            logger.warning("Error fetching price history for %s: %s", ticker, e)
        return _EMPTY_HISTORY.clone()

    def get_dividend_history(
        self,
        ticker: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> pl.DataFrame:
        """Fetch dividend history from Yahoo Finance.

        Returns a polars DataFrame with columns: date, amount_per_share.
        """
        try:
            self._throttle()
            stock = yf.Ticker(ticker)
            dividends = stock.dividends  # pandas Series indexed by date
            if dividends.empty:
                return _EMPTY_DIVIDENDS.clone()

            pdf = dividends.reset_index()
            pdf.columns = ["date", "amount_per_share"]
            # Strip timezone info to avoid tz-aware vs tz-naive comparison issues
            pdf["date"] = pdf["date"].dt.tz_localize(None)
            df = pl.from_pandas(pdf)

            if start_date is not None:
                df = df.filter(pl.col("date") >= start_date)
            if end_date is not None:
                df = df.filter(pl.col("date") <= end_date)
            return df
        except Exception as e:
            logger.warning("Error fetching dividends for %s: %s", ticker, e)
        return _EMPTY_DIVIDENDS.clone()

    def get_ticker_currency(self, ticker: str) -> Optional[str]:
        """Fetch the native trading currency of a ticker from Yahoo Finance."""
        try:
            self._throttle()
            stock = yf.Ticker(ticker)
            currency = stock.fast_info.get("currency")
            return currency.upper() if currency else None
        except Exception as e:
            logger.warning("Error fetching currency for %s: %s", ticker, e)
            return None

    def get_exchange_rate(
        self, from_currency: str, to_currency: str
    ) -> Optional[float]:
        """Fetch exchange rate using yfinance's {FROM}{TO}=X ticker format."""
        rate_ticker = f"{from_currency.upper()}{to_currency.upper()}=X"
        return self.get_current_price(rate_ticker)

    def resolve_isin(self, isin: str) -> Optional[str]:
        """Resolve an ISIN code to a ticker symbol via yfinance."""
        try:
            self._throttle()
            stock = yf.Ticker(isin)
            # Accessing info triggers the lookup; yfinance resolves ISINs to tickers
            info = stock.info
            symbol = info.get("symbol")
            if symbol and symbol.upper() != isin.upper():
                logger.info("Resolved ISIN %s → %s", isin, symbol)
                return symbol.upper()
            logger.warning("Could not resolve ISIN %s", isin)
            return None
        except Exception as e:
            logger.warning("Error resolving ISIN %s: %s", isin, e)
            return None

    # Mapping from yfinance quoteType to our AssetType values
    _QUOTE_TYPE_MAP: dict[str, str] = {
        "EQUITY": "STOCK",
        "ETF": "ETF",
        "CRYPTOCURRENCY": "CRYPTO",
        "BOND": "BOND",
        "COMMODITY": "COMMODITY",
        "MUTUALFUND": "ETF",
    }

    def resolve_asset_type(self, ticker: str) -> Optional[str]:
        """Resolve a ticker to its asset type via yfinance quoteType."""
        try:
            self._throttle()
            stock = yf.Ticker(ticker)
            quote_type = stock.info.get("quoteType", "")
            mapped = self._QUOTE_TYPE_MAP.get(quote_type.upper())
            if mapped:
                logger.info(
                    "Resolved asset type for %s: %s → %s", ticker, quote_type, mapped
                )
                return mapped
            logger.warning("Unknown quoteType '%s' for %s", quote_type, ticker)
            return None
        except Exception as e:
            logger.warning("Error resolving asset type for %s: %s", ticker, e)
            return None

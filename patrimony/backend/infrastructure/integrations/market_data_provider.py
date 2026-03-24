"""External market data provider implementations.

This module contains concrete implementations of the MarketDataProvider interface
for different data sources (Yahoo Finance, Alpha Vantage, etc.). Only Yfinance is implemented for now.
"""

import logging
from datetime import datetime

import yfinance as yf
from typing import Optional
import polars as pl

from ...domain.interfaces import MarketDataProvider


logger = logging.getLogger(__name__)


class YahooFinanceProvider(MarketDataProvider):
    """Market data provider using Yahoo Finance (yfinance library).

    This is the default provider - free, no API key required.
    """

    def get_current_price(self, ticker: str) -> Optional[float]:
        """Fetch current price from Yahoo Finance."""
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period="1d")
            if not data.empty:
                return float(data["Close"].iloc[-1])
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
            stock = yf.Ticker(ticker)
            data = stock.history(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                interval=interval,
            )
            if not data.empty:
                data = data.reset_index()
                date_col = "Datetime" if "Datetime" in data.columns else "Date"
                return pl.DataFrame(
                    {
                        "date": data[date_col].tolist(),
                        "close_price": data["Close"].tolist(),
                    }
                )
        except Exception as e:
            logger.warning("Error fetching price history for %s: %s", ticker, e)
        return pl.DataFrame(schema={"date": pl.Datetime, "close_price": pl.Float64})

    def get_price_history_period(
        self,
        ticker: str,
        period: str = None,
        interval: str = "1d",
    ) -> pl.DataFrame:
        """Fetch price history from Yahoo Finance using period."""
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period=period, interval=interval)
            if not data.empty:
                data = data.reset_index()
                date_col = "Datetime" if "Datetime" in data.columns else "Date"
                return pl.DataFrame(
                    {
                        "date": data[date_col].tolist(),
                        "close_price": data["Close"].tolist(),
                    }
                )
        except Exception as e:
            logger.warning("Error fetching price history for %s: %s", ticker, e)
        return pl.DataFrame(schema={"date": pl.Datetime, "close_price": pl.Float64})

    def get_ticker_currency(self, ticker: str) -> Optional[str]:
        """Fetch the native trading currency of a ticker from Yahoo Finance."""
        try:
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

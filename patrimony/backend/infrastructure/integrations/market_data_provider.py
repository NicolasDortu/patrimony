"""External market data provider implementations.

This module contains concrete implementations of the MarketDataProvider interface
for different data sources (Yahoo Finance, Alpha Vantage, etc.).
"""

import yfinance as yf
from typing import Optional
import polars as pl

from ...domain.repositories import MarketDataProvider


class YahooFinanceProvider(MarketDataProvider):
    """Market data provider using Yahoo Finance (yfinance library).

    This is the default provider - free, no API key required.
    Suitable for real-time quotes and historical data.
    """

    def get_current_price(self, ticker: str) -> Optional[float]:
        """Fetch current price from Yahoo Finance."""
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period="1d")
            if not data.empty:
                return float(data["Close"].iloc[-1])
        except Exception as e:
            print(f"Error fetching price for {ticker}: {e}")
            return None
        return None

    def get_price_history(self, ticker: str, period: str = "1mo") -> pl.DataFrame:
        """Fetch historical prices from Yahoo Finance."""
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period=period)
            if not data.empty:
                return pl.DataFrame(
                    {
                        "date": data.index.tolist(),
                        "close": data["Close"].tolist(),
                    }
                )
        except Exception:
            return pl.DataFrame(schema={"date": pl.Datetime, "close": pl.Float64})
        return pl.DataFrame(schema={"date": pl.Datetime, "close": pl.Float64})

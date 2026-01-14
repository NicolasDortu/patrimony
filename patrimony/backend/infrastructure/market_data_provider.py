import yfinance as yf
import polars as pl
from typing import Optional


def fetch_current_price(ticker: str) -> Optional[float]:
    """Fetch the current price for a ticker using yfinance."""
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="1d")
        if not data.empty:
            return float(data["Close"].iloc[-1])
    except Exception as e:
        print(e)
        return None
    return None


def fetch_price_history(ticker: str, period: str = "1mo") -> pl.DataFrame:
    """Fetch historical prices for a ticker."""
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

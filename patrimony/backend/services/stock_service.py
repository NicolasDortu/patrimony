from datetime import datetime
from dataclasses import dataclass
from typing import Optional

import polars as pl

from .price_service import fetch_and_cache_price
from ..domain.assets import Stock, Currency
from ..database.connection import DatabaseConnection
from ..database.queries import TradableAssetsOperations, PriceCacheOperations


@dataclass
class AddPositionResult:
    """Result of adding a position."""

    success: bool
    message: str
    current_price: Optional[float] = None


class StockService:
    """Service layer for stock operations."""

    def __init__(self):
        self._conn = DatabaseConnection().get_connection()
        self._price_cache = PriceCacheOperations(self._conn)
        self._tradable_assets = TradableAssetsOperations(self._conn)

    def add_position(
        self,
        ticker: str,
        buy_price: float,
        quantity: float,
        currency: Currency = Currency.USD,
    ) -> AddPositionResult:
        """
        Add a new stock position.

        Args:
            ticker: Stock ticker symbol
            buy_price: Purchase price per share
            quantity: Number of shares
            currency: Currency of the transaction

        Returns:
            AddPositionResult with success status and message
        """
        try:
            # Validate and create domain object
            stock = Stock(
                name=ticker.upper(),
                ticker=ticker.upper(),
                buy_price=buy_price,
                quantity=quantity,
                buy_date=datetime.now(),
                currency=currency,
            )

            # Store position in the database
            self._tradable_assets.add_position(
                ticker=stock.ticker,
                buy_price=stock.buy_price,
                quantity=stock.quantity,
            )
            # Fetch and cache current price
            current_price = fetch_and_cache_price(stock.ticker, self._price_cache)

            if current_price:
                return AddPositionResult(
                    success=True,
                    message=f"Added {stock.ticker} @ ${stock.buy_price:.2f} (Current: ${current_price:.2f})",
                    current_price=current_price,
                )
            else:
                return AddPositionResult(
                    success=True,
                    message=f"Added {stock.ticker} @ ${stock.buy_price:.2f}. Could not fetch current price.",
                )

        except Exception as e:
            return AddPositionResult(
                success=False,
                message=f"Error adding position: {str(e)}",
            )

    def validate_ticker(self, ticker: str) -> bool:
        """Validate if a ticker symbol is valid."""
        return bool(ticker and ticker.strip())

    def validate_price(self, price: float) -> bool:
        """Validate if a price is valid."""
        return price > 0

    def get_all_stocks(self) -> pl.DataFrame:
        """Retrieve all stock assets from the database."""
        return self._tradable_assets.get_positions()

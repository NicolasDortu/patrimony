from datetime import datetime
from dataclasses import dataclass
from typing import Optional

import polars as pl

from .price_service import fetch_and_cache_price
from ..domain.models.assets import Stock, Currency
from ..database.connection import DatabaseConnection
from ..database.queries.assets import TradableAssetsOperations
from ..database.queries.prices import PriceCacheOperations


@dataclass
class StockPositionResult:
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
        currency: Currency = Currency.EUR,
    ) -> StockPositionResult:
        """
        Add a new stock position.

        Args:
            ticker: Stock ticker symbol
            buy_price: Purchase price per share
            quantity: Number of shares
            currency: Currency of the transaction

        Returns:
            StockPositionResult with success status and message
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
                return StockPositionResult(
                    success=True,
                    message=f"Added {stock.ticker} @ ${stock.buy_price:.2f} (Current: ${current_price:.2f})",
                    current_price=current_price,
                )
            else:
                return StockPositionResult(
                    success=True,
                    message=f"Added {stock.ticker} @ ${stock.buy_price:.2f}. Could not fetch current price.",
                )

        except Exception as e:
            return StockPositionResult(
                success=False,
                message=f"Error adding position: {str(e)}",
            )

    def delete_position(self, id: int) -> StockPositionResult:
        """Delete a stock position by ID."""
        try:
            self._tradable_assets.delete_position(id=id)
            return StockPositionResult(
                success=True,
                message=f"Deleted position with ID {id}.",
            )
        except Exception as e:
            return StockPositionResult(
                success=False,
                message=f"Error deleting position: {str(e)}",
            )

    def validate_ticker(self, ticker: str) -> bool:
        """Validate if a ticker symbol is valid."""
        # TODO: Implement a check to see if the ticker exists
        pass

    def get_all_stocks(self) -> pl.DataFrame:
        """Retrieve all stock assets from the database."""
        return self._tradable_assets.get_positions()

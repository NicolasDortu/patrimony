import logging
from datetime import datetime, timedelta
from typing import Optional
import polars as pl

from ...domain.entities import (
    AssetType,
    Currency,
    EntryType,
    TransactionType,
)
from .operation_result import OperationResult
from ..di_container import container

logger = logging.getLogger(__name__)

PERIOD_CONFIG = {
    "1D": {"days": 1, "period": "1d", "interval": "5m"},
    "5D": {"days": 5, "period": "5d", "interval": "1d"},
    "1M": {"days": 30, "period": "1mo", "interval": "1d"},
    "6M": {"days": 180, "period": "6mo", "interval": "1d"},
    "1Y": {"days": 365, "period": "1y", "interval": "1d"},
    "5Y": {"days": 1825, "period": "5y", "interval": "1wk"},
}


class SecuritiesController:
    """Controller for securities (stocks, crypto, ETFs, bonds) operations."""

    @property
    def _securities_repo(self):
        """Get securities repository from DI container."""
        return container.securities_repository()

    @property
    def _price_repo(self):
        """Get price repository from DI container."""
        return container.price_repository()

    @property
    def _market_data(self):
        """Get market data provider from DI container."""
        return container.market_data_provider()

    def add_position(
        self,
        ticker: str,
        price: float,
        quantity: float,
        entry_type: EntryType,
        asset_type: AssetType,
        transaction_type: TransactionType,
        currency: Currency,
        date: Optional[datetime] = None,
    ) -> OperationResult:
        """Add new position (buy or sell).

        Args:
            ticker: Ticker symbol
            price: Price per unit
            quantity: Number of units
            entry_type: How entry was created (manual, API, etc.)
            asset_type: Type of asset (stock, crypto, etc.)
            transaction_type: Buy or sell
            currency: Currency of transaction
            date: Transaction date (defaults to now)

        Returns:
            OperationResult with success status and new position ID
        """
        try:
            if date is None:
                date = datetime.now()

            position_id = self._securities_repo.add_position(
                ticker=ticker,
                price=price,
                quantity=quantity,
                entry_type=entry_type,
                asset_type=asset_type,
                transaction_type=transaction_type,
                currency=currency,
                date=date,
            )

            return OperationResult(
                success=True,
                message=f"Position for {ticker} added successfully",
                data={"id": position_id},
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to add position: {str(e)}",
            )

    def delete_position(self, id: int) -> OperationResult:
        """Delete position by ID.

        Args:
            id: Position ID

        Returns:
            OperationResult with success status
        """
        try:
            self._securities_repo.delete(id)
            return OperationResult(
                success=True,
                message=f"Position {id} deleted successfully",
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to delete position: {str(e)}",
            )

    def get_all_positions(self) -> list[dict]:
        """Get all individual positions.

        Returns:
            List of position dictionaries
        """
        df = self._securities_repo.get_all()
        return df.to_dicts() if df is not None else []

    def get_positions_by_ticker(self, ticker: str) -> list[dict]:
        """Get all positions for specific ticker.

        Args:
            ticker: Ticker symbol

        Returns:
            List of position dictionaries
        """
        df = self._securities_repo.get_by_ticker(ticker)
        return df.to_dicts() if df is not None else []

    def get_aggregated_positions(self) -> list[dict]:
        """Get aggregated positions (total quantities, avg prices).

        Enriches data with current prices from price repository.

        Returns:
            List of aggregated position dictionaries with current prices
        """
        df = self._securities_repo.get_aggregated_positions()
        if df is None:
            return []

        # Enrich with current prices
        df = self._enrich_with_prices(df)
        return df.to_dicts()

    def get_position_by_id(self, id: int) -> Optional[dict]:
        """Get single position by ID.

        Args:
            id: Position ID

        Returns:
            Position dictionary or None if not found
        """
        df = self._securities_repo.get_by_id(id)
        if df is not None:
            return df.to_dicts()[0]
        return None

    def validate_ticker(self, ticker: str) -> bool:
        # TODO: Implement actual validation logic
        pass

    def _enrich_with_prices(self, df: pl.DataFrame) -> pl.DataFrame:
        """Enrich DataFrame with current prices.

        Args:
            df: DataFrame with ticker column

        Returns:
            DataFrame with added current_price column
        """
        if "ticker" not in df.columns:
            return df

        # Fetch current prices for all tickers
        prices = []
        for ticker in df["ticker"].to_list():
            try:
                price = self._price_repo.get_current_price(ticker)
                prices.append(price)
            except Exception as e:
                logger.error("Error fetching price for %s: %s", ticker, e)
                prices.append(None)

        # Add prices as new column and recompute total_value
        df = df.with_columns(pl.Series("current_price", prices))
        if "total_quantity" in df.columns:
            df = df.with_columns(
                (pl.col("current_price") * pl.col("total_quantity")).alias(
                    "total_value"
                )
            )

        return df

    # Chart methods
    def _fetch_price_data(
        self, ticker: str, config: dict, is_intraday: bool
    ) -> Optional[pl.DataFrame]:
        """Fetch price data from live API (intraday) or cache (daily)."""
        if is_intraday:
            return self._market_data.get_price_history_period(
                ticker, period=config["period"], interval=config["interval"]
            )
        else:
            start = datetime.now() - timedelta(days=config["days"])
            end = datetime.now()
            self._price_repo.sync_price_history([ticker], start)
            return self._price_repo.get_price_history([ticker], start, end)

    def get_chart_data_ticker(self, ticker: str, period: str = "1M") -> list[dict]:
        """Get time-series price data for a single ticker."""
        config = PERIOD_CONFIG.get(period, PERIOD_CONFIG["1M"])
        df = self._securities_repo.get_aggregated_positions_by_ticker(ticker)
        if df is None or df.is_empty():
            return []

        is_intraday = period == "1D"
        price_df = self._fetch_price_data(ticker, config, is_intraday)
        if price_df is None or price_df.is_empty():
            return []

        date_fmt = (
            "%H:%M" if is_intraday else ("%Y-%m" if config["days"] > 365 else "%d/%m")
        )

        rows = []
        last_valid_price = None
        for row in price_df.iter_rows(named=True):
            price = row["close_price"]
            if price is not None and price == price and price > 0:
                last_valid_price = price
            elif last_valid_price is not None:
                price = last_valid_price
            else:
                continue

            date_str = (
                row["date"].strftime(date_fmt)
                if hasattr(row["date"], "strftime")
                else str(row["date"])
            )
            rows.append(
                {
                    "name": date_str,
                    "price": round(price * df["total_quantity"][0], 2),
                }
            )
        return rows

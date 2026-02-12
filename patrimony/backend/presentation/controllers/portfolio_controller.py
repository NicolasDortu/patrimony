"""Portfolio Controller - Orchestrates multiple repositories to provide portfolio-wide metrics and views."""

from dataclasses import dataclass
from typing import Optional
import polars as pl

from ...domain.services import PortfolioCalculator
from ..di_container import container


@dataclass
class PortfolioOverview:
    """Aggregated portfolio data with metrics."""

    securities_total: list[dict]
    cash_entries: list[dict]
    total_value: float
    total_invested: float
    total_return: float
    securities_value: float
    cash_value: float


class PortfolioController:
    """Controller for portfolio-wide operations and metrics.

    Uses DI container to access repositories.
    Uses domain services for business logic.
    """

    @property
    def _securities_repo(self):
        """Get securities repository from DI container."""
        return container.securities_repository()

    @property
    def _cash_repo(self):
        """Get cash repository from DI container."""
        return container.cash_repository()

    @property
    def _price_repo(self):
        """Get price repository from DI container."""
        return container.price_repository()

    def get_portfolio_overview(self) -> PortfolioOverview:
        """Get complete portfolio overview with all metrics.

        Combines securities and cash data, enriches with current prices,
        and calculates total portfolio metrics.

        Returns:
            PortfolioOverview with all portfolio data and metrics
        """
        # Fetch aggregated securities positions
        securities_df = self._securities_repo.get_aggregated_positions()

        # Enrich with current prices
        if securities_df is not None and not securities_df.is_empty():
            securities_df = self._enrich_with_prices(securities_df)

        # Fetch cash accounts
        cash_df = self._cash_repo.get_all()

        # Calculate securities metrics
        total_invested, securities_value, total_return = (
            self._calculate_securities_metrics(securities_df)
        )

        # Calculate cash metrics
        cash_value = self._calculate_cash_value(cash_df)

        # Calculate total portfolio value
        total_value = securities_value + cash_value

        return PortfolioOverview(
            securities_total=securities_df.to_dicts()
            if securities_df is not None and not securities_df.is_empty()
            else [],
            cash_entries=cash_df.to_dicts()
            if cash_df is not None and not cash_df.is_empty()
            else [],
            total_value=total_value,
            total_invested=total_invested,
            total_return=total_return,
            securities_value=securities_value,
            cash_value=cash_value,
        )

    def get_portfolio_positions(self) -> list[dict]:
        """Get all individual security positions with current prices.

        Returns:
            List of position dictionaries
        """
        positions_df = self._securities_repo.get_all()
        if positions_df is not None and not positions_df.is_empty():
            positions_df = self._enrich_with_prices(positions_df)
            return positions_df.to_dicts()
        return []

    def _enrich_with_prices(self, df: pl.DataFrame) -> pl.DataFrame:
        """Enrich DataFrame with current prices.

        Args:
            df: DataFrame with ticker column

        Returns:
            DataFrame with added current_price column
        """
        if df is None or df.is_empty() or "ticker" not in df.columns:
            return df

        # Fetch current prices for all tickers
        prices = []
        for ticker in df["ticker"].to_list():
            try:
                price = self._price_repo.get_current_price(ticker)
                prices.append(price)
            except Exception as e:
                print(f"Error fetching price for {ticker}: {e}")
                prices.append(None)

        # Add prices as new column
        df = df.with_columns(pl.Series("current_price", prices))

        return df

    def _calculate_securities_metrics(
        self, securities_df: Optional[pl.DataFrame]
    ) -> tuple[float, float, float]:
        """Calculate total invested, current value, and return for securities.

        Args:
            securities_df: DataFrame with securities positions

        Returns:
            Tuple of (total_invested, securities_value, total_return)
        """
        if securities_df is None or securities_df.is_empty():
            return 0.0, 0.0, 0.0

        # Filter valid positions (non-null prices and quantities)
        valid_securities = securities_df.filter(
            (pl.col("current_price").is_not_null())
            & (pl.col("total_quantity").is_not_null())
            & (pl.col("total_quantity") > 0)
        )

        if valid_securities.is_empty():
            return 0.0, 0.0, 0.0

        # Use domain service for calculation
        return PortfolioCalculator.calculate_metrics(valid_securities)

    def _calculate_cash_value(self, cash_df: Optional[pl.DataFrame]) -> float:
        """Calculate total cash value.

        Args:
            cash_df: DataFrame with cash accounts

        Returns:
            Total cash balance
        """
        if cash_df is None or cash_df.is_empty():
            return 0.0

        return float(cash_df["balance"].sum())

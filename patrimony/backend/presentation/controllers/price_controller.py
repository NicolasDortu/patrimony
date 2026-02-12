"""Price Controller - Handles fetching and caching asset prices from external providers."""

from typing import Optional

from ...domain.entities import OperationResult
from ..di_container import container


class PriceController:
    """Controller for price-related operations."""

    @property
    def _price_repo(self):
        """Get price repository from DI container."""
        return container.price_repository()

    def get_current_price(self, ticker: str) -> OperationResult:
        """Get current price for a ticker.

        Tries cache first, then fetches from external provider if needed.

        Args:
            ticker: Ticker symbol

        Returns:
            OperationResult with price in data or error message
        """
        try:
            price = self._price_repo.get_current_price(ticker)
            if price is not None and price > 0:
                return OperationResult(
                    success=True,
                    message=f"Price fetched for {ticker}",
                    data={"price": price},
                )
            else:
                return OperationResult(
                    success=False,
                    message=f"Price not available for {ticker}",
                )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Error fetching price for {ticker}: {str(e)}",
            )

    def get_multiple_prices(self, tickers: list[str]) -> dict[str, Optional[float]]:
        """Get current prices for multiple tickers.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary mapping tickers to prices (None if unavailable)
        """
        prices = {}
        for ticker in tickers:
            try:
                prices[ticker] = self._price_repo.get_current_price(ticker)
            except Exception:
                prices[ticker] = None
        return prices

    def get_cached_price(
        self, ticker: str, max_age_minutes: int = 15
    ) -> Optional[float]:
        """Get cached price if available and fresh.

        Args:
            ticker: Ticker symbol
            max_age_minutes: Maximum cache age in minutes

        Returns:
            Cached price or None if not available/stale
        """
        try:
            return self._price_repo.get_cached_price(ticker, max_age_minutes)
        except Exception:
            return None

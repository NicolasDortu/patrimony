"""Repository implementation for price data.

Handles fetching current prices from external APIs and
caching price data in the database.
"""

from datetime import datetime

from ...domain.repositories import PriceRepository, MarketDataProvider
from ..database.connection import DatabaseConnection


class PriceRepositoryImpl(PriceRepository):
    """Concrete implementation of PriceRepository.

    Integrates external market data provider with local caching.
    """

    def __init__(
        self,
        connection: DatabaseConnection,
        market_data_provider: MarketDataProvider,
    ):
        """Initialize with database connection and market data provider.

        Args:
            connection: Database connection instance
            market_data_provider: External data provider (Yahoo, Alpha Vantage, etc.)
        """
        self._conn = connection
        self._market_data = market_data_provider

    def get_current_price(self, ticker: str) -> float:
        """Fetch current price from external API.

        First checks cache, then fetches from API if needed.
        """
        # Try cache first
        cached_price = self.get_cached_price(ticker, max_age_minutes=15)
        if cached_price:
            return cached_price

        # Fetch from external provider
        price = self._market_data.get_current_price(ticker)
        if price:
            self.cache_price(ticker, price, datetime.now())

        return price

    def cache_price(self, ticker: str, price: float, timestamp: datetime) -> None:
        """Cache a price in the database."""
        self._conn.execute(
            """
            INSERT OR REPLACE INTO price_cache
            (ticker, current_price, last_updated)
            VALUES (?, ?, ?)
            """,
            [ticker.upper(), price, timestamp],
        )

    def get_cached_price(self, ticker: str, max_age_minutes: int = 15) -> float:
        """Get cached price if available and not stale.

        Args:
            ticker: Ticker symbol
            max_age_minutes: Maximum age in minutes for cached price

        Returns:
            Cached price or None if not available/stale
        """
        result = self._conn.execute(
            f"""
            SELECT current_price, last_updated
            FROM price_cache
            WHERE ticker = ?
            AND last_updated > current_timestamp - INTERVAL '{max_age_minutes}' MINUTE
            ORDER BY last_updated DESC
            LIMIT 1
            """,
            [ticker.upper()],
        ).fetchone()

        return result[0] if result else None

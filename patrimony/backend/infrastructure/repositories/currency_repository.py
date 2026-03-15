"""Repository implementation for currency data."""

from ...domain.repositories import CurrencyRepository
from ..database.connection import DatabaseConnection


class CurrencyRepositoryImpl(CurrencyRepository):
    """Concrete implementation of CurrencyRepository using DuckDB."""

    def __init__(self, connection: DatabaseConnection):
        self._conn = connection

    def get_ticker_currency(self, ticker: str) -> str | None:
        """Get cached currency for a ticker."""
        result = self._conn.execute(
            "SELECT currency FROM ticker_currency WHERE ticker = ?",
            [ticker.upper()],
        ).fetchone()
        return result[0] if result else None

    def set_ticker_currency(self, ticker: str, currency: str) -> None:
        """Cache a ticker's native currency."""
        self._conn.execute(
            """
            INSERT OR REPLACE INTO ticker_currency
            (ticker, currency, last_updated)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
            [ticker.upper(), currency.upper()],
        )

    def get_exchange_rate(
        self, from_currency: str, to_currency: str, max_age_minutes: int = 60
    ) -> float | None:
        """Get cached exchange rate if fresh enough."""
        result = self._conn.execute(
            f"""
            SELECT rate FROM exchange_rate_cache
            WHERE from_currency = ? AND to_currency = ?
            AND last_updated > CURRENT_TIMESTAMP - INTERVAL '{max_age_minutes}' MINUTE
            """,
            [from_currency.upper(), to_currency.upper()],
        ).fetchone()
        return result[0] if result else None

    def set_exchange_rate(
        self, from_currency: str, to_currency: str, rate: float
    ) -> None:
        """Cache an exchange rate."""
        self._conn.execute(
            """
            INSERT OR REPLACE INTO exchange_rate_cache
            (from_currency, to_currency, rate, last_updated)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
            [from_currency.upper(), to_currency.upper(), rate],
        )

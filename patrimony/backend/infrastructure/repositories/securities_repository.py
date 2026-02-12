"""Repository implementations for securities."""

from datetime import datetime
import polars as pl

from ...domain.repositories import SecuritiesRepository
from ...domain.entities import AssetType, Currency, EntryType, TransactionType
from ..database.connection import DatabaseConnection


class SecuritiesRepositoryImpl(SecuritiesRepository):
    """Concrete implementation of SecuritiesRepository using DuckDB."""

    def __init__(self, connection: DatabaseConnection):
        self._conn = connection

    def add_position(
        self,
        ticker: str,
        price: float,
        quantity: float,
        entry_type: EntryType,
        asset_type: AssetType,
        transaction_type: TransactionType,
        currency: Currency,
        date: datetime,
    ) -> int:
        """Add a new position to the database."""
        result = self._conn.execute(
            """
            INSERT INTO positions
            (ticker, price, quantity, entry_type, asset_type, transaction_type, currency, date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            [
                ticker.upper(),
                price,
                quantity,
                entry_type.value,
                asset_type.value,
                transaction_type.value,
                currency.value,
                date,
            ],
        )
        return result.fetchone()[0]

    def get_by_ticker(self, ticker: str) -> pl.DataFrame:
        """Get all positions for a specific ticker."""
        return self._conn.execute(
            "SELECT * FROM positions WHERE ticker = ?", [ticker.upper()]
        ).pl()

    def get_aggregated_positions(self) -> pl.DataFrame:
        """Get aggregated positions from the positions_total view."""
        return self._conn.execute("SELECT * FROM positions_total").pl()

    def get_by_id(self, id: int) -> pl.DataFrame:
        """Get position by ID."""
        return self._conn.execute("SELECT * FROM positions WHERE id = ?", [id]).pl()

    def delete(self, id: int) -> None:
        """Delete a position by ID."""
        self._conn.execute("DELETE FROM positions WHERE id = ?", [id])

    def get_all(self) -> pl.DataFrame:
        """Get all positions."""
        return self._conn.execute("SELECT * FROM positions").pl()

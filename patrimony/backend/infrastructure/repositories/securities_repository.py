"""Repository implementations for securities."""

from datetime import datetime
import polars as pl

from ...domain.repositories import SecuritiesRepository
from ...domain.entities import AssetType, EntryType
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
        date: datetime,
        fees: float = 0.0,
    ) -> int:
        """Add a new position to the database."""
        result = self._conn.execute(
            """
            INSERT INTO positions
            (ticker, price, quantity, fees, entry_type, asset_type, date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            [
                ticker.upper(),
                price,
                quantity,
                fees,
                entry_type.value,
                asset_type.value,
                date,
            ],
        )
        return result.fetchone()[0]

    def update_position(
        self,
        id: int,
        ticker: str,
        price: float,
        quantity: float,
        entry_type: EntryType,
        asset_type: AssetType,
        date: datetime,
        fees: float = 0.0,
    ) -> None:
        """Update an existing position by ID."""
        self._conn.execute(
            """
            UPDATE positions
            SET ticker = ?, price = ?, quantity = ?, fees = ?,
                entry_type = ?, asset_type = ?, date = ?
            WHERE id = ?
            """,
            [
                ticker.upper(),
                price,
                quantity,
                fees,
                entry_type.value,
                asset_type.value,
                date,
                id,
            ],
        )

    def get_by_ticker(self, ticker: str) -> pl.DataFrame:
        """Get all positions for a specific ticker."""
        return self._conn.execute(
            "SELECT * FROM positions WHERE ticker = ?", [ticker.upper()]
        ).pl()

    def get_aggregated_positions(self, ticker: str | None = None) -> pl.DataFrame:
        """Get aggregated positions from the positions_total view, optionally filtered by ticker."""
        if ticker:
            return self._conn.execute(
                "SELECT * FROM positions_total WHERE ticker = ?", [ticker.upper()]
            ).pl()
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

    def get_earliest_purchase_date(self, ticker: str | None = None) -> datetime | None:
        """Return the earliest purchase date, optionally filtered by ticker."""
        if ticker:
            row = self._conn.execute(
                "SELECT MIN(date) AS min_date FROM positions WHERE ticker = ?",
                [ticker.upper()],
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT MIN(date) AS min_date FROM positions"
            ).fetchone()
        return row[0] if row and row[0] else None

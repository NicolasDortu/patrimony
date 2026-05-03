"""Repository implementation for physical properties."""

from datetime import datetime

import polars as pl

from ...domain.constants import DEFAULT_CURRENCY
from ...domain.entities import EntryType
from ...domain.repositories import PropertyRepository
from ..database.connection import DatabaseConnection


class PropertyRepositoryImpl(PropertyRepository):
    """Concrete implementation of PropertyRepository using DuckDB."""

    def __init__(self, connection: DatabaseConnection):
        self._conn = connection

    def add_property(
        self,
        name: str,
        value: float,
        purchase_date: datetime,
        description: str = "",
        category: str = "Other",
        currency: str = DEFAULT_CURRENCY,
        entry_type: EntryType = EntryType.MANUAL,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO properties (name, description, value, purchase_date, category, currency, entry_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                name,
                description,
                value,
                purchase_date,
                category,
                currency,
                entry_type.value,
            ],
        )

    def update_property(
        self,
        id: int,
        name: str,
        value: float,
        purchase_date: datetime,
        description: str = "",
        category: str = "Other",
        currency: str = DEFAULT_CURRENCY,
    ) -> None:
        self._conn.execute(
            """
            UPDATE properties
            SET name = ?, description = ?, value = ?, purchase_date = ?, category = ?, currency = ?
            WHERE id = ?
            """,
            [name, description, value, purchase_date, category, currency, id],
        )

    def get_all(self) -> pl.DataFrame:
        return self._conn.execute(
            "SELECT * FROM properties ORDER BY purchase_date DESC"
        ).pl()

    def get_total_value_by_currency(self) -> pl.DataFrame:
        return self._conn.execute(
            "SELECT currency, SUM(value) AS total_value FROM properties GROUP BY currency"
        ).pl()

    def get_by_id(self, id: int) -> pl.DataFrame:
        return self._conn.execute("SELECT * FROM properties WHERE id = ?", [id]).pl()

    def delete(self, id: int) -> None:
        self._conn.execute("DELETE FROM properties WHERE id = ?", [id])

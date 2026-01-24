from datetime import datetime
import polars as pl

from ...database.connection import DatabaseConnection


class TradableAssetsOperations:
    """Database operations for TradableAssets."""

    def __init__(self, conn: DatabaseConnection) -> None:
        self.conn = conn

    def add_position(
        self,
        ticker: str,
        price: float,
        quantity: float,
        entry_type: str,
        asset_type: str,
        buy_sell: str,
        currency: str,
        date: datetime,
        table: str = "positions",
    ) -> None:
        self.conn.execute(
            f"INSERT INTO {table} (ticker, price, quantity, entry_type, asset_type, buy_sell, currency, date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ticker.upper(),
                price,
                quantity,
                entry_type,
                asset_type,
                buy_sell,
                currency,
                date,
            ],
        )

    def get_positions(self, table: str = "positions") -> pl.DataFrame:
        return self.conn.execute(f"SELECT * FROM {table}").pl()

    def delete_position(self, id: int, table: str = "positions") -> None:
        self.conn.execute(f"DELETE FROM {table} WHERE id = ?", [id])

import polars as pl

from ...database.connection import DatabaseConnection


class TradableAssetsOperations:
    """Database operations for TradableAssets."""

    def __init__(self, conn: DatabaseConnection) -> None:
        self.conn = conn

    def add_position(
        self,
        ticker: str,
        buy_price: float,
        quantity: float = 1.0,
        table: str = "positions",
    ) -> None:
        self.conn.execute(
            f"INSERT INTO {table} (ticker, buy_price, quantity) VALUES (?, ?, ?)",
            [ticker.upper(), buy_price, quantity],
        )

    def get_positions(self, table: str = "positions") -> pl.DataFrame:
        return self.conn.execute(f"SELECT * FROM {table}").pl()

    def delete_position(self, id: int, table: str = "positions") -> None:
        self.conn.execute(f"DELETE FROM {table} WHERE id = ?", [id])

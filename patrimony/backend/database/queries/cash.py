from datetime import datetime
import polars as pl

from ...database.connection import DatabaseConnection


class CashOperations:
    """Database operations for Cash."""

    def __init__(self, conn: DatabaseConnection) -> None:
        self.conn = conn

    def add_cash(
        self,
        bank: str,
        account_number: str,
        currency: str,
        balance: float,
        last_updated: datetime,
        table: str = "cash",
    ) -> None:
        self.conn.execute(
            f"INSERT INTO {table} (bank, account_number, currency, balance, last_updated) VALUES (?, ?, ?, ?, ?)",
            [
                bank,
                account_number,
                currency,
                balance,
                last_updated,
            ],
        )

    def get_cash(self, table: str = "cash") -> pl.DataFrame:
        return self.conn.execute(f"SELECT * FROM {table}").pl()

    def get_cash_by_bank(self, bank: str, table: str = "cash") -> pl.DataFrame:
        return self.conn.execute(f"SELECT * FROM {table} WHERE bank = ?", [bank]).pl()

    def update_cash(
        self,
        id: int,
        bank: str,
        account_number: str,
        currency: str,
        balance: float,
        last_updated: datetime,
        table: str = "cash",
    ) -> None:
        self.conn.execute(
            f"UPDATE {table} SET bank = ?, account_number = ?, currency = ?, balance = ?, last_updated = ? WHERE id = ?",
            [bank, account_number, currency, balance, last_updated, id],
        )

    def delete_cash(self, id: int, table: str = "cash") -> None:
        self.conn.execute(f"DELETE FROM {table} WHERE id = ?", [id])

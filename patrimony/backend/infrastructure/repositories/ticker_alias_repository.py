"""Repository for ticker alias mappings (ISIN → ticker, etc.)."""

import logging

from ...domain.repositories import TickerAliasRepository
from ..database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class TickerAliasRepositoryImpl(TickerAliasRepository):
    """DuckDB implementation of TickerAliasRepository."""

    def __init__(self, connection: DatabaseConnection):
        self._conn = connection

    def get(self, alias: str) -> str | None:
        result = self._conn.execute(
            "SELECT ticker FROM ticker_alias WHERE alias = ?",
            [alias.upper()],
        )
        df = result.pl()
        if df.is_empty():
            return None
        return str(df["ticker"][0])

    def get_batch(self, aliases: list[str]) -> dict[str, str]:
        if not aliases:
            return {}
        upper = [a.upper() for a in aliases]
        placeholders = ", ".join("?" for _ in upper)
        result = self._conn.execute(
            f"SELECT alias, ticker FROM ticker_alias WHERE alias IN ({placeholders})",
            upper,
        )
        df = result.pl()
        if df.is_empty():
            return {}
        return dict(zip(df["alias"].to_list(), df["ticker"].to_list()))

    def save(self, alias: str, ticker: str, alias_type: str = "ISIN") -> None:
        self._conn.execute(
            """
            INSERT INTO ticker_alias (alias, ticker, alias_type)
            VALUES (?, ?, ?)
            ON CONFLICT (alias) DO UPDATE SET ticker = ?, alias_type = ?
            """,
            [alias.upper(), ticker.upper(), alias_type, ticker.upper(), alias_type],
        )

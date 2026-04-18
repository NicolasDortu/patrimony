"""Repository for enriched ticker metadata (ticker_info table)."""

import logging
from datetime import datetime

from ...domain.entities import TickerInfo
from ...domain.repositories import TickerInfoRepository
from ..database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class TickerInfoRepositoryImpl(TickerInfoRepository):
    """DuckDB implementation of TickerInfoRepository."""

    def __init__(self, connection: DatabaseConnection):
        self._conn = connection

    def get_by_ticker(self, ticker: str) -> TickerInfo | None:
        result = self._conn.execute(
            "SELECT ticker, isin, name, asset_type, exchange, currency, source, last_updated "
            "FROM ticker_info WHERE ticker = ?",
            [ticker.upper()],
        )
        df = result.pl()
        if df.is_empty():
            return None
        row = df.row(0, named=True)
        return TickerInfo(**row)

    def get_by_isin(self, isin: str) -> TickerInfo | None:
        result = self._conn.execute(
            "SELECT ticker, isin, name, asset_type, exchange, currency, source, last_updated "
            "FROM ticker_info WHERE isin = ?",
            [isin.upper()],
        )
        df = result.pl()
        if df.is_empty():
            return None
        row = df.row(0, named=True)
        return TickerInfo(**row)

    def get_by_name(self, name: str) -> TickerInfo | None:
        result = self._conn.execute(
            "SELECT ticker, isin, name, asset_type, exchange, currency, source, last_updated "
            "FROM ticker_info WHERE LOWER(name) = LOWER(?)",
            [name.strip()],
        )
        df = result.pl()
        if df.is_empty():
            return None
        row = df.row(0, named=True)
        return TickerInfo(**row)

    def get_batch_by_isin(self, isins: list[str]) -> dict[str, TickerInfo]:
        if not isins:
            return {}
        upper = [i.upper() for i in isins]
        placeholders = ", ".join("?" for _ in upper)
        result = self._conn.execute(
            f"SELECT ticker, isin, name, asset_type, exchange, currency, source, last_updated "
            f"FROM ticker_info WHERE isin IN ({placeholders})",
            upper,
        )
        df = result.pl()
        if df.is_empty():
            return {}
        mapping: dict[str, TickerInfo] = {}
        for row in df.iter_rows(named=True):
            info = TickerInfo(**row)
            if info.isin:
                mapping[info.isin.upper()] = info
        return mapping

    def upsert(self, info: TickerInfo) -> None:
        self._conn.execute(
            """
            INSERT INTO ticker_info (ticker, isin, name, asset_type, exchange, currency, source, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (ticker) DO UPDATE SET
                isin = COALESCE(excluded.isin, ticker_info.isin),
                name = COALESCE(excluded.name, ticker_info.name),
                asset_type = COALESCE(excluded.asset_type, ticker_info.asset_type),
                exchange = COALESCE(excluded.exchange, ticker_info.exchange),
                currency = COALESCE(excluded.currency, ticker_info.currency),
                source = excluded.source,
                last_updated = excluded.last_updated
            """,
            [
                info.ticker.upper(),
                info.isin.upper() if info.isin else None,
                info.name,
                info.asset_type,
                info.exchange,
                info.currency,
                info.source,
                info.last_updated or datetime.now().isoformat(),
            ],
        )

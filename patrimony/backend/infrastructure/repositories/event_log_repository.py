"""Repository implementation for persistent event log."""

import polars as pl

from ...domain.repositories import EventLogRepository
from ..database.connection import DatabaseConnection


class EventLogRepositoryImpl(EventLogRepository):
    """Stores and retrieves notification events in DuckDB."""

    def __init__(self, connection: DatabaseConnection):
        self._conn = connection

    def add(self, level: str, summary: str, detail: str = "") -> int:
        result = self._conn.execute(
            """
            INSERT INTO event_log (level, summary, detail)
            VALUES (?, ?, ?)
            RETURNING id
            """,
            [level, summary, detail],
        )
        return result.fetchone()[0]

    def add_batch(self, events: list[dict]) -> None:
        if not events:
            return
        with self._conn.transaction():
            for e in events:
                self._conn.execute(
                    "INSERT INTO event_log (level, summary, detail) VALUES (?, ?, ?)",
                    [e["level"], e["summary"], e.get("detail", "")],
                )

    def get_recent(self, limit: int = 100) -> pl.DataFrame:
        return self._conn.execute(
            "SELECT * FROM event_log ORDER BY created_at DESC LIMIT ?",
            [limit],
        ).pl()

    def clear(self) -> None:
        self._conn.execute("DELETE FROM event_log")

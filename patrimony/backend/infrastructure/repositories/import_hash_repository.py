"""Repository for tracking imported row hashes (deduplication)."""

import duckdb

from ...domain.repositories import ImportHashRepository
from ..database.connection import DatabaseConnection


class ImportHashRepositoryImpl(ImportHashRepository):
    """DuckDB implementation of import hash tracking."""

    def __init__(self, connection: DatabaseConnection):
        self._conn = connection

    def existing_hashes(self, hashes: set[str]) -> set[str]:
        """Return the subset of hashes that already exist."""
        if not hashes:
            return set()
        placeholders = ", ".join("?" for _ in hashes)
        rows = self._conn.execute(
            f"SELECT hash FROM import_hashes WHERE hash IN ({placeholders})",
            list(hashes),
        ).fetchall()
        return {row[0] for row in rows}

    def add_hashes(self, hashes: list[str], import_type: str) -> None:
        """Persist new hashes (ignores duplicates)."""
        if not hashes:
            return
        for h in hashes:
            try:
                self._conn.execute(
                    "INSERT INTO import_hashes (hash, import_type) VALUES (?, ?)",
                    [h, import_type],
                )
            except duckdb.ConstraintException:
                pass  # hash already exists — safe to ignore

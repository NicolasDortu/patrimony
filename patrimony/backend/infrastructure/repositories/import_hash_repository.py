"""Repository for tracking imported row hashes (deduplication)."""

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
        """Persist new hashes, skipping any that already exist."""
        if not hashes:
            return
        existing = self.existing_hashes(set(hashes))
        new_hashes = [(h, import_type) for h in hashes if h not in existing]
        if not new_hashes:
            return
        self._conn.executemany(
            "INSERT INTO import_hashes (hash, import_type) VALUES (?, ?)",
            new_hashes,
        )

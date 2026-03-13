"""Repository for securities reference data."""

from ...domain.repositories import ReferenceRepository
from ..database.connection import DatabaseConnection


class ReferenceRepositoryImpl(ReferenceRepository):
    """Repository for querying the securities reference table."""

    def __init__(self, connection: DatabaseConnection):
        self._conn = connection

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search securities by ticker or name (case-insensitive).

        Prioritizes exact ticker matches, then prefix matches, then substring matches.
        """
        search_param = f"%{query.lower()}%"
        prefix_param = f"{query.lower()}%"
        result = self._conn.execute(
            """
            SELECT ticker, name, asset_type, exchange, category, country
            FROM securities_reference
            WHERE LOWER(ticker) LIKE ? OR LOWER(name) LIKE ?
            ORDER BY
                CASE
                    WHEN LOWER(ticker) = ? THEN 0
                    WHEN LOWER(ticker) LIKE ? THEN 1
                    ELSE 2
                END,
                ticker
            LIMIT ?
            """,
            [search_param, search_param, query.lower(), prefix_param, limit],
        )
        df = result.pl()
        return df.to_dicts() if not df.is_empty() else []

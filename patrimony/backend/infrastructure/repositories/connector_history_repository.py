"""DuckDB implementation of the connector history repository."""

import json
from datetime import datetime

from ...domain.entities import ConnectorHistoryEntry
from ...domain.repositories import ConnectorHistoryRepository
from ..database.connection import DatabaseConnection


class ConnectorHistoryRepositoryImpl(ConnectorHistoryRepository):
    """DuckDB-backed connector history repository."""

    def __init__(self, connection: DatabaseConnection) -> None:
        self._conn = connection

    def add_entry(self, entry: ConnectorHistoryEntry) -> int:
        result = self._conn.execute(
            """
            INSERT INTO connector_history (
                connector_type, profile_id, source_name, source_path,
                import_mode, column_mapping, delimiter,
                asset_type_overrides,
                new_accounts,
                imported, skipped, errors, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            [
                entry.connector_type,
                entry.profile_id,
                entry.source_name,
                entry.source_path,
                entry.import_mode,
                json.dumps(entry.column_mapping) if entry.column_mapping else None,
                entry.delimiter,
                json.dumps(entry.asset_type_overrides)
                if entry.asset_type_overrides
                else None,
                json.dumps(entry.new_cash_accounts)
                if entry.new_cash_accounts
                else None,
                entry.imported,
                entry.skipped,
                json.dumps(entry.errors) if entry.errors else "[]",
                entry.status,
            ],
        ).fetchone()
        return result[0]

    def get_all(self) -> list[ConnectorHistoryEntry]:
        rows = self._conn.execute(
            """
            SELECT id, connector_type, profile_id, source_name, source_path,
                   import_mode, column_mapping, delimiter,
                   asset_type_overrides,
                   new_accounts,
                   imported, skipped, errors, status, created_at
            FROM connector_history
            WHERE id IN (
                SELECT id FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY connector_type,
                                            COALESCE(profile_id, ''),
                                            source_name,
                                            import_mode
                               ORDER BY created_at DESC
                           ) AS rn
                    FROM connector_history
                )
                WHERE rn = 1
            )
            ORDER BY created_at DESC
            """
        ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def delete(self, entry_id: int) -> None:
        self._conn.execute("DELETE FROM connector_history WHERE id = ?", [entry_id])

    @staticmethod
    def _row_to_entry(row: tuple) -> ConnectorHistoryEntry:
        return ConnectorHistoryEntry(
            id=row[0],
            connector_type=row[1],
            profile_id=row[2],
            source_name=row[3],
            source_path=row[4],
            import_mode=row[5],
            column_mapping=json.loads(row[6]) if row[6] else {},
            delimiter=row[7] or ",",
            asset_type_overrides=json.loads(row[8]) if row[8] else {},
            new_cash_accounts=json.loads(row[9]) if row[9] else None,
            imported=row[10] or 0,
            skipped=row[11] or 0,
            errors=json.loads(row[12]) if row[12] else [],
            status=row[13],
            created_at=row[14] if isinstance(row[14], datetime) else None,
        )

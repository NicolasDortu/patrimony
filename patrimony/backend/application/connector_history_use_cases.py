"""Use cases for connector import history management."""

from ..domain.entities import ConnectorHistoryEntry
from ..domain.repositories import ConnectorHistoryRepository


class ConnectorHistoryUseCases:
    """Application use cases for connector history operations."""

    def __init__(self, history_repo: ConnectorHistoryRepository):
        self._history_repo = history_repo

    def record_history(
        self,
        connector_type: str,
        source_name: str,
        import_mode: str,
        imported: int,
        skipped: int,
        errors: list[str],
        success: bool,
        profile_id: str | None = None,
        source_path: str | None = None,
        column_mapping: dict | None = None,
        delimiter: str = ",",
        asset_type_overrides: dict | None = None,
        new_accounts: dict | None = None,
    ) -> int | None:
        """Record a connector history entry."""
        status = (
            "success"
            if success and not errors
            else ("partial" if success else "failed")
        )
        entry = ConnectorHistoryEntry(
            connector_type=connector_type,
            profile_id=profile_id,
            source_name=source_name,
            source_path=source_path,
            import_mode=import_mode,
            column_mapping=column_mapping or {},
            delimiter=delimiter,
            asset_type_overrides=asset_type_overrides or {},
            new_cash_accounts=new_accounts,
            imported=imported,
            skipped=skipped,
            errors=errors,
            status=status,
        )
        return self._history_repo.add_entry(entry)

    def get_all_history(self) -> list[dict]:
        """Get all history entries as dicts."""
        entries = self._history_repo.get_all()
        return [
            {
                "id": e.id,
                "connector_type": e.connector_type,
                "profile_id": e.profile_id or "",
                "source_name": e.source_name,
                "source_path": e.source_path or "",
                "import_mode": e.import_mode,
                "column_mapping": e.column_mapping,
                "delimiter": e.delimiter,
                "asset_type_overrides": e.asset_type_overrides,
                "new_accounts": e.new_cash_accounts,
                "imported": e.imported,
                "skipped": e.skipped,
                "errors": e.errors,
                "status": e.status,
                "created_at": e.created_at.isoformat() if e.created_at else "",
            }
            for e in entries
        ]

    def delete_history(self, entry_id: int) -> None:
        self._history_repo.delete(entry_id)

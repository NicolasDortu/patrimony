"""Use cases for connector operations (file import, web import)."""

import logging
from pathlib import Path

from ..domain.entities import ConnectorHistoryEntry, EntryType
from ..domain.interfaces import FileConnector
from ..domain.repositories import ConnectorHistoryRepository
from ..domain.services.connectors import (
    FileConnectorService as FileConnectorDomainService,
)
from ..domain.services.connectors import (
    WebConnectorService as WebConnectorDomainService,
)

logger = logging.getLogger(__name__)


def build_import_message(
    imported: int, skipped: int, errors: list[str], label: str = "entries"
) -> tuple[bool, str]:
    """Build a standardized (success, message) tuple for import results.

    Returns (True, "Imported X ...") on success, (False, "Import failed: ...") on failure.
    """
    success = imported > 0 or (imported == 0 and skipped == 0 and not errors)
    if success:
        msg = f"Imported {imported} {label}"
        if skipped:
            msg += f" ({skipped} duplicates skipped)"
        return True, msg
    if errors:
        return False, f"Import failed: {'; '.join(errors)}"
    if skipped and imported == 0:
        return False, f"All {skipped} rows were duplicates"
    return False, "No rows could be imported"


class FileImportResult:
    """Result of a file import operation."""

    __slots__ = ("success", "message", "errors", "imported", "skipped", "history_id")

    def __init__(
        self,
        success: bool,
        message: str,
        errors: list[str] | None = None,
        imported: int = 0,
        skipped: int = 0,
        history_id: int | None = None,
    ):
        self.success = success
        self.message = message
        self.errors = errors or []
        self.imported = imported
        self.skipped = skipped
        self.history_id = history_id


class ConnectorUseCases:
    """Application use cases for file and web connector operations."""

    def __init__(
        self,
        file_connector: FileConnector,
        connector_service: FileConnectorDomainService,
        web_connector_service: WebConnectorDomainService,
        history_repo: ConnectorHistoryRepository,
    ):
        self._file_connector = file_connector
        self._connector_service = connector_service
        self._web_connector_service = web_connector_service
        self._history_repo = history_repo

    def read_file(
        self, file_bytes: bytes, filename: str, delimiter: str = ","
    ) -> tuple[list[str], list[dict]]:
        """Read an uploaded file and return (columns, preview_rows)."""
        df = self._file_connector.read_file(file_bytes, filename, delimiter)
        columns = df.columns
        preview = df.head(5).to_dicts()
        return columns, preview

    def read_file_full(
        self, file_bytes: bytes, filename: str, delimiter: str = ","
    ) -> list[dict]:
        """Read an uploaded file and return all rows."""
        df = self._file_connector.read_file(file_bytes, filename, delimiter)
        return df.to_dicts()

    def resolve_asset_types(self, tickers: list[str]) -> dict[str, str | None]:
        return self._connector_service.resolve_asset_types(tickers)

    def import_positions(
        self,
        file_bytes: bytes,
        filename: str,
        column_mapping: dict[str, str],
        delimiter: str = ",",
        asset_type_overrides: dict[str, str] | None = None,
    ) -> FileImportResult:
        """Import positions from an uploaded file."""
        lower = filename.lower()
        entry_type = (
            EntryType.EXCEL if lower.endswith((".xlsx", ".xls")) else EntryType.CSV
        )

        df = self._file_connector.read_file(file_bytes, filename, delimiter)
        result = self._connector_service.import_positions(
            df, column_mapping, entry_type, asset_type_overrides
        )

        success, msg = build_import_message(
            result.imported, result.skipped, result.errors, "positions"
        )
        return FileImportResult(
            success=success,
            message=msg,
            errors=result.errors,
            imported=result.imported,
            skipped=result.skipped,
        )

    def detect_unknown_cash_accounts(
        self,
        file_bytes: bytes,
        filename: str,
        column_mapping: dict[str, str],
        delimiter: str = ",",
    ) -> list[str]:
        """Return account numbers from the file that don't exist in the cash table."""
        df = self._file_connector.read_file(file_bytes, filename, delimiter)
        return self._connector_service.detect_unknown_cash_accounts(df, column_mapping)

    def import_cash_operations(
        self,
        file_bytes: bytes,
        filename: str,
        column_mapping: dict[str, str],
        delimiter: str = ",",
        new_accounts: dict[str, dict] | None = None,
    ) -> FileImportResult:
        """Import cash operations from an uploaded file."""
        lower = filename.lower()
        entry_type = (
            EntryType.EXCEL if lower.endswith((".xlsx", ".xls")) else EntryType.CSV
        )

        df = self._file_connector.read_file(file_bytes, filename, delimiter)
        result = self._connector_service.import_cash_operations(
            df, column_mapping, entry_type, new_accounts
        )

        success, msg = build_import_message(
            result.imported, result.skipped, result.errors, "cash operations"
        )
        return FileImportResult(
            success=success,
            message=msg,
            errors=result.errors,
            imported=result.imported,
            skipped=result.skipped,
        )

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
            new_accounts=new_accounts,
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
                "new_accounts": e.new_accounts,
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

    def reimport_from_history(
        self, entry: dict, source_path: str | None = None
    ) -> FileImportResult:
        """Re-import a file connector entry using a file path."""
        if not source_path:
            source_path = entry.get("source_path", "")
        if not source_path:
            return FileImportResult(success=False, message="No source path in history.")

        path = Path(source_path)
        if not path.is_file():
            return FileImportResult(
                success=False,
                message=f"File no longer found at: {path}. "
                "It may have been moved or deleted.",
            )

        file_bytes = path.read_bytes()
        filename = path.name
        column_mapping = entry.get("column_mapping", {})
        delimiter = entry.get("delimiter", ",")
        import_mode = entry.get("import_mode", "positions")

        if import_mode == "cash":
            new_accounts = entry.get("new_accounts")
            return self.import_cash_operations(
                file_bytes=file_bytes,
                filename=filename,
                column_mapping=column_mapping,
                delimiter=delimiter,
                new_accounts=new_accounts,
            )
        else:
            asset_type_overrides = entry.get("asset_type_overrides")
            return self.import_positions(
                file_bytes=file_bytes,
                filename=filename,
                column_mapping=column_mapping,
                delimiter=delimiter,
                asset_type_overrides=asset_type_overrides,
            )

    def list_web_profiles(self) -> list[dict]:
        """Return all available web connector profiles as dicts."""
        profiles = self._web_connector_service.list_profiles()
        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "import_mode": p.import_mode,
                "needs_matching": p.needs_matching,
                "credential_fields": [
                    {
                        "placeholder": f[0],
                        "label": f[1],
                        "type": (
                            "select"
                            if len(f) > 2
                            else "password"
                            if "password" in f[1].lower()
                            else "text"
                        ),
                        "options": list(f[2]) if len(f) > 2 else [],
                    }
                    for f in p.credential_fields
                ]
                if p.credential_fields
                else [],
            }
            for p in profiles
        ]

    def run_web_connector(
        self,
        profile_id: str,
        credentials: dict[str, str],
        on_user_input=None,
        headless: bool = False,
    ) -> dict:
        """Execute a web connector profile. Returns result dict with import data."""
        result = self._web_connector_service.run_connector(
            profile_id,
            credentials,
            on_user_input=on_user_input,
            headless=headless,
        )
        return {
            "success": result.success,
            "imported": result.imported,
            "skipped": result.skipped,
            "errors": result.errors,
            "status_log": result.status_log,
            "needs_matching": result.needs_matching,
            "unmatched_positions": result.unmatched_positions,
        }

    def get_web_profile(self, profile_id: str):
        return self._web_connector_service.get_profile(profile_id)

    def import_matched_positions(self, matched: list[dict]) -> dict:
        """Import user-matched positions from a web connector."""
        result = self._web_connector_service.import_matched_positions(matched)
        return {
            "success": result.success,
            "imported": result.imported,
            "skipped": result.skipped,
            "errors": result.errors,
        }

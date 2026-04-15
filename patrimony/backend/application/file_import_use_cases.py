"""Use cases for file-based connector operations (CSV/Excel import)."""

import logging
from pathlib import Path

from ..domain.entities import EntryType
from ..domain.interfaces import FileConnector
from ..domain.services.connectors import (
    FileConnectorService as FileConnectorDomainService,
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


class FileImportUseCases:
    """Application use cases for file-based connector operations."""

    def __init__(
        self,
        file_connector: FileConnector,
        connector_service: FileConnectorDomainService,
    ):
        self._file_connector = file_connector
        self._connector_service = connector_service

    def read_file(
        self,
        file_bytes: bytes,
        filename: str,
        delimiter: str = ",",
        *,
        preview_only: bool = True,
    ) -> tuple[list[str], list[dict]] | list[dict]:
        """Read an uploaded file.

        Args:
            preview_only: If True, return (columns, first-5-rows). If False, return all rows.
        """
        df = self._file_connector.read_file(file_bytes, filename, delimiter)
        if preview_only:
            return df.columns, df.head(5).to_dicts()
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

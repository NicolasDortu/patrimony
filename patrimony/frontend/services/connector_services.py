"""Frontend services for connector operations (file import, web import, credentials, history)."""

from collections.abc import Callable
import logging
from pathlib import Path

from ...backend.domain.entities import ConnectorHistoryEntry, EntryType
from ...backend.presentation.di_container import container
from ..config.file_connector_config import file_connector_paths
from .models import OperationResult

logger = logging.getLogger(__name__)


class FileConnectorService:
    """Frontend service for CSV/Excel file import."""

    @staticmethod
    def read_file(
        file_bytes: bytes, filename: str, delimiter: str = ","
    ) -> tuple[list[str], list[dict]]:
        """Read an uploaded file and return (columns, preview_rows).

        Returns:
            Tuple of (column names, first 5 rows as dicts).
        """
        df = container.file_connector().read_file(file_bytes, filename, delimiter)
        columns = df.columns
        preview = df.head(5).to_dicts()
        return columns, preview

    @staticmethod
    def read_file_full(
        file_bytes: bytes, filename: str, delimiter: str = ","
    ) -> list[dict]:
        """Read an uploaded file and return all rows."""
        df = container.file_connector().read_file(file_bytes, filename, delimiter)
        return df.to_dicts()

    @staticmethod
    def resolve_asset_types(tickers: list[str]) -> dict[str, str | None]:
        """Resolve asset types for a list of tickers from the reference table."""
        return container.connector_service().resolve_asset_types(tickers)

    @staticmethod
    def import_positions(
        file_bytes: bytes,
        filename: str,
        column_mapping: dict[str, str],
        delimiter: str = ",",
        asset_type_overrides: dict[str, str] | None = None,
        source_path: str | None = None,
    ) -> OperationResult:
        """Import positions from an uploaded file."""
        try:
            lower = filename.lower()
            entry_type = (
                EntryType.EXCEL if lower.endswith((".xlsx", ".xls")) else EntryType.CSV
            )

            svc = container.connector_service()
            df = container.file_connector().read_file(file_bytes, filename, delimiter)
            result = svc.import_positions(
                df,
                column_mapping,
                entry_type,
                asset_type_overrides,
            )

            if result.success:
                msg = f"Imported {result.imported} positions"
                if result.skipped:
                    msg += f" ({result.skipped} duplicates skipped)"
                op_result = OperationResult(
                    success=True, message=msg, data={"errors": result.errors}
                )
            else:
                if result.errors:
                    detail = "; ".join(result.errors)
                elif result.skipped and result.imported == 0:
                    detail = f"All {result.skipped} rows were duplicates"
                else:
                    detail = "No rows could be imported"
                op_result = OperationResult(
                    success=False,
                    message=f"Import failed: {detail}",
                )

            # Record history
            history_id = ConnectorHistoryService.record(
                connector_type="file",
                source_name=filename,
                source_path=source_path or filename,
                import_mode="positions",
                column_mapping=column_mapping,
                delimiter=delimiter,
                asset_type_overrides=asset_type_overrides,
                imported=result.imported,
                skipped=result.skipped,
                errors=result.errors,
                success=result.success,
            )

            # Persist source path in local JSON config
            if history_id and source_path:
                file_connector_paths.set(history_id, source_path)

            if op_result.success:
                logger.info("File import: %s", op_result.message)
            else:
                logger.error("File import failed: %s", op_result.message)

            return op_result
        except Exception as e:
            logger.error("File import exception: %s", e)
            return OperationResult(success=False, message=f"Import failed: {e}")

    @staticmethod
    def detect_unknown_cash_accounts(
        file_bytes: bytes,
        filename: str,
        column_mapping: dict[str, str],
        delimiter: str = ",",
    ) -> list[str]:
        """Return account numbers from the file that don't exist in the cash table."""
        svc = container.connector_service()
        df = container.file_connector().read_file(file_bytes, filename, delimiter)
        return svc.detect_unknown_cash_accounts(df, column_mapping)

    @staticmethod
    def import_cash_operations(
        file_bytes: bytes,
        filename: str,
        column_mapping: dict[str, str],
        delimiter: str = ",",
        new_accounts: dict[str, dict] | None = None,
        source_path: str | None = None,
    ) -> OperationResult:
        """Import cash operations from an uploaded file."""
        try:
            lower = filename.lower()
            entry_type = (
                EntryType.EXCEL if lower.endswith((".xlsx", ".xls")) else EntryType.CSV
            )

            svc = container.connector_service()
            df = container.file_connector().read_file(file_bytes, filename, delimiter)
            result = svc.import_cash_operations(
                df, column_mapping, entry_type, new_accounts
            )

            if result.success:
                msg = f"Imported {result.imported} cash operations"
                if result.skipped:
                    msg += f" ({result.skipped} duplicates skipped)"
                op_result = OperationResult(
                    success=True, message=msg, data={"errors": result.errors}
                )
            else:
                if result.errors:
                    detail = "; ".join(result.errors)
                elif result.skipped and result.imported == 0:
                    detail = f"All {result.skipped} rows were duplicates"
                else:
                    detail = "No rows could be imported"
                op_result = OperationResult(
                    success=False,
                    message=f"Import failed: {detail}",
                )

            # Record history
            history_id = ConnectorHistoryService.record(
                connector_type="file",
                source_name=filename,
                source_path=source_path or filename,
                import_mode="cash",
                column_mapping=column_mapping,
                delimiter=delimiter,
                new_accounts=new_accounts,
                imported=result.imported,
                skipped=result.skipped,
                errors=result.errors,
                success=result.success,
            )

            # Persist source path in local JSON config
            if history_id and source_path:
                file_connector_paths.set(history_id, source_path)

            if op_result.success:
                logger.info("Cash import: %s", op_result.message)
            else:
                logger.error("Cash import failed: %s", op_result.message)

            return op_result
        except Exception as e:
            logger.error("Cash import exception: %s", e)
            return OperationResult(success=False, message=f"Import failed: {e}")

    @staticmethod
    def reimport_from_history(entry: dict) -> OperationResult:
        """Re-import a file connector entry using the stored file path."""
        entry_id = entry.get("id")
        # Prefer path from local JSON config (editable by user)
        source_path = file_connector_paths.get(entry_id) if entry_id else ""
        if not source_path:
            source_path = entry.get("source_path", "")
        if not source_path:
            return OperationResult(success=False, message="No source path in history.")

        path = Path(source_path)
        if not path.is_file():
            return OperationResult(
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
            return FileConnectorService.import_cash_operations(
                file_bytes=file_bytes,
                filename=filename,
                column_mapping=column_mapping,
                delimiter=delimiter,
                new_accounts=new_accounts,
                source_path=source_path,
            )
        else:
            asset_type_overrides = entry.get("asset_type_overrides")
            return FileConnectorService.import_positions(
                file_bytes=file_bytes,
                filename=filename,
                column_mapping=column_mapping,
                delimiter=delimiter,
                asset_type_overrides=asset_type_overrides,
                source_path=source_path,
            )


class WebConnectorService:
    """Frontend service for browser-based automated data import."""

    @staticmethod
    def list_profiles() -> list[dict]:
        """Return all available connector profiles as dicts for the UI."""
        profiles = container.web_connector_service().list_profiles()
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

    @staticmethod
    def run_connector(
        profile_id: str,
        credentials: dict[str, str],
        on_user_input: Callable[[str, str], str] | None = None,
        headless: bool = False,
    ) -> OperationResult:
        """Execute a web connector profile and import the data."""
        try:
            svc = container.web_connector_service()
            result = svc.run_connector(
                profile_id,
                credentials,
                on_user_input=on_user_input,
                headless=headless,
            )

            data = {
                "imported": result.imported,
                "skipped": result.skipped,
                "errors": result.errors,
                "status_log": result.status_log,
                "needs_matching": result.needs_matching,
                "unmatched_positions": result.unmatched_positions,
            }

            if result.needs_matching:
                return OperationResult(
                    success=True,
                    message="Positions fetched — matching required.",
                    data=data,
                )

            if result.success:
                msg = f"Imported {result.imported} entries"
                if result.skipped:
                    msg += f" ({result.skipped} duplicates skipped)"
                op_result = OperationResult(success=True, message=msg, data=data)
            else:
                if result.errors:
                    detail = "; ".join(result.errors)
                elif result.skipped and result.imported == 0:
                    detail = f"All {result.skipped} rows were duplicates"
                else:
                    detail = "No rows could be imported"
                op_result = OperationResult(
                    success=False,
                    message=f"Import failed: {detail}",
                    data=data,
                )

            # Record history
            profile = svc.get_profile(profile_id)
            ConnectorHistoryService.record(
                connector_type="web",
                profile_id=profile_id,
                source_name=profile.name if profile else profile_id,
                import_mode=profile.import_mode if profile else "positions",
                imported=result.imported,
                skipped=result.skipped,
                errors=result.errors,
                success=result.success,
            )

            return op_result
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Connector failed: {e}",
                data={"errors": [str(e)], "status_log": []},
            )

    @staticmethod
    def import_matched_positions(
        matched: list[dict],
    ) -> OperationResult:
        """Import user-matched positions (name→ticker) from a web connector."""
        try:
            svc = container.web_connector_service()
            result = svc.import_matched_positions(matched)

            data = {
                "imported": result.imported,
                "skipped": result.skipped,
                "errors": result.errors,
            }

            if result.success:
                msg = f"Imported {result.imported} entries"
                if result.skipped:
                    msg += f" ({result.skipped} duplicates skipped)"
                return OperationResult(success=True, message=msg, data=data)
            else:
                detail = (
                    "; ".join(result.errors)
                    if result.errors
                    else "No rows could be imported"
                )
                return OperationResult(
                    success=False,
                    message=f"Import failed: {detail}",
                    data=data,
                )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Import failed: {e}",
            )


# Session-level Fernet key — held in memory, lost on app restart
_session_fernet_key: bytes | None = None


class CredentialService:
    """Frontend service for encrypted credential management."""

    @staticmethod
    def has_master_password() -> bool:
        return container.credential_repository().has_master_password()

    @staticmethod
    def is_unlocked() -> bool:
        return _session_fernet_key is not None

    @staticmethod
    def setup_master_password(password: str) -> bool:
        global _session_fernet_key
        try:
            _session_fernet_key = (
                container.credential_repository().setup_master_password(password)
            )
            return True
        except Exception as e:
            logger.error("Failed to setup master password: %s", e)
            return False

    @staticmethod
    def unlock(password: str) -> bool:
        global _session_fernet_key
        key = container.credential_repository().verify_master_password(password)
        if key:
            _session_fernet_key = key
            return True
        return False

    @staticmethod
    def lock() -> None:
        global _session_fernet_key
        _session_fernet_key = None

    @staticmethod
    def reset_master_password() -> bool:
        """Delete the master password and all stored credentials."""
        global _session_fernet_key
        try:
            container.credential_repository().reset_master_password()
            _session_fernet_key = None
            return True
        except Exception as e:
            logger.error("Failed to reset master password: %s", e)
            return False

    @staticmethod
    def store_credentials(profile_id: str, credentials: dict[str, str]) -> bool:
        if not _session_fernet_key:
            return False
        try:
            container.credential_repository().store_credentials(
                profile_id, credentials, _session_fernet_key
            )
            return True
        except Exception as e:
            logger.error("Failed to store credentials: %s", e)
            return False

    @staticmethod
    def get_credentials(profile_id: str) -> dict[str, str] | None:
        if not _session_fernet_key:
            return None
        return container.credential_repository().get_credentials(
            profile_id, _session_fernet_key
        )

    @staticmethod
    def delete_credentials(profile_id: str) -> bool:
        try:
            container.credential_repository().delete_credentials(profile_id)
            return True
        except Exception as e:
            logger.error("Failed to delete credentials: %s", e)
            return False

    @staticmethod
    def list_stored_profiles() -> list[str]:
        return container.credential_repository().list_stored_profiles()


class ConnectorHistoryService:
    """Frontend service for connector import history."""

    @staticmethod
    def record(
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
        try:
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
            return container.connector_history_repository().add_entry(entry)
        except Exception as e:
            logger.error("Failed to record connector history: %s", e)
            return None

    @staticmethod
    def get_all() -> list[dict]:
        """Get all history entries as dicts for the UI."""
        try:
            entries = container.connector_history_repository().get_all()
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
        except Exception as e:
            logger.error("Failed to get connector history: %s", e)
            return []

    @staticmethod
    def delete(entry_id: int) -> bool:
        """Delete a history entry."""
        try:
            container.connector_history_repository().delete(entry_id)
            return True
        except Exception as e:
            logger.error("Failed to delete history entry: %s", e)
            return False

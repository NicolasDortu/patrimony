"""Frontend services for connector operations (file import, web import, credentials, history)."""

from collections.abc import Callable
import logging

from ...backend.application.di_container import container
from ...backend.application.connector_use_cases import build_import_message
from ..config.file_connector_config import file_connector_paths
from .models import OperationResult, operation_result

logger = logging.getLogger(__name__)


class FileConnectorService:
    """Frontend service for CSV/Excel file import."""

    @staticmethod
    def read_file(
        file_bytes: bytes, filename: str, delimiter: str = ","
    ) -> tuple[list[str], list[dict]]:
        """Read an uploaded file and return (columns, preview_rows)."""
        return container.connector_use_cases().read_file(
            file_bytes, filename, delimiter
        )

    @staticmethod
    def read_file_full(
        file_bytes: bytes, filename: str, delimiter: str = ","
    ) -> list[dict]:
        """Read an uploaded file and return all rows."""
        return container.connector_use_cases().read_file_full(
            file_bytes, filename, delimiter
        )

    @staticmethod
    def resolve_asset_types(tickers: list[str]) -> dict[str, str | None]:
        """Resolve asset types for a list of tickers from the reference table."""
        return container.connector_use_cases().resolve_asset_types(tickers)

    @staticmethod
    @operation_result(failure="Import failed")
    def import_positions(
        file_bytes: bytes,
        filename: str,
        column_mapping: dict[str, str],
        delimiter: str = ",",
        asset_type_overrides: dict[str, str] | None = None,
        source_path: str | None = None,
    ) -> OperationResult:
        """Import positions from an uploaded file."""
        uc = container.connector_use_cases()
        result = uc.import_positions(
            file_bytes=file_bytes,
            filename=filename,
            column_mapping=column_mapping,
            delimiter=delimiter,
            asset_type_overrides=asset_type_overrides,
        )

        op_result = OperationResult(
            success=result.success,
            message=result.message,
            data={"errors": result.errors},
        )

        # Record history
        history_id = uc.record_history(
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

        if history_id and source_path:
            file_connector_paths.set(history_id, source_path)

        if op_result.success:
            logger.info("File import: %s", op_result.message)
        else:
            logger.error("File import failed: %s", op_result.message)

        return op_result

    @staticmethod
    def detect_unknown_cash_accounts(
        file_bytes: bytes,
        filename: str,
        column_mapping: dict[str, str],
        delimiter: str = ",",
    ) -> list[str]:
        """Return account numbers from the file that don't exist in the cash table."""
        return container.connector_use_cases().detect_unknown_cash_accounts(
            file_bytes, filename, column_mapping, delimiter
        )

    @staticmethod
    @operation_result(failure="Import failed")
    def import_cash_operations(
        file_bytes: bytes,
        filename: str,
        column_mapping: dict[str, str],
        delimiter: str = ",",
        new_accounts: dict[str, dict] | None = None,
        source_path: str | None = None,
    ) -> OperationResult:
        """Import cash operations from an uploaded file."""
        uc = container.connector_use_cases()
        result = uc.import_cash_operations(
            file_bytes=file_bytes,
            filename=filename,
            column_mapping=column_mapping,
            delimiter=delimiter,
            new_accounts=new_accounts,
        )

        op_result = OperationResult(
            success=result.success,
            message=result.message,
            data={"errors": result.errors},
        )

        # Record history
        history_id = uc.record_history(
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

        if history_id and source_path:
            file_connector_paths.set(history_id, source_path)

        if op_result.success:
            logger.info("Cash import: %s", op_result.message)
        else:
            logger.error("Cash import failed: %s", op_result.message)

        return op_result

    @staticmethod
    @operation_result(failure="Re-import failed")
    def reimport_from_history(entry: dict) -> OperationResult:
        """Re-import a file connector entry using the stored file path."""
        entry_id = entry.get("id")
        source_path = file_connector_paths.get(entry_id) if entry_id else ""
        if not source_path:
            source_path = entry.get("source_path", "")

        uc = container.connector_use_cases()
        result = uc.reimport_from_history(entry, source_path=source_path)

        op_result = OperationResult(
            success=result.success,
            message=result.message,
            data={"errors": result.errors} if result.errors else None,
        )

        if result.success:
            # Record history for re-import
            import_mode = entry.get("import_mode", "positions")
            history_id = uc.record_history(
                connector_type="file",
                source_name=entry.get("source_name", ""),
                source_path=source_path,
                import_mode=import_mode,
                column_mapping=entry.get("column_mapping", {}),
                delimiter=entry.get("delimiter", ","),
                asset_type_overrides=entry.get("asset_type_overrides"),
                new_accounts=entry.get("new_accounts"),
                imported=result.imported,
                skipped=result.skipped,
                errors=result.errors,
                success=result.success,
            )
            if history_id and source_path:
                file_connector_paths.set(history_id, source_path)

        return op_result


class WebConnectorService:
    """Frontend service for browser-based automated data import."""

    @staticmethod
    def list_profiles() -> list[dict]:
        """Return all available connector profiles as dicts for the UI."""
        return container.connector_use_cases().list_web_profiles()

    @staticmethod
    @operation_result(failure="Connector failed")
    def run_connector(
        profile_id: str,
        credentials: dict[str, str],
        on_user_input: Callable[[str, str], str] | None = None,
        headless: bool = False,
    ) -> OperationResult:
        """Execute a web connector profile and import the data."""
        uc = container.connector_use_cases()
        result = uc.run_web_connector(
            profile_id,
            credentials,
            on_user_input=on_user_input,
            headless=headless,
        )

        data = {
            "imported": result["imported"],
            "skipped": result["skipped"],
            "errors": result["errors"],
            "status_log": result["status_log"],
            "needs_matching": result["needs_matching"],
            "unmatched_positions": result["unmatched_positions"],
        }

        if result["needs_matching"]:
            return OperationResult(
                success=True,
                message="Positions fetched — matching required.",
                data=data,
            )

        success, msg = build_import_message(
            result["imported"], result["skipped"], result["errors"]
        )
        op_result = OperationResult(success=success, message=msg, data=data)

        # Record history
        profile = uc.get_web_profile(profile_id)
        uc.record_history(
            connector_type="web",
            profile_id=profile_id,
            source_name=profile.name if profile else profile_id,
            import_mode=profile.import_mode if profile else "positions",
            imported=result["imported"],
            skipped=result["skipped"],
            errors=result["errors"],
            success=result["success"],
        )

        return op_result

    @staticmethod
    @operation_result(failure="Import failed")
    def import_matched_positions(
        matched: list[dict],
    ) -> OperationResult:
        """Import user-matched positions (name→ticker) from a web connector."""
        result = container.connector_use_cases().import_matched_positions(matched)

        data = {
            "imported": result["imported"],
            "skipped": result["skipped"],
            "errors": result["errors"],
        }

        success, msg = build_import_message(
            result["imported"], result["skipped"], result["errors"]
        )
        return OperationResult(success=success, message=msg, data=data)


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
    def get_all() -> list[dict]:
        """Get all history entries as dicts for the UI."""
        return container.connector_use_cases().get_all_history()

    @staticmethod
    def delete(entry_id: int) -> bool:
        """Delete a history entry."""
        try:
            container.connector_use_cases().delete_history(entry_id)
            return True
        except Exception as e:
            logger.error("Failed to delete history entry: %s", e)
            return False

"""Domain service for web-based automated data import.

Orchestrates browser automation, file download, and ingestion
through the existing file import pipeline.
"""

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
import logging
import tempfile
from pathlib import Path

from ..entities import ConnectorProfile, EntryType, WebConnectorResult
from ..interfaces import FileConnector, WebConnector
from ..repositories import ConnectorProfileRepository
from .file_connector_service import FileConnectorService

logger = logging.getLogger(__name__)


class WebConnectorService:
    """Orchestrates the full web connector pipeline.

    1. Load profile
    2. Execute browser automation to download a file
    3. Read the downloaded file
    4. Apply the profile's column mapping
    5. Import via existing ConnectorService
    """

    def __init__(
        self,
        web_connector: WebConnector,
        file_connector: FileConnector,
        connector_service: FileConnectorService,
        profile_repo: ConnectorProfileRepository,
    ):
        self._web_connector = web_connector
        self._file_connector = file_connector
        self._connector_service = connector_service
        self._profile_repo = profile_repo

    def list_profiles(self) -> list[ConnectorProfile]:
        """Return all available connector profiles."""
        return self._profile_repo.list_profiles()

    def get_profile(self, profile_id: str) -> ConnectorProfile | None:
        """Load a specific connector profile."""
        return self._profile_repo.get_profile(profile_id)

    def run_connector(
        self,
        profile_id: str,
        credentials: dict[str, str],
        on_status: Callable[[str], None] | None = None,
        headless: bool = False,
    ) -> WebConnectorResult:
        """Execute the full web connector pipeline synchronously.

        Args:
            profile_id: ID of the connector profile to use.
            credentials: Dict with "username" and "password".
            on_status: Optional callback for status updates.

        Returns:
            WebConnectorResult with import counts and any errors.
        """
        status_log: list[str] = []

        def _log(msg: str) -> None:
            status_log.append(msg)
            logger.info(msg)
            if on_status:
                on_status(msg)

        # 1. Load profile
        profile = self._profile_repo.get_profile(profile_id)
        if not profile:
            return WebConnectorResult(
                success=False,
                errors=[f"Profile '{profile_id}' not found."],
                status_log=["Profile not found."],
            )

        _log(f"Loaded profile: {profile.name}")

        # 2. Execute browser automation
        with tempfile.TemporaryDirectory() as tmp_dir:
            download_dir = Path(tmp_dir)
            try:
                _log("Launching browser...")

                # Run playwright in a separate thread with its own event loop
                # because Reflex already occupies the main event loop.
                with ThreadPoolExecutor(1) as pool:
                    downloaded_file = pool.submit(
                        asyncio.run,
                        self._web_connector.execute_profile(
                            profile=profile,
                            credentials=credentials,
                            download_dir=download_dir,
                            on_status=_log,
                            headless=headless,
                        ),
                    ).result()
                _log(f"File downloaded: {downloaded_file.name}")
            except Exception as e:
                _log(f"Browser automation failed: {e}")
                return WebConnectorResult(
                    success=False,
                    errors=[f"Browser automation failed: {e}"],
                    status_log=status_log,
                )

            # 3. Read the downloaded file
            try:
                _log("Reading downloaded file...")
                file_bytes = downloaded_file.read_bytes()
                filename = downloaded_file.name
                df = self._file_connector.read_file(
                    file_bytes, filename, profile.delimiter
                )
                _log(f"Parsed {len(df)} rows from {filename}")
            except Exception as e:
                _log(f"Failed to read file: {e}")
                return WebConnectorResult(
                    success=False,
                    errors=[f"Failed to read downloaded file: {e}"],
                    status_log=status_log,
                    download_path=str(downloaded_file),
                )

            # 4. Import using existing pipeline with auto-applied column mapping
            try:
                _log("Importing data...")
                entry_type = EntryType.WEB

                if profile.import_mode == "cash":
                    result = self._connector_service.import_cash_operations(
                        df=df,
                        column_mapping=profile.column_mapping,
                        entry_type=entry_type,
                        new_accounts=profile.new_accounts,
                    )
                else:
                    result = self._connector_service.import_positions(
                        df=df,
                        column_mapping=profile.column_mapping,
                        entry_type=entry_type,
                    )

                if result.success:
                    _log(
                        f"Import complete: {result.imported} imported, "
                        f"{result.skipped} skipped"
                    )
                else:
                    _log(f"Import failed: {'; '.join(result.errors)}")

                return WebConnectorResult(
                    success=result.success,
                    imported=result.imported,
                    skipped=result.skipped,
                    errors=result.errors,
                    download_path=str(downloaded_file),
                    status_log=status_log,
                )
            except Exception as e:
                _log(f"Import failed: {e}")
                return WebConnectorResult(
                    success=False,
                    errors=[f"Import failed: {e}"],
                    status_log=status_log,
                    download_path=str(downloaded_file),
                )

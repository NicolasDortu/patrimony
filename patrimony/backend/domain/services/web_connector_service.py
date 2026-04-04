"""Domain service for web-based automated data import.

Orchestrates site connector selection, browser automation,
file download, and ingestion through the file import pipeline.
"""

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
import logging
import tempfile
from pathlib import Path

from ..entities import ConnectorProfile, EntryType, WebConnectorResult
from ..interfaces import FileConnector, SiteConnector
from .file_connector_service import FileConnectorService

logger = logging.getLogger(__name__)


class WebConnectorService:
    """Orchestrates the full web connector pipeline.

    1. Resolve the site connector by ID
    2. Execute browser automation to download a file
    3. Read the downloaded file
    4. Apply the connector's column mapping
    5. Import via existing FileConnectorService
    """

    def __init__(
        self,
        site_connectors: list[SiteConnector],
        file_connector: FileConnector,
        connector_service: FileConnectorService,
    ):
        self._sites: dict[str, SiteConnector] = {s.site_id: s for s in site_connectors}
        self._file_connector = file_connector
        self._connector_service = connector_service

    def list_profiles(self) -> list[ConnectorProfile]:
        """Return all available connector profiles."""
        return [s.profile for s in self._sites.values()]

    def get_profile(self, site_id: str) -> ConnectorProfile | None:
        """Load a specific connector profile."""
        site = self._sites.get(site_id)
        return site.profile if site else None

    def run_connector(
        self,
        site_id: str,
        credentials: dict[str, str],
        on_status: Callable[[str], None] | None = None,
        headless: bool = False,
    ) -> WebConnectorResult:
        """Execute the full web connector pipeline synchronously."""
        status_log: list[str] = []

        def _log(msg: str) -> None:
            status_log.append(msg)
            logger.info(msg)
            if on_status:
                on_status(msg)

        # 1. Resolve site connector
        site = self._sites.get(site_id)
        if not site:
            return WebConnectorResult(
                success=False,
                errors=[f"No connector registered for '{site_id}'."],
                status_log=[f"No connector for '{site_id}'."],
            )

        profile = site.profile
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
                        site.execute(
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

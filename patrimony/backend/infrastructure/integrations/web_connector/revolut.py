"""Revolut bank connector.

TODO: Implement Revolut-specific login, navigation,
      and transaction export download logic.
"""

from collections.abc import Callable
from pathlib import Path

from playwright.async_api import Page

from ....domain.entities import ConnectorProfile
from .base import PlaywrightSiteConnector


class RevolutConnector(PlaywrightSiteConnector):
    """Browser automation for Revolut transaction export."""

    @property
    def site_id(self) -> str:
        return "revolut"

    @property
    def profile(self) -> ConnectorProfile:
        return ConnectorProfile(
            id="revolut",
            name="Revolut",
            description="Revolut bank.",
            import_mode="cash",
            column_mapping={},  # TODO: fill when implementing
        )

    async def _run(
        self,
        page: Page,
        credentials: dict[str, str],
        download_dir: Path,
        on_status: Callable[[str], None] | None,
    ) -> Path:
        raise NotImplementedError("Revolut connector not yet implemented.")

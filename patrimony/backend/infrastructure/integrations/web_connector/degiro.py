"""Degiro broker connector.

TODO: Implement Degiro-specific login (2FA), navigation,
      and portfolio export download logic.
"""

from collections.abc import Callable
from pathlib import Path

from playwright.async_api import Page

from ....domain.entities import ConnectorProfile
from .base import PlaywrightSiteConnector


class DegiroConnector(PlaywrightSiteConnector):
    """Browser automation for Degiro portfolio export."""

    @property
    def site_id(self) -> str:
        return "degiro"

    @property
    def profile(self) -> ConnectorProfile:
        return ConnectorProfile(
            id="degiro",
            name="Degiro",
            description="Degiro online broker.",
            import_mode="positions",
            column_mapping={},  # TODO: fill when implementing
        )

    async def _run(
        self,
        page: Page,
        credentials: dict[str, str],
        download_dir: Path,
        on_status: Callable[[str], None] | None,
    ) -> Path:
        raise NotImplementedError("Degiro connector not yet implemented.")

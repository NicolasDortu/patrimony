"""Trade Republic broker connector.

TODO: Implement Trade Republic-specific login (OTP),
      navigation, and portfolio export download logic.
"""

from collections.abc import Callable
from pathlib import Path

from playwright.async_api import Page

from ....domain.entities import ConnectorProfile
from .base import PlaywrightSiteConnector


class TradeRepublicConnector(PlaywrightSiteConnector):
    """Browser automation for Trade Republic portfolio export."""

    @property
    def site_id(self) -> str:
        return "trade_republic"

    @property
    def profile(self) -> ConnectorProfile:
        return ConnectorProfile(
            id="trade_republic",
            name="Trade Republic",
            description="Trade Republic online broker.",
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
        raise NotImplementedError("Trade Republic connector not yet implemented.")

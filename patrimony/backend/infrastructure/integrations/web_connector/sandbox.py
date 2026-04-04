"""Sandbox connector for development and testing.

Connects to the local mock broker (localhost:5050) which accepts
any credentials and serves a CSV export.
"""

import logging
from collections.abc import Callable
from pathlib import Path

from playwright.async_api import Page

from ....domain.entities import ConnectorProfile
from .base import PlaywrightSiteConnector

logger = logging.getLogger(__name__)


class SandboxConnector(PlaywrightSiteConnector):
    """Test connector targeting the local mock broker."""

    @property
    def site_id(self) -> str:
        return "sandbox"

    @property
    def profile(self) -> ConnectorProfile:
        return ConnectorProfile(
            id="sandbox",
            name="Sandbox Broker",
            description="Test broker for development — accepts any credentials.",
            import_mode="positions",
            delimiter=",",
            column_mapping={
                "Ticker": "ticker",
                "Price": "price",
                "Quantity": "quantity",
                "Fees": "fees",
                "Date": "date",
                "Type": "asset_type",
            },
        )

    async def _run(
        self,
        page: Page,
        credentials: dict[str, str],
        download_dir: Path,
        on_status: Callable[[str], None] | None,
    ) -> Path:
        def _status(msg: str) -> None:
            if on_status:
                on_status(msg)

        url = "http://localhost:5050/login"
        _status(f"Navigating to {url}...")
        await page.goto(url, wait_until="domcontentloaded")
        await self.human_delay()

        # Fill login form
        _status("Entering credentials...")
        await self.human_type(page, "#username", credentials.get("username", ""))
        await self.human_delay()
        await self.human_type(page, "#password", credentials.get("password", ""))
        await self.human_delay()

        # Submit
        _status("Logging in...")
        await page.locator("#login-btn").click()
        await page.wait_for_selector(".dashboard", timeout=30_000)
        await self.human_delay()

        # Download export
        _status("Downloading positions export...")
        downloaded = await self.download_on_click(
            page, "#export-positions-csv", download_dir, timeout=15
        )
        _status(f"Downloaded: {downloaded.name}")
        return downloaded

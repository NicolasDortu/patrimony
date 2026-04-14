"""Degiro broker connector.

Automates login (with 2FA wait), navigates to the portfolio page,
and downloads the positions CSV export.
"""

import logging
import tempfile
from collections.abc import Callable
from pathlib import Path

import polars as pl
from playwright.async_api import Page

from ....domain.entities import ConnectorProfile
from .base import PlaywrightSiteConnector

logger = logging.getLogger(__name__)

_PORTFOLIO_URL = "https://trader.degiro.nl/trader/#/portfolio/assets"


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
            column_mapping={
                "col_0": "name",
                "col_1": "ticker",
                "col_2": "quantity",
                "col_3": "price",
                "col_4": "currency",
            },
            credential_fields=[("$user$", "Username"), ("$password$", "Password")],
        )

    async def _execute(
        self,
        page: Page,
        credentials: dict[str, str],
        on_status: Callable[[str], None] | None,
        on_user_input: Callable[[str, str], str] | None = None,
    ) -> pl.DataFrame:
        def _log(msg: str) -> None:
            logger.info(msg)
            if on_status:
                on_status(msg)

        # 1. Navigate to portfolio (redirects to login)
        _log("Navigating to Degiro...")
        await page.goto(_PORTFOLIO_URL)
        await self.human_delay()

        # 2. Accept cookies
        try:
            cookie_btn = page.get_by_role("button", name="Use necessary cookies only")
            await cookie_btn.click(timeout=5_000)
            await self.human_delay()
        except Exception:
            _log("No cookie banner found, continuing...")

        # 3. Login
        _log("Logging in...")
        await self.human_type(
            page, 'role=textbox[name="Username"]', credentials["$user$"]
        )
        await page.keyboard.press("Tab")
        await self.human_delay(0.3, 0.8)
        await self.human_type(
            page, 'role=textbox[name="Password"]', credentials["$password$"]
        )
        await self.human_delay()
        await page.get_by_role("button", name="Login").click()

        # 4. Wait for redirect (handles direct login or 2FA approval in app)
        _log("Waiting for login (approve 2FA in Degiro app if prompted)...")
        await page.wait_for_url("**/trader/#/portfolio/**", timeout=120_000)
        _log("Login successful.")
        await self.human_delay()

        # 5. Download CSV export
        _log("Downloading portfolio CSV...")
        await page.get_by_role("button", name="Exporter").click()
        await self.human_delay()

        with tempfile.TemporaryDirectory() as tmp:
            download_dir = Path(tmp)
            async with page.expect_download(timeout=30_000) as dl_info:
                async with page.expect_popup() as page1_info:
                    await page.get_by_role("link", name="CSV").click()
                page1 = await page1_info.value
            download = await dl_info.value
            dest = download_dir / download.suggested_filename
            await download.save_as(dest)
            await page1.close()

            _log(f"Downloaded: {download.suggested_filename}")
            df = pl.read_csv(dest, separator=",", infer_schema=False)

        _log(f"Parsed {len(df)} rows from CSV.")
        return df

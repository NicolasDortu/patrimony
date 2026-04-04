"""Shared browser automation helpers for site connectors.

Provides Playwright browser setup, stealth configuration,
human-like delays, and download handling.
"""

import asyncio
import logging
import random
from collections.abc import Callable
from pathlib import Path

from playwright.async_api import Page, async_playwright
from playwright_stealth import Stealth

from ....domain.interfaces import SiteConnector

logger = logging.getLogger(__name__)

_stealth = Stealth()

# Human-like delay ranges
MIN_ACTION_DELAY = 0.5
MAX_ACTION_DELAY = 2.0
MIN_TYPING_DELAY = 30  # ms per character
MAX_TYPING_DELAY = 120  # ms per character


class PlaywrightSiteConnector(SiteConnector):
    """Base class with shared Playwright browser lifecycle.

    Subclasses only need to implement:
    - site_id, profile (properties)
    - _run(page, credentials, download_dir, on_status) -> Path
    """

    async def execute(
        self,
        credentials: dict[str, str],
        download_dir: Path,
        on_status: Callable[[str], None] | None = None,
        headless: bool = False,
    ) -> Path:
        """Launch browser, delegate to _run(), then clean up."""
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )
            context = await browser.new_context(
                accept_downloads=True,
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()
            await _stealth.apply_stealth_async(page)

            try:
                return await self._run(page, credentials, download_dir, on_status)
            finally:
                await browser.close()

    async def _run(
        self,
        page: Page,
        credentials: dict[str, str],
        download_dir: Path,
        on_status: Callable[[str], None] | None,
    ) -> Path:
        """Site-specific automation logic. Override in subclasses."""
        raise NotImplementedError

    # --- Shared helpers for subclasses ---

    @staticmethod
    async def human_delay(
        min_s: float = MIN_ACTION_DELAY, max_s: float = MAX_ACTION_DELAY
    ) -> None:
        """Wait a random human-like interval."""
        await asyncio.sleep(random.uniform(min_s, max_s))

    @staticmethod
    async def human_type(page: Page, selector: str, value: str) -> None:
        """Click and type character-by-character for human-like behavior."""
        element = page.locator(selector)
        await element.click()
        await asyncio.sleep(random.uniform(0.2, 0.5))
        await element.press_sequentially(
            value,
            delay=random.randint(MIN_TYPING_DELAY, MAX_TYPING_DELAY),
        )

    @staticmethod
    async def download_on_click(
        page: Page, selector: str, download_dir: Path, timeout: int = 30
    ) -> Path:
        """Click a selector and wait for the triggered download."""
        async with page.expect_download(timeout=timeout * 1000) as dl_info:
            await page.locator(selector).click()
        download = await dl_info.value
        dest = download_dir / download.suggested_filename
        await download.save_as(dest)
        return dest

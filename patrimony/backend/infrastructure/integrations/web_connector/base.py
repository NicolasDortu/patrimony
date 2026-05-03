"""Shared browser automation helpers for site connectors.

Provides Playwright browser setup, stealth configuration,
human-like delays, and download/scrape handling.  All infrastructure
concerns (browser lifecycle, threading, file parsing) live here so
the domain only receives a DataFrame.
"""

import asyncio
import logging
import random
import tempfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import polars as pl
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

    Subclasses implement ``_execute(page, credentials, on_status)``
    and return a :class:`polars.DataFrame`.  The base class handles
    browser launch, stealth, threading, and cleanup.
    """

    def fetch_data(
        self,
        credentials: dict[str, str],
        on_status: Callable[[str], None] | None = None,
        on_user_input: Callable[[str, str], str] | None = None,
        **options,
    ) -> pl.DataFrame:
        """Launch browser, delegate to _execute(), return DataFrame.

        Runs Playwright in a dedicated thread with its own event loop
        because the caller (Reflex) already occupies the main loop.
        """
        headless = options.get("headless", False)
        with ThreadPoolExecutor(1) as pool:
            return pool.submit(
                asyncio.run,
                self._launch_and_execute(
                    credentials, on_status, on_user_input, headless
                ),
            ).result()

    async def _launch_and_execute(
        self,
        credentials: dict[str, str],
        on_status: Callable[[str], None] | None,
        on_user_input: Callable[[str, str], str] | None,
        headless: bool,
    ) -> pl.DataFrame:
        """Launch a stealth browser and delegate to ``_execute()``."""
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
                return await self._execute(page, credentials, on_status, on_user_input)
            finally:
                await browser.close()

    async def _execute(
        self,
        page: Page,
        credentials: dict[str, str],
        on_status: Callable[[str], None] | None,
        on_user_input: Callable[[str, str], str] | None = None,
    ) -> pl.DataFrame:
        """Site-specific data extraction logic.  Override in subclasses.

        For connectors that trigger a file download, use
        :meth:`download_and_parse`.  For connectors that scrape data
        directly from the page, build and return a DataFrame.
        """
        raise NotImplementedError

    @staticmethod
    def make_logger(
        on_status: Callable[[str], None] | None,
    ) -> Callable[[str], None]:
        """Return a callable that logs to the standard logger and forwards
        the message to ``on_status`` (if provided)."""

        def _log(msg: str) -> None:
            logger.info(msg)
            if on_status:
                on_status(msg)

        return _log

    @staticmethod
    async def request_user_input(
        on_user_input: Callable[[str, str], str] | None,
        prompt_type: str,
        message: str,
    ) -> str:
        """Request input from the user via the on_user_input callback.

        Runs the blocking callback in a thread so the async event loop
        is not blocked while waiting for user response.
        """
        if not on_user_input:
            raise RuntimeError("User input required but no callback provided.")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, on_user_input, prompt_type, message)

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
    async def download_and_parse(
        page: Page,
        selector: str,
        delimiter: str = ",",
        timeout: int = 30,
    ) -> pl.DataFrame:
        """Click a download trigger and parse the file into a DataFrame.

        Handles CSV and Excel formats based on the downloaded file extension.
        """
        with tempfile.TemporaryDirectory() as tmp:
            download_dir = Path(tmp)
            async with page.expect_download(timeout=timeout * 1000) as dl_info:
                await page.locator(selector).click()
            download = await dl_info.value
            dest = download_dir / download.suggested_filename
            await download.save_as(dest)

            suffix = dest.suffix.lower()
            if suffix in (".xlsx", ".xls"):
                return pl.read_excel(dest, infer_schema_length=0)
            return pl.read_csv(dest, separator=delimiter, infer_schema=False)

    @staticmethod
    async def copy_text(page: Page, selector: str) -> str:
        """Copy text from a selector to the clipboard and return it."""
        element = page.locator(selector)
        await element.click()
        await page.keyboard.press("Control+C")
        await asyncio.sleep(0.5)  # Wait for clipboard to update
        return await page.evaluate("navigator.clipboard.readText()")

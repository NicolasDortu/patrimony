"""Playwright-based web connector for automated browser data download.

Uses playwright-stealth for anti-detection and human-like interaction
patterns (random delays, per-character typing).
"""

from collections.abc import Callable
import asyncio
import logging
import random
from pathlib import Path

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from ...domain.entities import ConnectorProfile, ConnectorStep
from ...domain.interfaces import WebConnector

logger = logging.getLogger(__name__)

# Stealth instance (reusable, applied per page)
_stealth = Stealth()

# Human-like delay ranges (seconds)
MIN_ACTION_DELAY = 0.5
MAX_ACTION_DELAY = 2.0
MIN_TYPING_DELAY = 30  # ms per character
MAX_TYPING_DELAY = 120  # ms per character


class PlaywrightConnector(WebConnector):
    """Browser automation connector using Playwright with stealth."""

    async def execute_profile(
        self,
        profile: ConnectorProfile,
        credentials: dict[str, str],
        download_dir: Path,
        on_status: Callable[[str], None] | None = None,
        headless: bool = False,
    ) -> Path:
        """Execute all steps in a connector profile.

        Launches a visible Chromium browser with stealth settings,
        navigates to the profile URL, and executes each step.
        """

        def _status(msg: str) -> None:
            if on_status:
                on_status(msg)

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

            downloaded_file: Path | None = None

            try:
                _status(f"Navigating to {profile.url}...")
                await page.goto(profile.url, wait_until="domcontentloaded")
                await _human_delay()

                for i, step in enumerate(profile.steps):
                    _status(f"Step {i + 1}/{len(profile.steps)}: {step.action}...")
                    downloaded_file = await self._execute_step(
                        page, step, credentials, download_dir
                    )
                    await _human_delay()

                if downloaded_file is None:
                    raise RuntimeError(
                        "Profile completed but no file was downloaded. "
                        "Ensure the profile has a 'download' step."
                    )

                return downloaded_file

            finally:
                await browser.close()

    async def _execute_step(
        self,
        page,
        step: ConnectorStep,
        credentials: dict[str, str],
        download_dir: Path,
    ) -> Path | None:
        """Execute a single automation step."""
        action = step.action.lower()

        if action == "fill":
            value = self._substitute_credentials(step.value, credentials)
            await page.wait_for_selector(step.selector, timeout=step.timeout * 1000)
            element = page.locator(step.selector)
            await element.click()
            await _human_delay(0.2, 0.5)
            # Type character by character for human-like behavior
            await element.press_sequentially(
                value,
                delay=random.randint(MIN_TYPING_DELAY, MAX_TYPING_DELAY),
            )

        elif action == "click":
            await page.wait_for_selector(step.selector, timeout=step.timeout * 1000)
            await page.locator(step.selector).click()

        elif action == "wait":
            await page.wait_for_selector(step.selector, timeout=step.timeout * 1000)

        elif action == "download":
            # Wait for download triggered by the previous click
            async with page.expect_download(timeout=step.timeout * 1000) as dl_info:
                # If a selector is provided, click it to trigger download
                if step.selector:
                    await page.locator(step.selector).click()

            download = await dl_info.value
            dest = download_dir / download.suggested_filename
            await download.save_as(dest)
            return dest

        else:
            logger.warning("Unknown step action: %s", action)

        return None

    @staticmethod
    def _substitute_credentials(value: str, credentials: dict[str, str]) -> str:
        """Replace {{username}} and {{password}} placeholders."""
        result = value
        result = result.replace("{{username}}", credentials.get("username", ""))
        result = result.replace("{{password}}", credentials.get("password", ""))
        return result


async def _human_delay(
    min_s: float = MIN_ACTION_DELAY, max_s: float = MAX_ACTION_DELAY
) -> None:
    """Wait a random human-like interval."""
    await asyncio.sleep(random.uniform(min_s, max_s))

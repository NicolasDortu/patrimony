"""Manual browser launcher for testing web connectors.

Usage:
    # Browse mode – opens a stealth browser for manual testing
    python bin/manual_browser.py browse
    python bin/manual_browser.py browse --url https://trader.degiro.nl
    python bin/manual_browser.py browse --url https://app.revolut.com

    # Record mode – opens Playwright codegen to record actions as Python code
    python bin/manual_browser.py record
    python bin/manual_browser.py record --url https://trader.degiro.nl
    python bin/manual_browser.py record --output recorded_steps.py
"""

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# Same stealth / browser settings as base.py
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
VIEWPORT = {"width": 1280, "height": 800}
LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
]

_stealth = Stealth()

KNOWN_URLS: dict[str, str] = {
    "degiro": "https://trader.degiro.nl",
    "trade_republic": "https://app.traderepublic.com",
    "revolut": "https://app.revolut.com",
    "bnp_paribas_be": "https://www.bnpparibasfortis.be",
}


async def browse(url: str | None, download_dir: Path) -> None:
    """Open a stealth browser for manual interaction.

    The browser stays open until you close it manually.
    Downloads are saved to *download_dir*.
    """
    download_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            args=LAUNCH_ARGS,
        )
        context = await browser.new_context(
            accept_downloads=True,
            viewport=VIEWPORT,
            user_agent=USER_AGENT,
        )
        page = await context.new_page()
        await _stealth.apply_stealth_async(page)

        # Save any file that gets downloaded
        page.on(
            "download",
            lambda dl: asyncio.ensure_future(_save_download(dl, download_dir)),
        )

        if url:
            await page.goto(url, wait_until="domcontentloaded")

        print("=" * 60)
        print("  Manual browser session started.")
        print(f"  Downloads will be saved to: {download_dir.resolve()}")
        print("  Close the browser window to end the session.")
        print("=" * 60)

        # Keep running until the browser is closed
        try:
            await page.wait_for_event("close", timeout=0)
        except Exception:
            pass

        # If the page was closed but browser is still alive, wait for browser
        try:
            await browser.close()
        except Exception:
            pass

    print("Session ended.")


async def _save_download(download, download_dir: Path) -> None:
    """Save a triggered download to the download directory."""
    dest = download_dir / download.suggested_filename
    await download.save_as(dest)
    print(f"  Downloaded: {dest}")


def record(url: str | None, output_file: Path) -> None:
    """Launch Playwright codegen to record actions as Python code.

    This spawns `playwright codegen` as a subprocess so you get the
    full inspector UI with action recording.
    """
    cmd = [
        sys.executable,
        "-m",
        "playwright",
        "codegen",
        "--target",
        "python-async",
        "--viewport-size",
        f"{VIEWPORT['width']},{VIEWPORT['height']}",
        "-o",
        str(output_file),
    ]

    if url:
        cmd.append(url)

    print("=" * 60)
    print("  Playwright codegen (record mode) starting.")
    print(f"  Recorded script will be saved to: {output_file.resolve()}")
    if url:
        print(f"  Starting URL: {url}")
    print("  Close the browser window to stop recording.")
    print("=" * 60)

    subprocess.run(cmd)
    print(f"Recording saved to: {output_file.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manual browser for testing web connectors.",
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    # --- browse subcommand ---
    browse_parser = subparsers.add_parser(
        "browse", help="Open a stealth browser for manual testing."
    )
    browse_parser.add_argument(
        "--url",
        default=None,
        help="URL to navigate to, or a broker alias: " + ", ".join(KNOWN_URLS.keys()),
    )
    browse_parser.add_argument(
        "--download-dir",
        type=Path,
        default=Path("downloads"),
        help="Directory to save downloads (default: ./bin/downloads).",
    )

    # --- record subcommand ---
    record_parser = subparsers.add_parser(
        "record", help="Record browser actions with Playwright codegen."
    )
    record_parser.add_argument(
        "--url",
        default=None,
        help="URL to navigate to, or a broker alias: " + ", ".join(KNOWN_URLS.keys()),
    )
    record_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("recorded_steps.py"),
        help="Output file for recorded script (default: recorded_steps.py).",
    )

    args = parser.parse_args()

    # Resolve broker aliases
    if args.url and args.url in KNOWN_URLS:
        args.url = KNOWN_URLS[args.url]

    if args.mode == "browse":
        asyncio.run(browse(args.url, args.download_dir))
    elif args.mode == "record":
        record(args.url, args.output)


if __name__ == "__main__":
    main()

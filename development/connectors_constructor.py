"""Development tool for building and testing web connectors.

Usage:
    # Record mode – opens Playwright codegen to record actions
    uv run development/connectors_constructor.py record degiro
    uv run development/connectors_constructor.py record bnp_paribas_be
    uv run development/connectors_constructor.py record --url https://example.com -o my_recording.py

    # Run mode – execute a recording or connector step-by-step
    uv run development/connectors_constructor.py run development/records/degiro_recording.py
    uv run development/connectors_constructor.py run development/records/degiro_recording.py --no-step
"""

import argparse
import asyncio
import importlib.util
import random
import subprocess
import sys
from pathlib import Path

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# ── Browser settings (mirroring base.py) ───────────────────────

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

# Human-like delay ranges (mirroring base.py)
MIN_ACTION_DELAY = 1.0
MAX_ACTION_DELAY = 3.0
MIN_TYPING_DELAY = 30  # ms per character
MAX_TYPING_DELAY = 120  # ms per character


async def _human_delay() -> None:
    """Wait a random human-like interval between actions."""
    await asyncio.sleep(random.uniform(MIN_ACTION_DELAY, MAX_ACTION_DELAY))


KNOWN_URLS: dict[str, str] = {
    "degiro": "https://trader.degiro.nl/trader/#/portfolio/assets",
    "trade_republic": "https://app.traderepublic.com/portfolio?timeframe=1d",
    "revolut": "https://app.revolut.com",
    "bnp_paribas_be": "https://www.bnpparibasfortis.be/fr/secured/accounts/search-transactions",
}

DEV_DIR = Path(__file__).parent
RECORDS_DIR = DEV_DIR / "records"


# ── Record mode ────────────────────────────────────────────────


def record(url: str | None, output_file: Path) -> None:
    """Launch Playwright codegen to record actions as Python code."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

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
    print("  Playwright codegen (record mode)")
    print(f"  Output: {output_file.resolve()}")
    if url:
        print(f"  URL:    {url}")
    print("  Close the browser window to stop recording.")
    print("=" * 60)

    subprocess.run(cmd)
    print(f"\nRecording saved to: {output_file.resolve()}")


# ── Step-by-step wrappers ─────────────────────────────────────


def _print_step(num: int, desc: str) -> None:
    print(f"\n  [{num}] {desc}")


def _wait_for_enter() -> None:
    input("       Press Enter to execute...")


class StepByStepPage:
    """Wraps a Playwright Page to pause before each action."""

    _STEP_METHODS = {
        "goto",
        "click",
        "fill",
        "press",
        "check",
        "uncheck",
        "select_option",
        "set_input_files",
        "press_sequentially",
    }

    _LOCATOR_METHODS = {
        "locator",
        "get_by_role",
        "get_by_text",
        "get_by_label",
        "get_by_placeholder",
        "get_by_test_id",
    }

    def __init__(self, page, step: bool = True):
        self._page = page
        self._step = step
        self._action_num = 0

    def __getattr__(self, name: str):
        attr = getattr(self._page, name)
        if name in self._STEP_METHODS:
            return self._make_stepper(name, attr)
        if name in self._LOCATOR_METHODS:
            return self._make_locator_factory(name, attr)
        return attr

    def _make_stepper(self, name: str, method):
        async def wrapper(*args, **kwargs):
            self._action_num += 1
            desc = _describe_call(f"page.{name}", args, kwargs)
            _print_step(self._action_num, desc)
            if self._step:
                _wait_for_enter()
            await _human_delay()
            result = await method(*args, **kwargs)
            return result

        return wrapper

    def _make_locator_factory(self, name: str, method):
        def wrapper(*args, **kwargs):
            locator = method(*args, **kwargs)
            return _StepByStepLocator(locator, self)

        return wrapper

    # Properties that recordings access directly
    @property
    def keyboard(self):
        return self._page.keyboard

    @property
    def mouse(self):
        return self._page.mouse

    @property
    def url(self):
        return self._page.url

    # Context managers used by recordings
    def expect_download(self, **kwargs):
        return self._page.expect_download(**kwargs)

    def expect_popup(self, **kwargs):
        return self._page.expect_popup(**kwargs)

    def expect_event(self, event, **kwargs):
        return self._page.expect_event(event, **kwargs)

    # Async methods that should pass through without pausing
    async def wait_for_timeout(self, timeout):
        await self._page.wait_for_timeout(timeout)

    async def wait_for_load_state(self, state=None, **kwargs):
        await self._page.wait_for_load_state(state, **kwargs)

    async def wait_for_url(self, url, **kwargs):
        await self._page.wait_for_url(url, **kwargs)

    async def evaluate(self, expression, *args):
        return await self._page.evaluate(expression, *args)

    async def close(self):
        pass  # lifecycle managed by runner


class _StepByStepLocator:
    """Wraps a Playwright Locator to pause before terminal actions."""

    _STEP_METHODS = {
        "click",
        "fill",
        "press",
        "check",
        "uncheck",
        "press_sequentially",
        "select_option",
        "set_input_files",
    }

    _CHAIN_METHODS = {
        "locator",
        "filter",
        "get_by_role",
        "get_by_text",
        "get_by_label",
        "get_by_placeholder",
        "get_by_test_id",
        "nth",
    }

    def __init__(self, locator, page_wrapper: StepByStepPage):
        self._locator = locator
        self._pw = page_wrapper

    def __getattr__(self, name: str):
        attr = getattr(self._locator, name)
        if name in self._STEP_METHODS:
            return self._make_stepper(name, attr)
        if name in self._CHAIN_METHODS:
            return self._make_chain(attr)
        return attr

    def _make_stepper(self, name: str, method):
        async def wrapper(*args, **kwargs):
            self._pw._action_num += 1
            # For fill: use human-like character-by-character typing
            if name == "fill" and args:
                desc = _describe_call("locator.fill (human-typed)", args, kwargs)
                _print_step(self._pw._action_num, desc)
                if self._pw._step:
                    _wait_for_enter()
                await _human_delay()
                await self._locator.click()
                await asyncio.sleep(random.uniform(0.2, 0.5))
                await self._locator.press_sequentially(
                    args[0],
                    delay=random.randint(MIN_TYPING_DELAY, MAX_TYPING_DELAY),
                )
                return
            desc = _describe_call(f"locator.{name}", args, kwargs)
            _print_step(self._pw._action_num, desc)
            if self._pw._step:
                _wait_for_enter()
            await _human_delay()
            result = await method(*args, **kwargs)
            return result

        return wrapper

    def _make_chain(self, method):
        def wrapper(*args, **kwargs):
            return _StepByStepLocator(method(*args, **kwargs), self._pw)

        return wrapper

    @property
    def first(self):
        return _StepByStepLocator(self._locator.first, self._pw)

    @property
    def last(self):
        return _StepByStepLocator(self._locator.last, self._pw)


def _describe_call(prefix: str, args: tuple, kwargs: dict) -> str:
    parts = [repr(a) for a in args]
    parts += [f"{k}={v!r}" for k, v in kwargs.items()]
    return f"{prefix}({', '.join(parts)})"


# ── Playwright shim chain ─────────────────────────────────────
# Intercepts playwright.chromium.launch() → browser.new_context()
# → context.new_page() so recordings run unmodified against our
# pre-configured stealth browser + step-by-step wrapper.


class _PlaywrightShim:
    def __init__(self, browser, context, page):
        self.chromium = _BrowserTypeShim(browser, context, page)


class _BrowserTypeShim:
    def __init__(self, browser, context, page):
        self._browser = browser
        self._context = context
        self._page = page

    async def launch(self, **kwargs):
        return _BrowserShim(self._browser, self._context, self._page)


class _BrowserShim:
    def __init__(self, browser, context, page):
        self._browser = browser
        self._context = context
        self._page = page

    async def new_context(self, **kwargs):
        return _ContextShim(self._context, self._page)

    async def close(self):
        pass  # real cleanup handled by the runner


class _ContextShim:
    def __init__(self, context, page):
        self._context = context
        self._page = page

    async def new_page(self):
        return self._page

    async def close(self):
        pass  # real cleanup handled by the runner


# ── Run mode ──────────────────────────────────────────────────


async def run_script(script_path: Path, step: bool = True) -> None:
    """Execute a recording script with a stealth browser, step-by-step."""
    spec = importlib.util.spec_from_file_location("recording", script_path)
    mod = importlib.util.module_from_spec(spec)

    # Recordings end with asyncio.run(main()) at module level.
    # Monkey-patch asyncio.run to a no-op during import so it
    # doesn't crash inside our already-running event loop.
    _original_run = asyncio.run
    asyncio.run = lambda *a, **kw: None  # type: ignore[assignment]
    try:
        spec.loader.exec_module(mod)
    finally:
        asyncio.run = _original_run  # type: ignore[assignment]

    run_fn = getattr(mod, "run", None)
    if run_fn is None:
        print(f"Error: {script_path} has no run() function.")
        sys.exit(1)

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

        wrapped = StepByStepPage(page, step=step)
        shim = _PlaywrightShim(browser, context, wrapped)

        print("=" * 60)
        if step:
            print("  Step-by-step runner")
            print("  Press Enter before each action to proceed.")
        else:
            print("  Running script continuously (no pauses)")
        print(f"  Script: {script_path.resolve()}")
        print("=" * 60)

        try:
            await run_fn(shim)
        except Exception as e:
            print(f"\n  Error: {e}")
        finally:
            try:
                await browser.close()
            except Exception:
                pass

    print("\nSession ended.")


# ── CLI ────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Development tool for building and testing web connectors.",
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    # --- record subcommand ---
    rec = subparsers.add_parser(
        "record", help="Record browser actions with Playwright codegen."
    )
    rec.add_argument(
        "broker",
        nargs="?",
        default=None,
        help="Broker alias: " + ", ".join(KNOWN_URLS.keys()),
    )
    rec.add_argument(
        "--url",
        default=None,
        help="Custom URL (overrides broker alias).",
    )
    rec.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output file (default: records/{broker}_recording.py).",
    )

    # --- run subcommand ---
    run_p = subparsers.add_parser("run", help="Run a recording script step-by-step.")
    run_p.add_argument(
        "script",
        type=Path,
        help="Path to a recording .py file to execute.",
    )
    run_p.add_argument(
        "--no-step",
        action="store_true",
        help="Run continuously without pausing at each step.",
    )

    args = parser.parse_args()

    if args.mode == "record":
        url = args.url
        if not url and args.broker and args.broker in KNOWN_URLS:
            url = KNOWN_URLS[args.broker]

        output = args.output
        if output is None:
            name = args.broker or "recorded"
            output = RECORDS_DIR / f"{name}_recording.py"

        record(url, output)

    elif args.mode == "run":
        if not args.script.exists():
            print(f"Error: {args.script} not found.")
            sys.exit(1)
        asyncio.run(run_script(args.script, step=not args.no_step))


if __name__ == "__main__":
    main()

"""Revolut bank connector.

Automates login via QR code scanning, navigates to the accounts
overview, and scrapes account balances for cash import.
"""

import base64
import logging
import re
from collections.abc import Callable

import polars as pl
from playwright.async_api import Page

from ....domain.entities import ConnectorProfile
from .base import PlaywrightSiteConnector

logger = logging.getLogger(__name__)

_HOME_URL = "https://app.revolut.com/home"

# Pattern to detect currency amounts in various locales:
# €173.64, €173,64, CHF 1,010.21, CHF 1.010,21, CHF 1 010,21, $500.00, etc.
_AMOUNT_RE = re.compile(
    r"^(?:([A-Z]{3})[\s\xa0]+)?"  # optional currency code prefix (e.g. "CHF ")
    r"([€$£]?)"  # optional currency symbol
    r"[\s\xa0]*"  # optional whitespace after symbol
    r"(-?[\d.,\s\xa0']+\d)"  # numeric amount (various thousand/decimal seps)
    r"[\s\xa0]*([€$£]?)$"  # optional trailing currency symbol
)

# Map currency display names to ISO codes
_CURRENCY_NAMES: dict[str, str] = {
    "euro": "EUR",
    "dollar": "USD",
    "us dollar": "USD",
    "british pound": "GBP",
    "pound": "GBP",
    "franc suisse": "CHF",
    "swiss franc": "CHF",
    "japanese yen": "JPY",
    "yen": "JPY",
    "canadian dollar": "CAD",
    "australian dollar": "AUD",
    "swedish krona": "SEK",
    "norwegian krone": "NOK",
    "danish krone": "DKK",
    "polish zloty": "PLN",
    "czech koruna": "CZK",
    "hungarian forint": "HUF",
    "romanian leu": "RON",
    "turkish lira": "TRY",
    "singapore dollar": "SGD",
    "hong kong dollar": "HKD",
    "new zealand dollar": "NZD",
    "south african rand": "ZAR",
    "mexican peso": "MXN",
    "brazilian real": "BRL",
    "indian rupee": "INR",
    "chinese yuan": "CNY",
}

_SYMBOL_TO_CURRENCY: dict[str, str] = {
    "€": "EUR",
    "$": "USD",
    "£": "GBP",
}


class RevolutConnector(PlaywrightSiteConnector):
    """Browser automation for Revolut account balance scraping."""

    def __init__(self) -> None:
        super().__init__()
        self._discovered_accounts: dict[str, dict] | None = None

    @property
    def site_id(self) -> str:
        return "revolut"

    @property
    def profile(self) -> ConnectorProfile:
        return ConnectorProfile(
            id="revolut",
            name="Revolut",
            description="Revolut bank accounts.",
            import_mode="cash",
            column_mapping={
                "col_0": "account_number",
                "col_1": "amount",
                "col_2": "title",
            },
            new_accounts=self._discovered_accounts,
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

        # 1. Navigate to Revolut login
        _log("Navigating to Revolut...")
        await page.goto(_HOME_URL)
        await self.human_delay()

        # 2. Capture QR code and show to user
        _log("Waiting for QR code...")
        try:
            qr_img = page.get_by_role("img", name="Log in with QR code")
            await qr_img.wait_for(timeout=15_000)
            await self.human_delay(0.5, 1.0)

            # Screenshot the QR code element and encode as base64
            qr_bytes = await qr_img.screenshot()
            qr_b64 = base64.b64encode(qr_bytes).decode("ascii")
            qr_data_url = f"data:image/png;base64,{qr_b64}"

            _log("QR code captured. Waiting for user to scan...")
            await self.request_user_input(
                on_user_input,
                "qr",
                qr_data_url,
            )
        except Exception as e:
            _log(f"Could not capture QR code: {e}")
            # Fall back to action prompt — user scans from Playwright window
            await self.request_user_input(
                on_user_input,
                "action",
                "Scan the QR code in the Revolut browser window, "
                "then press Confirm.",
            )

        # 3. Wait for login to complete (URL changes to /home after scan)
        _log("Waiting for login to complete...")
        try:
            await page.wait_for_url("**/home**", timeout=120_000)
            await self.human_delay(2.0, 3.0)
        except Exception:
            _log("Login may have timed out, attempting to continue...")

        _log("Login successful.")
        await self.human_delay()

        # 4. Reject cookies if present
        try:
            await page.get_by_role("button", name="Reject all cookies").click(
                timeout=5_000
            )
            await self.human_delay()
        except Exception:
            pass

        # 5. Open account selector to reveal all accounts
        _log("Opening account selector...")
        try:
            await page.get_by_role("button", name="Select account").click(
                timeout=10_000
            )
            await self.human_delay(1.0, 2.0)
        except Exception:
            _log("Could not open account selector, scraping current view...")

        # 6. Scrape account text
        _log("Scraping account data...")
        main = page.locator("#layout__main").first
        try:
            await main.wait_for(timeout=10_000)
        except Exception:
            main = page.locator("main").first
            await main.wait_for(timeout=10_000)

        await self.human_delay()
        text = await main.inner_text()
        _log(f"Scraped {len(text)} chars.")
        # Log each line for debugging parser issues
        for idx, ln in enumerate(text.splitlines()):
            logger.info("Revolut line %d: %r", idx, ln)

        # 7. Parse accounts
        _log("Parsing account balances...")
        df = self._parse_accounts_text(text)
        _log(f"Parsed {len(df)} accounts.")

        # 8. Store discovered accounts for profile.new_accounts
        self._discovered_accounts = {}
        for row in df.iter_rows(named=True):
            acct = row["account_number"]
            self._discovered_accounts[acct] = {
                "bank": "Revolut",
                "currency": row.get("currency_code", "EUR"),
            }

        return df

    @staticmethod
    def _parse_accounts_text(text: str) -> pl.DataFrame:
        """Parse the Revolut account selector text into cash operations.

        Returns a DataFrame with: account_number, amount, title, currency_code.
        """
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

        rows: list[dict[str, str]] = []
        account_group = "Personal"  # default group name

        i = 0
        while i < len(lines):
            line = lines[i]

            # Detect account group headers (e.g. "Personal", "Joint", "Business")
            # They appear on a line by themselves, followed by "Accounts"
            if (
                i + 1 < len(lines)
                and lines[i + 1].lower() in ("accounts", "pockets")
                and not _AMOUNT_RE.match(line)
                and line.lower() not in ("accounts", "pockets")
                and "·" not in line
            ):
                account_group = line
                logger.info("Parser: group header -> %r", account_group)
                i += 1
                continue

            # Skip structural lines
            if line.lower() in ("accounts", "pockets") or "·" in line:
                logger.info("Parser: skip structural %r", line)
                i += 1
                continue

            # Try to detect a currency name followed by an amount
            currency_name_lower = line.lower()
            if currency_name_lower in _CURRENCY_NAMES and i + 1 < len(lines):
                currency_code = _CURRENCY_NAMES[currency_name_lower]
                amount_line = lines[i + 1]
                amount = _parse_amount(amount_line)
                logger.info(
                    "Parser: currency %r -> %s, next=%r, amount=%s",
                    line,
                    currency_code,
                    amount_line,
                    amount,
                )
                if amount is not None:
                    acct_number = f"Revolut {account_group} {currency_code}"
                    rows.append(
                        {
                            "account_number": acct_number,
                            "amount": amount,
                            "title": "Revolut balance",
                            "currency_code": currency_code,
                        }
                    )
                    i += 2
                    # Skip EUR equivalent line if present (second amount line)
                    if i < len(lines) and _parse_amount(lines[i]) is not None:
                        i += 1
                    continue
            else:
                logger.info("Parser: unrecognized line %r", line)

            i += 1

        schema = {
            "account_number": pl.Utf8,
            "amount": pl.Utf8,
            "title": pl.Utf8,
            "currency_code": pl.Utf8,
        }

        if not rows:
            return pl.DataFrame(schema=schema)

        return pl.DataFrame(rows, schema=schema)


def _parse_amount(line: str) -> str | None:
    """Try to parse a line as a currency amount. Return cleaned amount or None."""
    line = line.strip().replace("\xa0", " ")
    match = _AMOUNT_RE.match(line)
    if not match:
        return None
    raw = match.group(3).strip()
    # Normalise various thousand/decimal separators to a plain float string.
    # Detect European format: last separator is a comma  (e.g. 1.010,21 or 1 010,21)
    last_comma = raw.rfind(",")
    last_dot = raw.rfind(".")
    if last_comma > last_dot:
        # European: dots/spaces are thousands, comma is decimal
        raw = raw.replace(" ", "").replace("'", "").replace(".", "").replace(",", ".")
    else:
        # US/UK: commas/spaces are thousands, dot is decimal
        raw = raw.replace(" ", "").replace("'", "").replace(",", "")
    return raw

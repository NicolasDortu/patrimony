"""Trade Republic broker connector.

Automates login (with 4-digit OTP from the TR app), navigates to the
portfolio page, switches to "Since buy" view, and scrapes position data
directly from the DOM (Trade Republic does not offer CSV export).
"""

import logging
import re
from collections.abc import Callable

import polars as pl
from playwright.async_api import Page

from ....domain.entities import ConnectorProfile
from .base import PlaywrightSiteConnector

logger = logging.getLogger(__name__)

_LOGIN_URL = "https://app.traderepublic.com/login"

# Patterns for line-based position parsing from inner_text() output.
# Each position is 4 consecutive lines: Name, Quantity, Value €, PnL €
_QUANTITY_RE = re.compile(r"^\d[\d.]*$")  # e.g. "3.292116"
_VALUE_RE = re.compile(r"^-?[\d.,]+ [€$£]$")  # e.g. "2,062.77 €"


class TradeRepublicConnector(PlaywrightSiteConnector):
    """Browser automation for Trade Republic portfolio scraping."""

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
            needs_matching=True,
            column_mapping={
                "col_0": "name",
                "col_1": "quantity",
                "col_2": "price",
                "col_3": "currency",
            },
            credential_fields=[
                ("$country$", "Country", ["Belgium", "Germany", "France", "Spain"]),
                ("$phone$", "Phone number"),
                ("$pin$", "PIN (4 digits)"),
            ],
        )

    async def _execute(
        self,
        page: Page,
        credentials: dict[str, str],
        on_status: Callable[[str], None] | None,
        on_user_input: Callable[[str, str], str] | None = None,
    ) -> pl.DataFrame:
        _log = self.make_logger(on_status)

        country = credentials.get("$country$", "Belgium")
        phone = credentials.get("$phone$", "")
        pin = credentials.get("$pin$", "")

        # 1. Navigate to login
        _log("Navigating to Trade Republic...")
        await page.goto(_LOGIN_URL)
        await self.human_delay()

        # 2. Accept cookies
        try:
            await page.get_by_role("button", name="Accept Selected").click(
                timeout=5_000
            )
            await self.human_delay()
        except Exception:
            _log("No cookie banner found, continuing...")

        # 3. Select country
        _log(f"Selecting country: {country}...")
        try:
            await page.get_by_role("button", name="+").click(timeout=5_000)
            await self.human_delay(0.3, 0.8)
            await page.get_by_text(country, exact=False).first.click()
            await self.human_delay()
        except Exception:
            _log("Country selector not found, continuing...")

        # 4. Enter phone number
        _log("Entering phone number...")
        phone_input = page.get_by_role("textbox").first
        await phone_input.click()
        await phone_input.fill(phone)
        await self.human_delay()
        await page.get_by_role("button", name="Next").click()
        await self.human_delay()

        # 5. Enter PIN (character by character into 4 separate boxes)
        _log("Entering PIN...")
        pin_digits = list(pin.ljust(4, "0")[:4])
        textboxes = page.get_by_role("textbox")
        for i, digit in enumerate(pin_digits):
            box = textboxes.nth(i)
            await box.fill(digit)
            await self.human_delay(0.1, 0.3)
        await self.human_delay()

        # 6. Request OTP from user (4-digit code from the TR app)
        _log("Waiting for OTP code from app...")
        otp_code = await self.request_user_input(
            on_user_input,
            "text",
            "Enter the 4-digit code shown in your Trade Republic app.",
        )
        _log("Entering OTP code...")

        otp_digits = list(otp_code.ljust(4, "0")[:4])
        otp_boxes = page.get_by_role("textbox")
        for i, digit in enumerate(otp_digits):
            box = otp_boxes.nth(i)
            await box.fill(digit)
            await self.human_delay(0.1, 0.3)

        # 7. Wait for portfolio page to load
        _log("Waiting for login to complete...")
        await page.wait_for_url("**/portfolio**", timeout=60_000)
        _log("Login successful.")
        await self.human_delay()

        # 8. Switch to "Since buy (€)" view for absolute value display
        _log("Switching to 'Since buy' view...")
        try:
            await page.get_by_role("button", name="Daily trend").click(timeout=10_000)
            await self.human_delay()
            await page.get_by_role("option", name="Since buy (€)").click()
            await self.human_delay(2.0, 3.0)
        except Exception:
            _log("Could not switch to 'Since buy' view, using current view...")

        # 9. Scrape portfolio data from #layout__main
        _log("Scraping portfolio data...")
        main = page.locator("#layout__main")
        await main.wait_for(timeout=15_000)
        text = await main.inner_text()

        _log("Parsing scraped data...")
        df = self._parse_portfolio_text(text)
        _log(f"Parsed {len(df)} positions.")
        return df

    @staticmethod
    def _parse_portfolio_text(text: str) -> pl.DataFrame:
        """Parse line-separated inner_text() output into a DataFrame.

        inner_text() returns each DOM element on its own line.  Each
        position appears as 4 consecutive lines after the header::

            Core S&P 500 USD (Acc)     <- name (starts with letter)
            3.292116                   <- quantity (digits + optional dot)
            2,062.77 €                 <- value (number + currency symbol)
            37.77 €                    <- PnL  (number + currency symbol)

        Returns a DataFrame with columns: name, quantity, value, currency.
        """
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

        # Find the "Investments" header — positions start right after
        start = 0
        for i, ln in enumerate(lines):
            if ln.lower().startswith("investments"):
                start = i + 1
                break

        # Skip the view-mode label (e.g. "Since buy", "Daily trend")
        if start < len(lines) and not _QUANTITY_RE.match(lines[start]):
            start += 1

        rows: list[dict[str, str]] = []
        i = start
        while i + 3 <= len(lines):
            name = lines[i]
            qty_line = lines[i + 1]
            val_line = lines[i + 2]
            # lines[i + 3] is PnL — not needed for import

            # Validate: name should start with a letter, qty should be a number
            if not name or not name[0].isalpha() or not _QUANTITY_RE.match(qty_line):
                break

            # Extract currency from the position name if mentioned,
            # otherwise fall back to the value's currency symbol.
            # TR positions often include the fund currency, e.g.
            # "Core S&P 500 USD (Acc)", "Physical Swiss Gold USD"
            currency = ""
            for code in ("USD", "EUR", "GBP", "CHF", "JPY", "CAD", "AUD"):
                if f" {code}" in name:
                    currency = code
                    break
            if not currency:
                if "€" in val_line:
                    currency = "EUR"
                elif "$" in val_line:
                    currency = "USD"
                elif "£" in val_line:
                    currency = "GBP"
                else:
                    currency = "EUR"

            # Strip currency symbol from value
            value_raw = re.sub(r"[€$£]", "", val_line).strip()

            rows.append(
                {
                    "name": name,
                    "quantity": qty_line,
                    "value": value_raw,
                    "currency": currency,
                }
            )
            i += 4  # next position block

        if not rows:
            return pl.DataFrame(
                schema={
                    "name": pl.Utf8,
                    "quantity": pl.Utf8,
                    "value": pl.Utf8,
                    "currency": pl.Utf8,
                }
            )

        return pl.DataFrame(
            rows,
            schema={
                "name": pl.Utf8,
                "quantity": pl.Utf8,
                "value": pl.Utf8,
                "currency": pl.Utf8,
            },
        )

# Web Connectors

Browser-based connectors that automate login and data extraction from broker websites using Playwright. Each connector corresponds to a specific broker.

## Files

| File | Broker |
|---|---|
| `base.py` | Shared browser lifecycle base class (`PlaywrightSiteConnector`) |
| `degiro.py` | DeGiro broker |
| `revolut.py` | Revolut |
| `trade_republic.py` | Trade Republic |

All connectors are collected in `__init__.py` as `SITE_CONNECTORS` — the list consumed by the DI container and `WebConnectorService`.

---

## `base.py` — `PlaywrightSiteConnector`

Implements the `SiteConnector` domain interface. Provides shared browser lifecycle for all broker connectors so they only need to implement `_execute()`.

### How it works

Playwright is async-only. Because the Reflex frontend already runs in the main asyncio event loop, the browser runs in a **dedicated thread** with its own event loop (`ThreadPoolExecutor(1)` + `asyncio.run()`).

### Public API

- **`fetch_data(credentials, on_status, on_user_input, **options)`** — Launches the browser in a separate thread, calls `_execute()`, and returns the resulting DataFrame. Passes `headless` from `options` to the browser launch.

### Protected helpers (for subclasses)

- **`_launch_and_execute(credentials, on_status, on_user_input, headless)`** — *(async)* Launches a Chromium browser with stealth settings (via `playwright-stealth` to minimize bot-detection fingerprint), opens a new page, calls `_execute()`, and closes the browser.

- **`_execute(page, credentials, on_status, on_user_input)`** — *(abstract, async)* Broker-specific implementation. Receives a ready-to-use Playwright `Page`, performs login and data extraction, and returns a Polars DataFrame.

- **`human_delay(min?, max?)`** — *(async)* Sleeps for a random duration between `MIN_ACTION_DELAY` (0.5s) and `MAX_ACTION_DELAY` (2.0s) to simulate human pacing between actions.

- **`human_type(page, selector, text)`** — *(async)* Focuses a field and types text character-by-character with random per-character delays (`30–120ms`) to avoid triggering keystroke rate detection.

- **`download_file(page, trigger_fn, suffix)`** — *(async)* Waits for a download event triggered by `trigger_fn`, saves it to a temp file with the given suffix, and returns the `Path`.

---

## `degiro.py` — DeGiro Connector

Logs in to DeGiro using username and password, downloads the positions export, and parses it into a DataFrame.

**Profile:**
- `import_mode`: `"positions"`
- `credential_fields`: username, password

---

## `revolut.py` — Revolut Connector

Logs in to Revolut, scrapes the portfolio holdings page, and parses the table into a DataFrame. May require OTP input via `on_user_input`.

**Profile:**
- `import_mode`: `"positions"`
- `needs_matching`: `True` (Revolut uses display names, not tickers)
- `credential_fields`: phone number, OTP (requested interactively)

---

## `trade_republic.py` — Trade Republic Connector

Logs in to Trade Republic via phone number and PIN, navigates to the portfolio view, and extracts positions with their current values. Handles EUR-denominated positions directly.

**Profile:**
- `import_mode`: `"positions"`
- `credential_fields`: phone number, PIN

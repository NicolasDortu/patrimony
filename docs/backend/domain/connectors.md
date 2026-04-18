# Connector Services

These services implement the data import pipeline — both file-based (CSV/Excel) and browser-based (web connectors). They are part of the domain layer: no HTTP frameworks, no database drivers.

## Files

| File | Responsibility |
|---|---|
| `helpers.py` | Shared data classes, constants, and parsing/hashing utilities |
| `ticker_resolution.py` | ISIN/ticker resolution cascade (cache → reference → yfinance) |
| `import_service.py` | Core file import pipeline (mapping, validation, dedup, insertion) |
| `web_connector_service.py` | Orchestrates browser-based connector plugins end-to-end |

---

## `helpers.py`

Stateless utilities and type definitions shared across the import pipeline.

### Constants

- **`ISIN_RE`** — Compiled regex matching the ISIN format: 2-letter country code + 9 alphanumeric chars + 1 digit.
- **`REQUIRED_POSITION_FIELDS`** — Set of column names the user must map for a positions import: `{ticker, quantity}`.
- **`OPTIONAL_POSITION_FIELDS`** — Optional mappable fields: `{price, fees, date, asset_type, currency, name}`.
- **`REQUIRED_CASH_FIELDS`** — Required for cash import: `{account_number, amount, title}`.
- **`OPTIONAL_CASH_FIELDS`** — Optional cash field: `{operation_date}`.

### Data classes

- **`ResolvedTicker`** — Result of resolving a raw value to a ticker. Has `ticker` (or `None`), `asset_type`, and `source` (`"ticker_info"`, `"reference"`, `"yfinance"`, or `None`).
- **`ImportResult`** — Summary of a batch import: `success`, `imported`, `skipped`, `errors`.

### Parsing functions

- **`parse_date(value)`** — Tries a set of common date format strings against the input. Raises `DateParsingError` if none match.
- **`to_str(value)`** — Safely converts any value to string, treating `None` as `""`.
- **`normalize_number(value)`** — Handles European-style number formats (e.g. `"1.234,56"` → `"1234.56"`). Correctly identifies whether commas or dots are the decimal separator by checking which appears last.
- **`normalize_date(val)`** — Converts a date string or `datetime` to an ISO `YYYY-MM-DD` string for use in hash computation.

### Hashing functions

Used for deduplication: a row is considered a duplicate if its hash was previously imported.

- **`position_hash(row, source)`** — SHA-256 of `"source|ticker|price|quantity|fees|date"`. Normalizes numbers and dates before hashing so format differences don't create false uniqueness.
- **`cash_hash(row, source)`** — SHA-256 of `"source|account_number|amount|title|date"`.

---

## `ticker_resolution.py`

Handles ISIN-to-ticker resolution and asset type lookup through a layered cascade. All functions are module-level (stateless).

### `resolve_ticker_aliases(raw_values, info_repo, reference_repo, market_data)`

Resolves a list of raw ticker column values (which may be ISINs, ticker symbols, or names) to canonical tickers.

**4-step cascade per value:**
1. **Batch ISIN lookup** in `ticker_info` table — fastest, no API call needed.
2. **Reference table exact match** — checks if the value is already a valid ticker.
3. **yfinance ISIN resolution** — for ISIN-shaped values not found in step 1, calls `market_data.resolve_ticker_info()` and caches the result.
4. **Unresolved** — anything remaining gets `ResolvedTicker(ticker=None)`, requiring manual user matching.

Returns `dict[raw_value, ResolvedTicker]`.

---

### `save_ticker_info(info_repo, ticker, isin, source)`

Persists a manual ticker → info mapping to `ticker_info` table for reuse in future imports.

---

### `resolve_asset_types(tickers, info_repo, reference_repo, market_data)`

Looks up the asset type for each ticker. Checks `ticker_info`, then `tickers_reference`, and finally the yfinance API as a last resort. Returns `dict[ticker, asset_type | None]`.

---

## `import_service.py` — `FileConnectorService`

The main file import domain service. Handles the full pipeline from raw DataFrame to database records.

**Dependencies:** `SecuritiesRepository`, `CashRepository`, `ReferenceRepository`, `ImportHashRepository?`, `TickerInfoRepository?`, `MarketDataProvider?`

### Ticker resolution delegation

- **`resolve_ticker_aliases(raw_values)`** — Delegates to `ticker_resolution.resolve_ticker_aliases()`.
- **`save_ticker_alias(alias, ticker, alias_type)`** — Persists a manual alias mapping via `ticker_resolution.save_ticker_info()`.
- **`resolve_asset_types(tickers)`** — Delegates to `ticker_resolution.resolve_asset_types()`.
- **`find_ticker_by_name(name)`** — Looks up a `TickerInfo` record by human-readable name.

### Cash row detection

- **`detect_cash_rows(df, column_mapping)`** — Scans a positions DataFrame for rows that are actually cash entries (identified by a blank ticker field or a name containing `"CASH"`). Extracts them as `[{amount, currency, raw_name}]` and returns the remainder as a clean positions DataFrame. This handles brokers (e.g. Revolut) that mix cash balances and positions in the same export file.

### Position import

- **`import_positions(df, column_mapping, entry_type, asset_type_overrides, source)`** — Core positions import method:
  1. Validates that all required columns are mapped (raises `MissingMappingError` otherwise).
  2. Applies `column_mapping` to rename source columns to target field names.
  3. Computes a SHA-256 hash for every row and skips already-imported hashes.
  4. For each new row: parses date, normalizes numbers, resolves asset type, and calls `securities_repo.add_position()`.
  5. Collects new hashes and batch-stores them via `hash_repo.add_hashes()`.
  6. Returns an `ImportResult` with counts.

### Cash import

- **`import_cash_operations(rows, column_mapping, entry_type, source)`** — Imports a list of pre-extracted cash operation rows. Applies deduplication, validates required fields, and calls `cash_repo.add_operation_balance()` for each new row.

---

## `web_connector_service.py` — `WebConnectorService`

Orchestrates the full browser-based import pipeline.

**Dependencies:** `list[SiteConnector]`, `FileConnectorService`

The service maintains a dict of registered `SiteConnector` plugins keyed by `site_id`.

- **`list_profiles()`** — Returns all available connector profiles (one per registered site connector).

- **`get_profile(site_id)`** — Returns the `ConnectorProfile` for a specific connector, or `None`.

- **`run_connector(site_id, credentials, on_status, on_user_input, headless)`** — Executes the full pipeline:
  1. Resolves the site connector by ID (raises `ConnectorNotFoundError` if not found).
  2. Calls `site.fetch_data()` to scrape data from the broker. Propagates status messages to the `on_status` callback.
  3. Re-reads the profile after fetch (some connectors update dynamic state during scraping, e.g. Revolut discovering account names).
  4. Renames DataFrame columns to positional names (`col_0`, `col_1`, …) so the profile's column mapping is language-independent.
  5. If `profile.needs_matching` is `True`, returns the raw rows to the frontend for user-assisted ticker matching instead of importing directly.
  6. Otherwise, imports positions and/or cash via `FileConnectorService`.
  7. Returns a `WebConnectorResult`.

- **`import_matched_positions(matched)`** — Called after the user manually matches tickers. Takes a list of position dicts and imports them directly.

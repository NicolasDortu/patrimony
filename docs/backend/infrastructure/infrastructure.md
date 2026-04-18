# Infrastructure Layer

The infrastructure layer provides concrete implementations of all abstract domain interfaces and repositories. It handles the raw concerns: database connections, SQL queries, external API calls, browser automation, and file parsing.

**Rule:** nothing in this layer is imported by the domain. The domain only depends on its own ABCs (`interfaces.py`, `repositories/`). The DI container in `application/di_container.py` wires the concrete implementations into the domain at runtime.

## Structure

```
infrastructure/
├── database/
│   ├── connection.py     # DuckDB connection management + schema init
│   ├── ddl.py            # All CREATE TABLE statements
│   └── data/
│       └── tickers.csv   # Bulk-loaded reference data (~100k+ securities)
├── integrations/
│   ├── file_connector.py        # CSV/Excel file parser (ExcelCsvConnector)
│   ├── market_data_provider.py  # Yahoo Finance API (YahooFinanceProvider)
│   └── web_connector/
│       ├── base.py         # Shared Playwright browser automation base class
│       ├── degiro.py        # DeGiro broker connector
│       ├── revolut.py       # Revolut broker connector
│       └── trade_republic.py # Trade Republic broker connector
└── repositories/
    ├── cash_repository.py
    ├── connector_history_repository.py
    ├── credential_repository.py
    ├── currency_repository.py
    ├── dividend_repository.py
    ├── event_log_repository.py
    ├── import_hash_repository.py
    ├── price_repository.py
    ├── property_repository.py
    ├── reference_repository.py
    ├── securities_repository.py
    └── ticker_info_repository.py
```

---

## `database/`

See the [database README](database.md) for schema details.

### `connection.py` — `DatabaseConnection`

Manages the single DuckDB connection for the application.

- **`__init__(db_path?)`** — Opens (or creates) the DuckDB file. If no path is given, uses a platform-appropriate app data directory. Runs `init_db()` and registers `close_connection()` with `atexit`.
- **`init_db()`** — Executes every DDL command from `ddl.DDL_COMMANDS` in order. Then calls `_load_reference_data()`.
- **`_load_reference_data()`** — Checks if `tickers_reference` is empty. If so, reads `data/tickers.csv` and bulk-inserts all rows. This populates the ticker search/autocomplete table on first launch.
- **`execute(query, params?)`** — Thin wrapper around `conn.execute()`. Raises `DatabaseError` on failure, with the query and original exception attached for debugging.
- **`transaction()`** — Context manager for explicit transactions. Commits on success, rolls back on exception.
- **`close_connection()`** — Closes the DuckDB connection. Called automatically on process exit.

### `ddl.py`

Contains every `CREATE TABLE` / `CREATE SEQUENCE` / `CREATE VIEW` / `CREATE INDEX` SQL statement as module-level string constants. They are collected into `DDL_COMMANDS` (a list) and executed in order by `DatabaseConnection.init_db()`.

**Table groups:**
1. **Core portfolio** — `positions`, `positions_closed`, `dividends`
2. **Cash management** — `cash`, `balance_operations`
3. **Market data & pricing** — `price_cache`, `price_history`, `intraday_prices`, `ticker_currency`, `exchange_rate_cache`
4. **Reference data** — `tickers_reference` (static), `ticker_info` (enriched cache)
5. **Properties** — `properties`
6. **Connector infrastructure** — `connector_master_key`, `connector_credentials`, `connector_history`, `import_hashes`
7. **System** — `event_log`
8. **Views & indexes** — aggregation views and lookup indexes

---

## `integrations/`

### `file_connector.py` — `ExcelCsvConnector`

Implements `FileConnector` (domain interface).

- **`read_file(file_bytes, filename, delimiter)`** — Detects file format from the extension. Reads `.csv` files with Polars using the specified delimiter. Reads `.xlsx`/`.xls` files with `pl.read_excel`. All columns are read as strings (`infer_schema=False`) so the caller has full control over type coercion. Raises `ValueError` for unsupported formats.

---

### `market_data_provider.py` — `YahooFinanceProvider`

Implements `MarketDataProvider` (domain interface) using the `yfinance` library. The only concrete market data source currently in the application.

**Rate limiting:** all public methods go through `_throttle()`, which enforces a minimum interval of `0.55s` between consecutive API calls using a threading lock. This prevents Yahoo Finance from rate-limiting the application.

- **`_throttle()`** — Acquires a lock, sleeps if needed to reach the minimum interval, then updates `_last_call`. Also sets `_provider_was_called = True` (used by the base class telemetry flag).
- **`_parse_history_df(data)`** — Static method. Converts a yfinance pandas DataFrame (with `Date` or `Datetime` index) to a Polars DataFrame with columns `(date, close_price)`.
- **`get_current_price(ticker)`** — Fetches the last closing price using `period="1d"`. Returns `None` on failure.
- **`get_price_history(ticker, start_date, end_date, interval, *, period)`** — Fetches historical OHLCV data. If `period` is provided, it overrides the date range. Parses the result with `_parse_history_df`. Returns an empty `(date, close_price)` DataFrame on failure.
- **`get_ticker_currency(ticker)`** — Reads `info["currency"]` from the yfinance ticker info dict. Returns `None` on failure.
- **`get_exchange_rate(from_currency, to_currency)`** — Looks up the rate using a composite yfinance ticker like `"EURUSD=X"`. Returns `None` on failure.
- **`get_dividend_history(ticker, start_date, end_date)`** — Fetches the dividend history and returns a `(date, amount_per_share)` DataFrame. Returns an empty DataFrame on failure.
- **`resolve_ticker_info(identifier)`** — Takes an ISIN or ticker, calls `yf.Ticker(identifier).info`, maps `quoteType` to domain `AssetType` via `_QUOTE_TYPE_MAP`, and returns a `TickerInfo` entity. Returns `None` on failure.

---

### `web_connector/`

Browser-based connectors that automate login and data extraction from broker websites using Playwright.

#### `base.py` — `PlaywrightSiteConnector`

Implements the `SiteConnector` domain interface. Provides shared browser lifecycle management for all broker connectors.

- **`fetch_data(credentials, on_status, on_user_input, **options)`** — Entry point. Runs `_launch_and_execute()` in a dedicated thread with its own asyncio event loop (required because the Reflex main thread already owns the main loop). Playwright is run asynchronously inside this thread.
- **`_launch_and_execute(credentials, on_status, on_user_input, headless)`** — *(async)* Launches a Chromium browser with stealth settings (via `playwright-stealth` to avoid bot detection), opens a page, and calls `_execute()`. Closes the browser on exit.
- **`_execute(page, credentials, on_status, on_user_input)`** — *(abstract, async)* Implemented by each broker subclass. Performs the actual login and data scraping, returning a Polars DataFrame.
- **`human_delay(min?, max?)`** — *(async)* Sleeps for a random duration between `MIN_ACTION_DELAY` and `MAX_ACTION_DELAY` seconds to mimic human behavior.
- **`human_type(page, selector, text)`** — *(async)* Types text character by character with random delays between `MIN_TYPING_DELAY` and `MAX_TYPING_DELAY` milliseconds.
- **`download_file(page, trigger_fn, suffix)`** — *(async)* Triggers a file download, saves it to a temp directory, and returns the path.

#### `degiro.py`, `revolut.py`, `trade_republic.py`

Concrete broker connectors. Each:
- Declares a `ConnectorProfile` describing its data format and credential requirements.
- Implements `_execute()` to log in, navigate, and extract position/cash data into a DataFrame.
- Returns control to `PlaywrightSiteConnector.fetch_data()` which handles cleanup.

---

## `repositories/`

All repository implementations follow the same pattern:
- Accept a `DatabaseConnection` in the constructor.
- Use `self._conn.execute(sql, params)` for queries.
- Return Polars DataFrames or Python primitives.
- Always uppercase ticker symbols before storing.

See the [domain repositories README](../domain/repositories.md) for the interface contracts.

### `cash_repository.py`

- **`CashOperationRepositoryImpl`** — Manages `balance_operations`. The `add_operation_balance()` method inserts with `balance=0`, then calls `recalculate_balances()` which recomputes running balances and ranks in a single UPDATE. The `rank` column orders operations newest-first for display.
- **`CashRepositoryImpl`** — Manages the `cash` table. Extends `CashOperationRepositoryImpl` so all operation methods are available on the same object.

### `connector_history_repository.py` — `ConnectorHistoryRepositoryImpl`

Serializes `ConnectorHistoryEntry` fields to/from JSON for dict/list columns (`column_mapping`, `errors`, `asset_type_overrides`, `new_accounts`). `get_all()` uses a `LIMIT` subquery to return only the most recent entries per source to avoid returning stale duplicates.

### `credential_repository.py` — `CredentialRepositoryImpl`

Uses Fernet symmetric encryption. The master password is never stored directly — only a PBKDF2-derived salt and a verification hash. `setup_master_password()` and `verify_master_password()` derive the Fernet key on the fly; credentials are encrypted with this key before being written to the database.

### `currency_repository.py` — `CurrencyRepositoryImpl`

- `get_exchange_rate()` enforces a 60-minute freshness window in SQL using a `CURRENT_TIMESTAMP - INTERVAL` clause, so stale rates are transparently treated as missing (triggering a fresh API call).

### `dividend_repository.py` — `DividendRepositoryImpl`

Standard CRUD on the `dividends` table. The table has a `UNIQUE(ticker, date)` constraint that prevents duplicate dividends at the DB level.

### `event_log_repository.py` — `EventLogRepositoryImpl`

Append-only log. Stores JSON-serialized payloads with a timestamp.

### `import_hash_repository.py` — `ImportHashRepositoryImpl`

Stores SHA-256 hashes in the `import_hashes` table. `existing_hashes(hashes)` does a batch `IN (...)` query to find which hashes already exist, enabling O(1) deduplication checks per import batch.

### `price_repository.py` — `PriceRepositoryImpl`

- **Current price cache** — `price_cache` table, keyed by ticker. `get_cached_prices()` filters by `last_updated` freshness.
- **Daily price history** — `price_history` table with `(ticker, date, period)` primary key. `store_price_history()` uses `INSERT OR REPLACE`.
- **Intraday prices** — `intraday_prices` table. `store_intraday_prices()` does DELETE + INSERT (full replace per ticker) rather than upsert, because intraday data for a ticker is always replaced as a complete snapshot.
- **`get_cache_timestamps(tickers)`** — Returns `dict[ticker, last_updated]` used by `PriceService` to sort tickers by staleness.
- **`get_stored_date_range(ticker, period)`** — Returns `(MIN(date), MAX(date))` for gap-filling logic in `PriceService.sync_price_history()`.

### `property_repository.py` — `PropertyRepositoryImpl`

Standard CRUD on the `properties` table. `get_total_value_by_currency()` returns `GROUP BY currency` aggregated values used by `PropertyService` for multi-currency summation.

### `reference_repository.py` — `ReferenceRepositoryImpl`

Read-only queries against `tickers_reference`. `search()` does a case-insensitive `LIKE` query on both `ticker` and `name` columns.

### `securities_repository.py` — `SecuritiesRepositoryImpl`

- `get_aggregated_positions()` runs a SQL aggregation: `SUM(quantity)` and `WAVG(price, quantity)` grouped by ticker. Includes a join on `ticker_info` to resolve `asset_type` for enrichment.
- `get_earliest_purchase_date()` returns `MIN(date)` across all positions (or for a specific ticker), used to clamp chart start dates.

### `ticker_info_repository.py` — `TickerInfoRepositoryImpl`

Caches enriched ticker metadata. `upsert()` uses `ON CONFLICT (ticker) DO UPDATE SET ... COALESCE(excluded.field, ticker_info.field)` so existing non-null values are never overwritten by nulls from a later partial resolution.

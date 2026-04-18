# Database

Contains the DuckDB connection management, schema definitions, and seed data.

## Files

| File | Description |
|---|---|
| `connection.py` | `DatabaseConnection` — opens/creates the DuckDB file, runs DDL, seeds reference data |
| `ddl.py` | All `CREATE TABLE`, `CREATE VIEW`, and `CREATE INDEX` statements |
| `data/tickers.csv` | ~100k+ securities reference data loaded on first launch |

---

## Schema Overview

### Core Portfolio

#### `positions`
Individual buy/sell entries for securities.

| Column | Type | Description |
|---|---|---|
| `id` | `INTEGER PK` | Auto-incrementing sequence |
| `ticker` | `VARCHAR` | Uppercase ticker symbol |
| `price` | `DOUBLE` | Purchase price per unit |
| `quantity` | `DOUBLE` | Number of units (default 1.0) |
| `fees` | `DOUBLE` | Transaction fees (default 0.0) |
| `entry_type` | `VARCHAR` | `MANUAL`, `WEB`, `CSV`, `EXCEL`, `API` |
| `asset_type` | `VARCHAR` | `STOCK`, `ETF`, `CRYPTO`, etc. |
| `date` | `TIMESTAMP` | Purchase date |

#### `positions_closed`
Same schema as `positions`. Stores positions that have been fully sold/closed, for historical reporting without affecting current aggregations.

#### `dividends`
| Column | Type | Description |
|---|---|---|
| `id` | `INTEGER PK` | Auto-incrementing |
| `ticker` | `VARCHAR` | Uppercase ticker |
| `amount` | `DOUBLE` | Total dividend amount received (per_share × quantity) |
| `date` | `TIMESTAMP` | Ex-dividend date |

Has a `UNIQUE(ticker, date)` constraint to prevent duplicates.

---

### Cash Management

#### `cash`
One row per bank account.

| Column | Type | Description |
|---|---|---|
| `bank` | `VARCHAR` | Bank name |
| `account_number` | `VARCHAR PK` | Unique account identifier |
| `currency` | `VARCHAR` | Native currency (default `'EUR'`) |
| `last_updated` | `TIMESTAMP` | Last metadata update |
| `entry_type` | `VARCHAR` | How the account was created |

#### `balance_operations`
Individual credit/debit operations on a cash account.

| Column | Type | Description |
|---|---|---|
| `id` | `INTEGER PK` | Auto-incrementing |
| `account_number` | `VARCHAR FK` | References `cash(account_number)` |
| `rank` | `INTEGER` | Ordering index (recomputed on every insert/delete) |
| `amount` | `DOUBLE` | Credit (+) or debit (-) |
| `balance` | `DOUBLE` | Cumulative running balance after this operation |
| `title` | `VARCHAR` | Operation description |
| `category` | `VARCHAR` | User-defined category (default `'Uncategorized'`) |
| `operation_date` | `TIMESTAMP` | Date of the operation |
| `entry_type` | `VARCHAR` | How the operation was created |

> The `balance` and `rank` columns are always recomputed by `recalculate_balances()` after any insert/delete — they are derived values, not user inputs.

---

### Market Data & Pricing

#### `price_cache`
Latest known price per ticker for fast live-price lookup.

| Column | Type | Description |
|---|---|---|
| `ticker` | `VARCHAR PK` | Uppercase ticker |
| `current_price` | `DOUBLE` | Last fetched price |
| `last_updated` | `TIMESTAMP` | When it was fetched |

#### `price_history`
Daily (or weekly) closing prices for chart rendering.

| Column | Type | Description |
|---|---|---|
| `ticker` | `VARCHAR` | Uppercase ticker |
| `date` | `TIMESTAMP` | Close date |
| `close_price` | `DOUBLE` | Closing price |
| `period` | `VARCHAR` | Resolution granularity (e.g. `"1d"`, `"1wk"`) |
| `last_updated` | `TIMESTAMP` | When this row was fetched |

Primary key: `(ticker, date, period)`

#### `intraday_prices`
5-minute intraday prices for the 1D chart view. Always replaced as a complete snapshot per ticker.

| Column | Type | Description |
|---|---|---|
| `ticker` | `VARCHAR` | Uppercase ticker |
| `date` | `TIMESTAMP` | Timestamp of the 5-minute bar |
| `close_price` | `DOUBLE` | Close price of the bar |
| `last_updated` | `TIMESTAMP` | When this snapshot was fetched |

Primary key: `(ticker, date)`

#### `ticker_currency`
Caches the native trading currency of a ticker to avoid repeated API calls.

| Column | Type | Description |
|---|---|---|
| `ticker` | `VARCHAR PK` | Uppercase ticker |
| `currency` | `VARCHAR` | Native currency (e.g. `"USD"`) |
| `last_updated` | `TIMESTAMP` | Cache timestamp |

#### `exchange_rate_cache`
Caches FX rates with a 60-minute TTL (enforced in SQL by the repository).

| Column | Type | Description |
|---|---|---|
| `from_currency` | `VARCHAR` | Source currency |
| `to_currency` | `VARCHAR` | Target currency |
| `rate` | `DOUBLE` | Conversion rate |
| `last_updated` | `TIMESTAMP` | Cache timestamp |

Primary key: `(from_currency, to_currency)`

---

### Reference Data

#### `tickers_reference`
Static bulk-loaded reference table for ticker search and autocomplete. Loaded once from `data/tickers.csv` at startup.

| Column | Type | Description |
|---|---|---|
| `ticker` | `VARCHAR PK` | Ticker symbol |
| `name` | `VARCHAR` | Human-readable name |
| `asset_type` | `VARCHAR` | Asset classification |
| `exchange` | `VARCHAR` | Exchange code |
| `category` | `VARCHAR` | Sub-category |
| `country` | `VARCHAR` | Country of origin |

#### `ticker_info`
Enriched ticker metadata resolved from yfinance or entered manually. Acts as a persistent cache for ISIN→ticker resolution.

| Column | Type | Description |
|---|---|---|
| `ticker` | `VARCHAR PK` | Uppercase ticker symbol |
| `isin` | `VARCHAR` | ISIN code |
| `name` | `VARCHAR` | Human-readable name |
| `asset_type` | `VARCHAR` | Resolved domain asset type |
| `exchange` | `VARCHAR` | Exchange code |
| `currency` | `VARCHAR` | Native currency |
| `source` | `VARCHAR` | Where the info came from (`"yfinance"`, `"manual"`, etc.) |
| `last_updated` | `TIMESTAMP` | Resolution timestamp |

---

### Properties

#### `properties`
Physical assets (real estate, collectibles, etc.).

| Column | Type | Description |
|---|---|---|
| `id` | `INTEGER PK` | Auto-incrementing |
| `name` | `VARCHAR` | Property name |
| `description` | `VARCHAR` | Optional description |
| `value` | `DOUBLE` | Current estimated value |
| `purchase_date` | `TIMESTAMP` | Date acquired |
| `category` | `VARCHAR` | User-defined category (default `'Other'`) |
| `currency` | `VARCHAR` | Value currency |
| `entry_type` | `VARCHAR` | How it was created |

---

### Connector Infrastructure

#### `connector_master_key`
Stores the PBKDF2-derived salt and verification hash for the master password. Never stores the password itself. Single-row table (id=1).

#### `connector_credentials`
Encrypted credential blobs (Fernet), one row per connector profile.

#### `connector_history`
Full audit log of every import run. Dict/list fields (`column_mapping`, `errors`, etc.) are stored as JSON strings.

#### `import_hashes`
SHA-256 hashes of previously imported rows, used for deduplication. A row with a matching hash is silently skipped on re-import.

---

### System

#### `event_log`
Append-only application event log. Stores `event_type`, a JSON `payload`, and a `created_at` timestamp.

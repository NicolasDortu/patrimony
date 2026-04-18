# Domain Repositories

Abstract repository interfaces (ABCs) that the domain services depend on. **No SQL or infrastructure code lives here** — only method contracts. Concrete implementations are in `infrastructure/repositories/`.

The separation means you can swap the database layer (e.g. replace DuckDB with PostgreSQL) without touching any domain logic.

## Files

| File | What it covers |
|---|---|
| `asset_repositories.py` | Financial assets: securities, cash, prices, currencies, dividends, properties |
| `support_repositories.py` | Operational concerns: credentials, import history, hashes, event log, reference data, ticker info |

---

## `asset_repositories.py`

### `BaseRepository`
Mixin used by all repositories. Provides:
- **`delete(id)`** — Delete a record by ID.

---

### `SecuritiesRepository`
Manages individual position records (buy/sell entries).

- **`add_position(ticker, price, quantity, entry_type, asset_type, date, fees)`** — Insert a new position row. Returns the new row ID.
- **`update_position(id, ticker, price, quantity, entry_type, asset_type, date, fees)`** — Update all fields of an existing position.
- **`get_by_ticker(ticker)`** — Return a DataFrame of all individual entries for one ticker.
- **`get_all()`** — Return every position row in the database.
- **`get_aggregated_positions(ticker?)`** — Return aggregated view (group by ticker): `avg_price`, `total_quantity`, `asset_type`. Optionally filter to a single ticker.
- **`get_earliest_purchase_date(ticker?)`** — Return the oldest purchase date across all positions (or for a specific ticker). Used to clamp chart start dates.

---

### `CashOperationRepository`
Manages individual balance operations (deposits, withdrawals) on cash accounts.

- **`add_operation_balance(account_number, amount, title, operation_date, entry_type, category)`** — Insert a new operation and recalculate the running balance for that account. Returns operation ID.
- **`recalculate_balances(account_number)`** — Recompute the cumulative `balance` and `rank` columns for all operations on an account (called after every insert or delete).
- **`get_operations_by_account(account_number)`** — Return all operations for one account, ordered newest first.
- **`get_all_operations()`** — Return all operations across all accounts.
- **`get_cash_balance_history()`** — Return one row per operation with `(account_number, balance, operation_date)`, used to build the cash balance timeline for charts.
- **`delete_operation(id)`** — Delete an operation and recalculate balances.
- **`update_operation(id, ...)`** — Update an operation's fields and recalculate balances.

---

### `CashRepository`
Manages cash account records (the accounts themselves, not their operations).

Extends `CashOperationRepository`, so it also exposes all operation methods.

- **`add_cash(bank, account_number, currency, last_updated)`** — Create a new cash account record. Returns account ID.
- **`update_cash(bank, account_number, currency, last_updated)`** — Update an existing account's metadata.
- **`get_all()`** — Return all cash accounts with their current balance.
- **`delete(id)`** — Delete a cash account and all its operations.

---

### `PriceRepository`
Manages all price data: current price cache, daily history, intraday 5-minute data.

- **`get_cached_prices(tickers, max_age_minutes)`** — Return the latest cached current prices for a list of tickers, filtered by freshness. Returns `dict[ticker, price]`.
- **`cache_price(ticker, price, timestamp)`** — Write or overwrite the current price for a ticker in the cache table.
- **`get_cache_timestamps(tickers)`** — Return `dict[ticker, last_updated]` for sorting tickers by staleness.
- **`get_stored_date_range(ticker, period)`** — Return `(min_date, max_date)` of stored rows in `price_history` for a ticker. Returns `(None, None)` if no rows exist.
- **`get_price_history(tickers, start, end)`** — Return a DataFrame of `(ticker, date, close_price)` rows within the date window.
- **`store_price_history(ticker, df, period)`** — Upsert a price history DataFrame into the `price_history` table.
- **`store_intraday_prices(ticker, df)`** — Replace all stored intraday rows for a ticker (DELETE then INSERT).
- **`get_intraday_prices(tickers)`** — Return all stored intraday rows for a list of tickers as a DataFrame.
- **`get_intraday_last_updated(ticker)`** — Return the most recent `last_updated` timestamp for a ticker's intraday data.
- **`get_latest_intraday_prices(tickers, max_age_minutes)`** — Return `dict[ticker, latest_close_price]` only if the intraday data is fresh enough.

---

### `CurrencyRepository`
Caches ticker currencies and exchange rates to avoid repeated API calls.

- **`get_ticker_currency(ticker)`** — Return the cached native currency for a ticker, or `None`.
- **`set_ticker_currency(ticker, currency)`** — Store or update a ticker's native currency.
- **`get_exchange_rate(from_currency, to_currency)`** — Return the cached FX rate, or `None` if not cached.
- **`set_exchange_rate(from_currency, to_currency, rate)`** — Store or update an FX rate.

---

### `DividendRepository`
Manages dividend payment records.

- **`add_dividend(ticker, amount, date)`** — Insert a new dividend record. Returns the new row ID.
- **`get_by_ticker(ticker)`** — Return all dividends for a ticker.
- **`get_by_id(id)`** — Return a single dividend record.
- **`get_all()`** — Return all dividend records, newest first.
- **`get_total_amount()`** — Return the sum of all dividend amounts.
- **`delete(id)`** — Delete a dividend record.
- **`update_dividend(id, ticker, amount, date)`** — Update a dividend record.

---

### `PropertyRepository`
Manages physical property (real estate, collectibles, etc.) records.

- **`add_property(name, value, purchase_date, description, category, currency, entry_type)`** — Insert a new property. Returns row ID.
- **`update_property(id, name, value, purchase_date, description, category, currency)`** — Update a property's fields.
- **`get_all()`** — Return all properties as a DataFrame.
- **`get_total_value_by_currency()`** — Return a grouped DataFrame with `(currency, total_value)` for currency conversion in `PropertyService`.
- **`delete(id)`** — Delete a property.

---

## `support_repositories.py`

### `CredentialRepository`
Stores broker credentials encrypted with a user-supplied master password using Fernet symmetric encryption.

- **`has_master_password()`** — Returns `True` if a master password has been configured in the database.
- **`setup_master_password(password)`** — Derives an encryption key from the password, stores a salt and verification hash. Returns the Fernet key bytes.
- **`verify_master_password(password)`** — Checks the password against the stored hash. Returns the Fernet key if correct, `None` if wrong.
- **`store_credentials(profile_id, credentials, fernet_key)`** — Encrypts the credentials dict and writes it for the given profile.
- **`get_credentials(profile_id, fernet_key)`** — Decrypts and returns credentials for a profile, or `None` if not found.
- **`delete_credentials(profile_id)`** — Remove stored credentials for a profile.
- **`reset_master_password()`** — Wipe the master password and all stored credentials from the database.
- **`list_stored_profiles()`** — Return the list of profile IDs that have stored credentials.

---

### `ConnectorHistoryRepository`
Persists a record of every import run (file or web connector).

- **`add_entry(entry)`** — Persist a `ConnectorHistoryEntry` and return the new row ID.
- **`get_all()`** — Return all history entries as a list of `ConnectorHistoryEntry`, newest first.
- **`get_latest_by_source(connector_type, source_identifier)`** — Return the most recent entry for a given connector type and source, or `None`. Used to pre-fill import settings for repeat imports.

---

### `ImportHashRepository`
Tracks SHA-256 hashes of imported rows to prevent duplicate imports.

- **`has_hash(hash_value)`** — Returns `True` if this hash was already imported.
- **`add_hash(hash_value)`** — Store a hash, marking the corresponding row as imported.
- **`add_hashes(hashes)`** — Batch-insert multiple hashes at once.

---

### `EventLogRepository`
Append-only audit trail of application events.

- **`log(event_type, payload)`** — Write an event with a timestamp and JSON payload.
- **`get_recent(n)`** — Return the `n` most recent events.

---

### `ReferenceRepository`
Provides read access to the static `tickers_reference` table (bulk-loaded from `tickers.csv`). Used for ticker search and autocomplete.

- **`search(query, limit)`** — Full-text search on ticker symbol and name. Returns a list of matching dicts.
- **`get_by_ticker(ticker)`** — Exact lookup by ticker symbol.

---

### `TickerInfoRepository`
Stores enriched ticker metadata resolved from yfinance or entered manually. Used as a cache to avoid repeated API calls on future imports.

- **`get_by_ticker(ticker)`** — Return `TickerInfo` for an exact ticker symbol, or `None`.
- **`get_by_isin(isin)`** — Return `TickerInfo` for an ISIN, or `None`.
- **`get_by_name(name)`** — Case-insensitive lookup by full name, or `None`.
- **`get_batch_by_isin(isins)`** — Batch lookup of multiple ISINs. Returns `dict[isin, TickerInfo]`.
- **`upsert(info)`** — Insert or update a `TickerInfo` record. Uses `COALESCE` so existing non-null fields are preserved.

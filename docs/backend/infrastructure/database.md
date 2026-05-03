# Database

The database is an embedded **DuckDB** file managed by
`infrastructure/database/connection.py`. There is exactly one
`DatabaseConnection` instance per process (provided as a Singleton from the DI
container), shared by every repository.

## Lifecycle

```python
class DatabaseConnection:
    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or _get_db_path()
        self.conn = duckdb.connect(str(self.db_path))
        self.init_db()                      # CREATE TABLE IF NOT EXISTS …
        atexit.register(self.close_connection)
```

- `_get_db_path()` resolves to `%LOCALAPPDATA%/patrimony/patrimony.duckdb`
  on Windows and `~/.local/share/patrimony/patrimony.duckdb` elsewhere.
- `init_db()` runs every statement in `ddl.DDL_COMMANDS` then calls
  `_load_reference_data()` which seeds `tickers_reference` from
  `database/data/tickers.csv` if the table is empty.
- Tests can pass an explicit `db_path` (e.g. `":memory:"` or a tmp path) to
  get an isolated database.

## API

```python
execute(query, parameters=None) -> duckdb.DuckDBPyConnection
executemany(query, parameters: list[tuple]) -> None
fetchone(query, parameters=None) -> tuple | None
fetchall(query, parameters=None) -> list[tuple]
fetchdf(query, parameters=None) -> pl.DataFrame
register_df(name, df: pl.DataFrame) -> None
transaction() -> AbstractContextManager        # BEGIN / COMMIT / ROLLBACK
close_connection() -> None
```

`DatabaseError` wraps any underlying `duckdb.Error` and carries the failed
query for easier debugging.

## Schema

All DDL is in `database/ddl.py` as a list of `CREATE TABLE IF NOT EXISTS`
strings. Tables are grouped below by purpose; **bold** columns are part of the
primary key.

### Securities

| Table | Columns |
|---|---|
| `positions` | **id**, ticker, price, quantity, fees, entry_type, asset_type, date |
| `positions_closed` | mirrors `positions` for sold lots |
| `dividends` | **id**, ticker, amount, date — `UNIQUE(ticker, date)` |

### Cash

| Table | Columns |
|---|---|
| `cash` | **account_number**, bank, currency, last_updated, entry_type |
| `balance_operations` | **id**, account_number `→ cash`, rank, amount, balance, title, category, operation_date, entry_type |

`balance_operations.balance` is the running balance after the operation. It is
recomputed in-place by `recalculate_balances(account_number)` after any insert
or update so the read path stays trivial.

### Market data cache

| Table | Columns |
|---|---|
| `price_cache` | **ticker**, current_price, last_updated |
| `price_history` | **ticker**, **date**, **period**, close_price |
| `intraday_prices` | **ticker**, **date**, close_price, last_updated |
| `ticker_currency` | **ticker**, currency, last_updated |
| `exchange_rate_cache` | **from_currency**, **to_currency**, rate, last_updated |

### Reference

| Table | Columns |
|---|---|
| `tickers_reference` | **ticker**, name, asset_type, exchange, category, country |
| `ticker_info` | **ticker**, isin, name, asset_type, exchange, currency, source, last_updated |

`tickers_reference` is bulk-loaded once from a bundled CSV. `ticker_info` is
populated incrementally by `_enrich_ticker` on every position write.

### Properties

| Table | Columns |
|---|---|
| `properties` | **id**, name, description, value, purchase_date, category, currency, entry_type |

### Connector infrastructure

| Table | Columns |
|---|---|
| `connector_master_key` | **id**, salt, verification_hash |
| `connector_credentials` | **profile_id**, encrypted_data |
| `connector_history` | **id**, connector_type, profile_id, source_name, source_path, import_mode, column_mapping, delimiter, asset_type_overrides, new_cash_accounts, imported, skipped, errors, status, created_at |
| `import_hashes` | **hash**, import_type, created_at |

The credential vault uses Fernet symmetric encryption with a key derived from
the user's master password via PBKDF2-HMAC-SHA256 with the salt stored in
`connector_master_key`. The verification hash lets us check the password
without decrypting any payload.

### System

| Table | Columns |
|---|---|
| `event_log` | **id**, timestamp, event_type, details |

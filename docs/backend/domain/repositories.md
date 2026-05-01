# Repository contracts

Abstract repository classes live in `backend/domain/repositories/`. They define
storage contracts in domain terms and never reference DuckDB or any other
infrastructure detail. Implementations live in
`backend/infrastructure/repositories/` and are wired into the DI container.

All read-side methods return `polars.DataFrame` (or `dict` for keyed lookups);
mutation methods return `None` or the new row id.

## `asset_repositories.py`

### `BaseRepository`
```python
get_all() -> pl.DataFrame
get_by_id(id: int) -> pl.DataFrame
delete(id: int) -> None
```

### `SecuritiesRepository(BaseRepository)`
```python
add_position(ticker, price, quantity, entry_type, asset_type, date, fees=0.0) -> int
update_position(id, ticker, price, quantity, entry_type, asset_type, date, fees=0.0)
get_by_ticker(ticker: str) -> pl.DataFrame
get_aggregated_positions(ticker: str | None = None) -> pl.DataFrame
get_earliest_purchase_date(ticker: str | None = None) -> date | None
```
Aggregated rows include `total_quantity`, `total_invested`, `avg_price`,
`total_fees`, `currency`, `asset_type`, optionally `name`/`isin` after
ticker-info enrichment.

### `CashOperationRepository`
```python
add_operation_balance(account_number, amount, title, operation_date,
                     entry_type, category="Uncategorized")
get_operations_by_account(account_number) -> pl.DataFrame
get_all_operations() -> pl.DataFrame
update_operation_by_id(id, amount, title, operation_date, entry_type, category)
delete_operation_by_id(id)
get_cash_balance_history() -> pl.DataFrame  # for the timeline chart
recalculate_balances(account_number)        # rolls running balance after edits
```

### `CashRepository(BaseRepository, CashOperationRepository)`
```python
add_cash(bank, account_number, currency, last_updated, entry_type)
update_cash(bank, account_number, currency, last_updated)
rename_account(old_account, new_account)
get_balance(account_number) -> float
get_total_balance() -> pl.DataFrame   # grouped by currency
```

### `PriceRepository`
```python
cache_price(ticker, price, timestamp)
store_price_history(ticker, df, period)
get_stored_date_range(ticker, period) -> tuple[date, date] | None
get_cache_timestamps(tickers) -> dict[str, datetime]
get_cached_prices(tickers, max_age_minutes) -> dict[str, float]
get_last_known_prices(tickers) -> dict[str, float]
store_intraday_prices(ticker, df)
get_intraday_prices(tickers) -> pl.DataFrame
get_latest_intraday_prices(tickers, max_age_minutes) -> dict[str, float]
```

### `CurrencyRepository`
```python
get_ticker_currency(ticker) -> str | None
set_ticker_currency(ticker, currency)
get_exchange_rate(from_currency, to_currency, max_age_minutes=...) -> float | None
set_exchange_rate(from_currency, to_currency, rate)
```

### `DividendRepository(BaseRepository)`
```python
add_dividend(ticker, amount, date)
get_by_ticker(ticker) -> pl.DataFrame
update_dividend(id, ticker, amount, date)
get_total_amount() -> float
get_totals_by_ticker() -> pl.DataFrame
```

### `PropertyRepository(BaseRepository)`
```python
add_property(name, description, value, purchase_date, category, currency, entry_type)
update_property(id, name, description, value, purchase_date, category, currency)
get_total_value_by_currency() -> pl.DataFrame
```

## `support_repositories.py`

### `CredentialRepository`
```python
has_master_password() -> bool
setup_master_password(password)
verify_master_password(password) -> bool
store_credentials(profile_id, credentials: dict)
get_credentials(profile_id) -> dict | None
delete_credentials(profile_id)
reset_master_password()
```
Backed by Fernet (symmetric encryption) with a PBKDF2-derived key and a salt
stored in `connector_master_key`.

### `ConnectorHistoryRepository`
```python
add_entry(entry: ConnectorHistoryEntry) -> int
get_all() -> list[ConnectorHistoryEntry]
delete(entry_id)
```

### `ImportHashRepository`
```python
existing_hashes(hashes: list[str]) -> set[str]
add_hashes(hashes: list[str], import_type: str)
```
Used by file/web connectors to dedupe re-imports.

### `ReferenceRepository`
```python
search(query: str, limit: int = 10) -> pl.DataFrame
```
Looks up tickers from the bundled `tickers.csv` reference list.

### `TickerInfoRepository`
```python
get_by_ticker(tickers: list[str]) -> dict[str, TickerInfo]
get_by_isin(isins: list[str]) -> dict[str, TickerInfo]
upsert(info: TickerInfo)
```
Batch-friendly: pass a list, get back a dict keyed by ticker (or isin).

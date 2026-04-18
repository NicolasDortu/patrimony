# Application Layer

The application layer sits between the domain and the frontend. Its only jobs are:

1. **Orchestrate** domain services and repositories to fulfill user-facing operations.
2. **Translate** between domain types and plain dicts/primitives that the frontend can consume.
3. **Enforce cooldowns** and other application-level policies that don't belong in the domain.

Nothing in this layer contains business rules or SQL. All logic is delegated to domain services.

## Files

| File | What it exposes |
|---|---|
| `cash_use_cases.py` | CRUD for cash accounts and balance operations |
| `connector_history_use_cases.py` | Recording and retrieving import history |
| `di_container.py` | Dependency injection container (wires everything together) |
| `dividend_use_cases.py` | Dividend CRUD and sync with cooldown |
| `file_import_use_cases.py` | File-based import (CSV/Excel) orchestration |
| `portfolio_use_cases.py` | Portfolio overview and chart data |
| `property_use_cases.py` | Physical property CRUD |
| `securities_use_cases.py` | Securities CRUD, aggregation, prices, and ticker chart |
| `web_connector_use_cases.py` | Browser-based connector orchestration |

---

## `cash_use_cases.py` — `CashUseCases`

**Dependencies:** `CashRepository`

Handles all cash account and operation management.

- **`add_cash(bank, account_number, currency, balance, last_updated)`** — Creates a new cash account. If `balance` is non-zero, also records an `"Initial balance"` operation. Returns `{"id": str}`.
- **`update_cash(bank, account_number, currency, last_updated)`** — Updates account metadata (bank name, currency). Does not touch operations.
- **`delete_cash(id)`** — Deletes a cash account and all its operations.
- **`get_all_cash()`** — Returns all cash accounts with current balances as a list of dicts.
- **`add_operation_balance(account_number, amount, title, operation_date, entry_type, category)`** — Records a new cash operation (credit or debit). Triggers balance recalculation. Returns `{"id": int}`.
- **`get_operations_by_account(account_number)`** — Returns all operations for a specific account, ordered newest first.
- **`get_all_operations()`** — Returns all operations across all accounts.
- **`update_operation_by_id(id, amount, title, operation_date, entry_type, category)`** — Updates an operation's fields and recalculates the running balance.
- **`delete_operation_by_id(id)`** — Deletes an operation and recalculates the running balance.
- **`get_balance(account_number)`** — Returns the current balance for one account. Returns `0.0` if the account has no operations.

---

## `connector_history_use_cases.py` — `ConnectorHistoryUseCases`

**Dependencies:** `ConnectorHistoryRepository`

- **`record_history(connector_type, source_name, import_mode, imported, skipped, errors, success, profile_id?, source_path?, column_mapping?, delimiter?, asset_type_overrides?, new_accounts?)`** — Creates a `ConnectorHistoryEntry` and persists it. Computes the `status` field automatically: `"success"` if no errors, `"partial"` if some succeeded and some failed, `"failed"` otherwise. Returns the new record ID.

---

## `di_container.py` — `Container`

The dependency injection container, using the `dependency-injector` library. Every service, repository, and infrastructure component is declared here as a `Singleton` or `Factory` provider. This is the single place where all wiring happens.

**Lifecycle overview:**

```
DatabaseConnection (Singleton)
    └── All repositories (Singletons, share the same DB connection)
            └── Domain services (Singletons)
                    └── Use case classes (assembled by the frontend service layer)
```

The frontend does not construct any objects directly — it always pulls from this container. This ensures every component is instantiated once and shared correctly.

---

## `dividend_use_cases.py` — `DividendUseCases`

**Dependencies:** `DividendRepository`, `SecuritiesRepository`, `DividendService`

- **`add_dividend(ticker, amount, date?)`** — Manually adds a dividend record. Returns `{"id": int}`.
- **`get_dividends_by_ticker(ticker)`** — Returns all dividends for a specific ticker.
- **`get_all_dividends()`** — Returns all dividend records, newest first.
- **`get_total_amount()`** — Returns the total sum of all dividend amounts.
- **`delete_dividend(id)`** — Deletes a dividend record.
- **`update_dividend(id, ticker, amount, date?)`** — Updates a dividend record.
- **`sync_dividends(tickers?)`** — Triggers a market data sync for the given tickers (or all held tickers if `None`). Applies a **1-hour cooldown** per ticker using in-memory state (`_synced_tickers`, `_last_sync_time`) — already-synced tickers are skipped until the cooldown expires. Returns `{imported, skipped, errors}`.
- **`_filter_recently_synced(tickers)`** — *(private)* Filters out tickers synced within the last hour. Resets the cooldown state completely once the window expires.

---

## `file_import_use_cases.py` — `FileImportUseCases`

**Dependencies:** `FileConnector`, `FileConnectorDomainService`

Also provides two standalone helpers at module level:

- **`build_import_message(imported, skipped, errors, label)`** — Constructs a standardized `(success: bool, message: str)` tuple for display in the UI. Handles success, partial success, and failure cases.
- **`FileImportResult`** — Value object: `success`, `message`, `errors`, `imported`, `skipped`, `history_id`.

### `FileImportUseCases` methods

- **`read_file(file_bytes, filename, delimiter, *, preview_only=True)`** — Reads an uploaded file. In preview mode, returns `(columns, first_5_rows)`. In full mode, returns all rows as dicts.
- **`resolve_asset_types(tickers)`** — Delegates asset type lookup to the domain service.
- **`import_positions(file_bytes, filename, column_mapping, delimiter?, asset_type_overrides?)`** — Full positions import pipeline: reads the file, delegates to `FileConnectorDomainService.import_positions()`, and wraps the result in a `FileImportResult` with a user-friendly message.
- **`detect_unknown_cash_accounts(file_bytes, filename, column_mapping, delimiter?)`** — Returns a list of account numbers found in the file that don't yet exist in the cash table. Used to prompt the user to create missing accounts before importing.
- **`import_cash_operations(file_bytes, filename, column_mapping, delimiter?, new_accounts?)`** — Imports cash operations from a file. Same pattern as `import_positions`.
- **`reimport_from_history(history_entry, file_bytes)`** — Re-runs a previous import using the settings recorded in a `ConnectorHistoryEntry`. Useful for re-importing after a configuration fix.

---

## `portfolio_use_cases.py` — `PortfolioUseCases`

**Dependencies:** `PortfolioService`

Thin pass-through to the domain service.

- **`get_portfolio_overview(user_currency)`** — Returns a `PortfolioOverview` entity with aggregated totals.
- **`get_chart_data(period, user_currency)`** — Returns the time-series chart data for the full portfolio as a list of row dicts.

---

## `property_use_cases.py` — `PropertyUseCases`

**Dependencies:** `PropertyRepository`

- **`add_property(name, value, purchase_date?, description?, category?, currency?)`** — Adds a new property record. Returns `{"id": int}`.
- **`get_all_properties()`** — Returns all properties as a list of dicts.
- **`delete_property(id)`** — Deletes a property.
- **`update_property(id, name, value, purchase_date?, description?, category?, currency?)`** — Updates a property's fields.

---

## `securities_use_cases.py` — `SecuritiesUseCases`

**Dependencies:** `SecuritiesRepository`, `SecuritiesService`, `ChartService`, `PriceService`, `CurrencyService`

- **`add_position(ticker, price, quantity, entry_type, asset_type, date?, fees?)`** — Adds a new position. Returns `{"id": int}`.
- **`update_position(id, ticker, price, quantity, entry_type, asset_type, date?, fees?)`** — Updates an existing position.
- **`delete_position(id)`** — Deletes a position.
- **`get_all_positions()`** — Returns all raw position rows as dicts (drops `currency` column if present).
- **`get_positions_by_ticker(ticker)`** — Returns all individual position rows for one ticker.
- **`get_aggregated_positions(user_currency)`** — Returns aggregated positions (avg price, total quantity, current price, total value) converted to `user_currency`.
- **`get_chart_data_ticker(ticker, period, user_currency)`** — Returns single-ticker chart data as `[{name, price}]`. Delegates to `ChartService.get_ticker_chart_data()`.
- **`get_current_prices(tickers, user_currency)`** — Returns `dict[ticker, price_in_user_currency]` for a list of tickers. Fetches live prices via `PriceService` and applies FX conversion.

---

## `web_connector_use_cases.py` — `WebConnectorUseCases`

**Dependencies:** `WebConnectorDomainService`

- **`list_web_profiles()`** — Returns all available web connector profiles as frontend-friendly dicts, including formatted `credential_fields` descriptors (type, label, options).
- **`run_web_connector(profile_id, credentials, on_user_input?, headless?)`** — Runs a connector and returns the result as a plain dict: `{success, imported, skipped, errors, status_log, needs_matching, unmatched_positions}`.
- **`get_web_profile(profile_id)`** — Returns the raw `ConnectorProfile` for a given ID.
- **`import_matched_positions(matched)`** — Imports positions that the user has manually matched to tickers after a connector run. Returns `{success, imported, skipped, errors}`.

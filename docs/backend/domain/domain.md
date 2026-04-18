# Domain Layer

The domain layer is the heart of the application. It contains the business rules, entities, and service logic — completely free of infrastructure or framework concerns. Nothing in this folder imports from `infrastructure` or `application`.

## Structure

```
domain/
├── constants.py          # Shared domain constants
├── entities.py           # All domain data models (dataclasses + enums)
├── exceptions.py         # Domain-specific exception hierarchy
├── interfaces.py         # Abstract interfaces for external providers
├── repositories/         # Abstract repository contracts (ABCs)
│   ├── asset_repositories.py    # Securities, cash, price, currency, property repos
│   └── support_repositories.py  # Credentials, history, import, event repos
└── services/             # Business logic services
    ├── cash_service.py
    ├── chart_service.py
    ├── currency_service.py
    ├── dividend_service.py
    ├── portfolio_service.py
    ├── price_service.py
    ├── property_service.py
    ├── securities_service.py
    ├── timeline.py
    └── connectors/       # Import pipeline services
        ├── helpers.py
        ├── import_service.py
        ├── ticker_resolution.py
        └── web_connector_service.py
```

---

## `constants.py`

Shared constants used across domain services and application layer.

| Constant | Type | Description |
|---|---|---|
| `PERIOD_CONFIG` | `dict` | Maps period keys (`"1D"`, `"1M"`, etc.) to chart config dicts with `days`, `period`, `interval`, `format` fields |
| `ASSET_TYPE_LABELS` | `dict` | Maps `AssetType` string values to human-readable chart labels (e.g. `"STOCK"` → `"Stocks"`) |
| `DEFAULT_CURRENCY` | `str` | Default user currency: `"EUR"` |
| `DEFAULT_PERIOD` | `str` | Default chart period: `"1M"` |
| `MIN_CHART_DAYS` | `int` | Minimum number of days required to render a meaningful chart (avoids single-point charts) |

---

## `entities.py`

All domain data models. Uses Python dataclasses and `StrEnum` for type-safe value objects.

### Enums

#### `AssetType`
Classifies the type of financial asset.  
Values: `STOCK`, `CRYPTO`, `CASH`, `BOND`, `ETF`, `COMMODITY`, `PROPERTY`

#### `EntryType`
Describes how a record was created.  
Values: `MANUAL` (user-entered in the UI), `WEB` (automated web connector), `CSV`, `EXCEL`, `API`

#### `Currency`
Enumeration of all supported currencies (USD, EUR, GBP, JPY, CHF, and ~25 more).

- **`.label`** — Returns a human-readable string like `"EUR - Euro"`.
- **`.symbols`** — Returns the currency symbol like `"€"`.

---

### Dataclasses

#### `TickerInfo`
Enriched metadata for a financial instrument, resolved from yfinance or the reference table.

| Field | Type | Description |
|---|---|---|
| `ticker` | `str` | Canonical ticker symbol (always uppercase) |
| `isin` | `str \| None` | ISIN code if known |
| `name` | `str \| None` | Human-readable name (e.g. "Apple Inc.") |
| `asset_type` | `str \| None` | Resolved asset type (e.g. `"STOCK"`) |
| `exchange` | `str \| None` | Exchange code (e.g. `"NMS"`) |
| `currency` | `str \| None` | Native trading currency |
| `source` | `str` | Where the info came from (`"yfinance"`, `"manual"`, etc.) |
| `last_updated` | `str \| None` | ISO timestamp of last resolution |

---

#### `PortfolioOverview`
Aggregated snapshot of the entire portfolio at a point in time.

| Field | Description |
|---|---|
| `total_value` | Sum of all assets (securities + cash + properties) |
| `total_invested` | Total capital deployed (sum of buy prices × quantities) |
| `total_return` | Return as a percentage of invested capital |
| `securities_value` | Current market value of all securities positions |
| `cash_value` | Current balance across all cash accounts |
| `properties_value` | Current value of all physical properties |

---

#### `ConnectorProfile`
Configuration object for a web connector plugin. Describes what data it imports and what credentials it requires.

| Field | Description |
|---|---|
| `id` | Unique connector ID (e.g. `"degiro"`, `"revolut"`) |
| `name` | Display name for the UI |
| `column_mapping` | Maps source column names to target field names |
| `import_mode` | `"positions"` or `"cash"` |
| `description` | Optional description shown in the UI |
| `new_accounts` | Cash accounts to create automatically on import |
| `credential_fields` | List of `(field_name, label, [options])` tuples for the credential form |
| `needs_matching` | `True` if the user must manually match names to tickers after import |

---

#### `WebConnectorResult`
Result returned after running a web connector.

| Field | Description |
|---|---|
| `success` | Whether the run completed without fatal errors |
| `imported` | Number of rows successfully imported |
| `skipped` | Number of rows skipped (duplicates or empty) |
| `errors` | List of per-row error messages |
| `status_log` | Human-readable log of connector execution steps |
| `needs_matching` | `True` if unmatched positions were returned for manual review |
| `unmatched_positions` | Rows that could not be auto-matched to a ticker |

---

#### `ConnectorHistoryEntry`
A persisted record of a single import run (file or web connector).

| Field | Description |
|---|---|
| `id` | Auto-assigned database ID |
| `connector_type` | `"web"` or `"file"` |
| `profile_id` | Web connector profile ID, or `None` for file imports |
| `source_name` | Display name of the source (e.g. filename or broker name) |
| `source_path` | File path, if applicable |
| `import_mode` | `"positions"` or `"cash"` |
| `column_mapping` | The mapping used during import |
| `delimiter` | CSV delimiter used |
| `asset_type_overrides` | Manual asset type overrides applied |
| `new_cash_accounts` | Cash accounts created during this run |
| `imported` | Count of successfully imported rows |
| `skipped` | Count of skipped rows |
| `errors` | List of error messages |
| `status` | `"success"`, `"partial"`, or `"failed"` |
| `created_at` | ISO timestamp of the import run |

---

#### `CredentialInfo`
Safe metadata for a stored credential set. **Never exposes the raw credential values** — only profile ID and display information.

---

## `exceptions.py`

A structured hierarchy of domain exceptions. All exceptions extend `DomainError`.

### Import pipeline
| Exception | Raised when |
|---|---|
| `ImportError` | Base for all import failures |
| `MissingMappingError` | Required column mappings are absent |
| `AssetTypeResolutionError` | Cannot determine the asset type for a ticker |
| `DateParsingError` | A date string cannot be parsed to any known format |

### Connector / fetch
| Exception | Raised when |
|---|---|
| `ConnectorError` | Base for web connector failures |
| `ConnectorNotFoundError` | A requested site connector is not registered |
| `DataFetchError` | A site connector fails to retrieve data from the broker |

### Sync
| Exception | Raised when |
|---|---|
| `SyncError` | Base for price/dividend sync failures |
| `PriceSyncError` | Price history synchronization fails for a ticker |
| `DividendSyncError` | Dividend synchronization fails for a ticker |

---

## `interfaces.py`

Abstract interfaces that define the contracts for external data providers. The domain depends only on these ABCs — the concrete implementations live in `infrastructure/integrations/`.

### `PriceProvider`
- **`get_current_price(ticker)`** — Returns the current market price for a ticker.
- **`get_price_history(ticker, start_date, end_date, interval, *, period)`** — Returns a DataFrame with `(date, close_price)`. Accepts either a date range or a relative `period` string like `"1d"`.

### `CurrencyProvider`
- **`get_ticker_currency(ticker)`** — Returns the native trading currency of a ticker symbol.

### `MarketDataProvider`
Combines `PriceProvider` + `CurrencyProvider` and adds:
- **`check_provider_was_called()`** — Returns and resets a flag indicating whether any API call was made since last check. Used for telemetry/debugging.
- **`get_exchange_rate(from_currency, to_currency)`** — Returns the FX rate to convert between two currencies.
- **`get_dividend_history(ticker, start_date, end_date)`** — Returns a DataFrame with `(date, amount_per_share)`.
- **`resolve_ticker_info(identifier)`** — Resolves an ISIN or ticker string to a `TickerInfo` entity via a live API call.

### `FileConnector`
- **`read_file(file_bytes, filename, delimiter)`** — Parses an uploaded file (CSV or Excel) into a raw Polars DataFrame.

### `SiteConnector`
- **`site_id`** — Unique string identifier for the broker connector.
- **`profile`** — The `ConnectorProfile` describing this connector's behavior.
- **`fetch_data(credentials, on_status, on_user_input, headless)`** — Runs the browser automation to scrape data and returns a raw DataFrame.

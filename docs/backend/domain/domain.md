# Domain layer

The domain layer is pure Python. It defines the vocabulary of the
application and the contracts the rest of the code depends on. No I/O lives
here — repository contracts are abstract and external services are exposed as
interfaces.

## Entities (`domain/entities.py`)

All entities are `@dataclass(slots=True)` for memory and attribute-typo safety.

### Enums

| Enum | Values |
|---|---|
| `AssetType` | `STOCK`, `CRYPTO`, `CASH`, `BOND`, `ETF`, `COMMODITY`, `PROPERTY` |
| `EntryType` | `MANUAL`, `WEB`, `CSV`, `EXCEL`, `API` |
| `Currency` | 28 ISO codes (USD, EUR, GBP, JPY, CHF, CAD, …). Each value exposes `.label` and `.symbols` properties backed by an internal metadata dict. |

### Dataclasses

```python
TickerInfo(ticker, isin, name, asset_type, exchange, currency, source, last_updated)
PortfolioOverview(total_value, total_invested, total_return,
                  securities_value, cash_value, properties_value,
                  total_dividends, total_return_with_dividends)
ConnectorProfile(id, name, column_mapping, import_mode="positions",
                 description, new_accounts, credential_fields, needs_matching)
WebConnectorResult(success, imported, skipped, errors,
                   status_log, needs_matching, unmatched_positions)
ConnectorHistoryEntry(id, connector_type, profile_id, source_name, source_path,
                      import_mode, column_mapping, delimiter,
                      asset_type_overrides, new_cash_accounts,
                      imported, skipped, errors, status, created_at)
CredentialInfo(...)
```

## Constants (`domain/constants.py`)

| Constant | Purpose |
|---|---|
| `PERIOD_CONFIG` | Maps UI period buttons (`1D`/`5D`/`1M`/`6M`/`1Y`/`5Y`) to `{days, period, interval, format}` for yfinance and chart formatting. |
| `ASSET_TYPE_LABELS` | Default English labels per `AssetType` (frontend overrides via i18n). |
| `DEFAULT_CURRENCY` | `"EUR"` |
| `DEFAULT_PERIOD` | `"1M"` |
| `MIN_CHART_DAYS` | `3` — minimum points needed to render a chart. |

## Exceptions (`domain/exceptions.py`)

All inherit from `DomainError`.

```
DomainError
├── ImportError
│   ├── MissingMappingError(missing_fields: set[str])
│   ├── MissingColumnError(missing_columns: set[str])
│   ├── AssetTypeResolutionError(ticker, row=None)
│   └── DateParsingError(value)
├── ConnectorError
│   ├── ConnectorNotFoundError(site_id)
│   └── DataFetchError(site_id, cause=None)
├── SyncError
│   ├── PriceSyncError(ticker, cause=None)
│   └── DividendSyncError(ticker, cause=None)
├── CurrencyConversionError(from_currency, to_currency)
└── TickerCurrencyUnknownError(ticker)
```

## Interfaces (`domain/interfaces.py`)

Provider contracts that infrastructure must implement.

```python
class UnitOfWork(Protocol):
    def transaction(self) -> AbstractContextManager: ...

class PriceProvider(ABC):
    def get_current_price(ticker: str) -> float | None
    def get_price_history(ticker, start_date, end_date, interval, period) -> pl.DataFrame

class CurrencyProvider(ABC):
    def get_ticker_currency(ticker: str) -> str | None

class MarketDataProvider(PriceProvider, CurrencyProvider):
    def check_provider_was_called() -> bool
    def get_exchange_rate(from_currency, to_currency) -> float | None
    def get_dividend_history(ticker, start_date, end_date) -> pl.DataFrame
    def resolve_ticker_info(ticker: str) -> TickerInfo | None
```

`MarketDataProvider` exposes a `_provider_was_called` flag flipped by every
network call. The frontend reads it via `was_market_data_fetched()` to show a
"market data refreshed" toast on demand.

## See also

- [repositories.md](repositories.md)
- [services.md](services.md)
- [connectors.md](connectors.md)

# Application layer

The application layer is the only place that:

- opens DB transactions (through repositories that own them)
- normalises input at the boundary (ticker `.strip().upper()`, default dates, …)
- composes domain services into use-case operations
- is wired by the `dependency-injector` `Container`

Use cases are deliberately thin. Most are 5–15 lines that delegate to one or
two domain services. They exist so the frontend has a single, stable API
surface that doesn't leak repository internals.

## Use cases

| Class | File | Purpose |
|---|---|---|
| `CashUseCases` | `cash_use_cases.py` | Cash account CRUD, balance operations |
| `SecuritiesUseCases` | `securities_use_cases.py` | Position CRUD, aggregation, ticker enrichment |
| `PortfolioUseCases` | `portfolio_use_cases.py` | Portfolio overview & chart data |
| `DividendUseCases` | `dividend_use_cases.py` | Dividend CRUD + yfinance sync |
| `PropertyUseCases` | `property_use_cases.py` | Property CRUD |
| `FileImportUseCases` | `file_import_use_cases.py` | Run the file connector pipeline |
| `WebConnectorUseCases` | `web_connector_use_cases.py` | Run a Playwright web connector |
| `ConnectorHistoryUseCases` | `connector_history_use_cases.py` | Read/delete past import runs |

### `SecuritiesUseCases` (representative)

```python
add_position(ticker, price, quantity, entry_type, asset_type, date=None, fees=0.0) -> dict
update_position(id, ticker, price, quantity, entry_type, asset_type, date=None, fees=0.0)
delete_position(id)
get_all_positions() -> list[dict]
get_positions_by_ticker(ticker) -> list[dict]
get_aggregated_positions(user_currency=DEFAULT_CURRENCY) -> list[dict]
get_chart_data_ticker(ticker, period=DEFAULT_PERIOD, user_currency=DEFAULT_CURRENCY) -> list[dict]
get_current_prices(tickers, user_currency=DEFAULT_CURRENCY) -> dict[str, float]
```

`add_position` and `update_position` call `_enrich_ticker(ticker)` — a
best-effort lookup that fills `TickerInfoRepository` so the UI gets a company
name without the user having to do anything. Failures are swallowed and logged
because the position itself is already persisted.

`get_aggregated_positions` backfills missing names by batch-reading the info
repo first, then calling `_enrich_ticker` only for the truly unknown tickers.

## DI container — `backend/di_container.py`

Single `Container(containers.DeclarativeContainer)` with three sections:

```python
# Infrastructure (Singletons)
database              = providers.Singleton(DatabaseConnection)
market_data_provider  = providers.Singleton(YahooFinanceProvider)
file_connector        = providers.Singleton(ExcelCsvConnector)
site_connectors       = providers.Object(SITE_CONNECTORS)

# Repositories (Singletons; share the singleton DB connection)
cash_repository, securities_repository, price_repository,
reference_repository, currency_repository, dividend_repository,
import_hash_repository, credential_repository,
connector_history_repository, property_repository,
event_log_repository, ticker_info_repository

# Domain services (Singletons)
currency_service, price_sync, securities_service, dividend_sync,
cash_service, property_service, chart_service, portfolio_service

# Use cases (Singletons)
cash_use_cases, securities_use_cases, portfolio_use_cases,
dividend_use_cases, property_use_cases, file_import_use_cases,
web_connector_use_cases, connector_history_use_cases

# Connector services
file_connector_service, web_connector_service
```

The container is instantiated once in `frontend/services/__init__.py` and
reused for the lifetime of the app. Tests can replace any provider via
`container.<provider>.override(...)`.

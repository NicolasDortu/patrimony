# Backend

The backend is structured around **Domain-Driven Design (DDD)** with a strict dependency rule: inner layers never depend on outer layers.

```
domain  ←  application  ←  infrastructure
                ↑
           (frontend services consume use cases directly)
```

## Layer Map

```
backend/
├── domain/           # Business rules, entities, interfaces, repositories (ABCs)
│   ├── constants.py
│   ├── entities.py
│   ├── exceptions.py
│   ├── interfaces.py
│   ├── repositories/     # Abstract repository contracts
│   └── services/         # Domain business logic
│       └── connectors/   # Import pipeline services
├── application/      # Use cases — orchestrate domain services for the frontend
│   └── di_container.py   # Dependency injection wiring
├── infrastructure/   # Concrete implementations (DB, APIs, file parsing)
│   ├── database/         # DuckDB connection + schema DDL
│   ├── integrations/     # External providers (yfinance, file parser, Playwright)
│   └── repositories/     # SQL implementations of domain repository ABCs
└── config/           # Logging configuration
```

---

## Layers Explained

### Domain (`domain/`)
The core of the application. Contains all business rules, data models, and abstract contracts. **Has no dependencies on any other layer or external library** (except standard Python and Polars for data manipulation).

- **`entities.py`** — All data models: `AssetType`, `EntryType`, `Currency`, `TickerInfo`, `PortfolioOverview`, `ConnectorProfile`, `WebConnectorResult`, `ConnectorHistoryEntry`, `CredentialInfo`.
- **`constants.py`** — Shared constants: `PERIOD_CONFIG`, `ASSET_TYPE_LABELS`, `DEFAULT_CURRENCY`, `DEFAULT_PERIOD`, `MIN_CHART_DAYS`.
- **`exceptions.py`** — Domain exception hierarchy rooted at `DomainError`.
- **`interfaces.py`** — Abstract interfaces for external providers: `PriceProvider`, `CurrencyProvider`, `MarketDataProvider`, `FileConnector`, `SiteConnector`.
- **`repositories/`** — Abstract repository interfaces (ABCs) for all data access.
- **`services/`** — Business logic: `CashService`, `ChartService`, `CurrencyService`, `DividendService`, `PortfolioService`, `PriceService`, `PropertyService`, `SecuritiesService`, plus the import pipeline in `services/connectors/`.

→ See [domain/domain.md](domain/domain.md)

---

### Application (`application/`)
Thin use case classes that the frontend calls. Each use case class:
- Takes domain services/repositories as constructor arguments.
- Delegates all business logic to the domain.
- Returns plain `dict` / `list` / primitives (not domain entities) for frontend consumption.

Use cases: `CashUseCases`, `ConnectorHistoryUseCases`, `DividendUseCases`, `FileImportUseCases`, `PortfolioUseCases`, `PropertyUseCases`, `SecuritiesUseCases`, `WebConnectorUseCases`.

The `di_container.py` (`Container` class, using `dependency-injector`) wires all layers together as singletons, ensuring every component is instantiated once and shared correctly.

→ See [applications.md](applications.md)

---

### Infrastructure (`infrastructure/`)
Concrete implementations. Contains all I/O: SQL queries, HTTP calls, file I/O, and browser automation.

- **`database/`** — `DatabaseConnection` (DuckDB singleton) and `ddl.py` (all `CREATE TABLE` statements). See [infrastructure/database.md](infrastructure/database.md) for the full schema.
- **`integrations/`** — `YahooFinanceProvider` (market data), `ExcelCsvConnector` (file parsing), and Playwright-based broker connectors (`web_connector/`).
- **`repositories/`** — SQL implementations of every domain repository ABC.

→ See [infrastructure/infrastructure.md](infrastructure/infrastructure.md)

---

## Data Flow Example — Portfolio Chart

```
Frontend state
  → PortfolioUseCases.get_chart_data(period, currency)
    → PortfolioService.get_chart_data()
      → ChartService.get_portfolio_chart_data()
        → PriceService.sync_intraday() / sync_price_history()   (writes to DB)
        → PriceRepository.get_intraday_prices()                 (reads from DB)
        → CurrencyService.get_rates_for_tickers()               (cache → yfinance)
        → PriceService.sort_and_forward_fill()                  (pure computation)
        → ChartService._build_portfolio_rows()                  (pure computation)
      → Returns list[dict] with {Date, Stocks, ETFs, Cash, Properties, Total}
```

## Data Flow Example — File Import

```
Frontend uploads file
  → FileImportUseCases.import_positions(file_bytes, filename, column_mapping)
    → ExcelCsvConnector.read_file()                             (parse bytes → DataFrame)
    → FileConnectorService.import_positions()
      → ticker_resolution.resolve_ticker_aliases()              (cache → reference → yfinance)
      → ImportHashRepository.existing_hashes()                  (deduplication)
      → SecuritiesRepository.add_position()                     (insert rows)
      → ImportHashRepository.add_hashes()                       (mark as imported)
    → Returns FileImportResult {success, message, imported, skipped, errors}
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Domain has no SQL | Swapping DuckDB for another DB requires only changing `infrastructure/repositories/` |
| `DEFAULT_CURRENCY` / `DEFAULT_PERIOD` constants | Single source of truth; all service defaults reference these instead of magic strings |
| Intraday prices in a separate table | Prevents the high-frequency 5m data from polluting daily history queries |
| SHA-256 row hashing for deduplication | Dedup works across formats (CSV re-uploads, web re-imports) without unique DB constraints per broker |
| Playwright in a dedicated thread | Reflex occupies the main event loop; Playwright's async API needs its own loop |
| `COALESCE` in `ticker_info` upsert | Prevents partial resolutions (e.g. from a file import) from overwriting richer data already in the cache |

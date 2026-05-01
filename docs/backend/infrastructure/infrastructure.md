# Infrastructure layer

Concrete adapters for everything outside the process: DuckDB, the file system,
yfinance, and Playwright.

```
infrastructure/
├── database/         # DuckDB connection, DDL, reference data CSV
├── integrations/     # External-service adapters (yfinance, file parser, …)
│   └── web_connector/  # One module per supported broker / bank
└── repositories/     # All concrete repository implementations
```

## Repositories

Each implementation lives in its own module and depends on
`DatabaseConnection`. Constructors take a single `connection` argument so the
DI container can wire them all the same way.

| File | Class | Implements |
|---|---|---|
| `cash_repository.py` | `CashRepositoryImpl`, `CashOperationRepositoryImpl` | `CashRepository`, `CashOperationRepository` |
| `securities_repository.py` | `SecuritiesRepositoryImpl` | `SecuritiesRepository` |
| `price_repository.py` | `PriceRepositoryImpl` | `PriceRepository` |
| `dividend_repository.py` | `DividendRepositoryImpl` | `DividendRepository` |
| `property_repository.py` | `PropertyRepositoryImpl` | `PropertyRepository` |
| `reference_repository.py` | `ReferenceRepositoryImpl` | `ReferenceRepository` |
| `currency_repository.py` | `CurrencyRepositoryImpl` | `CurrencyRepository` |
| `credential_repository.py` | `CredentialRepositoryImpl` | `CredentialRepository` (Fernet + PBKDF2) |
| `connector_history_repository.py` | `ConnectorHistoryRepositoryImpl` | `ConnectorHistoryRepository` |
| `import_hash_repository.py` | `ImportHashRepositoryImpl` | `ImportHashRepository` |
| `ticker_info_repository.py` | `TickerInfoRepositoryImpl` | `TickerInfoRepository` |
| `event_log_repository.py` | `EventLogRepositoryImpl` | (system event log) |

Repository methods return Polars DataFrames for read-side calls (so the
domain can pipeline transforms without converting twice) and `None` /
new-row id for mutations. Inserts that span multiple statements are wrapped
in `with self._conn.transaction():`.

See:
- [database.md](database.md) — full DuckDB schema
- [integrations.md](integrations.md) — yfinance + file parser
- [web_connector.md](web_connector.md) — Playwright site connectors

# Backend

The backend is a pure-Python package with no Reflex dependency. It implements
a Domain-Driven layered architecture:

```
patrimony/backend/
├── application/       # Use cases (orchestration, transaction boundaries)
│   └── di_container   # Wires everything together with dependency-injector
├── domain/            # Business logic, free of I/O
│   ├── entities       # Dataclasses + StrEnums (AssetType, EntryType, Currency, …)
│   ├── constants      # Period configs, default currency/period, asset labels
│   ├── exceptions     # Typed DomainError hierarchy
│   ├── interfaces     # Provider Protocols / ABCs (MarketDataProvider, UnitOfWork)
│   ├── repositories   # Abstract repository contracts
│   └── services       # Pure business logic (portfolio, currency, charts, …)
└── infrastructure/    # Adapters that touch the outside world
    ├── database       # DuckDB connection + DDL + reference loader
    ├── integrations   # yfinance, file parser, Playwright site connectors
    └── repositories   # Concrete repository implementations
```

## Layer rules

| Layer | May import | Must NOT import |
|---|---|---|
| `domain` | `domain.*` only | `application`, `infrastructure`, `frontend` |
| `application` | `domain.*` | `infrastructure.*` directly (uses DI) |
| `infrastructure` | `domain.*` (interfaces) | `application`, `frontend` |
| `frontend` | `frontend.services.*` only | `backend.*` (goes through the service layer) |

The frontend never imports backend modules directly. It consumes a single
`Container` instance from `frontend.services` which resolves use cases through
the DI container.

## Data flow (read example)

```
UI page (states.cash_state)
    └─► frontend.services.cash_services.CashService
            └─► backend.application.cash_use_cases.CashUseCases
                    ├─► backend.domain.services.CashService
                    │       └─► CashRepository (abstract)
                    │               └─► CashRepositoryImpl (DuckDB)
                    └─► CurrencyService (FX conversion)
```

## Data flow (mutation example: add position)

```
position_dialog.on_submit
    └─► frontend.services.SecuritiesService.add_position
            └─► SecuritiesUseCases.add_position
                    ├─► normalises ticker (strip().upper())
                    ├─► SecuritiesRepository.add_position  (DuckDB transaction)
                    └─► _enrich_ticker  (best-effort yfinance lookup)
```

The application layer is the only place that opens transactions and normalises
input. Repositories trust their inputs.

## See also

- [domain/domain.md](domain/domain.md) — entities, constants, exceptions, interfaces
- [domain/repositories.md](domain/repositories.md) — abstract repository contracts
- [domain/services.md](domain/services.md) — domain services
- [domain/connectors.md](domain/connectors.md) — file & web connector services
- [applications.md](applications.md) — use cases and DI container
- [infrastructure/infrastructure.md](infrastructure/infrastructure.md) — adapters overview
- [infrastructure/database.md](infrastructure/database.md) — DuckDB schema reference
- [infrastructure/integrations.md](infrastructure/integrations.md) — yfinance & file parsing
- [infrastructure/web_connector.md](infrastructure/web_connector.md) — Playwright site connectors

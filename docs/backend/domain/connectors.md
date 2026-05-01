# Connector services

Connectors bring data in from the outside: spreadsheet files the user uploads,
or broker / bank websites driven by Playwright. Both sit under
`backend/domain/services/connectors/` so they can share validation logic and
the same `ImportHashRepository` for deduplication.

## File connectors — `FileConnectorService`

Constructor:
```python
FileConnectorService(
    securities_repo: SecuritiesRepository,
    cash_repo: CashRepository,
    reference_repo: ReferenceRepository,
    hash_repo: ImportHashRepository,
    uow: UnitOfWork,
    info_repo: TickerInfoRepository,
    market_data: MarketDataProvider,
)
```

Public surface:
```python
resolve_ticker_aliases(rows: list[dict]) -> list[dict]
import_positions(file_bytes, filename, mapping, delimiter, asset_type_overrides)
import_cash_operations(file_bytes, filename, mapping, new_accounts, delimiter)
```

Pipeline (positions):
1. `ExcelCsvConnector.read_file(...)` parses the file into a Polars DataFrame.
2. Required columns are validated against the mapping; missing keys raise
   `MissingMappingError` / `MissingColumnError`.
3. Each row is hashed; rows whose hash is already in `ImportHashRepository`
   are skipped (silently).
4. Tickers are resolved against `ReferenceRepository`; unresolved ones are
   sent to `MarketDataProvider.resolve_ticker_info` for enrichment.
5. `AssetType` is derived from the reference / overrides; unresolvable rows
   raise `AssetTypeResolutionError`.
6. All inserts happen inside a single transaction provided by the
   `UnitOfWork`.

The cash pipeline follows the same shape but writes to `CashRepository` and
can create new accounts on the fly via `new_accounts`.

## Web connectors — `WebConnectorService`

Constructor:
```python
WebConnectorService(
    site_connectors: dict[str, SiteConnector],
    connector_service: FileConnectorService,
)
```

Public surface:
```python
list_profiles() -> list[ConnectorProfile]
get_profile(site_id) -> ConnectorProfile
run_connector(site_id, credentials, on_status, on_user_input, headless) -> WebConnectorResult
```

A `SiteConnector` is a Playwright-driven plugin (see
[`infrastructure/web_connector.md`](../infrastructure/web_connector.md)). It
yields raw rows in the same shape `FileConnectorService` consumes, so the
final import path is unified.

The `on_status` and `on_user_input` callbacks let the frontend stream live
progress messages and prompt the user for 2FA codes / CAPTCHAs.

`WebConnectorResult.needs_matching` is set when imported tickers couldn't be
matched against existing positions; the UI then opens the matching wizard.

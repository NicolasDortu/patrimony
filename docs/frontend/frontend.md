# Frontend Layer

The frontend is built with **Reflex** (Python → React). It is the only layer that knows about the UI framework. It never imports from `backend.infrastructure` directly — all backend access goes through the service classes in `frontend/services/`.

## Structure

```
frontend/
├── services/           # Single interface between frontend and backend
│   ├── models.py           # Shared result types and decorators
│   ├── asset_services.py   # Securities, portfolio, dividends, properties, currency
│   ├── cash_services.py    # Cash accounts and balance operations
│   ├── connector_services.py # File import, web import, credentials, history
│   └── event_services.py   # Persistent event log
├── states/             # Reflex state classes (one per page/feature)
│   ├── mixins.py           # PaginationMixin + apply_sort_and_search
│   ├── spreadsheet_mixin.py # Editable spreadsheet mode
│   ├── aggregation_helpers.py # Pure computation helpers (monthly cash aggregation)
│   ├── portfolio_state.py
│   ├── securities_total_state.py
│   ├── securities_details_state.py
│   ├── cash_state.py
│   ├── cash_operations_state.py
│   ├── dividends_state.py
│   ├── properties_state.py
│   ├── connector_state.py
│   ├── connector_history_state.py
│   ├── web_connector_state.py
│   └── notification_state.py
├── pages/              # Route-level page functions
│   ├── index.py            # / — Portfolio overview
│   ├── securities.py       # /securities
│   ├── securities_detail.py # /securities/{ticker}
│   ├── cash.py             # /cash
│   ├── cash_operations.py  # /cash/{account_number}
│   ├── properties.py       # /properties
│   ├── connectors.py       # /connectors
│   ├── file_connector.py   # /connectors/file
│   ├── web_connector.py    # /connectors/web
│   ├── settings.py         # /settings
│   └── about.py            # /about
├── views/              # Reusable UI sections (charts, tables, KPIs)
│   ├── charts/
│   ├── kpis/
│   ├── tables/
│   ├── pickers/
│   └── connectors/
├── components/         # Low-level reusable components
├── dialogs/            # Add/edit dialogs for all entities
├── templates/          # Page wrapper (sidebar, theme, navbar)
├── config/             # JSON-backed config and logging
├── languages/locale/   # i18n JSON files (en, fr, es)
├── styles/             # Global CSS-in-Python tokens
└── utils.py            # Path helpers and color utilities
```

---

## `services/` — Backend Interface

All backend calls are routed through this layer. Service classes are pure static-method wrappers around use cases from `backend/application/`. They apply two decorators uniformly:

- **`@operation_result(failure, success)`** — Wraps a mutation method in a try/except. On success returns `OperationResult(success=True, message=success, data=...)`. On exception returns `OperationResult(success=False, message="{failure}: {exception}")`. If the inner function already returns an `OperationResult`, it passes through unchanged.
- **`@safe_query(default)`** — Wraps a query method in a try/except. Returns `default` on exception (typically `[]` or `{}`).

### `models.py` — Shared Types

- **`OperationResult`** — Dataclass with `success: bool`, `message: str`, `data: dict | None`. Used as the return type of all mutation operations.
- **`operation_result(failure, success)`** — Decorator factory. See above.
- **`safe_query(default)`** — Decorator factory. See above.
- **`df_to_dicts(df)`** — Converts a Polars `DataFrame` to `list[dict]`. Returns `[]` if `None` or empty.

---

### `asset_services.py`

#### `SecuritiesService`
Wraps `SecuritiesUseCases`.

| Method | Decorator | Description |
|---|---|---|
| `add_position(ticker, price, quantity, entry_type, asset_type, date?, fees)` | `@operation_result` | Add a new position |
| `update_position(id, ticker, price, quantity, entry_type, asset_type, date?, fees)` | `@operation_result` | Update an existing position by id |
| `delete_position(id)` | `@operation_result` | Delete a position by id |
| `get_all_positions()` | `@safe_query([])` | Return all positions as `list[dict]` |
| `get_positions_by_ticker(ticker)` | `@safe_query([])` | Return all positions for a ticker |
| `get_aggregated_positions(user_currency)` | `@safe_query([])` | Return aggregated holdings with live prices |
| `get_chart_data_ticker(ticker, period, user_currency)` | `@safe_query([])` | Return price history for a single ticker |
| `get_current_prices(tickers, user_currency)` | `@safe_query({})` | Return `{ticker: price}` dict |

#### `PortfolioService`
Wraps `PortfolioUseCases`.

| Method | Decorator | Description |
|---|---|---|
| `get_portfolio_overview(user_currency)` | *(none — raises)* | Returns `PortfolioOverview` entity |
| `get_chart_data(period, user_currency)` | `@safe_query([])` | Returns wealth chart rows as `list[dict]` |

#### `SecuritiesReferenceService`
Wraps `SecuritiesUseCases` reference methods for autocomplete and ticker lookup.

#### `DividendService`
Wraps `DividendUseCases`. Methods: `add_dividend`, `update_dividend`, `delete_dividend`, `get_all_dividends`, `get_dividends_by_ticker`, `sync_dividends(ticker, user_currency)`.

#### `PropertyService`
Wraps `PropertyUseCases`. Methods: `add_property`, `update_property`, `delete_property`, `get_all_properties`.

#### `CurrencyService`
Utility service. `get_currency_symbol(currency_code)` — returns the display symbol (`€`, `$`, etc.).

---

### `cash_services.py` — `CashService`
Wraps `CashUseCases`.

| Method | Decorator | Description |
|---|---|---|
| `add_cash(bank, account_number, currency, balance, last_updated?)` | `@operation_result` | Create a new cash account with an initial balance operation |
| `update_cash(bank, account_number, currency, last_updated?)` | `@operation_result` | Update account metadata |
| `delete_cash(id)` | `@operation_result` | Delete an account and all its operations |
| `get_all_cash()` | `@safe_query([])` | Return all accounts as `list[dict]` |
| `add_operation_balance(account_number, amount, title, operation_date, entry_type, category)` | `@operation_result` | Add a balance operation and recalculate running balances |
| `update_operation_balance(...)` | `@operation_result` | Update a balance operation and recalculate |
| `delete_operation_balance(id, account_number)` | `@operation_result` | Delete an operation and recalculate |
| `get_operations_by_account(account_number)` | `@safe_query([])` | Return all operations for an account |

---

### `connector_services.py`

#### `FileConnectorService`
Wraps `FileImportUseCases`.

| Method | Description |
|---|---|
| `read_file(file_bytes, filename, delimiter, *, preview_only)` | Parse file. Returns `(columns, preview_rows)` when `preview_only=True`, else full `list[dict]` |
| `resolve_asset_types(tickers)` | Resolve asset types for a list of tickers from the reference table |
| `import_positions(file_bytes, filename, column_mapping, delimiter, asset_type_overrides?, source_path?)` | Full import pipeline. Returns `OperationResult` with `errors` in `data` |
| `import_cash_operations(file_bytes, filename, column_mapping, delimiter, source_path?)` | Import cash operations from a file |

#### `WebConnectorService`
Wraps `WebConnectorUseCases`.

| Method | Description |
|---|---|
| `get_profiles()` | Return all available connector profiles |
| `fetch_data(profile_id, on_status, on_user_input, **options)` | Launch browser automation and return scraped data |
| `import_web_positions(profile_id, df_data, column_mapping, asset_type_overrides?)` | Import a scraped positions DataFrame into the DB |

#### `CredentialService`
Wraps `WebConnectorUseCases` credential methods. Methods: `has_master_key`, `create_master_key(password)`, `verify_master_key(password)`, `save_credential(profile_id, field, value, password)`, `get_credential(profile_id, field, password)`, `delete_credentials(profile_id)`.

#### `ConnectorHistoryService`
Wraps `ConnectorHistoryUseCases`. Methods: `get_all_history()`, `delete_history_entry(id)`.

---

### `event_services.py` — `EventLogService`
Persists UI notification events to DuckDB so they survive app restarts.

| Method | Description |
|---|---|
| `save_events(events)` | Batch-insert events into `event_log` |
| `get_recent(limit)` | Return the most recent `limit` events as `list[dict]` |
| `clear()` | Delete all events from the log |

---

## `states/` — Reflex State Classes

Each page has one or more `rx.State` subclasses. State classes hold reactive variables (`rx.var`) and event handlers (`@rx.event`). The frontend framework serializes state to JSON and re-renders components on changes.

### `mixins.py`

#### `PaginationMixin(rx.State, mixin=True)`
Mixed into any table state that needs pagination.

| Member | Type | Description |
|---|---|---|
| `total_items` | `int` | Total number of rows (set by the state after loading) |
| `offset` | `int` | Current page offset |
| `limit` | `int` | Rows per page (default 12) |
| `page_number` | `@rx.var` | Current 1-based page number |
| `total_pages` | `@rx.var` | Ceiling of `total_items / limit` |
| `prev_page()` | event | Decrement offset by limit |
| `next_page()` | event | Increment offset by limit |
| `first_page()` | event | Reset offset to 0 |
| `last_page()` | event | Jump to last page |

#### `apply_sort_and_search(items, sort_value, sort_reverse, search_value, numeric_sort_fields, search_fields, accessor)`
Pure function (not a mixin). Sorts and filters a `list[dict]` or `list[object]`. Used by all table states to avoid duplicating sort/search logic. The `accessor` parameter switches between `dict.get` and `getattr`.

---

### `spreadsheet_mixin.py` — `SpreadsheetMixin(rx.State, mixin=True)`
Mixed into table states that need an editable spreadsheet view (e.g. `CashOperationsState`, `SecuritiesDetailsState`).

Concrete states must implement:
- `spreadsheet_columns` — `@rx.var` returning column definitions for the grid
- `_load_spreadsheet_rows()` — loads data rows and their DB ids
- `_save_spreadsheet_row(row, index, rid, is_new)` — persists one row; returns an error string or `None`
- `_delete_spreadsheet_row(rid)` — deletes a removed row from the DB
- `_after_spreadsheet_save()` — reloads the table after a save

| Member | Description |
|---|---|
| `spreadsheet_mode` | `bool` — toggles between table and spreadsheet views |
| `spreadsheet_data` | `@rx.var` — current cell data as `list[list]` |
| `spreadsheet_row_count` | `@rx.var` — number of rows |
| `has_unsaved_changes` | `@rx.var` — true when any cell has been edited without saving |
| `on_spreadsheet_cell_edited(pos, cell)` | event — updates the in-memory grid on a cell change |
| `on_spreadsheet_row_appended()` | event — appends a blank row for a new entry |
| `save_spreadsheet()` | event — persists all rows, then calls `_after_spreadsheet_save()` |
| `toggle_spreadsheet_mode()` | event — toggles between spreadsheet and normal table view |

---

### `aggregation_helpers.py`
Pure Python functions used by `CashState`. Not a state class.

- **`aggregate_monthly_income_expense(operations)`** — Groups operations by `YYYY-MM`, sums positive amounts as `income` and absolute negative amounts as `expense`. Returns `list[dict]` sorted by month.
- **`aggregate_expenses_by_category(operations)`** — Groups expense-only operations by `category`. Returns `list[dict]` sorted by total descending, with a deterministic `fill` color assigned per position.

---

### State Files Overview

| File | State Class | Page | Key Responsibilities |
|---|---|---|---|
| `portfolio_state.py` | `PortfolioState` | `/` | Total wealth, KPIs, chart data, asset filter, performer lists, dividend summary |
| `securities_total_state.py` | `SecuritiesTotalState` | `/securities` | Aggregated positions table, allocation donut, heatmap |
| `securities_details_state.py` | `SecuritiesDetailsState` | `/securities/{ticker}` | Per-ticker positions list, price chart, spreadsheet editing |
| `cash_state.py` | `CashState` | `/cash` | Cash accounts table, total cash balance, monthly chart |
| `cash_operations_state.py` | `CashOperationsState` | `/cash/{acct}` | Operations table, running balance chart, category breakdown, spreadsheet editing |
| `dividends_state.py` | `DividendsState` | `/securities` | Dividends table, sync with cooldown guard |
| `properties_state.py` | `PropertiesState` | `/properties` | Properties table, total value |
| `connector_state.py` | `ConnectorState` | `/connectors/file` | Multi-step file import wizard: upload → column mapping → review → result |
| `connector_history_state.py` | `ConnectorHistoryState` | `/connectors` | Import history table |
| `web_connector_state.py` | `WebConnectorState` | `/connectors/web` | Profile selection, browser launch, OTP prompts, scraping result |
| `notification_state.py` | `NotificationState` | All pages | Drains `EventCollector`, persists to DB, exposes events to the notification bell |

---

## `templates/` — Page Wrapper

### `ThemeState(rx.State)` — in `template.py`
Global settings state shared across all pages.

| Field | Default | Description |
|---|---|---|
| `accent_color` | `"crimson"` | Radix accent color token |
| `gray_color` | `"gray"` | Radix gray color token |
| `radius` | `"large"` | Border radius token |
| `scaling` | `"100%"` | UI scaling factor |
| `default_currency` | `"EUR"` | User's display currency |
| `language` | `"en"` | Active locale (`en`, `fr`, `es`) |
| `translations` | `{}` | Loaded from the active locale JSON file |
| `stock_color` … `all_color` | various | Per-asset-type chart colors (Radix color names) |
| `show_browser` | `True` | Whether to show the browser window during web connector runs |
| `currency_symbol` | `@rx.var` | Display symbol (`€`, `$`, etc.) — derived from `default_currency` |

The `template()` function wraps every page with: the sidebar (desktop) / navbar (mobile), the Radix theme provider using `ThemeState` values, and a standard content area.

---

## `components/` — Reusable Components

| File | Component | Description |
|---|---|---|
| `card.py` | `card()` | Styled container box with optional heading |
| `chart_toggle.py` | `chart_toggle()` | Toggle button group for switching chart types (area / line / bar) |
| `dialog_factory.py` | `responsive_dialog()` | Responsive dialog wrapper — full-screen on mobile, centered on desktop |
| `donut_chart.py` | `donut_chart()` | Recharts donut with legend, used for allocation breakdowns |
| `empty_table.py` | `empty_table()` | Placeholder shown when a table has no rows |
| `loading.py` | `loading_spinner()` | Full-page loading indicator |
| `navigation.py` | `navbar()`, `sidebar()` | Mobile top bar and desktop left sidebar with route-aware active state |
| `notification.py` | `notification_bell()` | Notification bell icon with badge count and popover event list |

---

## `dialogs/` — Add/Edit Dialogs

Each dialog is a Reflex component that opens modally. They are triggered by state events and call service methods on submit.

| File | Entity | Operations |
|---|---|---|
| `position_dialog.py` | Position | Add, Edit |
| `cash_dialog.py` | Cash account | Add, Edit |
| `cash_operation_dialog.py` | Balance operation | Add, Edit |
| `dividend_dialog.py` | Dividend | Add, Edit |
| `property_dialog.py` | Property | Add, Edit |

---

## `views/` — Page Sections

Views are larger composed components used inside pages. They import state classes and service classes directly.

### `charts/`
| File | Chart | Used on |
|---|---|---|
| `wealth_chart.py` | Stacked area/line — total wealth by asset type over time | `/` |
| `stock_chart.py` | Price history chart for a single ticker | `/securities/{ticker}` |
| `cash_charts.py` | Running balance line chart | `/cash/{acct}` |
| `expense_chart.py` | Monthly income vs expense bar chart + category pie | `/cash/{acct}` |
| `securities_charts.py` | Allocation donut + holdings heatmap | `/securities` |
| `properties_charts.py` | Property value breakdown donut | `/properties` |
| `common.py` | Shared chart utilities (color helpers, axis formatters) | internal |

### `kpis/`
| File | Component | Description |
|---|---|---|
| `portfolio_stats_card.py` | KPI cards | Total value, total invested, total return % |
| `portfolio_allocation.py` | Allocation pills | Per-asset-type value badges with colored dots |
| `portfolio_performers.py` | Top/bottom performer lists | Best and worst performing tickers by return |
| `dividend_summary.py` | Dividend KPIs | Total dividends, last 12 months, annualised yield |

### `tables/`
| File | Table | Description |
|---|---|---|
| `securities_total_table.py` | Aggregated positions | Ticker, value, allocation %, P&L |
| `securities_details_table.py` | Per-ticker positions | Buy date, price, quantity, current value |
| `cash_table.py` | Cash accounts | Bank, account number, currency, current balance |
| `cash_operations_table.py` | Balance operations | Date, title, amount, category, running balance |
| `dividends_table.py` | Dividends | Ticker, amount, date |
| `properties_table.py` | Properties | Name, category, value, purchase date |
| `spreadsheet_view.py` | Editable grid | Shared grid component for detail tables in spreadsheet mode |
| `pagination.py` | Pagination bar | Prev/next/first/last controls shared by all tables |
| `common.py` | Shared table utilities | Sortable column headers, search bar |

### `pickers/`
Settings-page pickers. Each is a self-contained Reflex component that reads/writes `ThemeState`.

| File | Picker | Controls |
|---|---|---|
| `color_picker.py` | Accent color | Radix color palette swatches |
| `asset_color_picker.py` | Asset type colors | Per-asset-type color swatches |
| `currency_picker.py` | Display currency | Dropdown of supported currencies |
| `language_picker.py` | Language | `en` / `fr` / `es` |
| `radius_picker.py` | Border radius | `none` / `small` / `medium` / `large` / `full` |
| `scaling_picker.py` | UI scale | `90%` / `95%` / `100%` / `105%` / `110%` |

### `connectors/`
| File | Wizard | Description |
|---|---|---|
| `file_connector_wizard.py` | File import | 4-step wizard: upload → column mapping → review → result. Built on `ConnectorState`. |
| `web_connector_wizard.py` | Web import | Profile selection, browser launch with live status updates, OTP prompts, result review. Built on `WebConnectorState`. |

---

## `config/`

### `event_collector.py` — `EventCollector` / `EventRecord`
A `logging.Handler` that maintains a ring-buffer (`deque`, default 50 records) of log records. Attached to the root logger by `logging_config.py`, so any `logger.info/warning/error()` call is captured automatically.

- **`emit(record)`** — Appends an `EventRecord` (level, summary truncated to 120 chars, full detail, ISO timestamp) to the buffer.
- **`drain()`** — Returns all buffered records and clears the buffer. Called by `NotificationState.load_events()` on each page load.
- **`peek()`** — Returns records without clearing.
- **`count`** — Number of currently buffered records.

The module-level `event_collector` singleton is imported by `logging_config.py` (which attaches it to the logger) and by `notification_state.py` (which drains it).

### `file_connector_config.py` — `FileConnectorPathStore`
Persists source file paths for connector history entries as a JSON file (`file_connector_paths.json`) in the app data directory. Used so the history table can display the original file path even after import.

- **`get(entry_id)`** — Returns the stored path string, or `""` if not found.
- **`set(entry_id, path)`** — Stores or updates the path for a history entry id.
- **`remove(entry_id)`** — Removes the path entry.

The module-level `file_connector_paths` singleton is imported by `connector_services.py`.

### `logging_config.py`
Sets up the Python logging hierarchy for the frontend: attaches the `EventCollector` handler to capture INFO+ records for the notification bell, and configures file/console output.

---

## `languages/`

Three locale files under `locale/`: `en.json`, `fr.json`, `es.json`. Each is a flat dict of `"key": "translated string"` pairs loaded into `ThemeState.translations` on language change via `load_translations(language)`.

Key naming conventions:
- Navigation: `"nav.overview"`, `"nav.securities"`, `"nav.cash"`, etc.
- Buttons: `"button.add"`, `"button.save"`, `"button.cancel"`, etc.
- Dialog titles: `"dialog.title.add_position"`, `"dialog.title.edit_cash"`, etc.

---

## `styles/`

### `styles.py`
CSS-in-Python style tokens referenced by all components.

| Token | Value | Description |
|---|---|---|
| `accent_text_color` | `rx.color("accent", 11)` | Primary interactive text colour |
| `accent_bg_color` | `rx.color("accent", 3)` | Hover/active background colour |
| `gray_bg_color` | `rx.color("gray", 3)` | Subtle background |
| `text_color` | `rx.color("gray", 11)` | Default text colour |
| `border_color` | `rx.color("gray", 6)` | Border/divider colour |
| `border_radius` | derived from `ThemeState.radius` | Applied to cards and buttons |

---

## `utils.py`
Small helpers used across the frontend.

- **`get_settings_path()`** — Returns the platform-appropriate path to the app settings JSON file (inside the Tauri app data directory).
- **`get_pie_color(index)`** — Returns a deterministic Radix color name for pie chart segments by index position.

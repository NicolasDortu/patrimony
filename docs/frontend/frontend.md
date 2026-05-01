# Frontend

The frontend is built with [Reflex](https://reflex.dev) and packaged inside a
Tauri shell. It is split into the layers below; the only entry point into the
backend is `frontend/services/`.

```
patrimony/frontend/
├── patrimony.py        # rx.App bootstrap (one level up at frontend root parent)
├── components/         # Reusable presentational widgets
├── config/             # Logging + per-feature config helpers
├── dialogs/            # Add/edit dialog builders
├── languages/locale/   # en.json / fr.json / es.json
├── pages/              # @template-decorated route components
├── services/           # The single bridge to the backend container
├── states/             # rx.State subclasses, mixins, helpers
├── styles/             # CSS-in-Python tokens
├── templates/          # Page wrapper, ThemeState, t() helper
├── utils.py            # parse_form_date, get_settings_path, _RADIX_COLORS …
└── views/
    ├── charts/         # Recharts wrappers
    ├── tables/         # Table + pagination + spreadsheet view
    ├── kpis/           # Stat cards (total, return, dividend, performers, allocation)
    ├── pickers/        # Settings pickers (currency, color, language, …)
    └── connectors/     # File + web connector wizards
```

## App bootstrap — `patrimony/patrimony.py`

```python
import reflex as rx

from .backend.config import setup_backend_logging
from .frontend.config import setup_frontend_logging
from .frontend.styles import styles
from .frontend.pages import *  # registers every page via its @template decorator

setup_backend_logging()
setup_frontend_logging()

app = rx.App(
    style=styles.base_style,
    stylesheets=styles.base_stylesheets,
)
```

Pages register themselves through the `@template(route, title, on_load)`
decorator — there is no explicit page list.

## Templates — `frontend/templates/template.py`

Three exports the rest of the frontend uses:

| Symbol | Purpose |
|---|---|
| `template` | Page decorator. Wraps the page content with the navbar, sidebar, theme provider, and an `on_mount` that loads `ThemeState`. |
| `ThemeState` | Persistent settings (accent/gray color, radius, scaling, default currency, language, asset-type colors, `show_browser`). Saves to `<app dir>/settings/settings.json` via `_save()` and rehydrates via `load_settings()`. Exposes `currency_symbol` as an `@rx.var`. |
| `t(key)` | Translation helper — `return ThemeState.translations[key]`. Used everywhere a string is rendered so the locale switch reactively updates the UI. |

When the user changes the language, `set_language(value)` reloads the
translations dict from disk and calls `_save()`. Components that depend on
`t(...)` re-render automatically.

## Pages — `frontend/pages/`

| Page | Purpose |
|---|---|
| `index.py` | Portfolio overview (KPIs + wealth chart + allocation/performers/dividend cards) |
| `securities.py` | Aggregated securities table, asset-type filter, chart toggle |
| `securities_detail.py` | Single-ticker detail (price chart + positions tab + dividends tab) |
| `cash.py` | Cash accounts table, total balance chart |
| `cash_operations.py` | Operations ledger for one account, income/expense chart |
| `properties.py` | Properties table + category allocation chart |
| `connectors.py` | Hub showing past import runs and links to the wizards |
| `file_connector.py` | CSV/Excel upload + column mapping wizard |
| `web_connector.py` | Web connector profile selection + credential vault |
| `settings.py` | Theme, currency, language, color & radius pickers |
| `about.py` | About / credits |

## States — `frontend/states/`

State classes are `rx.State` subclasses. Anything that powers a table view
mixes in the helpers from `mixins.py`:

```python
class CashTableState(
    SpreadsheetMixin, SearchSortMixin, PaginationMixin, AddDialogMixin, rx.State
):
    items: list[dict] = []
    is_loading: bool = False

    @rx.event
    async def on_page_load(self):
        self.is_loading = True
        yield                          # show spinner
        self.load_entries()
        self.is_loading = False
```

### Mixins (`states/mixins.py`)

| Mixin | Provides |
|---|---|
| `PaginationMixin` | `total_items`, `offset`, `limit`, `page_number`, `total_pages`, `prev_page`, `next_page`, `first_page`, `last_page` |
| `SearchSortMixin` | `search_value`, `sort_value`, `sort_reverse`, `chart_view` + `set_search_value`, `set_sort_value`, `toggle_chart_view`, `set_chart_view` |
| `AddDialogMixin` | `add_dialog_open: bool`, `set_add_dialog_open(value)` for controlled add-entity dialogs |
| `SpreadsheetMixin` | Toggles between regular table and spreadsheet (CSV-style) view |

`apply_sort_and_search(items, sort_value, sort_reverse, search_value, …)` is
the generic filter+sort used by every table state. It works on both `dict`
items and dataclass items via the `accessor` parameter.

### Per-feature states

| Class | Backed page |
|---|---|
| `PortfolioState` | `index` |
| `TableStateTotal` | `securities` |
| `TableStateDetails` | `securities_detail` |
| `CashTableState` | `cash` |
| `CashOperationsState` | `cash_operations` |
| `PropertiesState` | `properties` |
| `DividendsState` | dividends widget on the index + detail pages |
| `ConnectorState` | `file_connector` |
| `WebConnectorState` | `web_connector` |
| `ConnectorHistoryState` | `connectors` |
| `NotificationState` | global toast queue |

### Cross-state access pattern

For a state that depends on values owned by another state (e.g. `ThemeState`),
use the async `await self.get_state(OtherState)` pattern inside an
`@rx.var` or `@rx.event`:

```python
@rx.var
async def asset_type_allocation(self) -> list[dict]:
    theme = await self.get_state(ThemeState)
    tr = theme.translations
    ...
```

This keeps the state graph reactive — the var recomputes when the language
changes.

## Services — `frontend/services/`

This package is **the only place the frontend talks to the backend**.
It instantiates the DI `Container`, resolves use cases and exposes them as
classmethods so state classes can call them without holding a reference.

| Module | Wraps |
|---|---|
| `asset_services.py` | `SecuritiesUseCases`, `PropertyUseCases`, `DividendUseCases`, `PortfolioUseCases` |
| `cash_services.py` | `CashUseCases` |
| `connector_services.py` | `FileImportUseCases`, `WebConnectorUseCases`, `ConnectorHistoryUseCases` |
| `event_services.py` | `event_log_repository` reads |
| `models.py` | `OperationResult` dataclass + `@operation_result(...)` and `@safe_query(...)` decorators |

`@operation_result(failure="…", success="…")` wraps mutations so every state
handler receives a uniform `OperationResult(success, message, data)` value.
`@safe_query(default=…)` does the same for read paths but returns `default` on
failure rather than surfacing an error. This keeps the UI free of
try/except blocks.

## Components — `frontend/components/`

| Module | Purpose |
|---|---|
| `card.py` | `card()` and `stats_card()` — styled containers used across the app |
| `navigation.py` | `navbar()` + `sidebar()` |
| `chart_toggle.py` | Chart ↔ table toggle button |
| `donut_chart.py` | Reusable donut/pie chart with translated legend |
| `empty_table.py` | Empty-state placeholder |
| `loading.py` | `loading_spinner()` |
| `notification.py` | Toast queue rendering |
| `dialog_factory.py` | `build_add_dialog(...)` + `DialogField` dataclass — emits a controlled rx.dialog with translated labels and a uniform Cancel/Submit footer |

## Dialogs — `frontend/dialogs/`

| Module | Form |
|---|---|
| `cash_dialog.py` | Add cash account |
| `cash_operation_dialog.py` | Add cash operation |
| `position_dialog.py` | Add security position (with ticker autocomplete and translated asset-type select) |
| `dividend_dialog.py` | Add dividend |
| `property_dialog.py` | Add property |

All dialogs are controlled via `AddDialogMixin.add_dialog_open`. Submit
handlers only set `add_dialog_open = False` on success, so validation
errors keep the dialog open with the user's input intact.

## Views

### Charts — `frontend/views/charts/`

| Module | Purpose |
|---|---|
| `wealth_chart.py` | Stacked area / bar chart of total wealth per asset |
| `securities_charts.py` | Securities allocation pie + value chart |
| `cash_charts.py` | Cash balance + income/expense bar chart |
| `expense_chart.py` | Income vs expense (cash operations page) |
| `properties_charts.py` | Property value pie chart |
| `stock_chart.py` | Single-ticker price chart |
| `common.py` | Shared axis/tooltip helpers |

### Tables — `frontend/views/tables/`

| Module | Purpose |
|---|---|
| `securities_total_table.py` | Aggregated holdings table |
| `securities_details_table.py` | Per-ticker transaction history |
| `cash_table.py` | Cash accounts table |
| `cash_operations_table.py` | Operations ledger |
| `properties_table.py` | Properties table |
| `dividends_table.py` | Dividend history (with total in toolbar) |
| `pagination.py` | Pagination control |
| `common.py` | `header_cell`, `table_row`, `table_toolbar`, sort dropdown |
| `spreadsheet_view.py` | CSV-grid view + toggle button |

### KPIs — `frontend/views/kpis/`

| Module | Purpose |
|---|---|
| `portfolio_stats_card.py` | Total value, total return, total invested cards |
| `portfolio_allocation.py` | Asset-type donut |
| `portfolio_performers.py` | Top / bottom 5 performers |
| `dividend_summary.py` | Total dividends + yield |

### Pickers — `frontend/views/pickers/`

`currency_picker.py`, `color_picker.py`, `asset_color_picker.py`,
`radius_picker.py`, `scaling_picker.py`, `language_picker.py` — all rebind to
a `set_*` event on `ThemeState`.

### Connectors — `frontend/views/connectors/`

`file_connector_wizard.py` and `web_connector_wizard.py` drive the multi-step
import flows.

## i18n

Locale files live under `frontend/languages/locale/` as flat
`{"key": "translation"}` JSON dictionaries. `load_translations(lang)` reads
the requested file (falling back to `en.json` for unknown languages) and
populates `ThemeState.translations`.

`AVAILABLE_LANGUAGES = {"en": "English", "fr": "Français", "es": "Español"}`.

A unit test (`tests/unit/test_translations.py`) enforces that every key
present in `en.json` is also present in `fr.json` and `es.json` and that
non-English translations differ from the English value (catching unfinished
translations).

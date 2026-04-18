# Infrastructure Integrations

Concrete implementations of the domain-level `MarketDataProvider`, `FileConnector`, and `SiteConnector` interfaces. These are the only places in the codebase that touch external APIs, file I/O, and browser automation.

## Files

| File | Implements | Description |
|---|---|---|
| `file_connector.py` | `FileConnector` | Parses CSV and Excel files into Polars DataFrames |
| `market_data_provider.py` | `MarketDataProvider` | Yahoo Finance API via yfinance |
| `web_connector/` | `SiteConnector` | Playwright browser automation per broker |

---

## `file_connector.py` — `ExcelCsvConnector`

A thin file-parsing adapter. All columns are read as raw strings (`infer_schema=False`) — the domain layer is responsible for type coercion during import.

- **`read_file(file_bytes, filename, delimiter)`** — Detects format from the file extension:
  - `.csv` → `pl.read_csv(buf, separator=delimiter, infer_schema=False)`
  - `.xlsx` / `.xls` → `pl.read_excel(buf, infer_schema_length=0)`
  - Anything else → raises `ValueError`

---

## `market_data_provider.py` — `YahooFinanceProvider`

The only market data source in the application. Wraps the `yfinance` Python library.

**Rate limiting:** all methods call `_throttle()` before hitting the API. This enforces a minimum interval of `0.55s` between calls using a `threading.Lock`, preventing Yahoo Finance from rate-limiting the application. The lock also sets `_provider_was_called = True` for telemetry.

### Internal helpers

- **`_throttle()`** — Thread-safe rate limiter. Sleeps if the last call was less than 0.55s ago.
- **`_parse_history_df(data)`** — Converts a yfinance pandas history DataFrame to Polars `(date, close_price)`. Handles both `Date` (daily) and `Datetime` (intraday) index column names.

### Provider methods

- **`get_current_price(ticker)`** — Fetches `period="1d"` history and returns the last closing price. Returns `None` on any failure.
- **`get_price_history(ticker, start_date, end_date, interval, *, period)`** — Fetches OHLCV history. Prefers `period` if supplied; otherwise uses the `(start_date, end_date)` range. Returns `(date, close_price)` DataFrame or an empty DataFrame on failure.
- **`get_ticker_currency(ticker)`** — Reads `info["currency"]` from the yfinance ticker dict. Returns `None` on failure.
- **`get_exchange_rate(from_currency, to_currency)`** — Constructs a composite ticker like `"EURUSD=X"` and fetches its price. Returns `None` on failure.
- **`get_dividend_history(ticker, start_date, end_date)`** — Calls `yf.Ticker.dividends`, filters to the date range, and returns `(date, amount_per_share)` DataFrame. Returns empty DataFrame on failure.
- **`resolve_ticker_info(identifier)`** — Calls `yf.Ticker(identifier).info`, maps `quoteType` to a domain `AssetType` via `_QUOTE_TYPE_MAP`, and returns a `TickerInfo` entity. Returns `None` if resolution fails or `symbol` is missing from the response.

### `_QUOTE_TYPE_MAP`

Maps yfinance `quoteType` strings to domain `AssetType` values:

| yfinance quoteType | Domain AssetType |
|---|---|
| `EQUITY` | `STOCK` |
| `ETF` | `ETF` |
| `CRYPTOCURRENCY` | `CRYPTO` |
| `FUTURE` | `COMMODITY` |
| `BOND` / `FIXED_INCOME` | `BOND` |

---

## `web_connector/`

See the [web connector README](web_connector.md) for full details.

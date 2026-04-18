# Domain Services

Business logic lives here. Each service is a pure Python class that orchestrates repositories and other services to implement domain rules. No HTTP, no database drivers, no framework imports — only domain entities, interfaces, and repositories.

## Files

| File | Responsibility |
|---|---|
| `cash_service.py` | Cash balance aggregation and historical timeline |
| `chart_service.py` | Time-series chart data for portfolio and single-ticker views |
| `currency_service.py` | Currency resolution, FX rates, and value conversion |
| `dividend_service.py` | Dividend sync from market data |
| `portfolio_service.py` | Portfolio-wide aggregation and overview |
| `price_service.py` | Price fetching, intraday sync, and chart timeline preparation |
| `property_service.py` | Physical property value aggregation |
| `securities_service.py` | Securities enrichment, price injection, and metrics |
| `timeline.py` | Shared date/quantity utilities used across services |
| `connectors/` | Import pipeline (file and web connector) |

---

## `timeline.py`

Stateless utility functions shared by `ChartService` and `DividendService`.

- **`normalize_date(dt)`** — Converts any `datetime`, Polars timestamp, or `date` value to a plain `datetime.date`. Used everywhere to ensure consistent date comparisons.

- **`build_quantity_timeline(securities_repo)`** — Reads all positions from the repository and constructs a per-ticker cumulative quantity timeline:  
  `dict[ticker, list[(date, cumulative_quantity)]]`  
  The list is sorted by date so binary search can be used to look up quantity at any point in time.

- **`get_quantity_at_date(quantity_timeline, ticker, dt)`** — Binary-searches the prebuilt timeline to find the quantity of a ticker held at a specific date. Returns `0.0` if no positions existed yet.

---

## `cash_service.py` — `CashService`

**Dependencies:** `CashRepository`, `CurrencyService`

- **`get_total_balance(user_currency)`** — Returns the sum of all cash account balances, each converted to `user_currency` using current FX rates.

- **`get_balance_timeline(user_currency)`** — Builds a `dict[date, total_balance]` showing how the total cash balance evolved over time. Iterates over all historical balance operations, converts each account's currency once (cached per currency), and accumulates a running total per date. Used by `ChartService` to add a cash series to portfolio charts.

---

## `currency_service.py` — `CurrencyService`

**Dependencies:** `CurrencyRepository`, `MarketDataProvider`

- **`get_ticker_currency(ticker)`** — Returns the native trading currency for a ticker. Checks the cache first; if missing, calls the market data API and stores the result. Falls back to `"EUR"` with a warning if resolution fails.

- **`get_exchange_rate(from_currency, to_currency)`** — Returns the FX rate to convert one currency to another. Returns `1.0` immediately for same-currency pairs. Checks the cache first, then calls the API, caches the result, and falls back to `1.0` on failure.

- **`get_rates_for_tickers(tickers, user_currency)`** — Returns `dict[ticker, rate]` for a list of tickers, where `rate` multiplied by the ticker's native price gives the value in `user_currency`. Internally caches rates by currency to avoid duplicate lookups within the same call.

- **`apply_conversion(df, user_currency)`** — Takes a positions DataFrame with `(ticker, current_price, avg_price, total_quantity)` columns and multiplies `current_price` and `avg_price` by the appropriate FX rate. Recomputes `total_value = current_price × total_quantity` after conversion.

- **`sum_with_conversion(df, value_col, target_currency)`** — Sums a numeric column across a DataFrame, converting each row from its own currency to `target_currency`. Handles mixed-currency DataFrames. Returns `0.0` if the DataFrame is empty or `None`.

---

## `dividend_service.py` — `DividendService`

**Dependencies:** `DividendRepository`, `SecuritiesRepository`, `MarketDataProvider`

- **`sync_dividends(tickers)`** — Top-level sync entry point. Builds a quantity timeline once (reused across all tickers), then syncs each ticker individually. Aggregates and returns `{imported, skipped, errors}`.

- **`_sync_ticker_dividends(ticker, quantity_timeline)`** — Syncs dividends for a single ticker:
  1. Determines earliest purchase date to bound the API request.
  2. Fetches dividend history from the market data provider.
  3. Compares against already-stored dividends to skip duplicates.
  4. For each new dividend date, looks up the held quantity at that date.
  5. Computes `total_amount = amount_per_share × quantity` and stores the result.

---

## `portfolio_service.py` — `PortfolioService`

**Dependencies:** `SecuritiesService`, `CashService`, `PropertyService`, `ChartService`

The top-level orchestrator for portfolio-wide data.

- **`get_overview(user_currency)`** — Builds a `PortfolioOverview` entity by:
  1. Calling `SecuritiesService.calculate_metrics()` for total invested, securities value, and return %.
  2. Calling `CashService.get_total_balance()` for cash value.
  3. Calling `PropertyService.get_total_value()` for property value.
  4. Summing them into a `PortfolioOverview` dataclass.

- **`get_chart_data(period, user_currency)`** — Delegates to `ChartService.get_portfolio_chart_data()` with the current securities map, cash balance, and property value. The `period` controls the time window (e.g. `"1M"`, `"1D"`).

- **`_build_securities_map(user_currency)`** — *(private helper)* Returns `dict[ticker, {asset_type, avg_price}]` for chart use.

---

## `price_service.py` — `PriceService`

**Dependencies:** `PriceRepository`, `MarketDataProvider`

Handles all price data concerns: live price fetching, intraday sync, historical sync, and chart timeline preparation.

### Live prices

- **`get_current_prices(tickers, max_age_minutes=15)`** — Returns `dict[ticker, price]` using a 3-tier strategy:
  1. **Intraday table** — checks `get_latest_intraday_prices()` for fresh recent data.
  2. **Price cache** — falls back to `get_cached_prices()` for tickers still missing.
  3. **API** — fetches remaining tickers live from the market data provider and stores in cache.

### Chart timeline helpers

- **`sort_and_forward_fill(ticker_data, all_dates_set)`** — Static method. Sorts all dates and fills gaps in each ticker's price dict by carrying the last valid price forward. A price is invalid if it is `None`, `NaN`, or `<= 0`. Returns `(ticker_data, sorted_dates)`.

- **`inject_today_prices(ticker_data, tickers, all_dates)`** — Appends today's price as the final chart point if today is not already in `all_dates`. Uses `get_current_prices()` to fetch live prices. Modifies `ticker_data` in place and returns the updated `all_dates` list.

### Sync operations

- **`sync_intraday(tickers, interval="5m", max_age_minutes=15)`** — For each ticker, checks how old its intraday data is. If stale (or absent), fetches a fresh `period="1d"` history from the API and replaces the stored rows.

- **`sync_price_history(tickers, start_date, period="1d")`** — Fetches and stores only **missing** price history. Sorts tickers by staleness (oldest-updated first) so the most out-of-date data is refreshed first. For each ticker, fills both the early gap (before `min_stored_date`) and the recent gap (after `max_stored_date`).

- **`_fetch_and_store(ticker, start, end, period)`** — *(private)* Fetches price history for a date range and stores it if the result is non-empty.

---

## `property_service.py` — `PropertyService`

**Dependencies:** `PropertyRepository`, `CurrencyService`

- **`get_total_value(user_currency)`** — Returns the total value of all properties converted to `user_currency`. Fetches per-currency totals from `get_total_value_by_currency()` and sums them with conversion via `CurrencyService.sum_with_conversion()`.

---

## `securities_service.py` — `SecuritiesService`

**Dependencies:** `SecuritiesRepository`, `CurrencyService`, `PriceService`

- **`get_aggregated_positions(user_currency)`** — Returns a Polars DataFrame of all aggregated positions with:
  1. Current prices injected via `_enrich_with_prices()`.
  2. All monetary columns converted to `user_currency` via `CurrencyService.apply_conversion()`.

- **`_enrich_with_prices(df)`** — *(private)* Bulk-fetches current prices for all tickers in the DataFrame, adds a `current_price` column, and recomputes `total_value = current_price × total_quantity`.

- **`calculate_metrics(user_currency)`** — Returns `(total_invested, securities_value, return_pct)`:
  1. Calls `get_aggregated_positions()` for fully enriched and converted positions.
  2. Filters to rows with valid quantity and price.
  3. Uses `math.fsum` for numerically stable summation of invested vs. current value.
  4. Computes `return_pct = (value - invested) / invested × 100`.

---

## `chart_service.py` — `ChartService`

**Dependencies:** `SecuritiesRepository`, `CashService`, `PriceRepository`, `CurrencyService`, `PriceService`

Builds time-series chart data for both portfolio-level and single-ticker views.

### Public API

- **`get_portfolio_chart_data(period, user_currency, securities, current_cash, properties_value)`** — Builds the full portfolio chart. Returns a list of row dicts like `{Date, Stocks, ETFs, Cash, Properties, Total}`.
  1. Determines config for the period (days, interval, format).
  2. Fetches intraday or daily prices depending on `period == "1D"`.
  3. Ensures the date list covers cash-only portfolios (`_fill_date_gaps`).
  4. Injects today's live price as the final point (for non-intraday views).
  5. Assembles rows via `_build_portfolio_rows`.

- **`get_ticker_chart_data(ticker, period, user_currency)`** — Builds a single-ticker chart. Returns `[{name: <formatted_date>, price: <value>}]`. Multiplies prices by the held quantity and FX rate so the Y-axis shows portfolio value in `user_currency`.

### Private helpers

- **`_fetch_intraday_prices(tickers, config)`** — Triggers `PriceService.sync_intraday()` then loads intraday rows from the DB. Filters out timestamps whose **time-of-day** is later than `now.time()` to prevent weekend charts from showing future hours. Delegates forward-filling to `PriceService.sort_and_forward_fill()`.

- **`_fetch_daily_prices(tickers, config, ticker=None)`** — Determines the date window (clamped to earliest purchase date, with a minimum of `MIN_CHART_DAYS`). Triggers `PriceService.sync_price_history()` then loads rows from the DB. Normalizes dates to `date` objects.

- **`_fill_date_gaps(all_dates, cash_timeline, config)`** — If no price data exists (securities-free portfolio), fills `all_dates` from the cash timeline so cash accounts still appear on the chart.

- **`_build_portfolio_rows(securities, ticker_data, all_dates, cash_timeline, current_cash, date_fmt, rates, quantity_timeline, properties_value)`** — Static method. For each date in `all_dates`, computes the total value of each asset type bucket by multiplying quantity × price × FX rate. Looks up the cash balance at each date using binary search on the cash timeline. Returns a list of row dicts.

---

## `connectors/`

See the [connectors README](connectors.md) for full details.

In brief:
- **`import_service.py`** — Core file import pipeline (column mapping, validation, deduplication, insertion).
- **`web_connector_service.py`** — Orchestrates browser-based connectors end-to-end.
- **`ticker_resolution.py`** — Resolution cascade: cache → reference table → yfinance API.
- **`helpers.py`** — Shared data classes, constants, and parsing utilities for the import pipeline.

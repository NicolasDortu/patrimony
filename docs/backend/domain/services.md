# Domain services

Domain services hold business logic that does not naturally belong to a single
entity. They depend only on repository interfaces and other domain services
(plus `MarketDataProvider` for live data).

| Module | Class | Depends on |
|---|---|---|
| `cash_service.py` | `CashService` | `CashRepository`, `CurrencyService` |
| `chart_service.py` | `ChartService` | `SecuritiesRepository`, `SecuritiesService`, `CashService`, `PropertyService`, `PriceRepository`, `CurrencyService`, `PriceService` |
| `currency_service.py` | `CurrencyService` | `CurrencyRepository`, `MarketDataProvider` |
| `dividend_service.py` | `DividendService` | `DividendRepository`, `SecuritiesRepository`, `SecuritiesService`, `MarketDataProvider`, `CurrencyService` |
| `portfolio_service.py` | `PortfolioService` | `SecuritiesService`, `CashService`, `PropertyService`, `ChartService`, `DividendService` |
| `price_service.py` | `PriceService` | `PriceRepository`, `MarketDataProvider` |
| `property_service.py` | `PropertyService` | `PropertyRepository`, `CurrencyService` |
| `securities_service.py` | `SecuritiesService` | `SecuritiesRepository`, `CurrencyService`, `PriceService` |
| `date_utils.py` | `normalize_date(dt) -> date` | (pure function) |
| `connectors/file_connector_service.py` | `FileConnectorService` | repos + parser + `MarketDataProvider` |
| `connectors/web_connector_service.py` | `WebConnectorService` | site connector registry |

## `CurrencyService`

Resolves ticker → currency, fetches FX rates, and converts Polars DataFrames.

```python
get_ticker_currency(ticker) -> str
get_exchange_rate(from_currency, to_currency) -> float
get_rates_for_tickers(tickers, user_currency) -> dict[ticker, rate]
apply_conversion(df: pl.DataFrame, user_currency) -> pl.DataFrame
sum_with_conversion(df, value_col, target_currency) -> float
```

Resolution order for `get_exchange_rate`:
1. identity (same currency → 1.0)
2. in-process cache (15 min TTL)
3. fresh repo cache
4. live provider (write-through to repo + cache on success)
5. stale repo cache (up to ~30 days) with a warning log

`get_ticker_currency` raises `TickerCurrencyUnknownError` if neither cache nor
provider can resolve the ticker.

## `PriceService`

```python
get_current_prices(tickers, max_age_minutes=15) -> dict[ticker, price]
sync_prices(tickers)                       # writes to PriceRepository
sync_intraday(ticker, interval="5m")
```
Reads cached prices first, only calls the provider for stale or missing
tickers.

## `SecuritiesService`

```python
get_aggregated_positions(user_currency) -> pl.DataFrame
calculate_metrics(user_currency) -> dict
```
Aggregates open positions from `SecuritiesRepository`, enriches with current
prices via `PriceService`, then converts to `user_currency` via
`CurrencyService.apply_conversion`.

## `DividendService`

```python
get_total_in_currency(user_currency) -> float
sync_dividends(tickers, start_date)        # writes to DividendRepository
```

## `CashService`

```python
get_total_balance(user_currency) -> float
get_balance_timeline(user_currency) -> pl.DataFrame
```

## `PropertyService`

```python
get_total_value(user_currency) -> float
get_value_timeline(user_currency) -> pl.DataFrame
```

## `ChartService`

```python
get_portfolio_chart_data(period, user_currency, securities) -> list[dict]
get_ticker_chart_data(ticker, period, user_currency) -> list[dict]
```
Reads from `PriceRepository` (history + intraday), fills gaps via
`PriceService`, normalises currency, and returns rows ready for the recharts
component.

## `PortfolioService`

```python
get_overview(user_currency) -> PortfolioOverview
```
Sums securities + cash + properties values, computes total return and
total return with dividends.

## `date_utils`

```python
normalize_date(dt) -> date
```
Coerces `datetime`, `date`, or anything with a `.date()` method to a plain
`date`. Used everywhere a chart key or DB filter needs a stable date type.

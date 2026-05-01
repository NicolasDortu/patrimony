# Integrations

External-service adapters live in `infrastructure/integrations/`.

## yfinance — `YahooFinanceProvider`

Implements `MarketDataProvider`. All public methods are wrapped in a
`_throttle()` helper that enforces a minimum interval between calls so we
don't get rate-limited by Yahoo.

```python
get_current_price(ticker) -> float | None
get_price_history(ticker, start_date, end_date, interval, period) -> pl.DataFrame
get_dividend_history(ticker, start_date, end_date) -> pl.DataFrame
get_exchange_rate(from_currency, to_currency) -> float | None
get_ticker_currency(ticker) -> str | None
resolve_ticker_info(ticker) -> TickerInfo | None
```

Implementation notes:

- `_throttle()` uses a class-level `threading.Lock` and a monotonic clock so
  concurrent requests serialise behind a `~0.55s` minimum gap.
- Every successful call flips `_provider_was_called = True`. Reset via
  `check_provider_was_called()`, which atomically reads-and-clears the flag.
- All methods return `None` (or empty DataFrames) on failure rather than
  raising — domain services are responsible for converting that into a
  `PriceSyncError` / `CurrencyConversionError` if the situation actually
  warrants surfacing it to the user.
- Currency for an FX pair is fetched as a synthetic `"{FROM}{TO}=X"` ticker.

## File parser — `ExcelCsvConnector`

Implements `FileConnector`.

```python
read_file(file_bytes: bytes, filename: str, delimiter: str = ",", encoding: str = "utf-8") -> pl.DataFrame
```

Format is sniffed from the file extension:

| Extension | Backend |
|---|---|
| `.csv` | Polars `read_csv` (delimiter passed through) |
| `.xlsx` | Polars `read_excel` (uses `fastexcel` engine) |
| `.xls` | Polars `read_excel` |

The connector does not interpret column names — that's the file connector
service's job. It only returns a normalised DataFrame.

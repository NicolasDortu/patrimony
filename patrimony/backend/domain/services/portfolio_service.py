"""Domain service for portfolio-wide operations and metrics.

Orchestrates securities, cash, prices, and currency conversion
to provide portfolio views and chart data.
"""

from datetime import datetime, timedelta
from typing import Optional

import polars as pl

from ..constants import ASSET_TYPE_LABELS, PERIOD_CONFIG
from ..entities import PortfolioOverview
from ..interfaces import MarketDataProvider
from ..repositories import (
    CashRepository,
    PriceRepository,
    SecuritiesRepository,
)
from .currency_service import CurrencyService
from .enrichment_utilities import (
    apply_currency_conversion,
    enrich_with_prices,
    forward_fill_prices,
    normalize_date,
)


class PortfolioService:
    """Domain service for portfolio aggregation and chart building."""

    def __init__(
        self,
        securities_repo: SecuritiesRepository,
        cash_repo: CashRepository,
        price_repo: PriceRepository,
        currency_service: CurrencyService,
        market_data: MarketDataProvider,
    ):
        self._securities_repo = securities_repo
        self._cash_repo = cash_repo
        self._price_repo = price_repo
        self._currency_service = currency_service
        self._market_data = market_data

    # -- Portfolio Overview --------------------------------------------------

    def get_overview(self, user_currency: str = "EUR") -> PortfolioOverview:
        """Build a complete portfolio overview with metrics."""
        # Securities
        securities_df = self._securities_repo.get_aggregated_positions()
        if securities_df is not None and not securities_df.is_empty():
            securities_df = enrich_with_prices(securities_df, self._price_repo)
            securities_df = apply_currency_conversion(
                securities_df, self._currency_service, user_currency
            )

        total_invested, securities_value, total_return = (
            self._calculate_securities_metrics(securities_df)
        )

        # Cash
        cash_df = self._cash_repo.get_all()
        cash_value = self._calculate_cash_value(cash_df, user_currency)

        return PortfolioOverview(
            securities_total=securities_df,
            cash_entries=cash_df,
            total_value=securities_value + cash_value,
            total_invested=total_invested,
            total_return=total_return,
            securities_value=securities_value,
            cash_value=cash_value,
        )

    # -- Chart Data ----------------------------------------------------------

    def get_chart_data(
        self, period: str = "1M", user_currency: str = "EUR"
    ) -> list[dict]:
        """Build time-series chart data for the entire portfolio."""
        config = PERIOD_CONFIG.get(period, PERIOD_CONFIG["1M"])
        is_intraday = period == "1D"

        securities = self._get_all_securities()
        current_cash = self._calculate_cash_value(
            self._cash_repo.get_all(), user_currency
        )
        cash_timeline = self._build_cash_timeline(user_currency)
        quantity_timeline = self._build_quantity_timeline()

        rates, ticker_data, all_dates = self._resolve_price_timeline(
            securities, config, is_intraday, user_currency
        )

        all_dates = self._fill_date_gaps(
            all_dates, cash_timeline, config, is_intraday, securities, ticker_data
        )

        if not all_dates:
            return []

        date_fmt = (
            "%H:%M" if is_intraday else ("%Y-%m" if config["days"] > 365 else "%d/%m")
        )

        return self._build_chart_rows(
            securities,
            ticker_data,
            all_dates,
            cash_timeline,
            current_cash,
            date_fmt,
            rates,
            quantity_timeline,
        )

    def _resolve_price_timeline(
        self,
        securities: dict[str, dict],
        config: dict,
        is_intraday: bool,
        user_currency: str,
    ) -> tuple[dict[str, float], dict[str, dict], list]:
        """Fetch exchange rates and price timelines for all securities."""
        if not securities:
            return {}, {}, []

        rates = self._currency_service.get_rates_for_tickers(
            list(securities.keys()), user_currency
        )
        ticker_data, all_dates = self._fetch_ticker_prices(
            list(securities.keys()), config, is_intraday
        )
        return rates, ticker_data, all_dates

    def _fill_date_gaps(
        self,
        all_dates: list,
        cash_timeline: dict,
        config: dict,
        is_intraday: bool,
        securities: dict[str, dict],
        ticker_data: dict[str, dict],
    ) -> list:
        """Ensure date list covers cash-only portfolios and includes today."""
        # For cash-only portfolios, build date range from cash timeline
        if not all_dates and cash_timeline:
            start_date = (datetime.now() - timedelta(days=config["days"])).date()
            all_dates = sorted(
                {
                    normalize_date(d)
                    for d in cash_timeline
                    if normalize_date(d) >= start_date
                }
            )

        # Add today's data point for non-intraday charts
        if not is_intraday:
            today = datetime.now().date()
            existing = {normalize_date(d) for d in all_dates} if all_dates else set()
            if today not in existing:
                for ticker in securities:
                    price = self._price_repo.get_current_price(ticker)
                    if price:
                        ticker_data.setdefault(ticker, {})[today] = price
                all_dates.append(today)

        return all_dates

    # -- Internal helpers ----------------------------------------------------

    def _calculate_securities_metrics(
        self, df: Optional[pl.DataFrame]
    ) -> tuple[float, float, float]:
        if df is None or df.is_empty():
            return 0.0, 0.0, 0.0

        valid_df = df.filter(
            pl.col("current_price").is_not_null()
            & pl.col("total_quantity").is_not_null()
            & (pl.col("total_quantity") > 0)
        )
        if valid_df.is_empty():
            return 0.0, 0.0, 0.0

        return PortfolioService._calculate_metrics(
            quantities=valid_df["total_quantity"].to_list(),
            buy_prices=valid_df["avg_price"].to_list(),
            current_prices=valid_df["current_price"].to_list(),
        )

    @staticmethod
    def _calculate_metrics(
        quantities: list[float],
        buy_prices: list[float],
        current_prices: list[float],
    ) -> tuple[float, float, float]:
        """Calculate total invested, current value, and return percentage."""
        import math

        total_invested = math.fsum(q * p for q, p in zip(quantities, buy_prices))
        total_value = math.fsum(q * p for q, p in zip(quantities, current_prices))
        return_percentage = (
            ((total_value - total_invested) / total_invested * 100)
            if total_invested > 0
            else 0.0
        )
        return total_invested, total_value, return_percentage

    def _calculate_cash_value(
        self, df: Optional[pl.DataFrame], user_currency: str
    ) -> float:
        if df is None or df.is_empty():
            return 0.0
        if "currency" in df.columns:
            total = 0.0
            rate_cache: dict[str, float] = {}
            for row in df.iter_rows(named=True):
                cash_curr = row.get("currency", "EUR")
                if cash_curr not in rate_cache:
                    rate_cache[cash_curr] = self._currency_service.get_exchange_rate(
                        cash_curr, user_currency
                    )
                total += row["balance"] * rate_cache[cash_curr]
            return total
        return float(df["balance"].sum())

    def _build_cash_timeline(self, user_currency: str) -> dict:
        """Build a timeline of total cash balance keyed by date."""
        df = self._cash_repo.get_cash_balance_history()
        if df is None or df.is_empty():
            return {}

        account_currencies: dict[str, str] = {}
        rate_cache: dict[str, float] = {}
        all_cash = self._cash_repo.get_all()
        if all_cash is not None and not all_cash.is_empty():
            for row in all_cash.iter_rows(named=True):
                account_currencies[row["account_number"]] = row.get("currency", "EUR")

        account_balances: dict[str, float] = {}
        timeline: dict = {}

        for row in df.iter_rows(named=True):
            key = row["account_number"]
            balance = row["balance"]

            cash_curr = account_currencies.get(key, "EUR")
            if cash_curr not in rate_cache:
                rate_cache[cash_curr] = self._currency_service.get_exchange_rate(
                    cash_curr, user_currency
                )
            balance *= rate_cache[cash_curr]

            account_balances[key] = balance
            timeline[row["operation_date"]] = sum(account_balances.values())

        return timeline

    def _get_all_securities(self) -> dict[str, dict]:
        df = self._securities_repo.get_aggregated_positions()
        if df is None or df.is_empty():
            return {}
        df = df.filter(pl.col("total_quantity") > 0)
        if df.is_empty():
            return {}
        return {
            t: {"quantity": float(q), "asset_type": at}
            for t, q, at in zip(
                df["ticker"].to_list(),
                df["total_quantity"].to_list(),
                df["asset_type"].to_list(),
            )
        }

    def _build_quantity_timeline(self) -> dict[str, list[tuple]]:
        """Build per-ticker cumulative quantity timeline from individual positions.

        Returns a dict mapping ticker -> sorted list of (date, cumulative_quantity).
        """
        df = self._securities_repo.get_all()
        if df is None or df.is_empty():
            return {}

        result = df.sort("date").with_columns(
            pl.col("quantity").cum_sum().over("ticker").alias("cum_qty"),
            pl.col("date")
            .map_elements(normalize_date, return_dtype=pl.Date)
            .alias("norm_date"),
        )

        timeline: dict[str, list[tuple]] = {}
        for ticker in result["ticker"].unique().to_list():
            ticker_df = result.filter(pl.col("ticker") == ticker)
            timeline[ticker] = list(
                zip(ticker_df["norm_date"].to_list(), ticker_df["cum_qty"].to_list())
            )
        return timeline

    @staticmethod
    def _get_quantity_at_date(
        quantity_timeline: dict[str, list[tuple]], ticker: str, dt
    ) -> float:
        """Get the cumulative quantity held for a ticker at a given date."""
        entries = quantity_timeline.get(ticker, [])
        if not entries:
            return 0.0
        dt_date = normalize_date(dt)
        result = 0.0
        for entry_date, qty in entries:
            if entry_date <= dt_date:
                result = qty
            else:
                break
        return result

    def _fetch_ticker_prices(
        self, tickers: list[str], config: dict, is_intraday: bool
    ) -> tuple[dict[str, dict], list]:
        ticker_data: dict[str, dict] = {}
        all_dates_set: set = set()

        if is_intraday:
            for ticker in tickers:
                df = self._market_data.get_price_history_period(
                    ticker, period=config["period"], interval=config["interval"]
                )
                if df is not None and not df.is_empty():
                    dates = df["date"].to_list()
                    prices = df["close_price"].to_list()
                    ticker_data[ticker] = dict(zip(dates, prices))
                    all_dates_set.update(dates)
        else:
            start = datetime.now() - timedelta(days=config["days"])
            earliest = self._securities_repo.get_earliest_purchase_date()
            if earliest is not None:
                earliest_dt = (
                    datetime.combine(earliest, datetime.min.time())
                    if not isinstance(earliest, datetime)
                    else earliest
                )
                if earliest_dt > start:
                    start = earliest_dt
            end = datetime.now()
            # Ensure at least a 2-day range so charts always have data
            if (end - start).days < 2:
                start = end - timedelta(days=2)
            self._price_repo.sync_price_history(tickers, start)
            df = self._price_repo.get_price_history(tickers, start, end)
            if df is not None and not df.is_empty():
                # Build ticker -> {date: price} dicts using column access
                for ticker in df["ticker"].unique().to_list():
                    mask = df["ticker"] == ticker
                    t_df = df.filter(mask)
                    dates = t_df["date"].to_list()
                    prices = t_df["close_price"].to_list()
                    td = {}
                    for d, p in zip(dates, prices):
                        day = normalize_date(d)
                        td[day] = p
                        all_dates_set.add(day)
                    ticker_data[ticker] = td

        sorted_dates = sorted(all_dates_set)

        # Forward-fill: replace missing/0/None with last known price
        for ticker in ticker_data:
            forward_fill_prices(ticker_data[ticker], sorted_dates)

        return ticker_data, sorted_dates

    @staticmethod
    def _get_cash_at_date(cash_timeline: dict, dt, current_cash: float) -> float:
        if not cash_timeline:
            return current_cash

        dt_date = normalize_date(dt)

        best_value = None
        for timeline_dt, value in cash_timeline.items():
            tl_date = normalize_date(timeline_dt)
            if tl_date <= dt_date:
                if best_value is None or tl_date >= best_value[0]:
                    best_value = (tl_date, value)

        return best_value[1] if best_value else 0.0

    def _build_chart_rows(
        self,
        securities: dict[str, dict],
        ticker_data: dict[str, dict],
        all_dates: list,
        cash_timeline: dict,
        current_cash: float,
        date_fmt: str,
        rates: dict[str, float] | None = None,
        quantity_timeline: dict[str, list[tuple]] | None = None,
    ) -> list[dict]:
        rows = []
        for dt in all_dates:
            asset_values = {v: 0.0 for v in ASSET_TYPE_LABELS.values()}
            for ticker, info in securities.items():
                price = ticker_data.get(ticker, {}).get(dt)
                if price is None or price != price or price <= 0:
                    price = 0
                rate = rates.get(ticker, 1.0) if rates else 1.0
                if quantity_timeline is not None:
                    qty = self._get_quantity_at_date(quantity_timeline, ticker, dt)
                else:
                    qty = info["quantity"]
                value = qty * price * rate
                label = ASSET_TYPE_LABELS.get(info.get("asset_type", "STOCK"), "Stocks")
                asset_values[label] += value

            cash = self._get_cash_at_date(cash_timeline, dt, current_cash)
            securities_total = sum(asset_values.values())
            date_str = dt.strftime(date_fmt) if hasattr(dt, "strftime") else str(dt)
            rows.append(
                {
                    "Date": date_str,
                    "Stocks": round(asset_values["Stocks"], 2),
                    "ETFs": round(asset_values["ETFs"], 2),
                    "Crypto": round(asset_values["Crypto"], 2),
                    "Commodity": round(asset_values["Commodity"], 2),
                    "Cash": round(cash, 2),
                    "Total": round(securities_total + cash, 2),
                }
            )
        return rows

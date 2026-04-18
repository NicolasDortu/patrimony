"""Domain service for building time-series chart data."""

import bisect
import logging
import math
from datetime import datetime, timedelta

import polars as pl

from ..constants import (
    ASSET_TYPE_LABELS,
    DEFAULT_CURRENCY,
    DEFAULT_PERIOD,
    MIN_CHART_DAYS,
    PERIOD_CONFIG,
)
from ..repositories import (
    PriceRepository,
    SecuritiesRepository,
)
from .cash_service import CashService
from .currency_service import CurrencyService
from .timeline import (
    build_quantity_timeline,
    get_quantity_at_date,
    normalize_date,
)
from .price_service import PriceService

logger = logging.getLogger(__name__)


class ChartService:
    """Builds time-series chart data for portfolio overview and single-ticker views."""

    def __init__(
        self,
        securities_repo: SecuritiesRepository,
        cash_service: CashService,
        price_repo: PriceRepository,
        currency_service: CurrencyService,
        price_sync: PriceService,
    ):
        self._securities_repo = securities_repo
        self._cash_service = cash_service
        self._price_repo = price_repo
        self._currency_service = currency_service
        self._price_sync = price_sync

    # == Public API ==========================================================

    def get_portfolio_chart_data(
        self,
        period: str,
        user_currency: str,
        securities: dict[str, dict],
        current_cash: float,
        properties_value: float,
    ) -> list[dict]:
        """Build time-series chart data for the entire portfolio.

        Returns rows like {"Date", "Stocks", "ETFs", …, "Cash", "Properties", "Total"}.
        """
        config = PERIOD_CONFIG.get(period, PERIOD_CONFIG["1M"])
        is_intraday = period == "1D"
        tickers = list(securities.keys())

        cash_timeline = self._cash_service.get_balance_timeline(user_currency)
        quantity_timeline = build_quantity_timeline(self._securities_repo)

        if securities:
            rates = self._currency_service.get_rates_for_tickers(tickers, user_currency)
            if is_intraday:
                ticker_data, all_dates = self._fetch_intraday_prices(tickers, config)
            else:
                ticker_data, all_dates = self._fetch_daily_prices(tickers, config)
        else:
            rates, ticker_data, all_dates = {}, {}, []

        all_dates = self._fill_date_gaps(all_dates, cash_timeline, config)
        if not is_intraday and tickers:
            all_dates = self._price_sync.inject_today_prices(
                ticker_data, tickers, all_dates
            )

        if not all_dates:
            return []

        return self._build_portfolio_rows(
            securities=securities,
            ticker_data=ticker_data,
            all_dates=all_dates,
            cash_timeline=cash_timeline,
            current_cash=current_cash,
            date_fmt=config["format"],
            rates=rates,
            quantity_timeline=quantity_timeline,
            properties_value=properties_value,
        )

    def get_ticker_chart_data(
        self,
        ticker: str,
        period: str = DEFAULT_PERIOD,
        user_currency: str = DEFAULT_CURRENCY,
    ) -> list[dict]:
        """Build time-series chart data for a single ticker.

        Returns rows like {"name": <formatted date>, "price": <value>}.
        """
        config = PERIOD_CONFIG.get(period, PERIOD_CONFIG["1M"])
        is_intraday = period == "1D"

        df = self._securities_repo.get_aggregated_positions(ticker)
        if df is None or df.is_empty():
            return []

        quantity = df["total_quantity"][0]
        rate = self._currency_service.get_rates_for_tickers(
            [ticker], user_currency
        ).get(ticker, 1.0)

        if is_intraday:
            ticker_data, all_dates = self._fetch_intraday_prices([ticker], config)
        else:
            ticker_data, all_dates = self._fetch_daily_prices(
                [ticker], config, ticker=ticker
            )
            all_dates = self._price_sync.inject_today_prices(
                ticker_data, [ticker], all_dates
            )

        prices = ticker_data.get(ticker, {})
        return [
            {
                "name": dt.strftime(config["format"])
                if hasattr(dt, "strftime")
                else str(dt),
                "price": round(prices[dt] * quantity * rate, 2),
            }
            for dt in all_dates
            if prices.get(dt) is not None and prices[dt] > 0
        ]

    # == Price fetching ======================================================

    def _fetch_intraday_prices(
        self, tickers: list[str], config: dict
    ) -> tuple[dict[str, dict], list]:
        """Fetch intraday prices via sync (cached in DB, refreshed every 15 min)."""
        self._price_sync.sync_intraday(tickers, interval=config["interval"])
        df = self._price_repo.get_intraday_prices(tickers)

        ticker_data: dict[str, dict] = {}
        all_dates_set: set = set()
        now = datetime.now()

        if df is not None and not df.is_empty():
            for t in df["ticker"].unique().to_list():
                t_df = df.filter(pl.col("ticker") == t)
                td = {
                    ts: p
                    for ts, p in zip(
                        t_df["date"].to_list(), t_df["close_price"].to_list()
                    )
                    if not hasattr(ts, "time") or ts.time() <= now.time()
                }
                ticker_data[t] = td
                all_dates_set.update(td.keys())

        return self._price_sync.sort_and_forward_fill(ticker_data, all_dates_set)

    def _fetch_daily_prices(
        self,
        tickers: list[str],
        config: dict,
        ticker: str | None = None,
    ) -> tuple[dict[str, dict], list]:
        """Fetch daily price history. Pass `ticker` for per-ticker earliest-date clamping."""
        end = datetime.now()
        start = end - timedelta(days=config["days"])

        earliest = self._securities_repo.get_earliest_purchase_date(ticker)
        if earliest is not None:
            if not isinstance(earliest, datetime):
                earliest = datetime.combine(earliest, datetime.min.time())
            start = max(start, earliest)

        if (end - start).days < MIN_CHART_DAYS:
            start = end - timedelta(days=MIN_CHART_DAYS)

        self._price_sync.sync_price_history(tickers, start)
        df = self._price_repo.get_price_history(tickers, start, end)

        ticker_data: dict[str, dict] = {}
        all_dates_set: set = set()

        if df is not None and not df.is_empty():
            for t in df["ticker"].unique().to_list():
                t_df = df.filter(pl.col("ticker") == t)
                td = {
                    normalize_date(d): p
                    for d, p in zip(
                        t_df["date"].to_list(), t_df["close_price"].to_list()
                    )
                }
                ticker_data[t] = td
                all_dates_set.update(td.keys())

        return self._price_sync.sort_and_forward_fill(ticker_data, all_dates_set)

    # == Date helpers ========================================================

    @staticmethod
    def _fill_date_gaps(all_dates: list, cash_timeline: dict, config: dict) -> list:
        """Ensure date list covers cash-only portfolios."""
        if not all_dates and cash_timeline:
            start_date = (datetime.now() - timedelta(days=config["days"])).date()
            all_dates = sorted(
                {
                    normalize_date(d)
                    for d in cash_timeline
                    if normalize_date(d) >= start_date
                }
            )
        return all_dates

    # == Portfolio chart row assembly ========================================

    @staticmethod
    def _build_portfolio_rows(
        securities: dict[str, dict],
        ticker_data: dict[str, dict],
        all_dates: list,
        cash_timeline: dict,
        current_cash: float,
        date_fmt: str,
        rates: dict[str, float],
        quantity_timeline: dict[str, list[tuple]],
        properties_value: float = 0.0,
    ) -> list[dict]:
        # Pre-sort cash timeline for bisect lookup
        if cash_timeline:
            sorted_items = sorted(
                ((normalize_date(d), v) for d, v in cash_timeline.items()),
                key=lambda x: x[0],
            )
            cash_dates = [item[0] for item in sorted_items]
            cash_values = [item[1] for item in sorted_items]
        else:
            cash_dates, cash_values = [], []

        rows = []
        for dt in all_dates:
            asset_values = {v: 0.0 for v in ASSET_TYPE_LABELS.values()}
            for ticker, info in securities.items():
                price = ticker_data.get(ticker, {}).get(dt)
                if price is None or math.isnan(price) or price <= 0:
                    price = 0
                rate = rates.get(ticker, 1.0)
                qty = get_quantity_at_date(quantity_timeline, ticker, dt)
                label = ASSET_TYPE_LABELS.get(info.get("asset_type", "STOCK"), "Stocks")
                asset_values[label] += qty * price * rate

            if cash_dates:
                idx = bisect.bisect_right(cash_dates, normalize_date(dt)) - 1
                cash = cash_values[idx] if idx >= 0 else 0.0
            else:
                cash = current_cash

            securities_total = sum(asset_values.values())
            date_str = dt.strftime(date_fmt) if hasattr(dt, "strftime") else str(dt)

            row = {"Date": date_str}
            row.update({k: round(v, 2) for k, v in asset_values.items()})
            row["Properties"] = round(properties_value, 2)
            row["Cash"] = round(cash, 2)
            row["Total"] = round(securities_total + cash + properties_value, 2)
            rows.append(row)
        return rows

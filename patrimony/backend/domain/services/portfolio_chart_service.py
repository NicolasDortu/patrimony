"""Domain service for building portfolio time-series chart data.

Handles price timeline resolution, date gap filling, cash timeline
construction, and chart row assembly for the portfolio overview chart.
"""

import bisect
import logging
from datetime import datetime, timedelta

import polars as pl

from ..constants import ASSET_TYPE_LABELS, PERIOD_CONFIG
from ..interfaces import MarketDataProvider
from ..repositories import (
    CashRepository,
    PriceRepository,
    SecuritiesRepository,
)
from .currency_service import CurrencyService
from .enrichment_utilities import (
    build_quantity_timeline,
    forward_fill_prices,
    get_quantity_at_date,
    normalize_date,
)
from .price_sync_service import PriceSyncService

logger = logging.getLogger(__name__)


class PortfolioChartService:
    """Builds time-series chart data for the portfolio overview."""

    def __init__(
        self,
        securities_repo: SecuritiesRepository,
        cash_repo: CashRepository,
        price_repo: PriceRepository,
        currency_service: CurrencyService,
        market_data: MarketDataProvider,
        price_sync: PriceSyncService,
    ):
        self._securities_repo = securities_repo
        self._cash_repo = cash_repo
        self._price_repo = price_repo
        self._currency_service = currency_service
        self._market_data = market_data
        self._price_sync = price_sync

    def get_chart_data(
        self,
        period: str,
        user_currency: str,
        securities: dict[str, dict],
        current_cash: float,
        properties_value: float,
    ) -> list[dict]:
        """Build time-series chart data for the entire portfolio.

        Args:
            period: Time period key (e.g. "1D", "1M", "1Y", "MAX").
            user_currency: Target currency code.
            securities: Ticker -> {quantity, asset_type} from the portfolio.
            current_cash: Precomputed total cash value in user_currency.
            properties_value: Precomputed total properties value in user_currency.
        """
        config = PERIOD_CONFIG.get(period, PERIOD_CONFIG["1M"])
        is_intraday = period == "1D"

        cash_timeline = self._build_cash_timeline(user_currency)
        quantity_timeline = build_quantity_timeline(self._securities_repo)

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
            user_currency,
            properties_value,
        )

    # -- Price timeline ------------------------------------------------------

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
        if not all_dates and cash_timeline:
            start_date = (datetime.now() - timedelta(days=config["days"])).date()
            all_dates = sorted(
                {
                    normalize_date(d)
                    for d in cash_timeline
                    if normalize_date(d) >= start_date
                }
            )

        if not is_intraday:
            today = datetime.now().date()
            existing = {normalize_date(d) for d in all_dates} if all_dates else set()
            if today not in existing:
                today_prices = self._price_sync.get_current_prices(
                    list(securities.keys())
                )
                for ticker in securities:
                    price = today_prices.get(ticker.upper())
                    if price:
                        ticker_data.setdefault(ticker, {})[today] = price
                all_dates.append(today)

        return all_dates

    # -- Cash timeline -------------------------------------------------------

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

    # -- Price fetching ------------------------------------------------------

    def _fetch_ticker_prices(
        self, tickers: list[str], config: dict, is_intraday: bool
    ) -> tuple[dict[str, dict], list]:
        ticker_data: dict[str, dict] = {}
        all_dates_set: set = set()

        if is_intraday:
            for ticker in tickers:
                try:
                    df = self._market_data.get_price_history_period(
                        ticker, period=config["period"], interval=config["interval"]
                    )
                    if df is not None and not df.is_empty():
                        dates = df["date"].to_list()
                        prices = df["close_price"].to_list()
                        ticker_data[ticker] = dict(zip(dates, prices))
                        all_dates_set.update(dates)
                except Exception as e:
                    logger.warning("Skipping intraday data for %s: %s", ticker, e)
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
            if (end - start).days < 2:
                start = end - timedelta(days=2)
            self._price_sync.sync_price_history(tickers, start)
            df = self._price_repo.get_price_history(tickers, start, end)
            if df is not None and not df.is_empty():
                for ticker in df["ticker"].unique().to_list():
                    t_df = df.filter(pl.col("ticker") == ticker)
                    dates = t_df["date"].to_list()
                    prices = t_df["close_price"].to_list()
                    td = {}
                    for d, p in zip(dates, prices):
                        day = normalize_date(d)
                        td[day] = p
                        all_dates_set.add(day)
                    ticker_data[ticker] = td

        sorted_dates = sorted(all_dates_set)

        for ticker in ticker_data:
            forward_fill_prices(ticker_data[ticker], sorted_dates)

        return ticker_data, sorted_dates

    # -- Chart row assembly --------------------------------------------------

    @staticmethod
    def _get_cash_at_date(
        sorted_dates: list, sorted_values: list, dt, current_cash: float
    ) -> float:
        if not sorted_dates:
            return current_cash

        dt_date = normalize_date(dt)
        idx = bisect.bisect_right(sorted_dates, dt_date) - 1
        return sorted_values[idx] if idx >= 0 else 0.0

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
        user_currency: str = "EUR",
        properties_value: float = 0.0,
    ) -> list[dict]:
        rows = []

        if cash_timeline:
            sorted_items = sorted(
                ((normalize_date(d), v) for d, v in cash_timeline.items()),
                key=lambda x: x[0],
            )
            cash_dates = [item[0] for item in sorted_items]
            cash_values = [item[1] for item in sorted_items]
        else:
            cash_dates, cash_values = [], []

        for dt in all_dates:
            asset_values = {v: 0.0 for v in ASSET_TYPE_LABELS.values()}
            for ticker, info in securities.items():
                price = ticker_data.get(ticker, {}).get(dt)
                if price is None or price != price or price <= 0:
                    price = 0
                rate = rates.get(ticker, 1.0) if rates else 1.0
                if quantity_timeline is not None:
                    qty = get_quantity_at_date(quantity_timeline, ticker, dt)
                else:
                    qty = info["quantity"]
                value = qty * price * rate
                label = ASSET_TYPE_LABELS.get(info.get("asset_type", "STOCK"), "Stocks")
                asset_values[label] += value

            cash = self._get_cash_at_date(cash_dates, cash_values, dt, current_cash)
            securities_total = sum(asset_values.values())
            date_str = dt.strftime(date_fmt) if hasattr(dt, "strftime") else str(dt)

            row = {"Date": date_str}
            row.update({k: round(v, 2) for k, v in asset_values.items()})
            row["Properties"] = round(properties_value, 2)
            row["Cash"] = round(cash, 2)
            row["Total"] = round(securities_total + cash + properties_value, 2)
            rows.append(row)
        return rows

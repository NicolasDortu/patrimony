"""Portfolio Controller - Orchestrates multiple repositories to provide portfolio-wide metrics and views."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional
import polars as pl

from ...domain.services import MetricsCalculator
from ..di_container import container

PERIOD_CONFIG = {
    "1D": {"days": 1, "period": "1d", "interval": "5m"},
    "5D": {"days": 5, "period": "5d", "interval": "1d"},
    "1M": {"days": 30, "period": "1mo", "interval": "1d"},
    "6M": {"days": 180, "period": "6mo", "interval": "1d"},
    "1Y": {"days": 365, "period": "1y", "interval": "1d"},
    "5Y": {"days": 1825, "period": "5y", "interval": "1wk"},
}


@dataclass(slots=True)
class PortfolioOverview:
    """Aggregated portfolio data with metrics."""

    securities_total: list[dict]
    cash_entries: list[dict]
    total_value: float
    total_invested: float
    total_return: float
    securities_value: float
    cash_value: float


class PortfolioController:
    """Controller for portfolio-wide operations and metrics."""

    @property
    def _securities_repo(self):
        return container.securities_repository()

    @property
    def _cash_repo(self):
        return container.cash_repository()

    @property
    def _price_repo(self):
        return container.price_repository()

    @property
    def _market_data(self):
        return container.market_data_provider()

    # Portfolio Overview Methods
    def _to_dicts(self, df: Optional[pl.DataFrame]) -> list[dict]:
        """Safely convert DataFrame to list of dicts."""
        if df is None or df.is_empty():
            return []
        return df.to_dicts()

    def _enrich_with_prices(self, df: pl.DataFrame) -> pl.DataFrame:
        """Add current_price column to DataFrame."""
        if df is None or df.is_empty() or "ticker" not in df.columns:
            return df

        prices = [self._price_repo.get_current_price(t) for t in df["ticker"].to_list()]
        return df.with_columns(pl.Series("current_price", prices))

    def _calculate_securities_metrics(
        self, df: Optional[pl.DataFrame]
    ) -> tuple[float, float, float]:
        """Calculate (total_invested, current_value, total_return)."""
        if df is None or df.is_empty():
            return 0.0, 0.0, 0.0

        valid_df = df.filter(
            pl.col("current_price").is_not_null()
            & pl.col("total_quantity").is_not_null()
            & (pl.col("total_quantity") > 0)
        )
        if valid_df.is_empty():
            return 0.0, 0.0, 0.0

        return MetricsCalculator.calculate_metrics(
            quantities=valid_df["total_quantity"].to_list(),
            buy_prices=valid_df["avg_price"].to_list(),
            current_prices=valid_df["current_price"].to_list(),
        )

    def _calculate_cash_value(self, df: Optional[pl.DataFrame]) -> float:
        """Calculate total cash balance."""
        if df is None or df.is_empty():
            return 0.0
        return float(df["balance"].sum())

    def _build_cash_timeline(self) -> dict:
        """Build a timeline of total cash balance keyed by date.

        Returns a dict mapping datetime -> total cash balance across all accounts.
        For each operation date, tracks the last known balance per (account, currency)
        and sums them to get the total.
        """
        df = self._cash_repo.get_cash_balance_history()
        if df is None or df.is_empty():
            return {}

        account_balances: dict[tuple[str, str], float] = {}
        timeline: dict = {}

        for row in df.iter_rows(named=True):
            key = row["account_number"]
            account_balances[key] = row["balance"]
            total = sum(account_balances.values())
            timeline[row["operation_date"]] = total

        return timeline

    def get_portfolio_overview(self) -> PortfolioOverview:
        """Get complete portfolio overview with all metrics."""
        # Securities
        securities_df = self._securities_repo.get_aggregated_positions()
        if securities_df is not None and not securities_df.is_empty():
            securities_df = self._enrich_with_prices(securities_df)
        total_invested, securities_value, total_return = (
            self._calculate_securities_metrics(securities_df)
        )

        # Cash
        cash_df = self._cash_repo.get_all()
        cash_value = self._calculate_cash_value(cash_df)

        return PortfolioOverview(
            securities_total=self._to_dicts(securities_df),
            cash_entries=self._to_dicts(cash_df),
            total_value=securities_value + cash_value,
            total_invested=total_invested,
            total_return=total_return,
            securities_value=securities_value,
            cash_value=cash_value,
        )

    # Chart Methods
    def _get_all_securities(self) -> dict[str, dict]:
        """Get all securities as {ticker: {quantity, asset_type}}."""
        df = self._securities_repo.get_aggregated_positions()
        if df is None or df.is_empty():
            return {}
        return {
            row["ticker"]: {
                "quantity": float(row["total_quantity"]),
                "asset_type": row.get("asset_type", "STOCK"),
            }
            for row in df.iter_rows(named=True)
            if row.get("total_quantity", 0) > 0
        }

    def _fetch_ticker_prices(
        self, tickers: list[str], config: dict, is_intraday: bool
    ) -> tuple[dict[str, dict], list]:
        """Fetch price data and return ({ticker: {date: price}}, sorted_dates)."""
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
            end = datetime.now()
            self._price_repo.sync_price_history(tickers, start)
            df = self._price_repo.get_price_history(tickers, start, end)
            if df is not None and not df.is_empty():
                for t_df in df.partition_by("ticker", as_dict=False):
                    ticker = t_df["ticker"][0]
                    dates = t_df["date"].to_list()
                    prices = t_df["close_price"].to_list()
                    # Normalize to date-only so tickers from different
                    # exchanges/timezones share matching keys
                    for d, p in zip(dates, prices):
                        day = d.date() if hasattr(d, "date") else d
                        ticker_data.setdefault(ticker, {})[day] = p
                        all_dates_set.add(day)

        sorted_dates = sorted(all_dates_set)

        # Forward-fill: for each ticker, replace missing/0/None with last known price
        for ticker in ticker_data:
            prices = ticker_data[ticker]
            last_valid = None
            for dt in sorted_dates:
                price = prices.get(dt)
                if price is not None and price == price and price > 0:
                    last_valid = price
                elif last_valid is not None:
                    prices[dt] = last_valid

        return ticker_data, sorted_dates

    def _get_cash_at_date(self, cash_timeline: dict, dt, current_cash: float) -> float:
        """Get the total cash balance as of a given date using forward-fill.

        Finds the most recent cash timeline entry that is <= dt.
        Returns 0.0 for dates before any cash operation exists.
        """
        if not cash_timeline:
            return current_cash

        # Normalize dt to date for comparison
        dt_date = (
            dt
            if isinstance(dt, date) and not isinstance(dt, datetime)
            else (dt.date() if hasattr(dt, "date") else dt)
        )

        best_value = None
        for timeline_dt, value in cash_timeline.items():
            tl_date = (
                timeline_dt.date() if hasattr(timeline_dt, "date") else timeline_dt
            )
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
    ) -> list[dict]:
        """Build chart rows with per-asset-type breakdown."""
        asset_type_labels = {
            "STOCK": "Stocks",
            "ETF": "ETFs",
            "CRYPTO": "Crypto",
            "COMMODITY": "Commodity",
        }
        rows = []
        for dt in all_dates:
            asset_values = {
                "Stocks": 0.0,
                "ETFs": 0.0,
                "Crypto": 0.0,
                "Commodity": 0.0,
            }
            for ticker, info in securities.items():
                price = ticker_data.get(ticker, {}).get(dt)
                if price is None or price != price or price <= 0:
                    price = 0
                value = info["quantity"] * price
                label = asset_type_labels.get(info.get("asset_type", "STOCK"), "Stocks")
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

    def get_chart_data(self, period: str = "1M") -> list[dict]:
        """Build time-series chart data for the entire portfolio."""
        config = PERIOD_CONFIG.get(period, PERIOD_CONFIG["1M"])
        securities = self._get_all_securities()
        current_cash = self._calculate_cash_value(self._cash_repo.get_all())
        cash_timeline = self._build_cash_timeline()

        if not securities:
            return []

        is_intraday = period == "1D"
        ticker_data, all_dates = self._fetch_ticker_prices(
            list(securities.keys()), config, is_intraday
        )

        if not ticker_data:
            return []

        date_fmt = (
            "%H:%M" if is_intraday else ("%Y-%m" if config["days"] > 365 else "%d/%m")
        )

        return self._build_chart_rows(
            securities, ticker_data, all_dates, cash_timeline, current_cash, date_fmt
        )

"""Domain service for securities-specific business logic.

Handles price enrichment, currency conversion, and chart data
for individual tickers.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import polars as pl

from ..constants import PERIOD_CONFIG
from ..repositories import (
    MarketDataProvider,
    PriceRepository,
    SecuritiesRepository,
)
from .currency_service import CurrencyService

logger = logging.getLogger(__name__)


class SecuritiesService:
    """Domain service for securities enrichment and per-ticker charts."""

    def __init__(
        self,
        securities_repo: SecuritiesRepository,
        price_repo: PriceRepository,
        currency_service: CurrencyService,
        market_data: MarketDataProvider,
    ):
        self._securities_repo = securities_repo
        self._price_repo = price_repo
        self._currency_service = currency_service
        self._market_data = market_data

    def get_aggregated_positions(self, user_currency: str = "EUR") -> list[dict]:
        """Get aggregated positions enriched with current prices and currency-converted."""
        df = self._securities_repo.get_aggregated_positions()
        if df is None or df.is_empty():
            return []

        df = self._enrich_with_prices(df)
        df = self._apply_currency_conversion(df, user_currency)
        return df.to_dicts()

    def get_chart_data_ticker(
        self, ticker: str, period: str = "1M", user_currency: str = "EUR"
    ) -> list[dict]:
        """Get time-series price data for a single ticker."""
        config = PERIOD_CONFIG.get(period, PERIOD_CONFIG["1M"])
        df = self._securities_repo.get_aggregated_positions_by_ticker(ticker)
        if df is None or df.is_empty():
            return []

        is_intraday = period == "1D"
        price_df = self._fetch_price_data(ticker, config, is_intraday)
        if price_df is None or price_df.is_empty():
            return []

        rate = self._currency_service.get_rates_for_tickers(
            [ticker], user_currency
        ).get(ticker, 1.0)

        date_fmt = (
            "%H:%M" if is_intraday else ("%Y-%m" if config["days"] > 365 else "%d/%m")
        )

        rows = []
        last_valid_price = None
        for row in price_df.iter_rows(named=True):
            price = row["close_price"]
            if price is not None and price == price and price > 0:
                last_valid_price = price
            elif last_valid_price is not None:
                price = last_valid_price
            else:
                continue

            date_str = (
                row["date"].strftime(date_fmt)
                if hasattr(row["date"], "strftime")
                else str(row["date"])
            )
            rows.append(
                {
                    "name": date_str,
                    "price": round(price * df["total_quantity"][0] * rate, 2),
                }
            )

        # Add today's data point for non-intraday charts
        if not is_intraday and rows:
            today_str = datetime.now().strftime(date_fmt)
            if rows[-1]["name"] != today_str:
                current_price = self._price_repo.get_current_price(ticker)
                if current_price and current_price > 0:
                    rows.append(
                        {
                            "name": today_str,
                            "price": round(
                                current_price * df["total_quantity"][0] * rate, 2
                            ),
                        }
                    )

        return rows

    # -- Internal helpers ----------------------------------------------------

    def _enrich_with_prices(self, df: pl.DataFrame) -> pl.DataFrame:
        if "ticker" not in df.columns:
            return df

        prices = []
        for ticker in df["ticker"].to_list():
            try:
                price = self._price_repo.get_current_price(ticker)
                prices.append(price)
            except Exception as e:
                logger.error("Error fetching price for %s: %s", ticker, e)
                prices.append(None)

        df = df.with_columns(pl.Series("current_price", prices))
        if "total_quantity" in df.columns:
            df = df.with_columns(
                (pl.col("current_price") * pl.col("total_quantity")).alias(
                    "total_value"
                )
            )
        return df

    def _apply_currency_conversion(
        self, df: pl.DataFrame, user_currency: str
    ) -> pl.DataFrame:
        tickers = df["ticker"].to_list()
        rates = self._currency_service.get_rates_for_tickers(tickers, user_currency)
        rate_list = pl.Series("_rate", [rates.get(t, 1.0) for t in tickers])
        df = df.with_columns(
            (pl.col("current_price") * rate_list).alias("current_price"),
            (pl.col("avg_price") * rate_list).alias("avg_price"),
        )
        return df.with_columns(
            (pl.col("current_price") * pl.col("total_quantity")).alias("total_value")
        )

    def _fetch_price_data(
        self, ticker: str, config: dict, is_intraday: bool
    ) -> Optional[pl.DataFrame]:
        if is_intraday:
            return self._market_data.get_price_history_period(
                ticker, period=config["period"], interval=config["interval"]
            )
        start = datetime.now() - timedelta(days=config["days"])
        end = datetime.now()
        self._price_repo.sync_price_history([ticker], start)
        return self._price_repo.get_price_history([ticker], start, end)

"""Shared timeline and date-normalization utilities.

Provides quantity timeline construction and date helpers used across domain services.
"""

import logging
from bisect import bisect_right
from datetime import date, datetime

import polars as pl

from ..repositories import SecuritiesRepository

logger = logging.getLogger(__name__)


def normalize_date(dt) -> date:
    """Normalize a datetime or date value to a plain date object."""
    if isinstance(dt, datetime):
        return dt.date()
    if hasattr(dt, "date") and callable(dt.date):
        return dt.date()
    return dt


def build_quantity_timeline(
    securities_repo: SecuritiesRepository,
) -> dict[str, list[tuple]]:
    """Build per-ticker cumulative quantity timeline from individual positions.

    Returns a dict mapping ticker -> sorted list of (date, cumulative_quantity).
    """
    df = securities_repo.get_all()
    if df is None or df.is_empty():
        return {}

    df = df.sort("date").with_columns(
        pl.col("quantity").cum_sum().over("ticker").alias("cum_qty"),
        pl.col("date")
        .map_elements(normalize_date, return_dtype=pl.Date)
        .alias("norm_date"),
    )

    timeline: dict[str, list[tuple]] = {}
    for ticker in df["ticker"].unique().to_list():
        ticker_df = df.filter(pl.col("ticker") == ticker)
        timeline[ticker] = list(
            zip(ticker_df["norm_date"].to_list(), ticker_df["cum_qty"].to_list())
        )
    return timeline


def get_quantity_at_date(
    quantity_timeline: dict[str, list[tuple]], ticker: str, dt
) -> float:
    """Get the cumulative quantity held for a ticker at a given date."""
    entries = quantity_timeline.get(ticker, [])
    if not entries:
        return 0.0
    dt_date = normalize_date(dt)
    idx = bisect_right(entries, dt_date, key=lambda e: e[0])
    return entries[idx - 1][1] if idx > 0 else 0.0

"""Shared cell-parsing helpers for ``_save_spreadsheet_row`` / ``_load_spreadsheet_rows``.

The six table states (securities total/details, cash, cash operations,
dividends, properties) all parse Glide grid rows the same way:
empty-string-tolerant float casts, stripped uppercase strings, ``%Y-%m-%d``
dates with ``datetime.now()`` fallback, and ``Currency`` enum lookups with
EUR fallback. These helpers centralise that logic so per-state row handlers
only describe the *mapping* to their service call.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..services import Currency


def cell_str(value: Any, default: str = "", upper: bool = False) -> str:
    """Strip a cell value to a clean string; return ``default`` if empty."""
    s = "" if value is None else str(value).strip()
    if upper:
        s = s.upper()
    return s or default


def cell_float(value: Any, default: float = 0.0) -> float:
    """Parse a cell value as ``float``; '' / None return ``default``."""
    if value == "" or value is None:
        return default
    return float(value)


def cell_date(value: Any, fmt: str = "%Y-%m-%d") -> datetime:
    """Parse a cell value as a ``datetime`` using ``fmt``; empty -> ``now()``."""
    s = "" if value is None else str(value).strip()
    if not s:
        return datetime.now()
    return datetime.strptime(s, fmt)


def cell_iso_datetime(value: Any) -> datetime:
    """Parse a cell value via ``datetime.fromisoformat``; empty -> ``now()``."""
    s = "" if value is None else str(value).strip()
    if not s:
        return datetime.now()
    return datetime.fromisoformat(s)


def cell_currency(value: Any, default: Currency = Currency.EUR) -> Currency:
    """Parse a cell value as a ``Currency`` enum; unknown -> ``default``."""
    s = cell_str(value, upper=True)
    if not s:
        return default
    try:
        return Currency[s]
    except KeyError:
        return default


def fmt_date_cell(value: Any) -> str:
    """Format a date-like value for spreadsheet display (``YYYY-MM-DD``)."""
    return str(value)[:10] if value else ""

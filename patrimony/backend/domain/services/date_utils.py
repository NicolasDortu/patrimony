"""Date normalization helpers shared across domain services."""

from datetime import date, datetime


def normalize_date(dt) -> date:
    """Normalize a datetime or date value to a plain date object."""
    if isinstance(dt, datetime):
        return dt.date()
    if hasattr(dt, "date") and callable(dt.date):
        return dt.date()
    return dt

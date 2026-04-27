"""Frontend data models for the service layer."""

import functools
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ...backend import AssetType, EntryType

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class OperationResult:
    """Generic result for mutation operations."""

    success: bool
    message: str
    data: Optional[dict] = None


def operation_result(failure: str = "Operation failed", success: str = ""):
    """Decorator that wraps a function in OperationResult for both success and failure paths.

    On success:
      - If the function returns an OperationResult, it passes through unchanged.
      - Otherwise, wraps the return value as OperationResult(success=True, message=success, data=result).
        If the return value is a dict, it's used as data. If None, data is omitted.
    On exception:
      - Returns OperationResult(success=False, message="{failure}: {exception}").
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                if isinstance(result, OperationResult):
                    return result
                data = result if isinstance(result, dict) else None
                return OperationResult(success=True, message=success, data=data)
            except Exception as e:
                logger.error("%s: %s", failure, e)
                return OperationResult(
                    success=False,
                    message=f"{failure}: {e}",
                )

        return wrapper

    return decorator


def safe_query(default=None):
    """Decorator that catches exceptions in query methods and returns a default value.

    Usage: @safe_query([]) or @safe_query(0.0)
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error("%s failed: %s", func.__name__, e)
                return default if default is not None else None

        return wrapper

    return decorator


def df_to_dicts(df) -> list[dict]:
    """Convert a DataFrame to a list of dicts, returning [] if None or empty."""
    if df is None:
        return []
    return df.to_dicts()


@dataclass(slots=True)
class SecurityPosition:
    """Frontend model for individual security position."""

    id: Optional[int] = None
    ticker: str = ""
    price: float = 0.0
    quantity: float = 1.0
    fees: float = 0.0
    entry_type: EntryType = EntryType.MANUAL
    date: datetime = field(default_factory=datetime.now)
    asset_type: AssetType = AssetType.STOCK


@dataclass(slots=True)
class SecurityTotal:
    """Frontend model for aggregated security positions."""

    ticker: str = ""
    display_ticker: str = ""
    name: str = ""
    isin: str = ""
    total_quantity: float = 0.0
    avg_price: float = 0.0
    current_price: float = 0.0
    total_value: float = 0.0
    asset_type: str = "STOCK"
    total_fees: float = 0.0


@dataclass(slots=True)
class Property:
    """Frontend model for a physical property."""

    id: Optional[int] = None
    name: str = ""
    description: str = ""
    value: float = 0.0
    purchase_date: datetime = field(default_factory=datetime.now)
    category: str = "Other"
    currency: str = "EUR"
    entry_type: str = "MANUAL"

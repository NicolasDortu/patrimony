"""Shared helpers, constants, and data classes for connector services."""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime

from ...exceptions import DateParsingError

# ISIN format: 2-letter country code + 9 alphanumeric + 1 check digit
ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")

# Columns the user must map for positions import
REQUIRED_POSITION_FIELDS = {"ticker", "quantity"}
OPTIONAL_POSITION_FIELDS = {"price", "fees", "date", "asset_type", "currency", "name"}

# Columns the user must map for cash operations import
REQUIRED_CASH_FIELDS = {"account_number", "amount", "title"}
OPTIONAL_CASH_FIELDS = {"operation_date"}


@dataclass(slots=True)
class ResolvedTicker:
    """Result of resolving a raw ticker value (ISIN, name, etc.) to a real ticker."""

    ticker: str | None = None
    asset_type: str | None = None
    source: str | None = None  # "ticker_info", "reference", "yfinance", None


@dataclass(slots=True)
class ImportResult:
    """Result of a batch import operation."""

    success: bool
    imported: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def parse_date(value: str) -> datetime:
    """Try common date formats and return a datetime."""
    for fmt in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%d-%m-%Y",
    ):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    raise DateParsingError(value)


def to_str(value) -> str:
    """Safely convert a value to string, treating None as empty."""
    if value is None:
        return ""
    return str(value)


def normalize_number(value: str) -> str:
    """Normalize European-style numbers (comma as decimal separator).

    Handles formats like:
    - "187,18"       → "187.18"   (comma as decimal)
    - "1.234,56"     → "1234.56"  (dot thousands, comma decimal)
    - "1.234.567,89" → "1234567.89" (multiple dot thousands)
    - "1,234.56"     → "1234.56"  (comma thousands, dot decimal)
    - "1234.56"      → "1234.56"  (already standard)
    """
    value = value.strip().strip('"')
    if not value:
        return "0"
    # If there's a comma but no dot, treat comma as decimal separator
    if "," in value and "." not in value:
        return value.replace(",", ".")
    # Both comma and dot present — determine which is the decimal separator
    if "," in value and "." in value:
        last_comma = value.rfind(",")
        last_dot = value.rfind(".")
        if last_comma > last_dot:
            # European: dots are thousands, comma is decimal (e.g. "1.234,56")
            return value.replace(".", "").replace(",", ".")
        else:
            # US/UK: commas are thousands, dot is decimal (e.g. "1,234.56")
            return value.replace(",", "")
    return value


def normalize_date(val) -> str:
    """Normalize a date value to ISO format string for hashing."""
    if isinstance(val, str):
        try:
            return parse_date(val).date().isoformat()
        except ValueError:
            return val.strip()
    elif isinstance(val, datetime):
        return val.date().isoformat()
    return ""


def position_hash(row: dict, source: str = "") -> str:
    """Compute SHA-256 hash for a position row."""
    src = source.strip().upper()
    ticker = to_str(row.get("ticker")).strip().upper()
    price_str = to_str(row.get("price")).strip()
    price = str(float(normalize_number(price_str))) if price_str else "0.0"
    qty_str = to_str(row.get("quantity")).strip()
    quantity = str(float(normalize_number(qty_str))) if qty_str else "0.0"
    fees_str = to_str(row.get("fees")).strip()
    fees = str(float(normalize_number(fees_str))) if fees_str else "0.0"
    date = normalize_date(row.get("date")) if "date" in row else ""
    raw = f"{src}|{ticker}|{price}|{quantity}|{fees}|{date}"
    return hashlib.sha256(raw.encode()).hexdigest()


def cash_hash(row: dict, source: str = "") -> str:
    """Compute SHA-256 hash for a cash operation row."""
    src = source.strip().upper()
    account = to_str(row.get("account_number")).strip()
    amount_str = to_str(row.get("amount")).strip()
    amount = str(float(normalize_number(amount_str))) if amount_str else "0.0"
    title = to_str(row.get("title")).strip()
    date = normalize_date(row.get("operation_date")) if "operation_date" in row else ""
    raw = f"{src}|{account}|{amount}|{title}|{date}"
    return hashlib.sha256(raw.encode()).hexdigest()

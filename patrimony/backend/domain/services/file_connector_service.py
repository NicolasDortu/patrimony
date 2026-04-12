"""Domain service for file-based data import (CSV/Excel connector).

Handles column mapping, validation, asset type resolution,
and batch insertion of positions and cash operations.
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime

import polars as pl

from ..entities import AssetType, Currency, EntryType
from ..exceptions import DateParsingError, MissingMappingError
from ..interfaces import MarketDataProvider
from ..repositories import (
    CashRepository,
    ImportHashRepository,
    ReferenceRepository,
    SecuritiesRepository,
    TickerAliasRepository,
)

logger = logging.getLogger(__name__)

# ISIN format: 2-letter country code + 9 alphanumeric + 1 check digit
_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")

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
    source: str | None = None  # "alias_cache", "reference", "yfinance", None


@dataclass(slots=True)
class ImportResult:
    """Result of a batch import operation."""

    success: bool
    imported: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


class FileConnectorService:
    """Domain service for importing data from uploaded files."""

    def __init__(
        self,
        securities_repo: SecuritiesRepository,
        cash_repo: CashRepository,
        reference_repo: ReferenceRepository,
        hash_repo: ImportHashRepository | None = None,
        alias_repo: TickerAliasRepository | None = None,
        market_data_provider: MarketDataProvider | None = None,
    ):
        self._securities_repo = securities_repo
        self._cash_repo = cash_repo
        self._reference_repo = reference_repo
        self._hash_repo = hash_repo
        self._alias_repo = alias_repo
        self._market_data = market_data_provider

    def resolve_ticker_aliases(
        self, raw_values: list[str]
    ) -> dict[str, ResolvedTicker]:
        """Resolve raw ticker column values (ISINs, tickers, names) to real tickers.

        Resolution cascade for each value:
        1. Check ticker_alias table (batch) → cached alias hit
        2. Check tickers_reference exact match → already a valid ticker
        3. If ISIN pattern → yfinance lookup → cache on success
        4. None → needs manual matching

        Returns dict mapping raw_value → ResolvedTicker.
        """
        if not raw_values:
            return {}

        upper_values = [v.strip().upper() for v in raw_values if v.strip()]
        result: dict[str, ResolvedTicker] = {}

        # Step 1: Batch lookup in alias table
        cached: dict[str, str] = {}
        if self._alias_repo:
            cached = self._alias_repo.get_batch(upper_values)

        for val in upper_values:
            if val in cached:
                result[val] = ResolvedTicker(ticker=cached[val], source="alias_cache")

        remaining = [v for v in upper_values if v not in result]

        # Step 2: Check reference table for exact ticker match
        for val in remaining:
            matches = self._reference_repo.search(val, limit=1)
            if matches and matches[0]["ticker"].upper() == val:
                result[val] = ResolvedTicker(ticker=val, source="reference")

        remaining = [v for v in remaining if v not in result]

        # Step 3: ISIN resolution via yfinance (only for ISIN-shaped values)
        if self._market_data:
            for val in remaining:
                if _ISIN_RE.match(val):
                    ticker = self._market_data.resolve_isin(val)
                    if ticker:
                        result[val] = ResolvedTicker(ticker=ticker, source="yfinance")
                        # Cache for future imports
                        if self._alias_repo:
                            self._alias_repo.save(val, ticker, "ISIN")

        # Step 4: Anything still remaining is unresolved
        for val in upper_values:
            if val not in result:
                result[val] = ResolvedTicker(ticker=None, source=None)

        return result

    def save_ticker_alias(
        self, alias: str, ticker: str, alias_type: str = "MANUAL"
    ) -> None:
        """Persist a manual alias → ticker mapping for future imports."""
        if self._alias_repo:
            self._alias_repo.save(alias, ticker, alias_type)

    def resolve_asset_types(self, tickers: list[str]) -> dict[str, str | None]:
        """Look up each ticker in the reference table, then yfinance as fallback.

        Returns a dict mapping ticker -> asset_type (or None if not found).
        """
        result: dict[str, str | None] = {}
        for ticker in tickers:
            upper = ticker.upper()
            # 1. Check reference table
            matches = self._reference_repo.search(ticker, limit=1)
            if matches and matches[0]["ticker"].upper() == upper:
                raw = matches[0].get("asset_type")
                if raw:
                    result[upper] = raw.upper()
                    continue

            # 2. Try yfinance as fallback
            if self._market_data:
                asset_type = self._market_data.resolve_asset_type(ticker)
                if asset_type:
                    result[upper] = asset_type
                    continue

            result[upper] = None
        return result

    def detect_cash_rows(
        self,
        df: pl.DataFrame,
        column_mapping: dict[str, str],
    ) -> tuple[list[dict], pl.DataFrame]:
        """Detect cash-like rows in a positions file and separate them.

        Detection: ticker column is empty/null/blank, OR name column contains 'CASH'.

        Returns:
            (cash_rows, positions_df) where cash_rows is a list of dicts
            with keys {amount, currency, raw_name} and positions_df is the
            DataFrame with cash rows removed.
        """
        rename_map = {
            src: dst for src, dst in column_mapping.items() if src in df.columns
        }
        mapped_df = df.select(list(rename_map.keys())).rename(rename_map)

        has_name = "name" in mapped_df.columns

        cash_rows: list[dict] = []
        cash_indices: list[int] = []

        for i, row in enumerate(mapped_df.iter_rows(named=True)):
            ticker_val = str(row.get("ticker") or "").strip()
            name_val = str(row.get("name") or "").strip()
            is_cash = False

            if not ticker_val:
                is_cash = True
            elif has_name and "CASH" in name_val.upper():
                is_cash = True

            if is_cash:
                # Extract amount from the row
                amount = 0.0
                for field_name in ("price", "quantity", "fees"):
                    raw = str(row.get(field_name) or "").strip()
                    if raw:
                        try:
                            amount = float(_normalize_number(raw))
                            break
                        except (ValueError, TypeError):
                            continue

                currency_val = str(row.get("currency") or "").strip().upper()
                if not currency_val:
                    currency_val = "EUR"

                cash_rows.append(
                    {"amount": amount, "currency": currency_val, "raw_name": name_val}
                )
                cash_indices.append(i)

        # Remove cash rows from the original DataFrame
        if cash_indices:
            mask = pl.Series([i not in cash_indices for i in range(len(df))])
            positions_df = df.filter(mask)
        else:
            positions_df = df

        return cash_rows, positions_df

    def import_positions(
        self,
        df: pl.DataFrame,
        column_mapping: dict[str, str],
        entry_type: EntryType,
        asset_type_overrides: dict[str, str] | None = None,
    ) -> ImportResult:
        """Import positions from a mapped DataFrame.

        Only ticker and quantity are required. Price, date, fees, and
        asset_type are optional — sensible defaults are applied when missing.

        Args:
            df: Raw DataFrame from the uploaded file.
            column_mapping: Maps file column names to required field names.
            entry_type: EXCEL or CSV.
            asset_type_overrides: Optional dict mapping ticker -> AssetType value.

        Returns:
            ImportResult with counts and any row-level errors.
        """
        if asset_type_overrides is None:
            asset_type_overrides = {}

        # Validate required fields are mapped
        mapped_fields = set(column_mapping.values())
        missing = REQUIRED_POSITION_FIELDS - mapped_fields
        if missing:
            raise MissingMappingError(missing)

        # Rename columns based on mapping
        rename_map = {
            src: dst for src, dst in column_mapping.items() if src in df.columns
        }
        mapped_df = df.select(list(rename_map.keys())).rename(rename_map)

        # Pre-compute hashes for deduplication
        row_hashes: dict[int, str] = {}
        known_hashes: set[str] = set()
        if self._hash_repo:
            for i, row in enumerate(mapped_df.iter_rows(named=True)):
                row_hashes[i] = _position_hash(row)
            known_hashes = self._hash_repo.existing_hashes(set(row_hashes.values()))

        imported = 0
        skipped = 0
        errors: list[str] = []
        new_hashes: list[str] = []

        # Batch-resolve asset types for all tickers before the loop
        all_tickers = list(
            {
                _to_str(row["ticker"]).strip().upper()
                for row in mapped_df.iter_rows(named=True)
                if _to_str(row.get("ticker")).strip()
            }
        )
        resolved_types = self.resolve_asset_types(all_tickers)

        for i, row in enumerate(mapped_df.iter_rows(named=True), start=1):
            try:
                # Dedup check
                h = row_hashes.get(i - 1)
                if h and h in known_hashes:
                    skipped += 1
                    continue

                ticker = _to_str(row["ticker"]).strip().upper()
                if not ticker:
                    skipped += 1
                    continue

                qty_str = _to_str(row["quantity"]).strip()
                if not qty_str:
                    skipped += 1
                    continue
                quantity = float(_normalize_number(qty_str))

                # Price is optional — default to 0.0
                price_str = _to_str(row.get("price")).strip()
                price = float(_normalize_number(price_str)) if price_str else 0.0

                fees_str = _to_str(row.get("fees")).strip()
                fees = float(_normalize_number(fees_str)) if fees_str else 0.0

                if "date" in row and row["date"]:
                    date_val = row["date"]
                    if isinstance(date_val, str):
                        date_val = _parse_date(date_val)
                    elif isinstance(date_val, datetime):
                        pass
                    else:
                        date_val = datetime.now()
                else:
                    date_val = datetime.now()

                # Resolve asset type: row value → user override → reference/yfinance → STOCK
                if "asset_type" in row and row["asset_type"]:
                    asset_type = AssetType(str(row["asset_type"]).strip().upper())
                elif ticker in asset_type_overrides:
                    asset_type = AssetType(asset_type_overrides[ticker])
                elif resolved_types.get(ticker):
                    asset_type = AssetType(resolved_types[ticker])
                else:
                    asset_type = AssetType.STOCK
                    logger.warning(
                        "Row %d: Could not resolve asset type for '%s', defaulting to STOCK",
                        i,
                        ticker,
                    )

                self._securities_repo.add_position(
                    ticker=ticker,
                    price=price,
                    quantity=quantity,
                    entry_type=entry_type,
                    asset_type=asset_type,
                    date=date_val,
                    fees=fees,
                )
                imported += 1
                if h:
                    new_hashes.append(h)

            except Exception as e:
                errors.append(f"Row {i}: {e}")
                skipped += 1

        if self._hash_repo and new_hashes:
            self._hash_repo.add_hashes(new_hashes, "positions")

        return ImportResult(
            success=imported > 0 or (skipped > 0 and not errors),
            imported=imported,
            skipped=skipped,
            errors=errors,
        )

    def _handle_cash_from_positions(
        self,
        cash_rows: list[dict],
        broker_name: str,
        entry_type: EntryType,
    ) -> None:
        """Create/update cash account from cash rows detected in a positions file."""
        # Sum all cash amounts (there may be multiple cash lines)
        total_amount = sum(row["amount"] for row in cash_rows)
        currency_str = cash_rows[0].get("currency", "EUR") if cash_rows else "EUR"

        try:
            currency = Currency(currency_str)
        except ValueError:
            currency = Currency.EUR

        account_number = broker_name

        # Check if account already exists
        existing_df = self._cash_repo.get_all()
        account_exists = False
        if existing_df is not None and not existing_df.is_empty():
            existing_accounts = set(existing_df["account_number"].to_list())
            account_exists = account_number in existing_accounts

        try:
            if not account_exists:
                self._cash_repo.add_cash(
                    bank=broker_name,
                    account_number=account_number,
                    currency=currency,
                    last_updated=datetime.now(),
                    entry_type=entry_type,
                )
                logger.info(
                    "Created cash account '%s' for broker %s",
                    account_number,
                    broker_name,
                )

            # Add balance as an operation
            self._cash_repo.add_operation_balance(
                account_number=account_number,
                amount=total_amount,
                title="Balance update",
                operation_date=datetime.now(),
                entry_type=entry_type,
            )
            logger.info(
                "Updated cash balance for '%s': %s %s",
                account_number,
                total_amount,
                currency_str,
            )
        except Exception as e:
            logger.warning("Failed to handle cash from positions: %s", e)

    def detect_unknown_cash_accounts(
        self,
        df: pl.DataFrame,
        column_mapping: dict[str, str],
    ) -> list[str]:
        """Return account numbers from the file that don't exist in the cash table.

        Args:
            df: Raw DataFrame from the uploaded file.
            column_mapping: Maps file column names to required field names.

        Returns:
            List of unknown account numbers.
        """
        acct_col = None
        for col, target in column_mapping.items():
            if target == "account_number":
                acct_col = col
                break
        if not acct_col or acct_col not in df.columns:
            return []

        file_accounts = {
            str(v).strip()
            for v in df[acct_col].to_list()
            if v is not None and str(v).strip()
        }

        existing_df = self._cash_repo.get_all()
        if existing_df is not None and not existing_df.is_empty():
            existing_accounts = set(existing_df["account_number"].to_list())
        else:
            existing_accounts = set()

        return sorted(file_accounts - existing_accounts)

    def import_cash_operations(
        self,
        df: pl.DataFrame,
        column_mapping: dict[str, str],
        entry_type: EntryType,
        new_accounts: dict[str, dict] | None = None,
    ) -> ImportResult:
        """Import cash operations from a mapped DataFrame.

        Args:
            df: Raw DataFrame from the uploaded file.
            column_mapping: Maps file column names to required field names. e.g. {"Col A": "account_number", "Col B": "amount"}.
            entry_type: EXCEL or CSV.
            new_accounts: Optional dict mapping account_number -> {"bank": str, "currency": str} for accounts that need to be created before importing.

        Returns:
            ImportResult with counts and any row-level errors.
        """
        # Auto-create unknown cash accounts
        if new_accounts:
            from ..entities import Currency

            for acct_num, info in new_accounts.items():
                try:
                    self._cash_repo.add_cash(
                        bank=info["bank"],
                        account_number=acct_num,
                        currency=Currency(info["currency"]),
                        last_updated=datetime.now(),
                        entry_type=entry_type,
                    )
                except Exception as e:
                    logger.warning("Failed to create account %s: %s", acct_num, e)

        mapped_fields = set(column_mapping.values())
        missing = REQUIRED_CASH_FIELDS - mapped_fields
        if missing:
            raise MissingMappingError(missing)

        rename_map = {
            src: dst for src, dst in column_mapping.items() if src in df.columns
        }
        mapped_df = df.select(list(rename_map.keys())).rename(rename_map)

        # Pre-compute hashes for deduplication
        row_hashes: dict[int, str] = {}
        known_hashes: set[str] = set()
        if self._hash_repo:
            for i, row in enumerate(mapped_df.iter_rows(named=True)):
                row_hashes[i] = _cash_hash(row)
            known_hashes = self._hash_repo.existing_hashes(set(row_hashes.values()))

        imported = 0
        skipped = 0
        errors: list[str] = []
        new_hashes: list[str] = []

        for i, row in enumerate(mapped_df.iter_rows(named=True), start=1):
            try:
                # Dedup check
                h = row_hashes.get(i - 1)
                if h and h in known_hashes:
                    skipped += 1
                    continue

                account_number = str(row["account_number"]).strip()
                amount = float(row["amount"])
                title = str(row.get("title") or "Imported operation")

                if "operation_date" in row and row["operation_date"]:
                    date_val = row["operation_date"]
                    if isinstance(date_val, str):
                        date_val = _parse_date(date_val)
                    elif isinstance(date_val, datetime):
                        pass
                    else:
                        date_val = datetime.now()
                else:
                    date_val = datetime.now()

                self._cash_repo.add_operation_balance(
                    account_number=account_number,
                    amount=amount,
                    title=title,
                    operation_date=date_val,
                    entry_type=entry_type,
                )
                imported += 1
                if h:
                    new_hashes.append(h)

            except Exception as e:
                errors.append(f"Row {i}: {e}")
                skipped += 1

        if self._hash_repo and new_hashes:
            self._hash_repo.add_hashes(new_hashes, "cash")

        return ImportResult(
            success=imported > 0 or (skipped > 0 and not errors),
            imported=imported,
            skipped=skipped,
            errors=errors,
        )


def _parse_date(value: str) -> datetime:
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


def _to_str(value) -> str:
    """Safely convert a value to string, treating None as empty."""
    if value is None:
        return ""
    return str(value)


def _normalize_number(value: str) -> str:
    """Normalize European-style numbers (comma as decimal separator).

    Handles formats like "187,18" → "187.18" and "2246,16" → "2246.16".
    If the value already uses dots, it is returned as-is.
    """
    value = value.strip().strip('"')
    if not value:
        return "0"
    # If there's a comma but no dot, treat comma as decimal separator
    if "," in value and "." not in value:
        return value.replace(",", ".")
    # If both comma and dot exist, comma is likely thousands separator
    if "," in value and "." in value:
        return value.replace(",", "")
    return value


def _normalize_date(val) -> str:
    """Normalize a date value to ISO format string for hashing."""
    if isinstance(val, str):
        try:
            return _parse_date(val).date().isoformat()
        except ValueError:
            return val.strip()
    elif isinstance(val, datetime):
        return val.date().isoformat()
    return ""


def _position_hash(row: dict) -> str:
    """Compute SHA-256 hash for a position row."""
    ticker = _to_str(row.get("ticker")).strip().upper()
    price_str = _to_str(row.get("price")).strip()
    price = str(float(_normalize_number(price_str))) if price_str else "0.0"
    qty_str = _to_str(row.get("quantity")).strip()
    quantity = str(float(_normalize_number(qty_str))) if qty_str else "0.0"
    fees_str = _to_str(row.get("fees")).strip()
    fees = str(float(_normalize_number(fees_str))) if fees_str else "0.0"
    date = _normalize_date(row.get("date")) if "date" in row else ""
    raw = f"{ticker}|{price}|{quantity}|{fees}|{date}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _cash_hash(row: dict) -> str:
    """Compute SHA-256 hash for a cash operation row."""
    account = _to_str(row.get("account_number")).strip()
    amount = str(float(row.get("amount", 0) or 0))
    title = _to_str(row.get("title")).strip()
    date = _normalize_date(row.get("operation_date")) if "operation_date" in row else ""
    raw = f"{account}|{amount}|{title}|{date}"
    return hashlib.sha256(raw.encode()).hexdigest()

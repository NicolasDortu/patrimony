"""Domain service for file-based data import (CSV/Excel connector).

Handles column mapping, validation, asset type resolution,
and batch insertion of positions and cash operations.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime

import polars as pl

from ..entities import AssetType, EntryType
from ..interfaces import FileConnector
from ..repositories import (
    CashRepository,
    ImportHashRepository,
    ReferenceRepository,
    SecuritiesRepository,
)

logger = logging.getLogger(__name__)

# Columns the user must map for positions import
REQUIRED_POSITION_FIELDS = {"ticker", "price", "quantity"}
OPTIONAL_POSITION_FIELDS = {"fees", "date", "asset_type"}

# Columns the user must map for cash operations import
REQUIRED_CASH_FIELDS = {"account_number", "amount", "title"}
OPTIONAL_CASH_FIELDS = {"operation_date"}


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
        file_connector: FileConnector,
        securities_repo: SecuritiesRepository,
        cash_repo: CashRepository,
        reference_repo: ReferenceRepository,
        hash_repo: ImportHashRepository | None = None,
    ):
        self._file_connector = file_connector
        self._securities_repo = securities_repo
        self._cash_repo = cash_repo
        self._reference_repo = reference_repo
        self._hash_repo = hash_repo

    def read_file(
        self, file_bytes: bytes, filename: str, delimiter: str = ","
    ) -> pl.DataFrame:
        """Read an uploaded file and return the raw DataFrame."""
        return self._file_connector.read_file(file_bytes, filename, delimiter)

    def resolve_asset_types(self, tickers: list[str]) -> dict[str, str | None]:
        """Look up each ticker in the reference table.

        Returns a dict mapping ticker -> asset_type (or None if not found).
        """
        result: dict[str, str | None] = {}
        for ticker in tickers:
            matches = self._reference_repo.search(ticker, limit=1)
            if matches and matches[0]["ticker"].upper() == ticker.upper():
                raw = matches[0].get("asset_type")
                result[ticker.upper()] = raw.upper() if raw else None
            else:
                result[ticker.upper()] = None
        return result

    def import_positions(
        self,
        df: pl.DataFrame,
        column_mapping: dict[str, str],
        entry_type: EntryType,
        asset_type_overrides: dict[str, str] | None = None,
    ) -> ImportResult:
        """Import positions from a mapped DataFrame.

        Args:
            df: Raw DataFrame from the uploaded file.
            column_mapping: Maps file column names to required field names. e.g. {"Column A": "ticker", "Column B": "price"}.
            entry_type: EXCEL or CSV.
            asset_type_overrides: Optional dict mapping ticker -> AssetType value for tickers not found in the reference table.

        Returns:
            ImportResult with counts and any row-level errors.
        """
        if asset_type_overrides is None:
            asset_type_overrides = {}

        # Validate required fields are mapped
        mapped_fields = set(column_mapping.values())
        missing = REQUIRED_POSITION_FIELDS - mapped_fields
        if missing:
            return ImportResult(
                success=False,
                errors=[f"Missing required mappings: {', '.join(missing)}"],
            )

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
                str(row["ticker"]).strip().upper()
                for row in mapped_df.iter_rows(named=True)
                if row.get("ticker")
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

                ticker = str(row["ticker"]).strip().upper()
                price = float(row["price"])
                quantity = float(row["quantity"])

                fees = float(row.get("fees") or 0) if "fees" in row else 0.0

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

                # Resolve asset type
                if "asset_type" in row and row["asset_type"]:
                    asset_type = AssetType(str(row["asset_type"]).strip().upper())
                elif ticker in asset_type_overrides:
                    asset_type = AssetType(asset_type_overrides[ticker])
                elif resolved_types.get(ticker):
                    asset_type = AssetType(resolved_types[ticker])
                else:
                    errors.append(
                        f"Row {i}: Unknown asset type for ticker '{ticker}', skipped"
                    )
                    skipped += 1
                    continue

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
                        balance=0.0,
                        last_updated=datetime.now(),
                    )
                except Exception as e:
                    logger.warning("Failed to create account %s: %s", acct_num, e)

        mapped_fields = set(column_mapping.values())
        missing = REQUIRED_CASH_FIELDS - mapped_fields
        if missing:
            return ImportResult(
                success=False,
                errors=[f"Missing required mappings: {', '.join(missing)}"],
            )

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
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: '{value}'")


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
    ticker = str(row.get("ticker", "")).strip().upper()
    price = str(float(row.get("price", 0)))
    quantity = str(float(row.get("quantity", 0)))
    fees = str(float(row.get("fees") or 0)) if "fees" in row else "0.0"
    date = _normalize_date(row.get("date")) if "date" in row else ""
    raw = f"{ticker}|{price}|{quantity}|{fees}|{date}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _cash_hash(row: dict) -> str:
    """Compute SHA-256 hash for a cash operation row."""
    account = str(row.get("account_number", "")).strip()
    amount = str(float(row.get("amount", 0)))
    title = str(row.get("title") or "").strip()
    date = _normalize_date(row.get("operation_date")) if "operation_date" in row else ""
    raw = f"{account}|{amount}|{title}|{date}"
    return hashlib.sha256(raw.encode()).hexdigest()

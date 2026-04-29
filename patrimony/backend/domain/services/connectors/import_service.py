"""Domain service for file-based data import (CSV/Excel connector).

Handles column mapping, validation, deduplication,
and batch insertion of positions and cash operations.
Delegates ticker resolution to the ticker_resolution module.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterator

import polars as pl

from ...entities import AssetType, Currency, EntryType, TickerInfo
from ...exceptions import MissingColumnError, MissingMappingError
from ...interfaces import MarketDataProvider, UnitOfWork
from ...repositories import (
    CashRepository,
    ImportHashRepository,
    ReferenceRepository,
    SecuritiesRepository,
    TickerInfoRepository,
)
from .helpers import (
    REQUIRED_CASH_FIELDS,
    REQUIRED_POSITION_FIELDS,
    ImportResult,
    ResolvedTicker,
    cash_hash,
    normalize_number,
    parse_date,
    position_hash,
    safe_str,
    to_str,
)
from . import ticker_resolution

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ParsedPosition:
    ticker: str
    price: float
    quantity: float
    fees: float
    date: datetime
    asset_type: AssetType


class FileConnectorService:
    """Domain service for importing data from uploaded files."""

    def __init__(
        self,
        securities_repo: SecuritiesRepository,
        cash_repo: CashRepository,
        reference_repo: ReferenceRepository,
        hash_repo: ImportHashRepository,
        unit_of_work: UnitOfWork,
        info_repo: TickerInfoRepository | None = None,
        market_data_provider: MarketDataProvider | None = None,
    ):
        # ``hash_repo`` is required: without it, re-importing the same file
        # would silently double every position. Deduplication is part of the
        # import contract, not an optional optimisation.
        self._securities_repo = securities_repo
        self._cash_repo = cash_repo
        self._reference_repo = reference_repo
        self._hash_repo = hash_repo
        self._uow = unit_of_work
        self._info_repo = info_repo
        self._market_data = market_data_provider

    # ------------------------------------------------------------------
    # Ticker resolution (delegated)
    # ------------------------------------------------------------------

    def resolve_ticker_aliases(
        self, raw_values: list[str]
    ) -> dict[str, ResolvedTicker]:
        """Resolve raw ticker column values to real tickers."""
        return ticker_resolution.resolve_ticker_aliases(
            raw_values, self._info_repo, self._reference_repo, self._market_data
        )

    def resolve_asset_types(self, tickers: list[str]) -> dict[str, str | None]:
        """Look up asset type for each ticker."""
        return ticker_resolution.resolve_asset_types(
            tickers, self._info_repo, self._reference_repo, self._market_data
        )

    def find_ticker_by_name(self, name: str) -> TickerInfo | None:
        """Look up ticker info by name (case-insensitive partial match)."""
        if not self._info_repo or not name:
            return None
        return self._info_repo.get_by_name(name)

    # ------------------------------------------------------------------
    # Cash row detection
    # ------------------------------------------------------------------

    def split_cash_and_positions(
        self,
        df: pl.DataFrame,
        column_mapping: dict[str, str],
    ) -> tuple[list[dict], pl.DataFrame]:
        """Separate cash-like rows from a positions file.

        A row is treated as cash when its ticker column is empty/blank,
        or when its name column contains the word ``CASH``.

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
            ticker_val = safe_str(row, "ticker")
            name_val = safe_str(row, "name")
            ticker_missing = not ticker_val
            name_says_cash = has_name and "CASH" in name_val.upper()
            if not (ticker_missing or name_says_cash):
                continue

            amount = 0.0
            for field_name in ("price", "quantity", "fees"):
                raw = safe_str(row, field_name)
                if raw:
                    try:
                        amount = float(normalize_number(raw))
                        break
                    except (ValueError, TypeError):
                        continue

            currency_val = safe_str(row, "currency").upper() or "EUR"

            cash_rows.append(
                {"amount": amount, "currency": currency_val, "raw_name": name_val}
            )
            cash_indices.append(i)

        if not cash_indices:
            return cash_rows, df

        keep = pl.Series("__keep", [i not in set(cash_indices) for i in range(len(df))])
        return cash_rows, df.filter(keep)

    # ------------------------------------------------------------------
    # Position import
    # ------------------------------------------------------------------

    def _validate_and_map(
        self,
        df: pl.DataFrame,
        column_mapping: dict[str, str],
        required: set[str],
    ) -> pl.DataFrame:
        """Check required mappings/columns and return the renamed sub-DataFrame."""
        missing = required - set(column_mapping.values())
        if missing:
            raise MissingMappingError(missing)
        missing_cols = {src for src in column_mapping if src not in df.columns}
        if missing_cols:
            raise MissingColumnError(missing_cols)
        return df.select(list(column_mapping.keys())).rename(dict(column_mapping))

    @staticmethod
    def _iter_rows_with_hash(
        mapped_df: pl.DataFrame, hasher: Callable[[dict], str]
    ) -> Iterator[tuple[int, dict, str]]:
        """Yield (1-based row index, row dict, hash) for every row."""
        for i, row in enumerate(mapped_df.iter_rows(named=True), start=1):
            yield i, row, hasher(row)

    @staticmethod
    def _parse_date_field(row: dict, key: str) -> datetime:
        val = row.get(key) if key in row else None
        if isinstance(val, datetime):
            return val
        if isinstance(val, str) and val.strip():
            return parse_date(val)
        return datetime.now()

    def _resolve_asset_type(
        self,
        row: dict,
        ticker: str,
        overrides: dict[str, str],
        resolved: dict[str, str | None],
        strict: bool,
        row_index: int,
    ) -> AssetType:
        """Resolve asset type via row > override > reference > default/strict-error."""
        if row.get("asset_type"):
            return AssetType(str(row["asset_type"]).strip().upper())
        if ticker in overrides:
            return AssetType(overrides[ticker])
        if resolved.get(ticker):
            return AssetType(resolved[ticker])
        if strict:
            raise ValueError(f"Unresolved asset type for ticker {ticker!r}")
        logger.warning(
            "Row %d: Could not resolve asset type for '%s', defaulting to STOCK",
            row_index,
            ticker,
        )
        return AssetType.STOCK

    def _parse_position_row(
        self,
        row: dict,
        index: int,
        overrides: dict[str, str],
        resolved: dict[str, str | None],
        strict: bool,
    ) -> ParsedPosition | None:
        """Parse one row into a ParsedPosition. Returns None to skip the row."""
        ticker = to_str(row["ticker"]).strip().upper()
        if not ticker:
            return None
        qty_str = to_str(row["quantity"]).strip()
        if not qty_str:
            return None
        price_str = to_str(row.get("price")).strip()
        fees_str = to_str(row.get("fees")).strip()
        return ParsedPosition(
            ticker=ticker,
            quantity=float(normalize_number(qty_str)),
            price=float(normalize_number(price_str)) if price_str else 0.0,
            fees=float(normalize_number(fees_str)) if fees_str else 0.0,
            date=self._parse_date_field(row, "date"),
            asset_type=self._resolve_asset_type(
                row, ticker, overrides, resolved, strict, index
            ),
        )

    def import_positions(
        self,
        df: pl.DataFrame,
        column_mapping: dict[str, str],
        entry_type: EntryType,
        asset_type_overrides: dict[str, str] | None = None,
        strict: bool = False,
    ) -> ImportResult:
        """Import positions from a mapped DataFrame.

        Only ticker and quantity are required. Price, date, fees, and
        asset_type are optional — sensible defaults are applied when missing.
        When ``strict`` is True, rows with unresolved asset types raise
        instead of defaulting to STOCK.
        """
        overrides = asset_type_overrides or {}
        mapped_df = self._validate_and_map(df, column_mapping, REQUIRED_POSITION_FIELDS)

        hashed_rows = list(self._iter_rows_with_hash(mapped_df, position_hash))
        known_hashes = self._hash_repo.existing_hashes({h for _, _, h in hashed_rows})

        all_tickers = list(
            {to_str(r["ticker"]).strip().upper() for _, r, _ in hashed_rows} - {""}
        )
        resolved_types = self.resolve_asset_types(all_tickers)

        imported = 0
        skipped = 0
        errors: list[str] = []
        new_hashes: list[str] = []

        with self._uow.transaction():
            for i, row, h in hashed_rows:
                if h in known_hashes:
                    skipped += 1
                    continue
                try:
                    parsed = self._parse_position_row(
                        row, i, overrides, resolved_types, strict
                    )
                    if parsed is None:
                        skipped += 1
                        continue
                    self._securities_repo.add_position(
                        ticker=parsed.ticker,
                        price=parsed.price,
                        quantity=parsed.quantity,
                        entry_type=entry_type,
                        asset_type=parsed.asset_type,
                        date=parsed.date,
                        fees=parsed.fees,
                    )
                    imported += 1
                    new_hashes.append(h)
                except Exception as e:
                    logger.debug("Row %d skipped", i, exc_info=True)
                    errors.append(f"Row {i}: {e}")
                    skipped += 1
            if new_hashes:
                self._hash_repo.add_hashes(new_hashes, "positions")

        return ImportResult(
            success=imported > 0 or (skipped > 0 and not errors),
            imported=imported,
            skipped=skipped,
            errors=errors,
        )

    def handle_cash_from_positions(
        self,
        cash_rows: list[dict],
        broker_name: str,
        entry_type: EntryType,
    ) -> None:
        """Create/update cash account from cash rows detected in a positions file."""
        total_amount = sum(row["amount"] for row in cash_rows)
        currency_str = cash_rows[0].get("currency", "EUR") if cash_rows else "EUR"

        try:
            currency = Currency(currency_str)
        except ValueError:
            currency = Currency.EUR

        account_number = broker_name

        existing_df = self._cash_repo.get_all()
        account_exists = False
        if not existing_df.is_empty():
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

    # ------------------------------------------------------------------
    # Cash import
    # ------------------------------------------------------------------

    def detect_unknown_cash_accounts(
        self,
        df: pl.DataFrame,
        column_mapping: dict[str, str],
    ) -> list[str]:
        """Return account numbers from the file that don't exist in the cash table."""
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
        if not existing_df.is_empty():
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
        """Import cash operations from a mapped DataFrame."""
        if new_accounts:
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

        mapped_df = self._validate_and_map(df, column_mapping, REQUIRED_CASH_FIELDS)
        hashed_rows = list(self._iter_rows_with_hash(mapped_df, cash_hash))
        known_hashes = self._hash_repo.existing_hashes({h for _, _, h in hashed_rows})

        imported = 0
        skipped = 0
        errors: list[str] = []
        new_hashes: list[str] = []

        with self._uow.transaction():
            for i, row, h in hashed_rows:
                if h in known_hashes:
                    skipped += 1
                    continue
                try:
                    self._cash_repo.add_operation_balance(
                        account_number=str(row["account_number"]).strip(),
                        amount=float(row["amount"]),
                        title=str(row.get("title") or "Imported operation"),
                        operation_date=self._parse_date_field(row, "operation_date"),
                        entry_type=entry_type,
                    )
                    imported += 1
                    new_hashes.append(h)
                except Exception as e:
                    logger.debug("Row %d skipped", i, exc_info=True)
                    errors.append(f"Row {i}: {e}")
                    skipped += 1
            if new_hashes:
                self._hash_repo.add_hashes(new_hashes, "cash")

        return ImportResult(
            success=imported > 0 or (skipped > 0 and not errors),
            imported=imported,
            skipped=skipped,
            errors=errors,
        )

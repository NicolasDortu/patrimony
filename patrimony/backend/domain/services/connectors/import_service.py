"""Domain service for file-based data import (CSV/Excel connector).

Handles column mapping, validation, deduplication,
and batch insertion of positions and cash operations.
Delegates ticker resolution to the ticker_resolution module.
"""

import logging
from datetime import datetime

import polars as pl

from ...entities import AssetType, Currency, EntryType
from ...exceptions import MissingMappingError
from ...interfaces import MarketDataProvider
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
    to_str,
)
from . import ticker_resolution

logger = logging.getLogger(__name__)


class FileConnectorService:
    """Domain service for importing data from uploaded files."""

    def __init__(
        self,
        securities_repo: SecuritiesRepository,
        cash_repo: CashRepository,
        reference_repo: ReferenceRepository,
        hash_repo: ImportHashRepository | None = None,
        info_repo: TickerInfoRepository | None = None,
        market_data_provider: MarketDataProvider | None = None,
    ):
        self._securities_repo = securities_repo
        self._cash_repo = cash_repo
        self._reference_repo = reference_repo
        self._hash_repo = hash_repo
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

    def save_ticker_alias(
        self, alias: str, ticker: str, alias_type: str = "MANUAL"
    ) -> None:
        """Persist a manual alias → ticker mapping for future imports."""
        ticker_resolution.save_ticker_info(
            self._info_repo,
            ticker,
            isin=alias if alias != ticker else None,
            source=alias_type,
        )

    def resolve_asset_types(self, tickers: list[str]) -> dict[str, str | None]:
        """Look up asset type for each ticker."""
        return ticker_resolution.resolve_asset_types(
            tickers, self._info_repo, self._reference_repo, self._market_data
        )

    # ------------------------------------------------------------------
    # Cash row detection
    # ------------------------------------------------------------------

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
                amount = 0.0
                for field_name in ("price", "quantity", "fees"):
                    raw = str(row.get(field_name) or "").strip()
                    if raw:
                        try:
                            amount = float(normalize_number(raw))
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

        if cash_indices:
            mask = pl.Series([i not in cash_indices for i in range(len(df))])
            positions_df = df.filter(mask)
        else:
            positions_df = df

        return cash_rows, positions_df

    # ------------------------------------------------------------------
    # Position import
    # ------------------------------------------------------------------

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
        """
        if asset_type_overrides is None:
            asset_type_overrides = {}

        mapped_fields = set(column_mapping.values())
        missing = REQUIRED_POSITION_FIELDS - mapped_fields
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
                row_hashes[i] = position_hash(row)
            known_hashes = self._hash_repo.existing_hashes(set(row_hashes.values()))

        imported = 0
        skipped = 0
        errors: list[str] = []
        new_hashes: list[str] = []

        # Batch-resolve asset types for all tickers before the loop
        all_tickers = list(
            {
                to_str(row["ticker"]).strip().upper()
                for row in mapped_df.iter_rows(named=True)
                if to_str(row.get("ticker")).strip()
            }
        )
        resolved_types = self.resolve_asset_types(all_tickers)

        for i, row in enumerate(mapped_df.iter_rows(named=True), start=1):
            try:
                h = row_hashes.get(i - 1)
                if h and h in known_hashes:
                    skipped += 1
                    continue

                ticker = to_str(row["ticker"]).strip().upper()
                if not ticker:
                    skipped += 1
                    continue

                qty_str = to_str(row["quantity"]).strip()
                if not qty_str:
                    skipped += 1
                    continue
                quantity = float(normalize_number(qty_str))

                price_str = to_str(row.get("price")).strip()
                price = float(normalize_number(price_str)) if price_str else 0.0

                fees_str = to_str(row.get("fees")).strip()
                fees = float(normalize_number(fees_str)) if fees_str else 0.0

                if "date" in row and row["date"]:
                    date_val = row["date"]
                    if isinstance(date_val, str):
                        date_val = parse_date(date_val)
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

        mapped_fields = set(column_mapping.values())
        missing = REQUIRED_CASH_FIELDS - mapped_fields
        if missing:
            raise MissingMappingError(missing)

        rename_map = {
            src: dst for src, dst in column_mapping.items() if src in df.columns
        }
        mapped_df = df.select(list(rename_map.keys())).rename(rename_map)

        row_hashes: dict[int, str] = {}
        known_hashes: set[str] = set()
        if self._hash_repo:
            for i, row in enumerate(mapped_df.iter_rows(named=True)):
                row_hashes[i] = cash_hash(row)
            known_hashes = self._hash_repo.existing_hashes(set(row_hashes.values()))

        imported = 0
        skipped = 0
        errors: list[str] = []
        new_hashes: list[str] = []

        for i, row in enumerate(mapped_df.iter_rows(named=True), start=1):
            try:
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
                        date_val = parse_date(date_val)
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

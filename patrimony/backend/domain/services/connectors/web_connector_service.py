"""Domain service for web-based automated data import.

Orchestrates site connector selection, data fetching,
and ingestion through the file import pipeline.
"""

import logging
from collections.abc import Callable

import polars as pl

from ...entities import ConnectorProfile, EntryType, WebConnectorResult
from ...exceptions import ConnectorNotFoundError, DataFetchError
from ...interfaces import SiteConnector
from .helpers import ImportResult
from .import_service import FileConnectorService

logger = logging.getLogger(__name__)


class WebConnectorService:
    """Orchestrates the web connector import pipeline.

    1. Resolve the site connector by ID
    2. Fetch data (connector handles all collection details)
    3. Import via existing FileConnectorService
    """

    def __init__(
        self,
        site_connectors: list[SiteConnector],
        connector_service: FileConnectorService,
    ):
        self._sites: dict[str, SiteConnector] = {s.site_id: s for s in site_connectors}
        self._connector_service = connector_service

    def list_profiles(self) -> list[ConnectorProfile]:
        """Return all available connector profiles."""
        return [s.profile for s in self._sites.values()]

    def get_profile(self, site_id: str) -> ConnectorProfile | None:
        """Load a specific connector profile."""
        site = self._sites.get(site_id)
        return site.profile if site else None

    def run_connector(
        self,
        site_id: str,
        credentials: dict[str, str],
        on_status: Callable[[str], None] | None = None,
        on_user_input: Callable[[str, str], str] | None = None,
        headless: bool = False,
    ) -> WebConnectorResult:
        """Execute the full web connector pipeline synchronously."""
        status_log: list[str] = []

        def _log(msg: str) -> None:
            status_log.append(msg)
            logger.info(msg)
            if on_status:
                on_status(msg)

        site = self._resolve_site(site_id)
        _log(f"Loaded profile: {site.profile.name}")

        df = self._fetch_data(site, credentials, _log, on_user_input, headless)
        # Re-read profile after fetch — connectors may update dynamic
        # properties (e.g. Revolut discovers accounts during scraping).
        profile = site.profile

        # Rename columns to positional names so column_mapping is language-independent.
        df = df.rename({old: f"col_{i}" for i, old in enumerate(df.columns)})

        try:
            _log("Importing data...")
            if profile.needs_matching:
                _log("Positions require name-to-ticker matching.")
                return WebConnectorResult(
                    success=True,
                    needs_matching=True,
                    unmatched_positions=self._build_unmatched_list(df, profile),
                    status_log=status_log,
                )
            return self._import_data(df, profile, _log, status_log)
        except Exception as e:
            _log(f"Import failed: {e}")
            return WebConnectorResult(
                success=False,
                errors=[f"Import failed: {e}"],
                status_log=status_log,
            )

    def _resolve_site(self, site_id: str) -> SiteConnector:
        site = self._sites.get(site_id)
        if not site:
            raise ConnectorNotFoundError(site_id)
        return site

    def _fetch_data(
        self,
        site: SiteConnector,
        credentials: dict[str, str],
        _log: Callable[[str], None],
        on_user_input: Callable[[str, str], str] | None,
        headless: bool,
    ) -> pl.DataFrame:
        try:
            _log("Fetching data...")
            df = site.fetch_data(
                credentials=credentials,
                on_status=_log,
                on_user_input=on_user_input,
                headless=headless,
            )
            _log(f"Fetched {len(df)} rows")
            return df
        except Exception as e:
            _log(f"Data fetch failed: {e}")
            raise DataFetchError(site.profile.site_id, cause=e) from e

    def _build_unmatched_list(
        self, df: pl.DataFrame, profile: ConnectorProfile
    ) -> list[dict]:
        """Resolve names from the file to (ticker, currency) suggestions."""
        cols_by_target = {tgt: src for src, tgt in profile.column_mapping.items()}
        name_col = cols_by_target.get("name")
        currency_col = cols_by_target.get("currency")
        qty_col = cols_by_target.get("quantity", "")
        price_col = cols_by_target.get("price", "")
        ref_repo = self._connector_service._reference_repo

        unmatched: list[dict] = []
        if not name_col or name_col not in df.columns:
            return unmatched

        for row in df.iter_rows(named=True):
            pos_name = str(row.get(name_col, "")).strip()
            if not pos_name:
                continue
            existing = self._connector_service.find_ticker_by_name(pos_name)
            ticker = existing.ticker if existing else ""
            currency = existing.currency if existing else ""
            if not ticker and ref_repo:
                matches = ref_repo.search(pos_name, limit=1)
                if matches:
                    ticker = matches[0]["ticker"]
            if not currency and currency_col:
                currency = str(row.get(currency_col, "")).strip()
            unmatched.append(
                {
                    "name": pos_name,
                    "ticker": ticker,
                    "currency": currency,
                    "quantity": row.get(qty_col, ""),
                    "value": row.get(price_col, ""),
                }
            )
        return unmatched

    def _import_data(
        self,
        df: pl.DataFrame,
        profile: ConnectorProfile,
        _log: Callable[[str], None],
        status_log: list[str],
    ) -> WebConnectorResult:
        entry_type = EntryType.WEB
        if profile.import_mode == "cash":
            result = self._connector_service.import_cash_operations(
                df=df,
                column_mapping=profile.column_mapping,
                entry_type=entry_type,
                new_accounts=profile.new_accounts,
            )
        else:
            result = self._import_positions(df, profile, entry_type, _log)

        if result.success:
            _log(
                f"Import complete: {result.imported} imported, "
                f"{result.skipped} skipped"
            )
        else:
            _log(f"Import failed: {'; '.join(result.errors)}")

        return WebConnectorResult(
            success=result.success,
            imported=result.imported,
            skipped=result.skipped,
            errors=result.errors,
            status_log=status_log,
        )

    def _import_positions(
        self,
        df: pl.DataFrame,
        profile: ConnectorProfile,
        entry_type: EntryType,
        _log: Callable[[str], None],
    ) -> ImportResult:
        """Resolve tickers, separate cash rows, and import positions."""
        # Resolve ISIN → ticker aliases and apply to DataFrame
        ticker_col = None
        for src, tgt in profile.column_mapping.items():
            if tgt == "ticker":
                ticker_col = src
                break

        if ticker_col and ticker_col in df.columns:
            raw_values = df[ticker_col].drop_nulls().unique().to_list()
            raw_values = [v for v in raw_values if v and str(v).strip()]
            if raw_values:
                _log(f"Resolving {len(raw_values)} ticker aliases...")
                resolved = self._connector_service.resolve_ticker_aliases(
                    [str(v) for v in raw_values]
                )
                ticker_overrides = {
                    raw: info.ticker for raw, info in resolved.items() if info.ticker
                }
                unresolved = [r for r, i in resolved.items() if not i.ticker]
                if unresolved:
                    _log(
                        f"Warning: {len(unresolved)} tickers could not "
                        f"be resolved: {', '.join(unresolved[:5])}"
                    )
                # Apply ticker overrides directly to the DataFrame
                if ticker_overrides:
                    df = df.with_columns(
                        pl.col(ticker_col).map_elements(
                            lambda v, _ov=ticker_overrides: _ov.get(
                                str(v).strip().upper(), v
                            ),
                            return_dtype=pl.Utf8,
                        )
                    )

        # Detect and handle cash rows before position import
        cash_rows, df = self._connector_service.split_cash_and_positions(
            df, profile.column_mapping
        )
        if cash_rows:
            self._connector_service.handle_cash_from_positions(
                cash_rows, profile.name, entry_type
            )
            _log(f"Processed {len(cash_rows)} cash row(s)")

        return self._connector_service.import_positions(
            df=df,
            column_mapping=profile.column_mapping,
            entry_type=entry_type,
        )

    def import_matched_positions(
        self,
        matched: list[dict],
    ) -> WebConnectorResult:
        """Import positions after user-assisted name→ticker matching.

        Each item in *matched* has keys: name, ticker, currency, quantity, value.
        The ticker and currency have been confirmed/overridden by the user.
        Saves the name→ticker mapping into ticker_info for future imports.
        """
        from datetime import datetime

        from ...entities import TickerInfo

        info_repo = self._connector_service._info_repo

        rows: list[dict] = []
        for m in matched:
            ticker = str(m.get("ticker", "")).strip()
            if not ticker:
                continue

            # Persist name→ticker association for future matching
            if info_repo:
                info_repo.upsert(
                    TickerInfo(
                        ticker=ticker.upper(),
                        name=m.get("name", ""),
                        currency=m.get("currency") or None,
                        source="WEB_MATCH",
                        last_updated=datetime.now().isoformat(),
                    )
                )

            rows.append(
                {
                    "col_0": ticker,
                    "col_1": str(m.get("quantity", "0")),
                    "col_2": str(m.get("value", "0")),
                    "col_3": m.get("currency", ""),
                }
            )

        if not rows:
            return WebConnectorResult(
                success=False,
                errors=["No valid matched positions to import."],
            )

        df = pl.DataFrame(
            rows,
            schema={
                "col_0": pl.Utf8,
                "col_1": pl.Utf8,
                "col_2": pl.Utf8,
                "col_3": pl.Utf8,
            },
        )
        column_mapping = {
            "col_0": "ticker",
            "col_1": "quantity",
            "col_2": "price",
            "col_3": "currency",
        }

        result = self._connector_service.import_positions(
            df=df,
            column_mapping=column_mapping,
            entry_type=EntryType.WEB,
        )

        return WebConnectorResult(
            success=result.success,
            imported=result.imported,
            skipped=result.skipped,
            errors=result.errors,
        )

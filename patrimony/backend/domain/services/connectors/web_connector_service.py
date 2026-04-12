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
        headless: bool = False,
    ) -> WebConnectorResult:
        """Execute the full web connector pipeline synchronously."""
        status_log: list[str] = []

        def _log(msg: str) -> None:
            status_log.append(msg)
            logger.info(msg)
            if on_status:
                on_status(msg)

        # 1. Resolve site connector
        site = self._sites.get(site_id)
        if not site:
            raise ConnectorNotFoundError(site_id)

        profile = site.profile
        _log(f"Loaded profile: {profile.name}")

        # 2. Fetch data from the external source
        try:
            _log("Fetching data...")
            df = site.fetch_data(
                credentials=credentials,
                on_status=_log,
                headless=headless,
            )
            _log(f"Fetched {len(df)} rows")
        except Exception as e:
            _log(f"Data fetch failed: {e}")
            raise DataFetchError(site_id, cause=e) from e

        # 3. Import using existing pipeline with auto-applied column mapping
        try:
            _log("Importing data...")
            entry_type = EntryType.WEB

            # Rename columns to positional names (col_0, col_1, ...)
            # so the profile's column_mapping is language-independent
            positional_names = {old: f"col_{i}" for i, old in enumerate(df.columns)}
            df = df.rename(positional_names)

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
        except Exception as e:
            _log(f"Import failed: {e}")
            return WebConnectorResult(
                success=False,
                errors=[f"Import failed: {e}"],
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
        cash_rows, df = self._connector_service.detect_cash_rows(
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

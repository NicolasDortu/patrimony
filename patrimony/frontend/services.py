"""Service Layer - Single interface between frontend and backend.

This module is the ONLY frontend module that accesses the backend.
States and components should only import from this file, never directly from backend.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..backend.domain.entities import (
    AssetType,
    ConnectorHistoryEntry,
    Currency,
    EntryType,
    PortfolioOverview,
)
from ..backend.presentation.di_container import container

from .config.file_connector_config import file_connector_paths

logger = logging.getLogger(__name__)


def was_market_data_fetched() -> bool:
    """Check and reset whether the market data API was called since last check."""
    return container.market_data_provider().check_api_was_called()


# ============================================================================
# FRONTEND DATA MODELS
# ============================================================================


@dataclass(slots=True)
class OperationResult:
    """Generic result for mutation operations."""

    success: bool
    message: str
    data: Optional[dict] = None


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
    total_quantity: float = 0.0
    avg_price: float = 0.0
    current_price: float = 0.0
    total_value: float = 0.0
    asset_type: str = "STOCK"


# ============================================================================
# BACKEND INTERFACE - Cash Operations
# ============================================================================


class CashService:
    """Frontend service for cash operations."""

    @staticmethod
    def add_cash(
        bank: str,
        account_number: str,
        currency: Currency,
        balance: float,
        last_updated: Optional[datetime] = None,
    ) -> OperationResult:
        """Add new cash account."""
        try:
            if last_updated is None:
                last_updated = datetime.now()
            cash_id = container.cash_repository().add_cash(
                bank=bank,
                account_number=account_number,
                currency=currency,
                balance=balance,
                last_updated=last_updated,
            )
            return OperationResult(
                success=True,
                message="Bank account added successfully",
                data={"id": cash_id},
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to add bank account: {e}",
            )

    @staticmethod
    def update_cash(
        bank: str,
        account_number: str,
        currency: Currency,
        last_updated: Optional[datetime] = None,
    ) -> OperationResult:
        """Update existing cash account."""
        try:
            if last_updated is None:
                last_updated = datetime.now()
            container.cash_repository().update_cash(
                bank=bank,
                account_number=account_number,
                currency=currency,
                last_updated=last_updated,
            )
            return OperationResult(
                success=True,
                message=f"Account {account_number} updated successfully",
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to update account {account_number}: {e}",
            )

    @staticmethod
    def delete_cash(id: int) -> OperationResult:
        """Delete cash account."""
        try:
            container.cash_repository().delete(id)
            return OperationResult(
                success=True,
                message=f"Account {id} deleted successfully",
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to delete account {id}: {e}",
            )

    @staticmethod
    def get_all_cash() -> list[dict]:
        """Get all cash accounts."""
        df = container.cash_repository().get_all()
        return df.to_dicts() if df is not None else []

    @staticmethod
    def add_operation_balance(
        account_number: str,
        amount: float,
        title: str,
        operation_date: datetime,
        entry_type: EntryType = EntryType.MANUAL,
        category: str = "Uncategorized",
    ) -> OperationResult:
        """Make an operation on cash balance."""
        try:
            op_id = container.cash_repository().add_operation_balance(
                account_number=account_number,
                amount=amount,
                title=title,
                operation_date=operation_date,
                entry_type=entry_type,
                category=category,
            )
            return OperationResult(
                success=True,
                message=f"Operation successful, id: {op_id}",
                data={"id": op_id},
            )
        except Exception as e:
            logger.error("Failed to record cash operation: %s", e)
            return OperationResult(
                success=False,
                message=f"Failed to record cash operation: {e}",
            )

    @staticmethod
    def get_operations_by_account(account_number: str) -> list[dict]:
        """Get balance operations for specific account."""
        try:
            df = container.cash_repository().get_operations_by_account(account_number)
            return df.to_dicts() if df is not None else []
        except Exception as e:
            logger.error(
                "Failed to get operations for account %s: %s", account_number, e
            )
            return []

    @staticmethod
    def get_all_operations() -> list[dict]:
        """Get all balance operations."""
        try:
            df = container.cash_repository().get_all_operations()
            return df.to_dicts() if df is not None else []
        except Exception as e:
            logger.error("Failed to get all operations: %s", e)
            return []

    @staticmethod
    def update_operation_by_id(
        id: int,
        amount: float,
        title: str,
        operation_date: datetime,
        entry_type: EntryType,
        category: str = "Uncategorized",
    ) -> OperationResult:
        """Update a balance operation by ID."""
        try:
            container.cash_repository().update_operation_by_id(
                id=id,
                amount=amount,
                title=title,
                operation_date=operation_date,
                entry_type=entry_type,
                category=category,
            )
            return OperationResult(
                success=True, message="Operation updated successfully"
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to update cash operation {id}: {e}",
            )

    @staticmethod
    def delete_operation_by_id(id: int) -> OperationResult:
        """Delete a balance operation by ID."""
        try:
            container.cash_repository().delete_operation_by_id(id)
            return OperationResult(
                success=True, message="Operation deleted successfully"
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to delete cash operation {id}: {e}",
            )

    @staticmethod
    def get_balance(account_number: str) -> float:
        """Get current balance for specific account."""
        try:
            balance = container.cash_repository().get_balance(account_number)
            return balance if balance is not None else 0.0
        except Exception as e:
            logger.error("Failed to get balance for account %s: %s", account_number, e)
            return 0.0


# ============================================================================
# BACKEND INTERFACE - Securities Operations
# ============================================================================


class SecuritiesService:
    """Frontend service for securities operations."""

    @staticmethod
    def add_position(
        ticker: str,
        price: float,
        quantity: float,
        entry_type: EntryType,
        asset_type: AssetType,
        date: Optional[datetime] = None,
        fees: float = 0.0,
    ) -> OperationResult:
        """Add new security position."""
        try:
            if date is None:
                date = datetime.now()
            position_id = container.securities_repository().add_position(
                ticker=ticker,
                price=price,
                quantity=quantity,
                entry_type=entry_type,
                asset_type=asset_type,
                date=date,
                fees=fees,
            )
            return OperationResult(
                success=True,
                message=f"Position for {ticker} added successfully",
                data={"id": position_id},
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to add position: {e}",
            )

    @staticmethod
    def update_position(
        id: int,
        ticker: str,
        price: float,
        quantity: float,
        entry_type: EntryType,
        asset_type: AssetType,
        date: Optional[datetime] = None,
        fees: float = 0.0,
    ) -> OperationResult:
        """Update an existing security position."""
        try:
            if date is None:
                date = datetime.now()
            container.securities_repository().update_position(
                id=id,
                ticker=ticker,
                price=price,
                quantity=quantity,
                entry_type=entry_type,
                asset_type=asset_type,
                date=date,
                fees=fees,
            )
            return OperationResult(
                success=True,
                message=f"Position {id} updated successfully",
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to update position: {e}",
            )

    @staticmethod
    def delete_position(id: int) -> OperationResult:
        """Delete security position."""
        try:
            container.securities_repository().delete(id)
            return OperationResult(
                success=True,
                message=f"Position {id} deleted successfully",
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to delete position: {e}",
            )

    @staticmethod
    def get_all_positions() -> list[dict]:
        """Get all individual positions."""
        df = container.securities_repository().get_all()
        if df is None:
            return []
        if "currency" in df.columns:
            df = df.drop("currency")
        return df.to_dicts()

    @staticmethod
    def get_positions_by_ticker(ticker: str) -> list[dict]:
        """Get positions for specific ticker."""
        df = container.securities_repository().get_by_ticker(ticker)
        if df is None:
            return []
        if "currency" in df.columns:
            df = df.drop("currency")
        return df.to_dicts()

    @staticmethod
    def get_aggregated_positions(user_currency: str = "EUR") -> list[dict]:
        """Get aggregated positions (totals)."""
        df = container.securities_service().get_aggregated_positions(user_currency)
        return df.to_dicts() if df is not None else []

    @staticmethod
    def get_chart_data_ticker(
        ticker: str, period: str = "1M", user_currency: str = "EUR"
    ) -> list[dict]:
        """Get chart data for a single ticker."""
        return container.securities_service().get_chart_data_ticker(
            ticker, period, user_currency
        )


# ============================================================================
# BACKEND INTERFACE - Portfolio Operations
# ============================================================================


class PortfolioService:
    """Frontend service for portfolio operations."""

    @staticmethod
    def get_portfolio_overview(user_currency: str = "EUR") -> PortfolioOverview:
        """Get complete portfolio overview."""
        overview = container.portfolio_service().get_overview(user_currency)
        overview.securities_total = (
            overview.securities_total.to_dicts()
            if overview.securities_total is not None
            else []
        )
        overview.cash_entries = (
            overview.cash_entries.to_dicts()
            if overview.cash_entries is not None
            else []
        )
        return overview

    @staticmethod
    def get_chart_data(period: str = "1M", user_currency: str = "EUR") -> list[dict]:
        """Get chart data for the entire portfolio."""
        return container.portfolio_service().get_chart_data(period, user_currency)


# ============================================================================
# BACKEND INTERFACE - Securities Reference
# ============================================================================


class SecuritiesReferenceService:
    """Frontend service for securities reference lookup."""

    @staticmethod
    def search(query: str, limit: int = 10) -> list[dict]:
        """Search securities reference by ticker or name."""
        if not query or len(query) < 1:
            return []
        return container.reference_repository().search(query, limit)


# ============================================================================
# BACKEND INTERFACE - Currency Operations
# ============================================================================


class CurrencyService:
    """Frontend service for currency operations."""

    @staticmethod
    def get_exchange_rate(from_currency: str, to_currency: str) -> float:
        """Get exchange rate between two currencies."""
        return container.currency_service().get_exchange_rate(
            from_currency, to_currency
        )

    @staticmethod
    def get_currency_symbol(currency_code: str) -> str:
        """Get the display symbol for a currency code."""
        try:
            return Currency(currency_code).symbols
        except ValueError:
            return currency_code


# ============================================================================
# BACKEND INTERFACE - Dividend Operations
# ============================================================================


class DividendService:
    """Frontend service for dividend operations."""

    @staticmethod
    def add_dividend(
        ticker: str,
        amount: float,
        date: Optional[datetime] = None,
    ) -> OperationResult:
        """Add a new dividend."""
        try:
            if date is None:
                date = datetime.now()
            dividend_id = container.dividend_repository().add_dividend(
                ticker=ticker,
                amount=amount,
                date=date,
            )
            return OperationResult(
                success=True,
                message=f"Dividend for {ticker} added successfully",
                data={"id": dividend_id},
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to add dividend: {e}",
            )

    @staticmethod
    def get_dividends_by_ticker(ticker: str) -> list[dict]:
        """Get dividends for a specific ticker."""
        df = container.dividend_repository().get_by_ticker(ticker)
        return df.to_dicts() if df is not None else []

    @staticmethod
    def get_all_dividends() -> list[dict]:
        """Get all dividends."""
        df = container.dividend_repository().get_all()
        return df.to_dicts() if df is not None else []

    @staticmethod
    def get_total_amount() -> float:
        """Get total amount of all dividends."""
        return container.dividend_repository().get_total_amount()

    @staticmethod
    def delete_dividend(id: int) -> OperationResult:
        """Delete a dividend by ID."""
        try:
            container.dividend_repository().delete(id)
            return OperationResult(
                success=True,
                message=f"Dividend {id} deleted successfully",
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to delete dividend: {e}",
            )

    @staticmethod
    def update_dividend(
        id: int,
        ticker: str,
        amount: float,
        date: Optional[datetime] = None,
    ) -> OperationResult:
        """Update an existing dividend."""
        try:
            if date is None:
                date = datetime.now()
            container.dividend_repository().update_dividend(
                id=id,
                ticker=ticker,
                amount=amount,
                date=date,
            )
            return OperationResult(
                success=True,
                message=f"Dividend {id} updated successfully",
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to update dividend: {e}",
            )


# ============================================================================
# BACKEND INTERFACE - Property Operations
# ============================================================================


@dataclass(slots=True)
class Property:
    """Frontend model for a physical property."""

    id: Optional[int] = None
    name: str = ""
    description: str = ""
    value: float = 0.0
    purchase_date: datetime = field(default_factory=datetime.now)
    category: str = "Other"
    entry_type: str = "MANUAL"


class PropertyService:
    """Frontend service for physical property operations."""

    @staticmethod
    def add_property(
        name: str,
        value: float,
        purchase_date: Optional[datetime] = None,
        description: str = "",
        category: str = "Other",
    ) -> OperationResult:
        try:
            if purchase_date is None:
                purchase_date = datetime.now()
            prop_id = container.property_repository().add_property(
                name=name,
                value=value,
                purchase_date=purchase_date,
                description=description,
                category=category,
            )
            return OperationResult(
                success=True,
                message=f"Property '{name}' added successfully",
                data={"id": prop_id},
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to add property: {e}",
            )

    @staticmethod
    def get_all_properties() -> list[dict]:
        df = container.property_repository().get_all()
        return df.to_dicts() if df is not None else []

    @staticmethod
    def get_total_value() -> float:
        return container.property_repository().get_total_value()

    @staticmethod
    def delete_property(id: int) -> OperationResult:
        try:
            container.property_repository().delete(id)
            return OperationResult(
                success=True,
                message="Property deleted successfully",
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to delete property: {e}",
            )

    @staticmethod
    def update_property(
        id: int,
        name: str,
        value: float,
        purchase_date: Optional[datetime] = None,
        description: str = "",
        category: str = "Other",
    ) -> OperationResult:
        try:
            if purchase_date is None:
                purchase_date = datetime.now()
            container.property_repository().update_property(
                id=id,
                name=name,
                value=value,
                purchase_date=purchase_date,
                description=description,
                category=category,
            )
            return OperationResult(
                success=True,
                message="Property updated successfully",
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to update property: {e}",
            )


# ============================================================================
# BACKEND INTERFACE - File Connector Operations
# ============================================================================


class FileConnectorService:
    """Frontend service for CSV/Excel file import."""

    @staticmethod
    def read_file(
        file_bytes: bytes, filename: str, delimiter: str = ","
    ) -> tuple[list[str], list[dict]]:
        """Read an uploaded file and return (columns, preview_rows).

        Returns:
            Tuple of (column names, first 5 rows as dicts).
        """
        df = container.connector_service().read_file(file_bytes, filename, delimiter)
        columns = df.columns
        preview = df.head(5).to_dicts()
        return columns, preview

    @staticmethod
    def read_file_full(
        file_bytes: bytes, filename: str, delimiter: str = ","
    ) -> list[dict]:
        """Read an uploaded file and return all rows."""
        df = container.connector_service().read_file(file_bytes, filename, delimiter)
        return df.to_dicts()

    @staticmethod
    def resolve_asset_types(tickers: list[str]) -> dict[str, str | None]:
        """Resolve asset types for a list of tickers from the reference table."""
        return container.connector_service().resolve_asset_types(tickers)

    @staticmethod
    def import_positions(
        file_bytes: bytes,
        filename: str,
        column_mapping: dict[str, str],
        delimiter: str = ",",
        asset_type_overrides: dict[str, str] | None = None,
        source_path: str | None = None,
    ) -> OperationResult:
        """Import positions from an uploaded file."""
        try:
            lower = filename.lower()
            entry_type = (
                EntryType.EXCEL if lower.endswith((".xlsx", ".xls")) else EntryType.CSV
            )

            svc = container.connector_service()
            df = svc.read_file(file_bytes, filename, delimiter)
            result = svc.import_positions(
                df, column_mapping, entry_type, asset_type_overrides
            )

            if result.success:
                msg = f"Imported {result.imported} positions"
                if result.skipped:
                    msg += f" ({result.skipped} duplicates skipped)"
                op_result = OperationResult(
                    success=True, message=msg, data={"errors": result.errors}
                )
            else:
                if result.errors:
                    detail = "; ".join(result.errors)
                elif result.skipped and result.imported == 0:
                    detail = f"All {result.skipped} rows were duplicates"
                else:
                    detail = "No rows could be imported"
                op_result = OperationResult(
                    success=False,
                    message=f"Import failed: {detail}",
                )

            # Record history
            history_id = ConnectorHistoryService.record(
                connector_type="file",
                source_name=filename,
                source_path=source_path or filename,
                import_mode="positions",
                column_mapping=column_mapping,
                delimiter=delimiter,
                asset_type_overrides=asset_type_overrides,
                imported=result.imported,
                skipped=result.skipped,
                errors=result.errors,
                success=result.success,
            )

            # Persist source path in local JSON config
            if history_id and source_path:
                file_connector_paths.set(history_id, source_path)

            if op_result.success:
                logger.info("File import: %s", op_result.message)
            else:
                logger.error("File import failed: %s", op_result.message)

            return op_result
        except Exception as e:
            logger.error("File import exception: %s", e)
            return OperationResult(success=False, message=f"Import failed: {e}")

    @staticmethod
    def detect_unknown_cash_accounts(
        file_bytes: bytes,
        filename: str,
        column_mapping: dict[str, str],
        delimiter: str = ",",
    ) -> list[str]:
        """Return account numbers from the file that don't exist in the cash table."""
        svc = container.connector_service()
        df = svc.read_file(file_bytes, filename, delimiter)
        return svc.detect_unknown_cash_accounts(df, column_mapping)

    @staticmethod
    def import_cash_operations(
        file_bytes: bytes,
        filename: str,
        column_mapping: dict[str, str],
        delimiter: str = ",",
        new_accounts: dict[str, dict] | None = None,
        source_path: str | None = None,
    ) -> OperationResult:
        """Import cash operations from an uploaded file."""
        try:
            lower = filename.lower()
            entry_type = (
                EntryType.EXCEL if lower.endswith((".xlsx", ".xls")) else EntryType.CSV
            )

            svc = container.connector_service()
            df = svc.read_file(file_bytes, filename, delimiter)
            result = svc.import_cash_operations(
                df, column_mapping, entry_type, new_accounts
            )

            if result.success:
                msg = f"Imported {result.imported} cash operations"
                if result.skipped:
                    msg += f" ({result.skipped} duplicates skipped)"
                op_result = OperationResult(
                    success=True, message=msg, data={"errors": result.errors}
                )
            else:
                if result.errors:
                    detail = "; ".join(result.errors)
                elif result.skipped and result.imported == 0:
                    detail = f"All {result.skipped} rows were duplicates"
                else:
                    detail = "No rows could be imported"
                op_result = OperationResult(
                    success=False,
                    message=f"Import failed: {detail}",
                )

            # Record history
            history_id = ConnectorHistoryService.record(
                connector_type="file",
                source_name=filename,
                source_path=source_path or filename,
                import_mode="cash",
                column_mapping=column_mapping,
                delimiter=delimiter,
                new_accounts=new_accounts,
                imported=result.imported,
                skipped=result.skipped,
                errors=result.errors,
                success=result.success,
            )

            # Persist source path in local JSON config
            if history_id and source_path:
                file_connector_paths.set(history_id, source_path)

            if op_result.success:
                logger.info("Cash import: %s", op_result.message)
            else:
                logger.error("Cash import failed: %s", op_result.message)

            return op_result
        except Exception as e:
            logger.error("Cash import exception: %s", e)
            return OperationResult(success=False, message=f"Import failed: {e}")

    @staticmethod
    def reimport_from_history(entry: dict) -> OperationResult:
        """Re-import a file connector entry using the stored file path."""
        entry_id = entry.get("id")
        # Prefer path from local JSON config (editable by user)
        source_path = file_connector_paths.get(entry_id) if entry_id else ""
        if not source_path:
            source_path = entry.get("source_path", "")
        if not source_path:
            return OperationResult(success=False, message="No source path in history.")

        path = Path(source_path)
        if not path.is_file():
            return OperationResult(
                success=False,
                message=f"File no longer found at: {path}. "
                "It may have been moved or deleted.",
            )

        file_bytes = path.read_bytes()
        filename = path.name
        column_mapping = entry.get("column_mapping", {})
        delimiter = entry.get("delimiter", ",")
        import_mode = entry.get("import_mode", "positions")

        if import_mode == "cash":
            new_accounts = entry.get("new_accounts")
            return FileConnectorService.import_cash_operations(
                file_bytes=file_bytes,
                filename=filename,
                column_mapping=column_mapping,
                delimiter=delimiter,
                new_accounts=new_accounts,
                source_path=source_path,
            )
        else:
            asset_type_overrides = entry.get("asset_type_overrides")
            return FileConnectorService.import_positions(
                file_bytes=file_bytes,
                filename=filename,
                column_mapping=column_mapping,
                delimiter=delimiter,
                asset_type_overrides=asset_type_overrides,
                source_path=source_path,
            )


# ============================================================================
# BACKEND INTERFACE - Web Connector Operations
# ============================================================================


class WebConnectorService:
    """Frontend service for browser-based automated data import."""

    @staticmethod
    def list_profiles() -> list[dict]:
        """Return all available connector profiles as dicts for the UI."""
        profiles = container.web_connector_service().list_profiles()
        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "import_mode": p.import_mode,
            }
            for p in profiles
        ]

    @staticmethod
    def run_connector(
        profile_id: str,
        credentials: dict[str, str],
        headless: bool = False,
    ) -> OperationResult:
        """Execute a web connector profile and import the data.

        Args:
            profile_id: ID of the connector profile.
            credentials: Dict with "username" and "password".
            headless: Whether to run the browser in headless mode.

        Returns:
            OperationResult with success status, message, and data
            containing import counts, errors, and status log.
        """
        try:
            svc = container.web_connector_service()
            result = svc.run_connector(profile_id, credentials, headless=headless)

            data = {
                "imported": result.imported,
                "skipped": result.skipped,
                "errors": result.errors,
                "status_log": result.status_log,
            }

            if result.success:
                msg = f"Imported {result.imported} entries"
                if result.skipped:
                    msg += f" ({result.skipped} duplicates skipped)"
                op_result = OperationResult(success=True, message=msg, data=data)
            else:
                if result.errors:
                    detail = "; ".join(result.errors)
                elif result.skipped and result.imported == 0:
                    detail = f"All {result.skipped} rows were duplicates"
                else:
                    detail = "No rows could be imported"
                op_result = OperationResult(
                    success=False,
                    message=f"Import failed: {detail}",
                    data=data,
                )

            # Record history
            profile = svc.get_profile(profile_id)
            ConnectorHistoryService.record(
                connector_type="web",
                profile_id=profile_id,
                source_name=profile.name if profile else profile_id,
                import_mode=profile.import_mode if profile else "positions",
                imported=result.imported,
                skipped=result.skipped,
                errors=result.errors,
                success=result.success,
            )

            return op_result
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Connector failed: {e}",
                data={"errors": [str(e)], "status_log": []},
            )


# ============================================================================
# BACKEND INTERFACE - Credential Operations
# ============================================================================

# Session-level Fernet key — held in memory, lost on app restart
_session_fernet_key: bytes | None = None


class CredentialService:
    """Frontend service for encrypted credential management."""

    @staticmethod
    def has_master_password() -> bool:
        return container.credential_repository().has_master_password()

    @staticmethod
    def is_unlocked() -> bool:
        return _session_fernet_key is not None

    @staticmethod
    def setup_master_password(password: str) -> bool:
        global _session_fernet_key
        try:
            _session_fernet_key = (
                container.credential_repository().setup_master_password(password)
            )
            return True
        except Exception as e:
            logger.error("Failed to setup master password: %s", e)
            return False

    @staticmethod
    def unlock(password: str) -> bool:
        global _session_fernet_key
        key = container.credential_repository().verify_master_password(password)
        if key:
            _session_fernet_key = key
            return True
        return False

    @staticmethod
    def lock() -> None:
        global _session_fernet_key
        _session_fernet_key = None

    @staticmethod
    def reset_master_password() -> bool:
        """Delete the master password and all stored credentials."""
        global _session_fernet_key
        try:
            container.credential_repository().reset_master_password()
            _session_fernet_key = None
            return True
        except Exception as e:
            logger.error("Failed to reset master password: %s", e)
            return False

    @staticmethod
    def store_credentials(profile_id: str, username: str, password: str) -> bool:
        if not _session_fernet_key:
            return False
        try:
            container.credential_repository().store_credentials(
                profile_id, username, password, _session_fernet_key
            )
            return True
        except Exception as e:
            logger.error("Failed to store credentials: %s", e)
            return False

    @staticmethod
    def get_credentials(profile_id: str) -> tuple[str, str] | None:
        if not _session_fernet_key:
            return None
        return container.credential_repository().get_credentials(
            profile_id, _session_fernet_key
        )

    @staticmethod
    def delete_credentials(profile_id: str) -> bool:
        try:
            container.credential_repository().delete_credentials(profile_id)
            return True
        except Exception as e:
            logger.error("Failed to delete credentials: %s", e)
            return False

    @staticmethod
    def list_stored_profiles() -> list[str]:
        return container.credential_repository().list_stored_profiles()


# ============================================================================
# BACKEND INTERFACE - Connector History Operations
# ============================================================================


class ConnectorHistoryService:
    """Frontend service for connector import history."""

    @staticmethod
    def record(
        connector_type: str,
        source_name: str,
        import_mode: str,
        imported: int,
        skipped: int,
        errors: list[str],
        success: bool,
        profile_id: str | None = None,
        source_path: str | None = None,
        column_mapping: dict | None = None,
        delimiter: str = ",",
        asset_type_overrides: dict | None = None,
        new_accounts: dict | None = None,
    ) -> int | None:
        """Record a connector history entry."""
        try:
            status = (
                "success"
                if success and not errors
                else ("partial" if success else "failed")
            )
            entry = ConnectorHistoryEntry(
                connector_type=connector_type,
                profile_id=profile_id,
                source_name=source_name,
                source_path=source_path,
                import_mode=import_mode,
                column_mapping=column_mapping or {},
                delimiter=delimiter,
                asset_type_overrides=asset_type_overrides or {},
                new_accounts=new_accounts,
                imported=imported,
                skipped=skipped,
                errors=errors,
                status=status,
            )
            return container.connector_history_repository().add_entry(entry)
        except Exception as e:
            logger.error("Failed to record connector history: %s", e)
            return None

    @staticmethod
    def get_all() -> list[dict]:
        """Get all history entries as dicts for the UI."""
        try:
            entries = container.connector_history_repository().get_all()
            return [
                {
                    "id": e.id,
                    "connector_type": e.connector_type,
                    "profile_id": e.profile_id or "",
                    "source_name": e.source_name,
                    "source_path": e.source_path or "",
                    "import_mode": e.import_mode,
                    "column_mapping": e.column_mapping,
                    "delimiter": e.delimiter,
                    "asset_type_overrides": e.asset_type_overrides,
                    "new_accounts": e.new_accounts,
                    "imported": e.imported,
                    "skipped": e.skipped,
                    "errors": e.errors,
                    "status": e.status,
                    "created_at": e.created_at.isoformat() if e.created_at else "",
                }
                for e in entries
            ]
        except Exception as e:
            logger.error("Failed to get connector history: %s", e)
            return []

    @staticmethod
    def delete(entry_id: int) -> bool:
        """Delete a history entry."""
        try:
            container.connector_history_repository().delete(entry_id)
            return True
        except Exception as e:
            logger.error("Failed to delete history entry: %s", e)
            return False


class EventLogService:
    """Frontend service for persistent event log."""

    @staticmethod
    def save_events(events: list[dict]) -> None:
        try:
            container.event_log_repository().add_batch(events)
        except Exception as e:
            logger.error("Failed to persist events: %s", e)

    @staticmethod
    def get_recent(limit: int = 100) -> list[dict]:
        try:
            df = container.event_log_repository().get_recent(limit)
            return df.to_dicts() if len(df) > 0 else []
        except Exception as e:
            logger.error("Failed to load events: %s", e)
            return []

    @staticmethod
    def clear() -> None:
        try:
            container.event_log_repository().clear()
        except Exception as e:
            logger.error("Failed to clear events: %s", e)

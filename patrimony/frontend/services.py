"""Service Layer - Single interface between frontend and backend.

This module is the ONLY frontend module that accesses the backend.
States and components should only import from this file, never directly from backend.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..backend.domain.entities import (
    AssetType,
    Currency,
    EntryType,
    PortfolioOverview,
)
from ..backend.presentation.di_container import container

logger = logging.getLogger(__name__)


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
        id: int,
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
                id=id,
                bank=bank,
                account_number=account_number,
                currency=currency,
                last_updated=last_updated,
            )
            return OperationResult(
                success=True,
                message=f"Account {id} updated successfully",
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to update account {id}: {e}",
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
    ) -> OperationResult:
        """Make an operation on cash balance."""
        try:
            op_id = container.cash_repository().add_operation_balance(
                account_number=account_number,
                amount=amount,
                title=title,
                operation_date=operation_date,
                entry_type=entry_type,
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
    ) -> OperationResult:
        """Update a balance operation by ID."""
        try:
            container.cash_repository().update_operation_by_id(
                id=id,
                amount=amount,
                title=title,
                operation_date=operation_date,
                entry_type=entry_type,
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
                    msg += f" ({result.skipped} skipped)"
                return OperationResult(
                    success=True, message=msg, data={"errors": result.errors}
                )
            else:
                return OperationResult(
                    success=False,
                    message=f"Import failed: {'; '.join(result.errors)}",
                )
        except Exception as e:
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
                    msg += f" ({result.skipped} skipped)"
                return OperationResult(
                    success=True, message=msg, data={"errors": result.errors}
                )
            else:
                return OperationResult(
                    success=False,
                    message=f"Import failed: {'; '.join(result.errors)}",
                )
        except Exception as e:
            return OperationResult(success=False, message=f"Import failed: {e}")

"""Service Layer - Single interface between frontend and backend.

This module is the ONLY frontend module that accesses backend (controllers and entities).
States and components should only import from this file, never directly from backend.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..backend.domain.entities import (
    AssetType,
    Currency,
    EntryType,
    PortfolioOverview,
    TransactionType,
)

from ..backend.presentation.controllers import OperationResult
from ..backend.presentation.di_container import container


# ============================================================================
# FRONTEND DATA MODELS
# ============================================================================


@dataclass(slots=True)
class SecurityPosition:
    """Frontend model for individual security position."""

    id: Optional[int] = None
    ticker: str = ""
    price: float = 0.0
    quantity: float = 1.0
    entry_type: EntryType = EntryType.MANUAL
    transaction_type: TransactionType = TransactionType.BUY
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
        return container.cash_controller().add_cash(
            bank, account_number, currency, balance, last_updated
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
        return container.cash_controller().update_cash(
            id, bank, account_number, currency, last_updated
        )

    @staticmethod
    def delete_cash(id: int) -> OperationResult:
        """Delete cash account."""
        return container.cash_controller().delete_cash(id)

    @staticmethod
    def get_all_cash() -> list[dict]:
        """Get all cash accounts."""
        return container.cash_controller().get_all_cash()

    @staticmethod
    def add_operation_balance(
        account_number: str,
        amount: float,
        title: str,
        operation_date: datetime,
        entry_type: EntryType = EntryType.MANUAL,
    ) -> OperationResult:
        """Make an operation on cash balance."""
        return container.cash_controller().add_operation_balance(
            account_number, amount, title, operation_date, entry_type
        )

    @staticmethod
    def get_operations_by_account(account_number: str) -> list[dict]:
        """Get balance operations for specific account."""
        return container.cash_controller().get_operations_by_account(account_number)

    @staticmethod
    def get_all_operations() -> list[dict]:
        """Get all balance operations."""
        return container.cash_controller().get_all_operations()

    @staticmethod
    def update_operation_by_id(
        id: int,
        amount: float,
        title: str,
        operation_date: datetime,
        entry_type: EntryType,
    ) -> OperationResult:
        """Update a balance operation by ID."""
        return container.cash_controller().update_operation_by_id(
            id, amount, title, operation_date, entry_type
        )

    @staticmethod
    def delete_operation_by_id(id: int) -> OperationResult:
        """Delete a balance operation by ID."""
        return container.cash_controller().delete_operation_by_id(id)

    @staticmethod
    def get_balance(account_number: str) -> float:
        """Get current balance for specific account."""
        return container.cash_controller().get_balance(account_number)


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
        transaction_type: TransactionType,
        date: Optional[datetime] = None,
    ) -> OperationResult:
        """Add new security position."""
        return container.securities_controller().add_position(
            ticker,
            price,
            quantity,
            entry_type,
            asset_type,
            transaction_type,
            date,
        )

    @staticmethod
    def delete_position(id: int) -> OperationResult:
        """Delete security position."""
        return container.securities_controller().delete_position(id)

    @staticmethod
    def get_all_positions() -> list[dict]:
        """Get all individual positions."""
        return container.securities_controller().get_all_positions()

    @staticmethod
    def get_positions_by_ticker(ticker: str) -> list[dict]:
        """Get positions for specific ticker."""
        return container.securities_controller().get_positions_by_ticker(ticker)

    @staticmethod
    def get_aggregated_positions(user_currency: str = "EUR") -> list[dict]:
        """Get aggregated positions (totals)."""
        return container.securities_controller().get_aggregated_positions(user_currency)

    @staticmethod
    def get_chart_data_ticker(
        ticker: str, period: str = "1M", user_currency: str = "EUR"
    ) -> list[dict]:
        """Get chart data for a single ticker."""
        return container.securities_controller().get_chart_data_ticker(
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
        return container.portfolio_controller().get_portfolio_overview(user_currency)

    @staticmethod
    def get_chart_data(period: str = "1M", user_currency: str = "EUR") -> list[dict]:
        """Get chart data for the entire portfolio."""
        return container.portfolio_controller().get_chart_data(period, user_currency)


# ============================================================================
# BACKEND INTERFACE - Securities Reference
# ============================================================================


class SecuritiesReferenceService:
    """Frontend service for securities reference lookup."""

    @staticmethod
    def search(query: str, limit: int = 10) -> list[dict]:
        """Search securities reference by ticker or name."""
        return container.reference_controller().search(query, limit)


# ============================================================================
# BACKEND INTERFACE - Currency Operations
# ============================================================================


class CurrencyService:
    """Frontend service for currency operations."""

    @staticmethod
    def get_exchange_rate(from_currency: str, to_currency: str) -> float:
        """Get exchange rate between two currencies."""
        return container.currency_controller().get_exchange_rate(
            from_currency, to_currency
        )

    @staticmethod
    def get_currency_symbol(currency_code: str) -> str:
        """Get the display symbol for a currency code."""
        try:
            return Currency(currency_code).symbols
        except ValueError:
            return currency_code

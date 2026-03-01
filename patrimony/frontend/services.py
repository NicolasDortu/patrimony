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
    TransactionType,
)
from ..backend.presentation.controllers import (
    OperationResult,
    CashController,
    SecuritiesController,
    PortfolioController,
    PortfolioOverview,
)


# ============================================================================
# FRONTEND DATA MODELS
# ============================================================================


@dataclass
class SecurityPosition:
    """Frontend model for individual security position."""

    id: Optional[int] = None
    ticker: str = ""
    price: float = 0.0
    quantity: float = 1.0
    entry_type: EntryType = EntryType.MANUAL
    transaction_type: TransactionType = TransactionType.BUY
    currency: Currency = Currency.EUR
    date: datetime = field(default_factory=datetime.now)
    asset_type: AssetType = AssetType.STOCK


@dataclass
class SecurityTotal:
    """Frontend model for aggregated security positions."""

    ticker: str = ""
    total_quantity: float = 0.0
    avg_price: float = 0.0
    current_price: float = 0.0
    total_value: float = 0.0


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
        return CashController().add_cash(
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
        return CashController().update_cash(
            id, bank, account_number, currency, last_updated
        )

    @staticmethod
    def delete_cash(id: int) -> OperationResult:
        """Delete cash account."""
        return CashController().delete_cash(id)

    @staticmethod
    def get_all_cash() -> list[dict]:
        """Get all cash accounts."""
        return CashController().get_all_cash()

    @staticmethod
    def post_operation_balance(
        account_number: str,
        currency: Currency,
        amount: float,
        title: str,
        operation_date: datetime,
        entry_type: EntryType = EntryType.MANUAL,
    ) -> OperationResult:
        """Make an operation on cash balance."""
        return CashController().post_operation_balance(
            account_number, currency, amount, title, operation_date, entry_type
        )

    @staticmethod
    def get_operations_by_account(account_number: str) -> list[dict]:
        """Get balance operations for specific account."""
        return CashController().get_operations_by_account(account_number)

    @staticmethod
    def get_all_operations() -> list[dict]:
        """Get all balance operations."""
        return CashController().get_all_operations()

    @staticmethod
    def update_operation_by_id(
        id: int,
        amount: float,
        title: str,
        operation_date: datetime,
        entry_type: EntryType,
    ) -> OperationResult:
        """Update a balance operation by ID."""
        return CashController().update_operation_by_id(
            id, amount, title, operation_date, entry_type
        )

    @staticmethod
    def delete_operation_by_id(id: int) -> OperationResult:
        """Delete a balance operation by ID."""
        return CashController().delete_operation_by_id(id)

    @staticmethod
    def get_balance(account_number: str, currency: Currency) -> float:
        """Get current balance for specific account and currency."""
        return CashController().get_balance(account_number, currency)


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
        currency: Currency,
        date: Optional[datetime] = None,
    ) -> OperationResult:
        """Add new security position."""
        return SecuritiesController().add_position(
            ticker,
            price,
            quantity,
            entry_type,
            asset_type,
            transaction_type,
            currency,
            date,
        )

    @staticmethod
    def delete_position(id: int) -> OperationResult:
        """Delete security position."""
        return SecuritiesController().delete_position(id)

    @staticmethod
    def get_all_positions() -> list[dict]:
        """Get all individual positions."""
        return SecuritiesController().get_all_positions()

    @staticmethod
    def get_positions_by_ticker(ticker: str) -> list[dict]:
        """Get positions for specific ticker."""
        return SecuritiesController().get_positions_by_ticker(ticker)

    @staticmethod
    def get_aggregated_positions() -> list[dict]:
        """Get aggregated positions (totals)."""
        return SecuritiesController().get_aggregated_positions()

    @staticmethod
    def get_chart_data_ticker(ticker: str, period: str = "1M") -> list[dict]:
        """Get chart data for a single ticker."""
        return SecuritiesController().get_chart_data_ticker(ticker, period)


# ============================================================================
# BACKEND INTERFACE - Portfolio Operations
# ============================================================================


class PortfolioService:
    """Frontend service for portfolio operations."""

    @staticmethod
    def get_portfolio_overview() -> PortfolioOverview:
        """Get complete portfolio overview."""
        return PortfolioController().get_portfolio_overview()

    @staticmethod
    def get_chart_data(period: str = "1M") -> list[dict]:
        """Get chart data for the entire portfolio."""
        return PortfolioController().get_chart_data(period)

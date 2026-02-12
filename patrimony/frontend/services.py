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
    OperationResult,
)
from ..backend.presentation.controllers import (
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
        controller = CashController()
        return controller.add_cash(
            bank, account_number, currency, balance, last_updated
        )

    @staticmethod
    def update_cash(
        id: int,
        bank: str,
        account_number: str,
        currency: Currency,
        balance: float,
        last_updated: Optional[datetime] = None,
    ) -> OperationResult:
        """Update existing cash account."""
        controller = CashController()
        return controller.update_cash(
            id, bank, account_number, currency, balance, last_updated
        )

    @staticmethod
    def delete_cash(id: int) -> OperationResult:
        """Delete cash account."""
        controller = CashController()
        return controller.delete_cash(id)

    @staticmethod
    def get_all_cash() -> list[dict]:
        """Get all cash accounts."""
        controller = CashController()
        return controller.get_all_cash()


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
        controller = SecuritiesController()
        return controller.add_position(
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
        controller = SecuritiesController()
        return controller.delete_position(id)

    @staticmethod
    def get_all_positions() -> list[dict]:
        """Get all individual positions."""
        controller = SecuritiesController()
        return controller.get_all_positions()

    @staticmethod
    def get_positions_by_ticker(ticker: str) -> list[dict]:
        """Get positions for specific ticker."""
        controller = SecuritiesController()
        return controller.get_positions_by_ticker(ticker)

    @staticmethod
    def get_aggregated_positions() -> list[dict]:
        """Get aggregated positions (totals)."""
        controller = SecuritiesController()
        return controller.get_aggregated_positions()


# ============================================================================
# BACKEND INTERFACE - Portfolio Operations
# ============================================================================


class PortfolioService:
    """Frontend service for portfolio operations."""

    @staticmethod
    def get_portfolio_overview() -> PortfolioOverview:
        """Get complete portfolio overview."""
        controller = PortfolioController()
        return controller.get_portfolio_overview()

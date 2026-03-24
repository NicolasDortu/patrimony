"""Securities Controller - Thin delegate to repositories and SecuritiesService."""

import logging
from datetime import datetime
from typing import Optional

from ...domain.entities import AssetType, EntryType, TransactionType
from ...domain.repositories import SecuritiesRepository
from ...domain.services.securities_service import SecuritiesService
from .operation_result import OperationResult

logger = logging.getLogger(__name__)


class SecuritiesController:
    """Controller for securities (stocks, crypto, ETFs, bonds) operations."""

    def __init__(
        self,
        securities_repo: SecuritiesRepository,
        securities_service: SecuritiesService,
    ):
        self._securities_repo = securities_repo
        self._service = securities_service

    def add_position(
        self,
        ticker: str,
        price: float,
        quantity: float,
        entry_type: EntryType,
        asset_type: AssetType,
        transaction_type: TransactionType,
        date: Optional[datetime] = None,
    ) -> OperationResult:
        """Add new position (buy or sell)."""
        try:
            if date is None:
                date = datetime.now()

            position_id = self._securities_repo.add_position(
                ticker=ticker,
                price=price,
                quantity=quantity,
                entry_type=entry_type,
                asset_type=asset_type,
                transaction_type=transaction_type,
                date=date,
            )

            return OperationResult(
                success=True,
                message=f"Position for {ticker} added successfully",
                data={"id": position_id},
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to add position: {str(e)}",
            )

    def delete_position(self, id: int) -> OperationResult:
        """Delete position by ID."""
        try:
            self._securities_repo.delete(id)
            return OperationResult(
                success=True,
                message=f"Position {id} deleted successfully",
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Failed to delete position: {str(e)}",
            )

    def get_all_positions(self) -> list[dict]:
        """Get all individual positions."""
        df = self._securities_repo.get_all()
        if df is None:
            return []
        if "currency" in df.columns:
            df = df.drop("currency")
        return df.to_dicts()

    def get_positions_by_ticker(self, ticker: str) -> list[dict]:
        """Get all positions for specific ticker."""
        df = self._securities_repo.get_by_ticker(ticker)
        if df is None:
            return []
        if "currency" in df.columns:
            df = df.drop("currency")
        return df.to_dicts()

    def get_aggregated_positions(self, user_currency: str = "EUR") -> list[dict]:
        """Get aggregated positions enriched with current prices."""
        return self._service.get_aggregated_positions(user_currency)

    def get_position_by_id(self, id: int) -> Optional[dict]:
        """Get single position by ID."""
        df = self._securities_repo.get_by_id(id)
        if df is not None:
            return df.to_dicts()[0]
        return None

    def get_chart_data_ticker(
        self, ticker: str, period: str = "1M", user_currency: str = "EUR"
    ) -> list[dict]:
        """Get time-series price data for a single ticker."""
        return self._service.get_chart_data_ticker(ticker, period, user_currency)

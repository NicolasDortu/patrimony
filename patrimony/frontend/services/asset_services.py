"""Frontend services for asset operations (securities, dividends, properties, portfolio, currency)."""

import logging
from datetime import datetime
from typing import Optional

from ...backend.domain.entities import AssetType, Currency, EntryType, PortfolioOverview
from ...backend.presentation.di_container import container
from .models import OperationResult

logger = logging.getLogger(__name__)


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


class SecuritiesReferenceService:
    """Frontend service for securities reference lookup."""

    @staticmethod
    def search(query: str, limit: int = 10) -> list[dict]:
        """Search securities reference by ticker or name."""
        if not query or len(query) < 1:
            return []
        return container.reference_repository().search(query, limit)


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

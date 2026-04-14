"""Frontend services for asset operations (securities, dividends, properties, portfolio, currency)."""

import logging
from datetime import datetime
from typing import Optional

from ...backend.domain.entities import AssetType, Currency, EntryType, PortfolioOverview
from ...backend.application.di_container import container
from .models import OperationResult, operation_result, safe_query

logger = logging.getLogger(__name__)


class SecuritiesService:
    """Frontend service for securities operations."""

    @staticmethod
    @operation_result(
        failure="Failed to add position", success="Position added successfully"
    )
    def add_position(
        ticker: str,
        price: float,
        quantity: float,
        entry_type: EntryType,
        asset_type: AssetType,
        date: Optional[datetime] = None,
        fees: float = 0.0,
    ):
        return container.securities_use_cases().add_position(
            ticker=ticker,
            price=price,
            quantity=quantity,
            entry_type=entry_type,
            asset_type=asset_type,
            date=date,
            fees=fees,
        )

    @staticmethod
    @operation_result(
        failure="Failed to update position", success="Position updated successfully"
    )
    def update_position(
        id: int,
        ticker: str,
        price: float,
        quantity: float,
        entry_type: EntryType,
        asset_type: AssetType,
        date: Optional[datetime] = None,
        fees: float = 0.0,
    ):
        container.securities_use_cases().update_position(
            id=id,
            ticker=ticker,
            price=price,
            quantity=quantity,
            entry_type=entry_type,
            asset_type=asset_type,
            date=date,
            fees=fees,
        )

    @staticmethod
    @operation_result(
        failure="Failed to delete position", success="Position deleted successfully"
    )
    def delete_position(id: int):
        container.securities_use_cases().delete_position(id)

    @staticmethod
    @safe_query([])
    def get_all_positions() -> list[dict]:
        return container.securities_use_cases().get_all_positions()

    @staticmethod
    @safe_query([])
    def get_positions_by_ticker(ticker: str) -> list[dict]:
        return container.securities_use_cases().get_positions_by_ticker(ticker)

    @staticmethod
    @safe_query([])
    def get_aggregated_positions(user_currency: str = "EUR") -> list[dict]:
        return container.securities_use_cases().get_aggregated_positions(user_currency)

    @staticmethod
    @safe_query([])
    def get_chart_data_ticker(
        ticker: str, period: str = "1M", user_currency: str = "EUR"
    ) -> list[dict]:
        return container.securities_use_cases().get_chart_data_ticker(
            ticker, period, user_currency
        )

    @staticmethod
    @safe_query({})
    def get_current_prices(
        tickers: list[str], user_currency: str = "EUR"
    ) -> dict[str, float]:
        return container.securities_use_cases().get_current_prices(
            tickers, user_currency
        )


class PortfolioService:
    """Frontend service for portfolio operations."""

    @staticmethod
    def get_portfolio_overview(user_currency: str = "EUR") -> PortfolioOverview:
        return container.portfolio_use_cases().get_portfolio_overview(user_currency)

    @staticmethod
    @safe_query([])
    def get_chart_data(period: str = "1M", user_currency: str = "EUR") -> list[dict]:
        return container.portfolio_use_cases().get_chart_data(period, user_currency)


class SecuritiesReferenceService:
    """Frontend service for securities reference lookup."""

    @staticmethod
    @safe_query([])
    def search(query: str, limit: int = 10) -> list[dict]:
        if not query or len(query) < 1:
            return []
        return container.reference_repository().search(query, limit)


class CurrencyService:
    """Frontend service for currency operations."""

    @staticmethod
    def get_currency_symbol(currency_code: str) -> str:
        try:
            return Currency(currency_code).symbols
        except ValueError:
            return currency_code


class DividendService:
    """Frontend service for dividend operations."""

    @staticmethod
    @operation_result(
        failure="Failed to add dividend", success="Dividend added successfully"
    )
    def add_dividend(
        ticker: str,
        amount: float,
        date: Optional[datetime] = None,
    ):
        return container.dividend_use_cases().add_dividend(
            ticker=ticker, amount=amount, date=date
        )

    @staticmethod
    @safe_query([])
    def get_dividends_by_ticker(ticker: str) -> list[dict]:
        return container.dividend_use_cases().get_dividends_by_ticker(ticker)

    @staticmethod
    @safe_query([])
    def get_all_dividends() -> list[dict]:
        return container.dividend_use_cases().get_all_dividends()

    @staticmethod
    @safe_query(0.0)
    def get_total_amount() -> float:
        return container.dividend_use_cases().get_total_amount()

    @staticmethod
    @operation_result(
        failure="Failed to delete dividend", success="Dividend deleted successfully"
    )
    def delete_dividend(id: int):
        container.dividend_use_cases().delete_dividend(id)

    @staticmethod
    @operation_result(
        failure="Failed to update dividend", success="Dividend updated successfully"
    )
    def update_dividend(
        id: int,
        ticker: str,
        amount: float,
        date: Optional[datetime] = None,
    ):
        container.dividend_use_cases().update_dividend(
            id=id, ticker=ticker, amount=amount, date=date
        )

    @staticmethod
    @operation_result(failure="Failed to sync dividends")
    def sync_dividends(tickers: list[str] | None = None) -> OperationResult:
        result = container.dividend_use_cases().sync_dividends(tickers)
        imported = result["imported"]
        skipped = result["skipped"]
        errors = result.get("errors", [])
        if errors:
            return OperationResult(
                success=imported > 0,
                message=f"Synced {imported} dividends, {skipped} skipped, {len(errors)} errors",
                data=result,
            )
        return OperationResult(
            success=True,
            message=f"Synced {imported} new dividends ({skipped} already existed)",
            data=result,
        )


class PropertyService:
    """Frontend service for physical property operations."""

    @staticmethod
    @operation_result(
        failure="Failed to add property", success="Property added successfully"
    )
    def add_property(
        name: str,
        value: float,
        purchase_date: Optional[datetime] = None,
        description: str = "",
        category: str = "Other",
        currency: str = "EUR",
    ):
        return container.property_use_cases().add_property(
            name=name,
            value=value,
            purchase_date=purchase_date,
            description=description,
            category=category,
            currency=currency,
        )

    @staticmethod
    @safe_query([])
    def get_all_properties() -> list[dict]:
        return container.property_use_cases().get_all_properties()

    @staticmethod
    @operation_result(
        failure="Failed to delete property", success="Property deleted successfully"
    )
    def delete_property(id: int):
        container.property_use_cases().delete_property(id)

    @staticmethod
    @operation_result(
        failure="Failed to update property", success="Property updated successfully"
    )
    def update_property(
        id: int,
        name: str,
        value: float,
        purchase_date: Optional[datetime] = None,
        description: str = "",
        category: str = "Other",
        currency: str = "EUR",
    ):
        container.property_use_cases().update_property(
            id=id,
            name=name,
            value=value,
            purchase_date=purchase_date,
            description=description,
            category=category,
            currency=currency,
        )

"""Service Layer - Single interface between frontend and backend.

This package is the ONLY frontend module that accesses the backend.
States and components should only import from this package, never directly from backend.
"""

from ...backend.domain.entities import AssetType, Currency, EntryType
from ...backend.presentation.di_container import container

from .models import OperationResult, Property, SecurityPosition, SecurityTotal
from .cash_services import CashService
from .asset_services import (
    CurrencyService,
    DividendService,
    PortfolioService,
    PropertyService,
    SecuritiesReferenceService,
    SecuritiesService,
)
from .connector_services import (
    ConnectorHistoryService,
    CredentialService,
    FileConnectorService,
    WebConnectorService,
)
from .event_services import EventLogService


def was_market_data_fetched() -> bool:
    """Check and reset whether the market data API was called since last check."""
    return container.market_data_provider().check_api_was_called()


__all__ = [
    # Re-exported domain entities (consumers import these from services)
    "AssetType",
    "Currency",
    "EntryType",
    # Frontend models
    "OperationResult",
    "Property",
    "SecurityPosition",
    "SecurityTotal",
    # Services
    "CashService",
    "CurrencyService",
    "DividendService",
    "PortfolioService",
    "PropertyService",
    "SecuritiesReferenceService",
    "SecuritiesService",
    "FileConnectorService",
    "WebConnectorService",
    "ConnectorHistoryService",
    "CredentialService",
    "EventLogService",
    # Functions
    "was_market_data_fetched",
]

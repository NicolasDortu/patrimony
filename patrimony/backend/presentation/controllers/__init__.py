"""Controllers package - Presentation layer for clean architecture.
- Receive requests from the UI/API layer
- Delegate to domain services
- Format and return responses
- Handle errors and validation
"""

from .operation_result import OperationResult
from .cash_controller import CashController
from .securities_controller import SecuritiesController
from .price_controller import PriceController
from .portfolio_controller import PortfolioController
from .reference_controller import ReferenceController
from .currency_controller import CurrencyController

# Re-export PortfolioOverview from domain for backward compatibility
from ...domain.entities import PortfolioOverview

__all__ = [
    "OperationResult",
    "CashController",
    "SecuritiesController",
    "PriceController",
    "PortfolioController",
    "PortfolioOverview",
    "ReferenceController",
    "CurrencyController",
]

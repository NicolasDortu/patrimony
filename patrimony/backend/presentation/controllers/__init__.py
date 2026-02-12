"""Controllers package - Presentation layer for clean architecture.

Controllers are thin orchestration layers that:
- Receive requests from the UI/API layer
- Delegate to repositories and domain services
- Format and return responses
- Handle errors and validation

Controllers should NOT contain business logic.
"""

from .cash_controller import CashController
from .securities_controller import SecuritiesController
from .price_controller import PriceController
from .portfolio_controller import PortfolioController, PortfolioOverview
from ...domain.entities import OperationResult

__all__ = [
    "CashController",
    "SecuritiesController",
    "PriceController",
    "PortfolioController",
    "PortfolioOverview",
    "OperationResult",
]

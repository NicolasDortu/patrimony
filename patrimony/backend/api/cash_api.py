from .service_factory import get_service
from ..services.cash_service import CashService, CashOperationResult
from ...shared.models.assets import Cash


def add_cash(cash: Cash) -> CashOperationResult:
    """Add a new cash entry."""
    return get_service(CashService).add_cash(cash=cash)


def update_cash(id: int, cash: Cash) -> CashOperationResult:
    """Update an existing cash entry."""
    return get_service(CashService).update_cash(id=id, cash=cash)


def delete_cash(id: int) -> CashOperationResult:
    """Delete a cash entry by ID."""
    return get_service(CashService).delete_cash(id=id)


def get_all_cash() -> list[dict]:
    """Get all cash entries."""
    return get_service(CashService).get_all_cash().to_dicts()


def get_cash_by_bank(bank: str) -> list[dict]:
    """Get all cash entries for a specific bank."""
    return get_service(CashService).get_cash_by_bank(bank).to_dicts()

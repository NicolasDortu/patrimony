from .service_factory import get_service
from ..services.stock_service import StockService, StockPositionResult
from ...shared.models.assets import Stock


def add_stock_position(stock: Stock) -> StockPositionResult:
    return get_service(StockService).add_position(
        stock=stock,
    )


def delete_stock_position(id: int) -> StockPositionResult:
    return get_service(StockService).delete_position(id=id)


def validate_ticker(ticker: str) -> bool:
    return get_service(StockService).validate_ticker(ticker)


def get_all_stocks() -> list[dict]:
    return get_service(StockService).get_all_positions().to_dicts()


def get_all_stocks_total() -> list[dict]:
    return get_service(StockService).get_all_positions_total().to_dicts()

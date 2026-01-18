from .service_factory import get_service
from ..services.stock_service import StockService, StockPositionResult


def add_stock_position(
    ticker: str, buy_price: float, quantity: float
) -> StockPositionResult:
    return get_service(StockService).add_position(
        ticker=ticker,
        buy_price=buy_price,
        quantity=quantity,
    )


def delete_stock_position(id: int) -> None:
    return get_service(StockService).delete_position(id=id)


def validate_ticker(ticker: str) -> bool:
    return get_service(StockService).validate_ticker(ticker)


def get_all_stocks() -> list[dict]:
    return get_service(StockService).get_all_stocks().to_dicts()

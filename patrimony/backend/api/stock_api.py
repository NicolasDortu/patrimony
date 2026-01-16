from typing import List

from .service_factory import get_service
from ..services.stock_service import StockService, AddPositionResult
from ..domain.assets import Currency


def add_stock_position(
    ticker: str, buy_price: float, quantity: float
) -> AddPositionResult:
    return get_service(StockService).add_position(
        ticker=ticker,
        buy_price=buy_price,
        quantity=quantity,
        currency=Currency.USD,
    )


def validate_ticker(ticker: str) -> bool:
    return get_service(StockService).validate_ticker(ticker)


def validate_price(price: float) -> bool:
    return get_service(StockService).validate_price(price)


def get_all_stocks() -> List[dict]:
    value = get_service(StockService).get_all_stocks().to_dicts()
    print(value)
    return value

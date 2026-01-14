from ..services.stock_service import StockService, AddPositionResult
from ..domain.assets import Currency

_service = StockService()


def add_stock_position(
    ticker: str, buy_price: float, quantity: float
) -> AddPositionResult:
    return _service.add_position(
        ticker=ticker,
        buy_price=buy_price,
        quantity=quantity,
        currency=Currency.USD,
    )


def validate_ticker(ticker: str) -> bool:
    return _service.validate_ticker(ticker)


def validate_price(price: float) -> bool:
    return _service.validate_price(price)

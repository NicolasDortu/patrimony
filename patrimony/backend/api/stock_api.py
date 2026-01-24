import datetime
from .service_factory import get_service
from ..services.stock_service import StockService, StockPositionResult
from ..domain.models.assets import Stock, EntryType, BuySell, Currency


def add_stock_position(
    ticker: str,
    price: float,
    quantity: float,
    entry_type: str,
    buy_sell: str = "BUY",
    currency: str = "EUR",
    date: datetime.datetime = datetime.datetime.now(),
) -> StockPositionResult:
    stock = Stock(
        name=ticker,
        ticker=ticker,
        price=price,
        quantity=quantity,
        entry_type=EntryType(entry_type),
        buy_sell=BuySell(buy_sell),
        currency=Currency(currency),
        date=date,
    )
    return get_service(StockService).add_position(
        stock=stock,
    )


def delete_stock_position(id: int) -> None:
    return get_service(StockService).delete_position(id=id)


def validate_ticker(ticker: str) -> bool:
    return get_service(StockService).validate_ticker(ticker)


def get_all_stocks() -> list[dict]:
    return get_service(StockService).get_all_stocks().to_dicts()

"""Models for different types of assets in the patrimony application."""

import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AssetType(Enum):
    STOCK = "STOCK"
    CRYPTO = "CRYPTO"
    CASH = "CASH"
    BOND = "BOND"
    ETF = "ETF"
    FUND = "FUND"


class EntryType(Enum):
    MANUAL = "MANUAL"
    WEB = "WEB"
    CSV = "CSV"
    EXCEL = "EXCEL"
    API = "API"


class BuySell(Enum):
    BUY = "BUY"
    SELL = "SELL"


class Currency(Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"


@dataclass
class Asset:
    """Base class for all assets."""

    id: int = field(default=None)
    name: str = field(default=None)
    asset_type: AssetType = field(default=None)
    currency: Currency = Currency.EUR


@dataclass
class TradableAsset(Asset):
    """Assets that can be bought/sold with price tracking (stocks, crypto)."""

    ticker: str = ""
    price: float = 0.0
    quantity: float = 1.0
    entry_type: EntryType = field(default=EntryType.MANUAL)
    buy_sell: BuySell = field(default=BuySell.BUY)
    date: datetime.datetime = field(default_factory=datetime.datetime.now)


@dataclass
class Stock(TradableAsset):
    """Stock asset representation."""

    def __post_init__(self) -> None:
        self.asset_type = AssetType.STOCK
        # Name defaults to ticker if not provided
        if not self.name:
            self.name = self.ticker


@dataclass
class Crypto(TradableAsset):
    """Cryptocurrency asset representation."""

    def __post_init__(self):
        self.asset_type = AssetType.CRYPTO
        if not self.name:
            self.name = self.ticker


@dataclass
class Cash(Asset):
    """Cash asset representation."""

    balance: float = 0.0
    bank_name: Optional[str] = None

    def __post_init__(self):
        self.asset_type = AssetType.CASH

    @property
    def current_value(self) -> float:
        """Current value is simply the balance."""
        return self.balance


@dataclass
class EquityTotal:
    """Dataclass for total equity representation from the positions_total view."""

    ticker: str
    total_quantity: int
    current_price: float
    total_value: float

"""Models for different types of assets in the patrimony application."""

import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AssetType(Enum):
    STOCK = "stock"
    CRYPTO = "crypto"
    CASH = "cash"


class Currency(Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"


@dataclass
class Asset:
    """Base class for all assets."""

    name: str
    type: AssetType = field(default=None)
    currency: Currency = Currency.EUR


@dataclass
class TradableAsset(Asset):
    """Assets that can be bought/sold with price tracking (stocks, crypto)."""

    ticker: str = ""
    buy_price: float = 0.0
    quantity: float = 1.0
    buy_date: datetime.datetime = field(default_factory=datetime.datetime.now)


@dataclass
class Stock(TradableAsset):
    """Stock asset representation."""

    def __post_init__(self) -> None:
        self.type = AssetType.STOCK
        # Name defaults to ticker if not provided
        if not self.name:
            self.name = self.ticker


@dataclass
class Crypto(TradableAsset):
    """Cryptocurrency asset representation."""

    def __post_init__(self):
        self.type = AssetType.CRYPTO
        if not self.name:
            self.name = self.ticker


@dataclass
class Cash(Asset):
    """Cash asset representation."""

    balance: float = 0.0
    bank_name: Optional[str] = None

    def __post_init__(self):
        self.type = AssetType.CASH

    @property
    def current_value(self) -> float:
        """Current value is simply the balance."""
        return self.balance

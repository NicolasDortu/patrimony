from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class AssetType(Enum):
    """Asset classification."""

    STOCK = "STOCK"
    CRYPTO = "CRYPTO"
    CASH = "CASH"
    BOND = "BOND"
    ETF = "ETF"
    FUND = "FUND"


class Currency(Enum):
    """Supported currencies."""

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"


class EntryType(Enum):
    """How the entry was created."""

    MANUAL = "MANUAL"
    WEB = "WEB"
    CSV = "CSV"
    EXCEL = "EXCEL"
    API = "API"


class TransactionType(Enum):
    """Buy or sell transaction."""

    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class AssetIdentifier:
    """Value object for asset identification."""

    symbol: str
    asset_type: AssetType

    def __str__(self) -> str:
        return f"{self.symbol}:{self.asset_type.value}"


@dataclass
class OperationResult:
    """Generic result for operations."""

    success: bool
    message: str
    data: Optional[dict] = None


@dataclass
class CashAccount:
    """Cash account entity."""

    id: Optional[int]
    bank: str
    account_number: str
    currency: Currency
    balance: float
    last_updated: datetime

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "bank": self.bank,
            "account_number": self.account_number,
            "currency": self.currency.value,
            "balance": self.balance,
            "last_updated": self.last_updated.isoformat()
            if self.last_updated
            else None,
        }

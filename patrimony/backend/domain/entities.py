from enum import Enum


class AssetType(Enum):
    """Asset classification."""

    STOCK = "STOCK"
    CRYPTO = "CRYPTO"
    CASH = "CASH"
    BOND = "BOND"
    ETF = "ETF"
    COMMODITY = "COMMODITY"


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

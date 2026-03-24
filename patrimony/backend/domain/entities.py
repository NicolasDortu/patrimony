from dataclasses import dataclass
from enum import StrEnum


@dataclass(slots=True)
class PortfolioOverview:
    """Aggregated portfolio data with metrics."""

    securities_total: list[dict]
    cash_entries: list[dict]
    total_value: float
    total_invested: float
    total_return: float
    securities_value: float
    cash_value: float


class AssetType(StrEnum):
    """Asset classification."""

    STOCK = "STOCK"
    CRYPTO = "CRYPTO"
    CASH = "CASH"
    BOND = "BOND"
    ETF = "ETF"
    COMMODITY = "COMMODITY"


class EntryType(StrEnum):
    """How the entry was created."""

    MANUAL = "MANUAL"
    WEB = "WEB"
    CSV = "CSV"
    EXCEL = "EXCEL"
    API = "API"


class TransactionType(StrEnum):
    """Buy or sell transaction."""

    BUY = "BUY"
    SELL = "SELL"


class Currency(StrEnum):
    """Supported currencies."""

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"
    CAD = "CAD"
    AUD = "AUD"
    NZD = "NZD"
    CNY = "CNY"
    HKD = "HKD"
    SGD = "SGD"
    SEK = "SEK"
    NOK = "NOK"
    DKK = "DKK"
    KRW = "KRW"
    INR = "INR"
    BRL = "BRL"
    MXN = "MXN"
    ZAR = "ZAR"
    TRY = "TRY"
    PLN = "PLN"
    THB = "THB"
    TWD = "TWD"
    CZK = "CZK"
    HUF = "HUF"
    ILS = "ILS"
    AED = "AED"
    SAR = "SAR"

    @property
    def label(self) -> str:
        """Human-readable label for the currency."""
        labels = {
            "USD": "USD - US Dollar",
            "EUR": "EUR - Euro",
            "GBP": "GBP - British Pound",
            "JPY": "JPY - Japanese Yen",
            "CHF": "CHF - Swiss Franc",
            "CAD": "CAD - Canadian Dollar",
            "AUD": "AUD - Australian Dollar",
            "NZD": "NZD - New Zealand Dollar",
            "CNY": "CNY - Chinese Renminbi",
            "HKD": "HKD - Hong Kong Dollar",
            "SGD": "SGD - Singapore Dollar",
            "SEK": "SEK - Swedish Krona",
            "NOK": "NOK - Norwegian Krone",
            "DKK": "DKK - Danish Krone",
            "KRW": "KRW - South Korean Won",
            "INR": "INR - Indian Rupee",
            "BRL": "BRL - Brazilian Real",
            "MXN": "MXN - Mexican Peso",
            "ZAR": "ZAR - South African Rand",
            "TRY": "TRY - Turkish Lira",
            "PLN": "PLN - Polish Zloty",
            "THB": "THB - Thai Baht",
            "TWD": "TWD - Taiwan Dollar",
            "CZK": "CZK - Czech Koruna",
            "HUF": "HUF - Hungarian Forint",
            "ILS": "ILS - Israeli Shekel",
            "AED": "AED - UAE Dirham",
            "SAR": "SAR - Saudi Riyal",
        }
        return labels.get(self.value, self.value)

    @property
    def symbols(self) -> str:
        """Symbols for the currency."""
        symbols = {
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "JPY": "¥",
            "CHF": "CHF",
            "CAD": "CA$",
            "AUD": "A$",
            "NZD": "NZ$",
            "HKD": "HK$",
            "SGD": "S$",
            "MXN": "MX$",
            "CNY": "CN¥",
            "SEK": "kr",
            "NOK": "kr",
            "DKK": "kr",
            "KRW": "₩",
            "INR": "₹",
            "BRL": "R$",
            "ZAR": "R",
            "TRY": "₺",
            "PLN": "zł",
            "THB": "฿",
            "TWD": "NT$",
            "CZK": "Kč",
            "HUF": "Ft",
            "ILS": "₪",
            "AED": "AED",
            "SAR": "﷼",
        }
        return symbols.get(self.value, self.value)

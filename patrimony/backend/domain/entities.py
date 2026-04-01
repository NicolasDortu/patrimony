from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional

import polars as pl


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


@dataclass(slots=True)
class PortfolioOverview:
    """Aggregated portfolio data with metrics."""

    securities_total: Optional[pl.DataFrame]
    cash_entries: Optional[pl.DataFrame]
    total_value: float
    total_invested: float
    total_return: float
    securities_value: float
    cash_value: float


@dataclass(slots=True)
class ConnectorStep:
    """A single automation step in a web connector profile."""

    action: str  # "fill", "click", "wait", "download"
    selector: str = ""
    value: str = ""
    timeout: int = 30


@dataclass(slots=True)
class ConnectorProfile:
    """Definition of a web connector for a specific broker/bank."""

    id: str
    name: str
    url: str
    steps: list[ConnectorStep]
    column_mapping: dict[str, str]
    import_mode: str = "positions"  # "positions" or "cash"
    delimiter: str = ","
    description: str = ""
    new_accounts: dict[str, dict] | None = (
        None  # for cash import: acct -> {bank, currency}
    )


@dataclass(slots=True)
class WebConnectorResult:
    """Result of a web connector execution."""

    success: bool
    imported: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    download_path: str = ""
    status_log: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ConnectorHistoryEntry:
    """A recorded connector import run."""

    id: int | None = None
    connector_type: str = ""  # "web" or "file"
    profile_id: str | None = None
    source_name: str = ""
    source_path: str | None = None
    import_mode: str = "positions"
    column_mapping: dict[str, str] = field(default_factory=dict)
    delimiter: str = ","
    asset_type_overrides: dict[str, str] = field(default_factory=dict)
    new_accounts: dict[str, dict] | None = None
    imported: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    status: str = ""  # "success", "partial", "failed"
    created_at: str = ""


@dataclass(slots=True)
class CredentialInfo:
    """Safe credential metadata (never exposes raw credentials to frontend)."""

    profile_id: str
    has_credentials: bool

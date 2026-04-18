"""Domain entities related to core data structures and connectors."""

from dataclasses import dataclass, field
from enum import StrEnum


### Domain entities representing core data structures in the application. ###
class AssetType(StrEnum):
    """Asset classification."""

    STOCK = "STOCK"
    CRYPTO = "CRYPTO"
    CASH = "CASH"
    BOND = "BOND"
    ETF = "ETF"
    COMMODITY = "COMMODITY"
    PROPERTY = "PROPERTY"


class EntryType(StrEnum):
    """How the entry was created."""

    MANUAL = "MANUAL"
    WEB = "WEB"
    CSV = "CSV"
    EXCEL = "EXCEL"
    API = "API"


# Centralised currency metadata — (label, symbol) per code.
_CURRENCY_DICT: dict[str, tuple[str, str]] = {
    "USD": ("USD - US Dollar", "$"),
    "EUR": ("EUR - Euro", "€"),
    "GBP": ("GBP - British Pound", "£"),
    "JPY": ("JPY - Japanese Yen", "¥"),
    "CHF": ("CHF - Swiss Franc", "CHF"),
    "CAD": ("CAD - Canadian Dollar", "CA$"),
    "AUD": ("AUD - Australian Dollar", "A$"),
    "NZD": ("NZD - New Zealand Dollar", "NZ$"),
    "CNY": ("CNY - Chinese Renminbi", "CN¥"),
    "HKD": ("HKD - Hong Kong Dollar", "HK$"),
    "SGD": ("SGD - Singapore Dollar", "S$"),
    "SEK": ("SEK - Swedish Krona", "kr"),
    "NOK": ("NOK - Norwegian Krone", "kr"),
    "DKK": ("DKK - Danish Krone", "kr"),
    "KRW": ("KRW - South Korean Won", "₩"),
    "INR": ("INR - Indian Rupee", "₹"),
    "BRL": ("BRL - Brazilian Real", "R$"),
    "MXN": ("MXN - Mexican Peso", "MX$"),
    "ZAR": ("ZAR - South African Rand", "R"),
    "TRY": ("TRY - Turkish Lira", "₺"),
    "PLN": ("PLN - Polish Zloty", "zł"),
    "THB": ("THB - Thai Baht", "฿"),
    "TWD": ("TWD - Taiwan Dollar", "NT$"),
    "CZK": ("CZK - Czech Koruna", "Kč"),
    "HUF": ("HUF - Hungarian Forint", "Ft"),
    "ILS": ("ILS - Israeli Shekel", "₪"),
    "AED": ("AED - UAE Dirham", "AED"),
    "SAR": ("SAR - Saudi Riyal", "﷼"),
}


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
        info = _CURRENCY_DICT.get(self.value)
        return info[0] if info else self.value

    @property
    def symbols(self) -> str:
        """Symbol for the currency."""
        info = _CURRENCY_DICT.get(self.value)
        return info[1] if info else self.value


@dataclass(slots=True)
class TickerInfo:
    """Enriched ticker metadata"""

    ticker: str
    isin: str | None = None
    name: str | None = None
    asset_type: str | None = None
    exchange: str | None = None
    currency: str | None = None
    source: str = ""
    last_updated: str | None = None


@dataclass(slots=True)
class PortfolioOverview:
    """Aggregated portfolio metrics."""

    total_value: float
    total_invested: float
    total_return: float
    securities_value: float
    cash_value: float
    properties_value: float


### Entities related to web connector configuration and results. ###
@dataclass(slots=True)
class ConnectorProfile:
    """Data mapping configuration for a web connector.

    Each web connector plugin owns its own URL and navigation logic.
    The profile holds only the data-mapping and import settings.

    Args:
        id: Unique identifier for the connector profile.
        name: User-friendly name for the connector configuration.
        description: Optional description of the connector profile.
        credential_fields: List of (field_name, field_type) tuples defining required credentials.
        import_mode: "positions" to import quantity and price, "cash" to import only cash value.
        new_accounts: Dictionary defining new cash accounts to be created during import.
        column_mapping: Dictionary mapping source columns to target fields.
        needs_matching: Boolean indicating if manual matching is required after import.
    """

    id: str
    name: str
    column_mapping: dict[str, str]
    import_mode: str = "positions"  # "positions" or "cash"
    description: str = ""
    new_accounts: dict[str, dict] | None = None
    credential_fields: list[tuple] | None = None
    needs_matching: bool = False


@dataclass(slots=True)
class WebConnectorResult:
    """Result of a web connector execution."""

    success: bool
    imported: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    status_log: list[str] = field(default_factory=list)
    needs_matching: bool = False
    unmatched_positions: list[dict] = field(default_factory=list)


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
    new_cash_accounts: dict[str, dict] | None = None
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

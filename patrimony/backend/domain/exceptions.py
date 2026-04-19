"""Custom domain exceptions for error handling and reporting."""


class DomainError(Exception):
    """Base exception for all domain-level errors."""


# ── Import pipeline ────────────────────────────────────────────


class ImportError(DomainError):
    """Base exception for data import failures."""


class MissingMappingError(ImportError):
    """Required column mappings are missing."""

    def __init__(self, missing_fields: set[str]):
        self.missing_fields = missing_fields
        super().__init__(
            f"Missing required mappings: {', '.join(sorted(missing_fields))}"
        )


class MissingColumnError(ImportError):
    """target field mapped to a source column that doesn't exist in the file."""

    def __init__(self, missing_columns: set[str]):
        self.missing_columns = missing_columns
        super().__init__(
            f"Mapped columns not found in file: {', '.join(sorted(missing_columns))}"
        )


class AssetTypeResolutionError(ImportError):
    """Could not resolve the asset type for a ticker."""

    def __init__(self, ticker: str, row: int | None = None):
        self.ticker = ticker
        self.row = row
        location = f"Row {row}: " if row else ""
        super().__init__(f"{location}Unknown asset type for ticker '{ticker}'")


class DateParsingError(ImportError):
    """Could not parse a date string into a known format."""

    def __init__(self, value: str):
        self.value = value
        super().__init__(f"Unrecognized date format: '{value}'")


# ── Connector / fetch ──────────────────────────────────────────


class ConnectorError(DomainError):
    """Base exception for site connector failures."""


class ConnectorNotFoundError(ConnectorError):
    """Requested site connector does not exist in the registry."""

    def __init__(self, site_id: str):
        self.site_id = site_id
        super().__init__(f"No connector registered for '{site_id}'")


class DataFetchError(ConnectorError):
    """The site connector failed to retrieve data."""

    def __init__(self, site_id: str, cause: Exception | None = None):
        self.site_id = site_id
        self.cause = cause
        msg = f"Data fetch failed for '{site_id}'"
        if cause:
            msg += f": {cause}"
        super().__init__(msg)


# ── Sync ───────────────────────────────────────────────────────


class SyncError(DomainError):
    """Base exception for price/dividend sync failures."""


class PriceSyncError(SyncError):
    """Price history synchronization failed for a ticker."""

    def __init__(self, ticker: str, cause: Exception | None = None):
        self.ticker = ticker
        self.cause = cause
        msg = f"Price sync failed for '{ticker}'"
        if cause:
            msg += f": {cause}"
        super().__init__(msg)


class DividendSyncError(SyncError):
    """Dividend synchronization failed for a ticker."""

    def __init__(self, ticker: str, cause: Exception | None = None):
        self.ticker = ticker
        self.cause = cause
        msg = f"Dividend sync failed for '{ticker}'"
        if cause:
            msg += f": {cause}"
        super().__init__(msg)


# ── Currency ───────────────────────────────────────────────────


class CurrencyConversionError(DomainError):
    """No usable exchange rate (fresh or stale) is available for a conversion."""

    def __init__(
        self, from_currency: str, to_currency: str, cause: Exception | None = None
    ):
        self.from_currency = from_currency
        self.to_currency = to_currency
        self.cause = cause
        msg = f"No exchange rate available for {from_currency} -> {to_currency}"
        if cause:
            msg += f": {cause}"
        super().__init__(msg)


class TickerCurrencyUnknownError(DomainError):
    """The native currency for a ticker could not be resolved."""

    def __init__(self, ticker: str):
        self.ticker = ticker
        super().__init__(f"Could not resolve native currency for ticker '{ticker}'")

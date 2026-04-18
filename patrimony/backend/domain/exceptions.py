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

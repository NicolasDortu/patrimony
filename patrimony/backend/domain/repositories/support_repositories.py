"""Repository interfaces for support/infrastructure concerns.

Covers connectors, credentials, import tracking, and event logging.
"""

from abc import ABC, abstractmethod

import polars as pl

from ..entities import ConnectorHistoryEntry, TickerInfo


class CredentialRepository(ABC):
    """Repository for encrypted credential storage with master password."""

    @abstractmethod
    def has_master_password(self) -> bool:
        """Check if a master password has been configured."""
        pass

    @abstractmethod
    def setup_master_password(self, password: str) -> bytes:
        """Set up a new master password. Returns Fernet key."""
        pass

    @abstractmethod
    def verify_master_password(self, password: str) -> bytes | None:
        """Verify the master password. Returns Fernet key if correct, None otherwise."""
        pass

    @abstractmethod
    def store_credentials(
        self, profile_id: str, credentials: dict[str, str], fernet_key: bytes
    ) -> None:
        """Encrypt and store credentials for a profile."""
        pass

    @abstractmethod
    def get_credentials(
        self, profile_id: str, fernet_key: bytes
    ) -> dict[str, str] | None:
        """Decrypt and return credentials dict for a profile, or None."""
        pass

    @abstractmethod
    def delete_credentials(self, profile_id: str) -> None:
        """Delete stored credentials for a profile."""
        pass

    @abstractmethod
    def reset_master_password(self) -> None:
        """Delete the master password and all stored credentials."""
        pass

    @abstractmethod
    def list_stored_profiles(self) -> list[str]:
        """Return profile IDs that have stored credentials."""
        pass


class ConnectorHistoryRepository(ABC):
    """Repository for connector import history."""

    @abstractmethod
    def add_entry(self, entry: ConnectorHistoryEntry) -> int:
        """Record a connector history entry and return its ID."""
        pass

    @abstractmethod
    def get_all(self) -> list[ConnectorHistoryEntry]:
        """Return all history entries, newest first."""
        pass

    @abstractmethod
    def get_latest_by_source(
        self, connector_type: str, source_identifier: str
    ) -> ConnectorHistoryEntry | None:
        """Get the most recent entry for a given source."""
        pass

    @abstractmethod
    def delete(self, entry_id: int) -> None:
        """Delete a history entry."""
        pass


class ImportHashRepository(ABC):
    """Repository for tracking imported row hashes (deduplication)."""

    @abstractmethod
    def existing_hashes(self, hashes: set[str]) -> set[str]:
        """Return the subset of hashes that already exist in the store."""
        pass

    @abstractmethod
    def add_hashes(self, hashes: list[str], import_type: str) -> None:
        """Persist new hashes."""
        pass


class ReferenceRepository(ABC):
    """Repository for securities reference data."""

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search securities by ticker or name (case-insensitive)."""
        pass


class TickerInfoRepository(ABC):
    """Repository for enriched ticker metadata (ISIN lookups, asset type, etc.)."""

    @abstractmethod
    def get_by_ticker(self, ticker: str) -> TickerInfo | None:
        """Return ticker info for a given ticker, or None."""
        pass

    @abstractmethod
    def get_by_isin(self, isin: str) -> TickerInfo | None:
        """Return ticker info for a given ISIN, or None."""
        pass

    @abstractmethod
    def get_by_name(self, name: str) -> TickerInfo | None:
        """Return ticker info by name (case-insensitive match), or None."""
        pass

    @abstractmethod
    def get_batch_by_isin(self, isins: list[str]) -> dict[str, TickerInfo]:
        """Return a dict of ISIN → TickerInfo for all ISINs found."""
        pass

    @abstractmethod
    def upsert(self, info: TickerInfo) -> None:
        """Insert or update ticker info."""
        pass


class EventLogRepository(ABC):
    """Repository for persistent notification/event storage."""

    @abstractmethod
    def add_batch(self, events: list[dict]) -> None:
        """Persist a batch of events."""
        pass

    @abstractmethod
    def get_recent(self, limit: int = 100) -> pl.DataFrame:
        """Return the most recent events, newest first."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Delete all stored events."""
        pass

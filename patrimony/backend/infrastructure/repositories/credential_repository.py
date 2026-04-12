"""Repository for encrypted credential storage using Fernet + PBKDF2.

Master password is never stored. A random salt and verification hash
are persisted so we can re-derive the Fernet key from the password.
"""

import base64
import hashlib
import logging
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from ...domain.repositories import CredentialRepository
from ..database.connection import DatabaseConnection

logger = logging.getLogger(__name__)

_PBKDF2_ITERATIONS = 480_000


def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive a Fernet-compatible key from a password and salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


class CredentialRepositoryImpl(CredentialRepository):
    """DuckDB-backed encrypted credential storage."""

    def __init__(self, connection: DatabaseConnection):
        self._conn = connection

    def has_master_password(self) -> bool:
        row = self._conn.execute("SELECT COUNT(*) FROM connector_master_key").fetchone()
        return row[0] > 0

    def setup_master_password(self, password: str) -> bytes:
        salt = os.urandom(32)
        fernet_key = _derive_key(password, salt)
        verification_hash = hashlib.sha256(fernet_key).digest()

        # Remove any existing master key (reset scenario)
        self._conn.execute("DELETE FROM connector_master_key")
        self._conn.execute("DELETE FROM connector_credentials")
        self._conn.execute(
            "INSERT INTO connector_master_key (id, salt, verification_hash) VALUES (1, ?, ?)",
            [salt, verification_hash],
        )
        return fernet_key

    def verify_master_password(self, password: str) -> bytes | None:
        row = self._conn.execute(
            "SELECT salt, verification_hash FROM connector_master_key WHERE id = 1"
        ).fetchone()
        if not row:
            return None

        salt, stored_hash = row[0], row[1]
        fernet_key = _derive_key(password, salt)
        computed_hash = hashlib.sha256(fernet_key).digest()

        # Convert memoryview to bytes for comparison if needed
        stored = (
            bytes(stored_hash) if isinstance(stored_hash, memoryview) else stored_hash
        )
        if computed_hash == stored:
            return fernet_key
        return None

    def store_credentials(
        self, profile_id: str, credentials: dict[str, str], fernet_key: bytes
    ) -> None:
        f = Fernet(fernet_key)

        # Delete existing credentials for this profile
        self._conn.execute(
            "DELETE FROM connector_credentials WHERE profile_id = ?",
            [profile_id],
        )

        # Insert each credential field
        for placeholder, value in credentials.items():
            enc_value = f.encrypt(value.encode())
            self._conn.execute(
                "INSERT INTO connector_credentials "
                "(profile_id, placeholder, encrypted_value) VALUES (?, ?, ?)",
                [profile_id, placeholder, enc_value],
            )

    def get_credentials(
        self, profile_id: str, fernet_key: bytes
    ) -> dict[str, str] | None:
        rows = self._conn.execute(
            "SELECT placeholder, encrypted_value "
            "FROM connector_credentials WHERE profile_id = ?",
            [profile_id],
        ).fetchall()
        if not rows:
            return None

        try:
            f = Fernet(fernet_key)
            result = {}
            for placeholder, enc_value in rows:
                raw = (
                    bytes(enc_value) if isinstance(enc_value, memoryview) else enc_value
                )
                result[placeholder] = f.decrypt(raw).decode()
            return result
        except InvalidToken:
            logger.warning("Failed to decrypt credentials for profile %s", profile_id)
            return None

    def delete_credentials(self, profile_id: str) -> None:
        self._conn.execute(
            "DELETE FROM connector_credentials WHERE profile_id = ?",
            [profile_id],
        )

    def reset_master_password(self) -> None:
        self._conn.execute("DELETE FROM connector_credentials")
        self._conn.execute("DELETE FROM connector_master_key")

    def list_stored_profiles(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT profile_id FROM connector_credentials"
        ).fetchall()
        return [row[0] for row in rows]

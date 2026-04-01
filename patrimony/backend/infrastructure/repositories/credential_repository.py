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
        self, profile_id: str, username: str, password: str, fernet_key: bytes
    ) -> None:
        f = Fernet(fernet_key)
        enc_user = f.encrypt(username.encode())
        enc_pass = f.encrypt(password.encode())

        # Upsert
        existing = self._conn.execute(
            "SELECT 1 FROM connector_credentials WHERE profile_id = ?",
            [profile_id],
        ).fetchone()

        if existing:
            self._conn.execute(
                "UPDATE connector_credentials "
                "SET encrypted_username = ?, encrypted_password = ?, updated_at = CURRENT_TIMESTAMP "
                "WHERE profile_id = ?",
                [enc_user, enc_pass, profile_id],
            )
        else:
            self._conn.execute(
                "INSERT INTO connector_credentials "
                "(profile_id, encrypted_username, encrypted_password) VALUES (?, ?, ?)",
                [profile_id, enc_user, enc_pass],
            )

    def get_credentials(
        self, profile_id: str, fernet_key: bytes
    ) -> tuple[str, str] | None:
        row = self._conn.execute(
            "SELECT encrypted_username, encrypted_password "
            "FROM connector_credentials WHERE profile_id = ?",
            [profile_id],
        ).fetchone()
        if not row:
            return None

        try:
            f = Fernet(fernet_key)
            enc_user = bytes(row[0]) if isinstance(row[0], memoryview) else row[0]
            enc_pass = bytes(row[1]) if isinstance(row[1], memoryview) else row[1]
            username = f.decrypt(enc_user).decode()
            password = f.decrypt(enc_pass).decode()
            return username, password
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
            "SELECT profile_id FROM connector_credentials"
        ).fetchall()
        return [row[0] for row in rows]

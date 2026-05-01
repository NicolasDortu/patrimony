"""Shared pytest fixtures."""

from pathlib import Path

import pytest

from patrimony.backend.infrastructure.database.connection import DatabaseConnection


@pytest.fixture
def tmp_db(tmp_path: Path):
    """A fresh DuckDB instance backed by a temporary file.

    Each test gets its own database with the full DDL applied. Closed at
    teardown so the file can be deleted by pytest's tmp_path cleanup.
    """
    db = DatabaseConnection(db_path=tmp_path / "test.duckdb")
    yield db
    db.close_connection()

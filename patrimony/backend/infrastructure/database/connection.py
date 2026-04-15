import os
import atexit
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Any

import polars as pl
import duckdb

from . import ddl

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Raised when a database operation fails."""

    def __init__(self, message: str, query: str = None, original: Exception = None):
        self.query = query
        self.original = original
        super().__init__(message)


class DatabaseConnection:
    """Duckdb instantiation and connection management."""

    def __init__(self, db_path: Path = None) -> None:
        self.db_path = db_path if db_path else _get_db_path()
        self.conn = duckdb.connect(str(self.db_path))
        self.init_db()
        atexit.register(self.close_connection)

    def init_db(self) -> None:
        for command in ddl.DDL_COMMANDS:
            self.conn.execute(command)
        self._load_reference_data()

    def _load_reference_data(self) -> None:
        """Load tickers reference table from CSV if empty."""
        filled = self.conn.execute(
            "SELECT EXISTS (SELECT 1 FROM tickers_reference)"
        ).fetchone()[0]
        if filled:
            return

        csv_path = Path(__file__).parent / "data" / "tickers.csv"
        if not csv_path.exists():
            logger.warning("Tickers CSV not found at %s", csv_path)
            return

        df = pl.read_csv(str(csv_path), encoding="utf8-lossy")
        self.conn.execute(
            "INSERT INTO tickers_reference "
            "(ticker, name, asset_type, exchange, category, country) "
            "SELECT ticker, name, asset_type, exchange, category, country FROM df"
        )
        logger.info("Loaded %d securities into reference table", len(df))

    def execute(
        self, query: str, parameters: list[Any] = None
    ) -> duckdb.DuckDBPyConnection:
        """Execute a query and return the result.

        Args:
            query: SQL query string
            parameters: Optional parameters for parameterized queries

        Returns:
            DuckDB query result

        Raises:
            DatabaseError: If the query fails
        """
        try:
            if parameters:
                return self.conn.execute(query, parameters)
            return self.conn.execute(query)
        except duckdb.Error as e:
            logger.error(
                "Query failed: %s | Params: %s | Error: %s", query, parameters, e
            )
            raise DatabaseError(message=str(e), query=query, original=e) from e

    def executemany(self, query: str, parameters: list[tuple]) -> None:
        """Execute a query once for each parameter set (batch insert).

        Args:
            query: SQL query string with placeholders
            parameters: List of parameter tuples/lists

        Raises:
            DatabaseError: If the query fails
        """
        try:
            self.conn.executemany(query, parameters)
        except duckdb.Error as e:
            logger.error("Batch query failed: %s | Error: %s", query, e)
            raise DatabaseError(message=str(e), query=query, original=e) from e

    @contextmanager
    def transaction(self):
        """Context manager for transactions with automatic rollback on failure.

        Raises:
            DatabaseError: If the transaction or any operation within it fails
        """
        self.execute("BEGIN TRANSACTION")
        try:
            yield
            self.execute("COMMIT")
        except DatabaseError:
            self.execute("ROLLBACK")
            raise
        except Exception as e:
            self.execute("ROLLBACK")
            logger.error("Transaction failed: %s", e)
            raise DatabaseError(message=f"Transaction failed: {e}", original=e) from e

    @property
    def connection(self) -> duckdb.DuckDBPyConnection:
        return self.conn

    def close_connection(self) -> None:
        self.conn.close()


def _get_db_path() -> Path:
    """Set the database path based on the environment and OS."""
    if os.name == "nt":  # Windows
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    else:  # Unix-like systems
        base = Path.home() / ".local" / "share"

    db_dir = base / "patrimony" / "data"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "patrimony.duckdb"

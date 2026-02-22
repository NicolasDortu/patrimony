import os
import atexit
from pathlib import Path

import duckdb

from . import ddl


def _get_db_path() -> Path:
    """Set the database path based on the environment and OS."""
    if os.name == "nt":  # Windows
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    else:  # Unix-like systems
        base = Path.home() / ".local" / "share"

    db_dir = base / "patrimony" / "data"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "patrimony.duckdb"


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

    def execute(self, query: str, parameters=None) -> duckdb.DuckDBPyConnection:
        """Execute a query and return the result.

        Args:
            query: SQL query string
            parameters: Optional parameters for parameterized queries

        Returns:
            DuckDB query result
        """
        if parameters:
            return self.conn.execute(query, parameters)
        return self.conn.execute(query)

    @property
    def connection(self) -> duckdb.DuckDBPyConnection:
        return self.conn

    def close_connection(self) -> None:
        self.conn.close()

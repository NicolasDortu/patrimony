from pathlib import Path

import duckdb

from ..common.metaclasses import Singleton
from ..database import ddl


class DatabaseConnection(metaclass=Singleton):
    """Duckdb instantiation and connection management."""

    def __init__(self, db_path: Path = None) -> None:
        self.db_path = (
            db_path if db_path else Path(__file__).parent / "data" / "patrimony.duckdb"
        )
        self.conn = duckdb.connect(str(self.db_path))
        self.init_db()

    def init_db(self) -> None:
        for command in ddl.DDL_COMMANDS:
            self.conn.execute(command)

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        return self.conn

    def close(self) -> None:
        self.conn.close()

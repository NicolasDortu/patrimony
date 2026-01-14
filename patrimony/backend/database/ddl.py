"""Data Definition Language (DDL) commands for duckdb database schema."""

CREATE_POSITIONS_TABLE = """
    CREATE SEQUENCE IF NOT EXISTS positions_id_seq;
    CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY DEFAULT nextval('positions_id_seq'),
        ticker VARCHAR NOT NULL,
        buy_price DOUBLE NOT NULL,
        quantity DOUBLE DEFAULT 1.0,
        buy_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_PRICE_CACHE_TABLE = """
    CREATE TABLE IF NOT EXISTS price_cache (
        ticker VARCHAR PRIMARY KEY,
        current_price DOUBLE NOT NULL,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_PRICE_HISTORY_TABLE = """
    CREATE TABLE IF NOT EXISTS price_history (
        ticker VARCHAR NOT NULL,
        date TIMESTAMP NOT NULL,
        close_price DOUBLE NOT NULL,
        period VARCHAR NOT NULL,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (ticker, date, period)
)
"""

DDL_COMMANDS = [
    CREATE_POSITIONS_TABLE,
    CREATE_PRICE_CACHE_TABLE,
    CREATE_PRICE_HISTORY_TABLE,
]

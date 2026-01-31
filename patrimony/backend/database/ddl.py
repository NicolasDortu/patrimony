"""Data Definition Language (DDL) commands for duckdb database schema."""

CREATE_POSITIONS_TABLE = """
    CREATE SEQUENCE IF NOT EXISTS positions_id_seq;
    CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY DEFAULT nextval('positions_id_seq'),
        ticker VARCHAR NOT NULL,
        price DOUBLE NOT NULL,
        quantity DOUBLE DEFAULT 1.0,
        entry_type VARCHAR NOT NULL,
        asset_type VARCHAR NOT NULL,
        buy_sell VARCHAR NOT NULL DEFAULT 'BUY',
        currency VARCHAR DEFAULT 'EUR',
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

CREATE_POSITIONS_TOTAL_VIEW = """
    CREATE OR REPLACE VIEW positions_total AS
    SELECT
        agg.ticker,
        agg.total_quantity,
        pc.current_price,
        agg.total_quantity * pc.current_price AS total_value
    FROM (
        SELECT
            ticker,
            SUM(CASE WHEN buy_sell = 'BUY' THEN quantity ELSE -quantity END) AS total_quantity
        FROM positions
        GROUP BY ticker
    ) agg
    LEFT JOIN price_cache pc ON agg.ticker = pc.ticker
"""

CREATE_CASH_TABLE = """
    CREATE SEQUENCE IF NOT EXISTS cash_id_seq;
    CREATE TABLE IF NOT EXISTS cash (
        id INTEGER PRIMARY KEY DEFAULT nextval('cash_id_seq'),
        bank VARCHAR NOT NULL,
        account_number VARCHAR NOT NULL,
        currency VARCHAR DEFAULT 'EUR',
        balance DOUBLE NOT NULL,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

DDL_COMMANDS = [
    CREATE_POSITIONS_TABLE,
    CREATE_PRICE_CACHE_TABLE,
    CREATE_PRICE_HISTORY_TABLE,
    CREATE_POSITIONS_TOTAL_VIEW,
    CREATE_CASH_TABLE,
]

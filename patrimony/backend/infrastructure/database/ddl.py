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
        transaction_type VARCHAR NOT NULL DEFAULT 'BUY',
        currency VARCHAR DEFAULT 'EUR',
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
    CREATE INDEX IF NOT EXISTS idx_positions_ticker ON positions (ticker);
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
        agg.avg_price,
        pc.current_price,
        agg.total_quantity * pc.current_price AS total_value
    FROM (
        SELECT
            ticker,
            SUM(CASE WHEN transaction_type = 'BUY' THEN quantity ELSE -quantity END) AS total_quantity,
            SUM(CASE WHEN transaction_type = 'BUY' THEN price * quantity ELSE -price * quantity END) /
                NULLIF(SUM(CASE WHEN transaction_type = 'BUY' THEN quantity ELSE -quantity END), 0) AS avg_price
        FROM positions
        GROUP BY ticker
    ) agg
    LEFT JOIN price_cache pc ON agg.ticker = pc.ticker
"""

CREATE_CASH_TABLE = """
    CREATE TABLE IF NOT EXISTS cash (
        bank VARCHAR NOT NULL,
        account_number VARCHAR PRIMARY KEY,
        currency VARCHAR DEFAULT 'EUR',
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        entry_type VARCHAR NOT NULL DEFAULT 'MANUAL'
)
"""

CREATE_BALANCE_OPERATIONS_TABLE = """
    CREATE SEQUENCE IF NOT EXISTS balance_operations_id_seq;
    CREATE TABLE IF NOT EXISTS balance_operations (
        id INTEGER PRIMARY KEY DEFAULT nextval('balance_operations_id_seq'),
        account_number VARCHAR NOT NULL,
        rank INTEGER NOT NULL,
        amount DOUBLE NOT NULL,
        balance DOUBLE NOT NULL,
        title VARCHAR,
        operation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        entry_type VARCHAR NOT NULL DEFAULT 'MANUAL',
        FOREIGN KEY (account_number) REFERENCES cash(account_number)
);
    CREATE INDEX IF NOT EXISTS idx_balance_ops_accountnumber
        ON balance_operations (account_number);
"""

CREATE_CASH_BALANCE_VIEW = """
    CREATE OR REPLACE VIEW cash_balance AS
    SELECT account_number, balance
    FROM balance_operations
    WHERE (account_number, rank) IN (
        SELECT account_number, MAX(rank)
        FROM balance_operations
        GROUP BY account_number
    )
"""

DDL_COMMANDS = [
    CREATE_POSITIONS_TABLE,
    CREATE_PRICE_CACHE_TABLE,
    CREATE_PRICE_HISTORY_TABLE,
    CREATE_POSITIONS_TOTAL_VIEW,
    CREATE_CASH_TABLE,
    CREATE_BALANCE_OPERATIONS_TABLE,
    CREATE_CASH_BALANCE_VIEW,
]

"""Data Definition Language (DDL) commands for duckdb database schema."""

CREATE_POSITIONS_TABLE = """
    CREATE SEQUENCE IF NOT EXISTS positions_id_seq;
    CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY DEFAULT nextval('positions_id_seq'),
        ticker VARCHAR NOT NULL,
        price DOUBLE NOT NULL,
        quantity DOUBLE DEFAULT 1.0,
        fees DOUBLE DEFAULT 0.0,
        entry_type VARCHAR NOT NULL,
        asset_type VARCHAR NOT NULL,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_POSITIONS_CLOSED_TABLE = """
    CREATE SEQUENCE IF NOT EXISTS positions_closed_id_seq;
    CREATE TABLE IF NOT EXISTS positions_closed (
        id INTEGER PRIMARY KEY DEFAULT nextval('positions_closed_id_seq'),
        ticker VARCHAR NOT NULL,
        price DOUBLE NOT NULL,
        quantity DOUBLE DEFAULT 1.0,
        fees DOUBLE DEFAULT 0.0,
        entry_type VARCHAR NOT NULL,
        asset_type VARCHAR NOT NULL,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_DIVIDENDS_TABLE = """
    CREATE SEQUENCE IF NOT EXISTS dividends_id_seq;
    CREATE TABLE IF NOT EXISTS dividends (
        id INTEGER PRIMARY KEY DEFAULT nextval('dividends_id_seq'),
        ticker VARCHAR NOT NULL,
        amount DOUBLE NOT NULL,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (ticker, date)
);
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
        agg.asset_type,
        pc.current_price,
        agg.total_quantity * pc.current_price AS total_value
    FROM (
        SELECT
            b.ticker,
            b.asset_type,
            b.buy_qty - COALESCE(s.sell_qty, 0) AS total_quantity,
            b.total_cost / NULLIF(b.buy_qty, 0) AS avg_price
        FROM (
            SELECT
                ticker,
                MIN(asset_type) AS asset_type,
                SUM(quantity) AS buy_qty,
                SUM(price * quantity + fees) AS total_cost
            FROM positions
            GROUP BY ticker
        ) b
        LEFT JOIN (
            SELECT ticker, SUM(quantity) AS sell_qty
            FROM positions_closed
            GROUP BY ticker
        ) s ON b.ticker = s.ticker
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
        category VARCHAR DEFAULT 'Uncategorized',
        operation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        entry_type VARCHAR NOT NULL DEFAULT 'MANUAL',
        FOREIGN KEY (account_number) REFERENCES cash(account_number)
);
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

CREATE_TICKERS_REFERENCE_TABLE = """
CREATE TABLE IF NOT EXISTS tickers_reference (
    ticker VARCHAR PRIMARY KEY,
    name VARCHAR,
    asset_type VARCHAR,
    exchange VARCHAR,
    category VARCHAR,
    country VARCHAR
);

"""

CREATE_TICKER_CURRENCY_TABLE = """
CREATE TABLE IF NOT EXISTS ticker_currency (
    ticker VARCHAR PRIMARY KEY,
    currency VARCHAR NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_EXCHANGE_RATE_CACHE_TABLE = """
CREATE TABLE IF NOT EXISTS exchange_rate_cache (
    from_currency VARCHAR NOT NULL,
    to_currency VARCHAR NOT NULL,
    rate DOUBLE NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (from_currency, to_currency)
);
"""

CREATE_USER_ASSET_TYPES_VIEW = """
CREATE OR REPLACE VIEW user_asset_types AS
SELECT DISTINCT asset_type
FROM positions
"""

CREATE_CONNECTOR_MASTER_KEY_TABLE = """
CREATE TABLE IF NOT EXISTS connector_master_key (
    id INTEGER PRIMARY KEY DEFAULT 1,
    salt BLOB NOT NULL,
    verification_hash BLOB NOT NULL
);
"""

CREATE_CONNECTOR_CREDENTIALS_TABLE = """
CREATE TABLE IF NOT EXISTS connector_credentials (
    profile_id VARCHAR PRIMARY KEY,
    encrypted_username BLOB NOT NULL,
    encrypted_password BLOB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_CONNECTOR_HISTORY_TABLE = """
CREATE SEQUENCE IF NOT EXISTS connector_history_id_seq;
CREATE TABLE IF NOT EXISTS connector_history (
    id INTEGER PRIMARY KEY DEFAULT nextval('connector_history_id_seq'),
    connector_type VARCHAR NOT NULL,
    profile_id VARCHAR,
    source_name VARCHAR NOT NULL,
    source_path VARCHAR,
    import_mode VARCHAR NOT NULL,
    column_mapping TEXT,
    delimiter VARCHAR DEFAULT ',',
    asset_type_overrides TEXT,
    new_accounts TEXT,
    imported INTEGER DEFAULT 0,
    skipped INTEGER DEFAULT 0,
    errors TEXT,
    status VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_IMPORT_HASHES_TABLE = """
CREATE TABLE IF NOT EXISTS import_hashes (
    hash VARCHAR PRIMARY KEY,
    import_type VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_PROPERTIES_TABLE = """
    CREATE SEQUENCE IF NOT EXISTS properties_id_seq;
    CREATE TABLE IF NOT EXISTS properties (
        id INTEGER PRIMARY KEY DEFAULT nextval('properties_id_seq'),
        name VARCHAR NOT NULL,
        description VARCHAR DEFAULT '',
        value DOUBLE NOT NULL,
        purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        category VARCHAR DEFAULT 'Other',
        currency VARCHAR DEFAULT 'EUR',
        entry_type VARCHAR NOT NULL DEFAULT 'MANUAL'
);
"""

CREATE_EVENT_LOG_TABLE = """
    CREATE SEQUENCE IF NOT EXISTS event_log_id_seq;
    CREATE TABLE IF NOT EXISTS event_log (
        id INTEGER PRIMARY KEY DEFAULT nextval('event_log_id_seq'),
        level VARCHAR NOT NULL,
        summary VARCHAR NOT NULL,
        detail VARCHAR DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

BUILD_INDEXES = """
    CREATE INDEX IF NOT EXISTS idx_ref_name ON tickers_reference(name);
    CREATE INDEX IF NOT EXISTS idx_ref_asset_type ON tickers_reference(asset_type);
"""

# Indexes on user-modified tables are rebuilt on every startup to prevent DuckDB ART index corruption.
REBUILD_INDEXES = """
    DROP INDEX IF EXISTS idx_positions_ticker;
    CREATE INDEX idx_positions_ticker ON positions (ticker);
    DROP INDEX IF EXISTS idx_positions_closed_ticker;
    CREATE INDEX idx_positions_closed_ticker ON positions_closed (ticker);
    DROP INDEX IF EXISTS idx_dividends_ticker;
    CREATE INDEX idx_dividends_ticker ON dividends (ticker);
    DROP INDEX IF EXISTS idx_balance_ops_accountnumber;
    CREATE INDEX idx_balance_ops_accountnumber ON balance_operations (account_number);
"""

DDL_COMMANDS = [
    CREATE_POSITIONS_TABLE,
    CREATE_POSITIONS_CLOSED_TABLE,
    CREATE_PRICE_CACHE_TABLE,
    CREATE_PRICE_HISTORY_TABLE,
    CREATE_POSITIONS_TOTAL_VIEW,
    CREATE_CASH_TABLE,
    CREATE_BALANCE_OPERATIONS_TABLE,
    CREATE_DIVIDENDS_TABLE,
    CREATE_CASH_BALANCE_VIEW,
    CREATE_TICKERS_REFERENCE_TABLE,
    CREATE_TICKER_CURRENCY_TABLE,
    CREATE_EXCHANGE_RATE_CACHE_TABLE,
    CREATE_USER_ASSET_TYPES_VIEW,
    CREATE_CONNECTOR_MASTER_KEY_TABLE,
    CREATE_CONNECTOR_CREDENTIALS_TABLE,
    CREATE_CONNECTOR_HISTORY_TABLE,
    CREATE_IMPORT_HASHES_TABLE,
    CREATE_PROPERTIES_TABLE,
    CREATE_EVENT_LOG_TABLE,
    BUILD_INDEXES,
    REBUILD_INDEXES,
]

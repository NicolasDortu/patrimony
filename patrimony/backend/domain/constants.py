"""Domain constants shared across services."""

PERIOD_CONFIG = {
    "1D": {"days": 1, "period": "1d", "interval": "5m"},
    "5D": {"days": 5, "period": "5d", "interval": "1d"},
    "1M": {"days": 30, "period": "1mo", "interval": "1d"},
    "6M": {"days": 180, "period": "6mo", "interval": "1d"},
    "1Y": {"days": 365, "period": "1y", "interval": "1d"},
    "5Y": {"days": 1825, "period": "5y", "interval": "1wk"},
}

ASSET_TYPE_LABELS = {
    "STOCK": "Stocks",
    "ETF": "ETFs",
    "CRYPTO": "Crypto",
    "COMMODITY": "Commodity",
    "BOND": "Bonds",
    "CASH": "Cash",
    "PROPERTY": "Properties",
}

# Sync batch settings for price & dividend synchronization.
SYNC_BATCH_SIZE: int = 5
SYNC_BATCH_DELAY_S: float = 2.0

# Minimum days of data required to render a meaningful chart.
MIN_CHART_DAYS: int = 2

# Minimum interval (seconds) between consecutive external API calls.
MIN_API_REQUEST_INTERVAL_S: float = 0.55

"""Domain repository interfaces.

Split into two modules by concern:
- asset_repositories: securities, cash, prices, currencies, dividends, properties
- support_repositories: connectors, credentials, references, import tracking, event log
"""

from .asset_repositories import (
    CashOperationRepository,
    CashRepository,
    CurrencyRepository,
    DividendRepository,
    PriceRepository,
    PropertyRepository,
    SecuritiesRepository,
)
from .support_repositories import (
    ConnectorHistoryRepository,
    CredentialRepository,
    EventLogRepository,
    ImportHashRepository,
    ReferenceRepository,
    TickerInfoRepository,
)

__all__ = [
    "CashOperationRepository",
    "CashRepository",
    "ConnectorHistoryRepository",
    "CredentialRepository",
    "CurrencyRepository",
    "DividendRepository",
    "EventLogRepository",
    "ImportHashRepository",
    "PriceRepository",
    "PropertyRepository",
    "ReferenceRepository",
    "SecuritiesRepository",
    "TickerInfoRepository",
]

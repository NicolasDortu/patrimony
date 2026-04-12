"""Domain repository interfaces.

Split into two modules by concern:
- asset_repositories: securities, cash, prices, currencies, dividends, properties
- support_repositories: connectors, credentials, import tracking, event log
"""

from .asset_repositories import (
    CashOperationRepository,
    CashRepository,
    CurrencyRepository,
    DividendRepository,
    PriceRepository,
    PropertyRepository,
    ReferenceRepository,
    SecuritiesRepository,
)
from .support_repositories import (
    ConnectorHistoryRepository,
    CredentialRepository,
    EventLogRepository,
    ImportHashRepository,
    TickerAliasRepository,
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
    "TickerAliasRepository",
]

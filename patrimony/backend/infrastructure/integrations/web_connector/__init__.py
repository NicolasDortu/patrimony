"""Site connector plugins for browser-based data download.

To add a new connector: create a new file, implement BaseSiteConnector,
and add an instance to SITE_CONNECTORS below.
"""

from .base import PlaywrightSiteConnector
from .sandbox import SandboxConnector
from .degiro import DegiroConnector
from .trade_republic import TradeRepublicConnector
from .revolut import RevolutConnector

# Registry of all available site connectors.
SITE_CONNECTORS = [
    SandboxConnector(),
    DegiroConnector(),
    TradeRepublicConnector(),
    RevolutConnector(),
]

__all__ = [
    "PlaywrightSiteConnector",
    "SITE_CONNECTORS",
    "SandboxConnector",
    "DegiroConnector",
    "TradeRepublicConnector",
    "RevolutConnector",
]

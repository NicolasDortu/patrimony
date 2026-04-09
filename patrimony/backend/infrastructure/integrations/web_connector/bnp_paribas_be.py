"""BNP Paribas Belgium bank connector.

TODO: Implement BNP-specific login, navigation,
      and transaction export download logic.
"""

from collections.abc import Callable

import polars as pl
from playwright.async_api import Page

from ....domain.entities import ConnectorProfile
from .base import PlaywrightSiteConnector


class BNPParibasBEConnector(PlaywrightSiteConnector):
    """Browser automation for BNP Paribas Belgium transaction export."""

    @property
    def site_id(self) -> str:
        return "bnp_paribas_be"

    @property
    def profile(self) -> ConnectorProfile:
        return ConnectorProfile(
            id="bnp_paribas_be",
            name="BNP Paribas Belgium",
            description="BNP Paribas Belgium bank.",
            import_mode="cash",
            column_mapping={},  # TODO: fill when implementing
        )

    async def _execute(
        self,
        page: Page,
        credentials: dict[str, str],
        on_status: Callable[[str], None] | None,
    ) -> pl.DataFrame:
        raise NotImplementedError("BNP Paribas Belgium connector not yet implemented.")

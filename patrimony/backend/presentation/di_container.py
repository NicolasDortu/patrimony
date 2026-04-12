from dependency_injector import containers, providers

from ..infrastructure.database.connection import DatabaseConnection
from ..infrastructure.integrations import (
    YahooFinanceProvider,
    ExcelCsvConnector,
)
from ..infrastructure.integrations.web_connector import SITE_CONNECTORS
from ..domain.services.connectors import FileConnectorService
from ..domain.services.currency_service import CurrencyService
from ..domain.services.portfolio_service import PortfolioService
from ..domain.services.portfolio_chart_service import PortfolioChartService
from ..domain.services.price_sync_service import PriceSyncService
from ..domain.services.securities_service import SecuritiesService
from ..domain.services.connectors import WebConnectorService
from ..domain.services.dividend_sync_service import DividendSyncService
from ..infrastructure.repositories import (
    CashRepositoryImpl,
    SecuritiesRepositoryImpl,
    PriceRepositoryImpl,
    ReferenceRepositoryImpl,
    CurrencyRepositoryImpl,
    DividendRepositoryImpl,
    CredentialRepositoryImpl,
    ImportHashRepositoryImpl,
    ConnectorHistoryRepositoryImpl,
    PropertyRepositoryImpl,
    EventLogRepositoryImpl,
    TickerInfoRepositoryImpl,
)


class Container(containers.DeclarativeContainer):
    """Application DI container.

    Manages lifecycle of all layers:
    - Infrastructure (database, external services, repositories)
    - Domain services (business logic)

    The frontend service layer (frontend/services.py) consumes
    repositories and domain services directly from here.
    """

    # Infrastructure Layer - Singletons
    database = providers.Singleton(DatabaseConnection)

    # External Services - Singletons
    market_data_provider = providers.Singleton(YahooFinanceProvider)
    file_connector = providers.Singleton(ExcelCsvConnector)

    # Site Connectors
    site_connectors = providers.Object(SITE_CONNECTORS)

    # Repository Layer - Singletons (stateless, share singleton DB connection)
    cash_repository = providers.Singleton(
        CashRepositoryImpl,
        connection=database,
    )

    securities_repository = providers.Singleton(
        SecuritiesRepositoryImpl,
        connection=database,
    )

    price_repository = providers.Singleton(
        PriceRepositoryImpl,
        connection=database,
        market_data_provider=market_data_provider,
    )

    reference_repository = providers.Singleton(
        ReferenceRepositoryImpl,
        connection=database,
    )

    currency_repository = providers.Singleton(
        CurrencyRepositoryImpl,
        connection=database,
    )

    dividend_repository = providers.Singleton(
        DividendRepositoryImpl,
        connection=database,
    )

    import_hash_repository = providers.Singleton(
        ImportHashRepositoryImpl,
        connection=database,
    )

    credential_repository = providers.Singleton(
        CredentialRepositoryImpl,
        connection=database,
    )

    connector_history_repository = providers.Singleton(
        ConnectorHistoryRepositoryImpl,
        connection=database,
    )

    property_repository = providers.Singleton(
        PropertyRepositoryImpl,
        connection=database,
    )

    event_log_repository = providers.Singleton(
        EventLogRepositoryImpl,
        connection=database,
    )

    ticker_info_repository = providers.Singleton(
        TickerInfoRepositoryImpl,
        connection=database,
    )

    # Domain Services
    currency_service = providers.Singleton(
        CurrencyService,
        currency_repo=currency_repository,
        market_data_provider=market_data_provider,
    )

    price_sync_service = providers.Singleton(
        PriceSyncService,
        price_repo=price_repository,
        market_data=market_data_provider,
    )

    dividend_sync_service = providers.Singleton(
        DividendSyncService,
        dividend_repo=dividend_repository,
        securities_repo=securities_repository,
        market_data=market_data_provider,
    )

    portfolio_chart_service = providers.Singleton(
        PortfolioChartService,
        securities_repo=securities_repository,
        cash_repo=cash_repository,
        price_repo=price_repository,
        currency_service=currency_service,
        market_data=market_data_provider,
        price_sync=price_sync_service,
    )

    portfolio_service = providers.Singleton(
        PortfolioService,
        securities_repo=securities_repository,
        cash_repo=cash_repository,
        price_repo=price_repository,
        currency_service=currency_service,
        chart_service=portfolio_chart_service,
        property_repo=property_repository,
    )

    securities_service = providers.Singleton(
        SecuritiesService,
        securities_repo=securities_repository,
        price_repo=price_repository,
        currency_service=currency_service,
        market_data=market_data_provider,
        price_sync=price_sync_service,
    )

    connector_service = providers.Factory(
        FileConnectorService,
        securities_repo=securities_repository,
        cash_repo=cash_repository,
        reference_repo=reference_repository,
        hash_repo=import_hash_repository,
        info_repo=ticker_info_repository,
        market_data_provider=market_data_provider,
    )

    web_connector_service = providers.Factory(
        WebConnectorService,
        site_connectors=site_connectors,
        connector_service=connector_service,
    )


# Global container instance
container = Container()

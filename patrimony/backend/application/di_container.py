from dependency_injector import containers, providers

from . import (
    CashUseCases,
    ConnectorHistoryUseCases,
    DividendUseCases,
    FileImportUseCases,
    PortfolioUseCases,
    PropertyUseCases,
    SecuritiesUseCases,
    WebConnectorUseCases,
)
from ..domain.services import (
    CashService,
    ChartService,
    CurrencyService,
    DividendSyncService,
    PortfolioService,
    PriceSyncService,
    PropertyService,
    SecuritiesService,
)
from ..domain.services.connectors import FileConnectorService, WebConnectorService
from ..infrastructure import (
    DatabaseConnection,
    YahooFinanceProvider,
    ExcelCsvConnector,
    SITE_CONNECTORS,
)
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

    cash_service = providers.Singleton(
        CashService,
        cash_repo=cash_repository,
        currency_service=currency_service,
    )

    property_service = providers.Singleton(
        PropertyService,
        property_repo=property_repository,
        currency_service=currency_service,
    )

    chart_service = providers.Singleton(
        ChartService,
        securities_repo=securities_repository,
        cash_service=cash_service,
        price_repo=price_repository,
        currency_service=currency_service,
        price_sync=price_sync_service,
    )

    securities_service = providers.Singleton(
        SecuritiesService,
        securities_repo=securities_repository,
        currency_service=currency_service,
        price_sync=price_sync_service,
    )

    portfolio_service = providers.Singleton(
        PortfolioService,
        securities_service=securities_service,
        cash_service=cash_service,
        property_service=property_service,
        chart_service=chart_service,
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

    # Application Layer - Use Cases
    securities_use_cases = providers.Singleton(
        SecuritiesUseCases,
        securities_repo=securities_repository,
        securities_service=securities_service,
        chart_service=chart_service,
        price_sync=price_sync_service,
        currency_service=currency_service,
    )

    portfolio_use_cases = providers.Singleton(
        PortfolioUseCases,
        portfolio_service=portfolio_service,
    )

    cash_use_cases = providers.Singleton(
        CashUseCases,
        cash_repo=cash_repository,
    )

    dividend_use_cases = providers.Singleton(
        DividendUseCases,
        dividend_repo=dividend_repository,
        securities_repo=securities_repository,
        dividend_sync_service=dividend_sync_service,
    )

    property_use_cases = providers.Singleton(
        PropertyUseCases,
        property_repo=property_repository,
    )

    connector_use_cases = providers.Factory(
        FileImportUseCases,
        file_connector=file_connector,
        connector_service=connector_service,
    )

    web_connector_use_cases = providers.Factory(
        WebConnectorUseCases,
        web_connector_service=web_connector_service,
    )

    connector_history_use_cases = providers.Singleton(
        ConnectorHistoryUseCases,
        history_repo=connector_history_repository,
    )


# Global container instance
container = Container()

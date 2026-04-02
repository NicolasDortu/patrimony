from dependency_injector import containers, providers

from ..infrastructure.database.connection import DatabaseConnection
from ..infrastructure.integrations import (
    YahooFinanceProvider,
    ExcelCsvConnector,
    PlaywrightConnector,
)
from ..domain.services.file_connector_service import FileConnectorService
from ..domain.services.currency_service import CurrencyService
from ..domain.services.portfolio_service import PortfolioService
from ..domain.services.securities_service import SecuritiesService
from ..domain.services.web_connector_service import WebConnectorService
from ..infrastructure.repositories import (
    CashRepositoryImpl,
    SecuritiesRepositoryImpl,
    PriceRepositoryImpl,
    ReferenceRepositoryImpl,
    CurrencyRepositoryImpl,
    DividendRepositoryImpl,
    ConnectorProfileRepositoryImpl,
    CredentialRepositoryImpl,
    ImportHashRepositoryImpl,
    ConnectorHistoryRepositoryImpl,
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
    web_connector = providers.Singleton(PlaywrightConnector)

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

    connector_profile_repository = providers.Singleton(
        ConnectorProfileRepositoryImpl,
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

    # Domain Services
    currency_service = providers.Factory(
        CurrencyService,
        currency_repo=currency_repository,
        market_data_provider=market_data_provider,
    )

    portfolio_service = providers.Factory(
        PortfolioService,
        securities_repo=securities_repository,
        cash_repo=cash_repository,
        price_repo=price_repository,
        currency_service=currency_service,
        market_data=market_data_provider,
    )

    securities_service = providers.Factory(
        SecuritiesService,
        securities_repo=securities_repository,
        price_repo=price_repository,
        currency_service=currency_service,
        market_data=market_data_provider,
    )

    connector_service = providers.Factory(
        FileConnectorService,
        file_connector=file_connector,
        securities_repo=securities_repository,
        cash_repo=cash_repository,
        reference_repo=reference_repository,
        hash_repo=import_hash_repository,
    )

    web_connector_service = providers.Factory(
        WebConnectorService,
        web_connector=web_connector,
        file_connector=file_connector,
        connector_service=connector_service,
        profile_repo=connector_profile_repository,
    )


# Global container instance
container = Container()

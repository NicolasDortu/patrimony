from dependency_injector import containers, providers

from ..infrastructure.database.connection import DatabaseConnection
from ..infrastructure.integrations import YahooFinanceProvider, ExcelCsvConnector
from ..domain.services.connector_service import ConnectorService
from ..domain.services.currency_service import CurrencyService
from ..domain.services.portfolio_service import PortfolioService
from ..domain.services.securities_service import SecuritiesService
from ..infrastructure.repositories import (
    CashRepositoryImpl,
    SecuritiesRepositoryImpl,
    PriceRepositoryImpl,
    ReferenceRepositoryImpl,
    CurrencyRepositoryImpl,
    DividendRepositoryImpl,
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

    # Repository Layer - Factories (new instance per call, but with singleton deps)
    cash_repository = providers.Factory(
        CashRepositoryImpl,
        connection=database,
    )

    securities_repository = providers.Factory(
        SecuritiesRepositoryImpl,
        connection=database,
    )

    price_repository = providers.Factory(
        PriceRepositoryImpl,
        connection=database,
        market_data_provider=market_data_provider,
    )

    reference_repository = providers.Factory(
        ReferenceRepositoryImpl,
        connection=database,
    )

    currency_repository = providers.Factory(
        CurrencyRepositoryImpl,
        connection=database,
    )

    dividend_repository = providers.Factory(
        DividendRepositoryImpl,
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
        ConnectorService,
        file_connector=file_connector,
        securities_repo=securities_repository,
        cash_repo=cash_repository,
        reference_repo=reference_repository,
    )


# Global container instance
container = Container()

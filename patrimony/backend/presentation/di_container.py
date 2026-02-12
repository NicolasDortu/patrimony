from dependency_injector import containers, providers

from ..infrastructure.database.connection import DatabaseConnection
from ..infrastructure.integrations import YahooFinanceProvider
from ..infrastructure.repositories import (
    CashRepositoryImpl,
    SecuritiesRepositoryImpl,
    PriceRepositoryImpl,
)


class Container(containers.DeclarativeContainer):
    """Application DI container.

    Manages lifecycle of infrastructure components:
    - Database connections (singletons)
    - External services (singletons)
    - Repositories (factories with singleton dependencies)

    Controllers access repositories directly from this container.
    """

    # Infrastructure Layer - Singletons
    database = providers.Singleton(DatabaseConnection)

    # External Services - Singletons
    market_data_provider = providers.Singleton(
        YahooFinanceProvider,
        # TODO: Add config for API keys when using paid providers
    )

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


# Global container instance
container = Container()

from __future__ import annotations
from orionis.container.providers.service_provider import ServiceProvider
from orionis.logging.contracts.logger import ILogger
from orionis.logging import Logger
from orionis.support.facades.logger import Log as LoggerFacade

class LoggerProvider(ServiceProvider):

    def register(self) -> None:
        """
        Register the Logger service implementation in the application container.

        Bind the `Logger` class to the `ILogger` contract within the application's
        dependency injection container. Retrieve the logging configuration from the
        application, create a `Logger` instance using this configuration, and
        register it with an alias for internal framework identification.

        Returns
        -------
        None
            No return value. Performs service registration as a side effect on the
            application container.
        """
        self.app.singleton(ILogger, Logger, alias="x-orionis-ILogger")

    async def boot(self) -> None:
        """
        Initialize the logging system after all services are registered.

        This method retrieves the logging configuration from the application,
        creates a Logger instance with this configuration, and initializes the
        Logger service. Ensures the logging system is ready after all providers
        have been registered.

        Returns
        -------
        None
            This method does not return a value. It performs initialization as a
            side effect.
        """
        await LoggerFacade.pin()

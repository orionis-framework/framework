"""Register logger services in the application container."""

from __future__ import annotations
from orionis.container.providers.service_provider import ServiceProvider
from orionis.logging.contracts.logger import ILogger
from orionis.logging import Logger
from orionis.support.facades.logger import Log as LoggerFacade


class LoggerProvider(ServiceProvider):
    """Register logger services in the application container."""

    def register(self) -> None:
        """
        Register the Logger service implementation in the application container.

        Bind the ``Logger`` class to the ``ILogger`` contract within the application's
        dependency injection container with an alias for internal framework
        identification. Construction remains lazy until the service is resolved.

        Returns
        -------
        None
            No return value.
        """
        self.app.singleton(ILogger, Logger, alias="x-orionis-ILogger")

    async def boot(self) -> None:
        """
        Resolve the logger service and pin its application facade.

        Resolving the singleton retains application configuration. File handlers
        and queue listeners remain lazy until a message or ``getLogger`` call.

        Returns
        -------
        None
            No return value.
        """
        await LoggerFacade.pin()

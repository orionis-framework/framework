"""Register catch services in the application container."""

from __future__ import annotations
from orionis.container.providers.service_provider import ServiceProvider
from orionis.failure.catch import Catch
from orionis.failure.contracts.catch import ICatch
from orionis.support.facades.catch import Catch as CatchFacade


class CatchProvider(ServiceProvider):
    """Register catch services in the application container."""

    def register(self) -> None:
        """
        Register the Catch service as a singleton in the application container.

        Returns
        -------
        None
            No return value.

        Notes
        -----
        Binds the ``ICatch`` interface to the ``Catch`` implementation as a singleton,
        using a specific alias. Ensures only one instance of ``Catch`` is created
        and shared throughout the application's lifecycle.
        """
        self.app.singleton(ICatch, Catch, alias="x-orionis-ICatch")

    async def boot(self) -> None:
        """
        Resolve and pin the Catch facade after service registration.

        Returns
        -------
        None
            No return value.
        """
        await CatchFacade.pin()

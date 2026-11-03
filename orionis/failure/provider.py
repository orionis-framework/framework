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

        Parameters
        ----------
        self : orionis.failure.provider.CatchProvider
            The instance of the CathcProvider class.

        Returns
        -------
        None
            This method does not return a value. It registers the Catch service
            as a singleton in the application container.

        Notes
        -----
        Binds the ``ICatch`` interface to the ``Catch`` implementation as a singleton,
        using a specific alias. Ensures only one instance of ``Catch`` is created
        and shared throughout the application's lifecycle.
        """
        self.app.singleton(ICatch, Catch, alias="x-orionis-ICatch")

    async def boot(self) -> None:
        """
        Boot the Catch service provider after registration.

        Parameters
        ----------
        self : orionis.failure.provider.CatchProvider
            Instance of the CathcProvider class.

        Returns
        -------
        None
            This method does not return a value. It performs asynchronous
            initialization for the Catch service provider after all services
            have been registered.
        """
        await CatchFacade.pin()

from __future__ import annotations
from orionis.container.providers.service_provider import ServiceProvider
from orionis.failure.catch import Catch
from orionis.failure.contracts.catch import ICatch
from orionis.support.facades.catch import Catch as CatchFacade

class CatchProvider(ServiceProvider):

    def register(self) -> None:
        """
        Register the Catch service as a singleton in the application container.

        Parameters
        ----------
        self : CathcProvider
            The instance of the CathcProvider class.

        Returns
        -------
        None
            This method does not return a value. It registers the Catch service
            as a singleton in the application container.

        Notes
        -----
        Binds the `ICatch` interface to the `Catch` implementation as a singleton,
        using a specific alias. Ensures only one instance of `Catch` is created
        and shared throughout the application's lifecycle.
        """
        self.app.singleton(ICatch, Catch, alias="x-orionis-ICatch")

    async def boot(self) -> None:
        """
        Boot the Catch service provider after registration.

        Parameters
        ----------
        self : CathcProvider
            Instance of the CathcProvider class.

        Returns
        -------
        None
            This method does not return a value. It performs asynchronous
            initialization for the Catch service provider after all services
            have been registered.
        """
        await CatchFacade.pin()

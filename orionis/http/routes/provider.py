from __future__ import annotations
from orionis.container.providers.service_provider import ServiceProvider
from orionis.http.routes.contracts.router import IRouter
from orionis.http.routes.router import Router
from orionis.support.facades.router import Route as RouteFacade

class RouterProvider(ServiceProvider):

    def register(self) -> None:
        """
        Register the IRouter contract as a singleton in the application container.

        Bind IRouter to Router with the alias ``x-orionis-IRouter`` for later
        resolution.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.app.singleton(IRouter, Router, alias="x-orionis-IRouter")

    async def boot(self) -> None:
        """
        Initialize the Route facade asynchronously during the boot process.

        This method ensures that the Route facade is properly initialized before
        handling requests.

        Returns
        -------
        None
            This method does not return a value.
        """
        await RouteFacade.pin()

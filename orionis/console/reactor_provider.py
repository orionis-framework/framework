from __future__ import annotations
from orionis.console.core.contracts.reactor import IReactor
from orionis.console.core.reactor import Reactor
from orionis.container.providers.service_provider import ServiceProvider
from orionis.support.facades.reactor import Reactor as ReactorFacade

class ReactorProvider(ServiceProvider):

    def register(self) -> None:
        """
        Register the reactor management service in the application container.

        Bind the `IReactor` interface as a singleton to the `Reactor`
        implementation in the application's dependency injection container.

        Returns
        -------
        None
            No return value. Service is registered in the container.
        """
        self.app.singleton(IReactor, Reactor, alias="x-orionis-IReactor")

    async def boot(self) -> None:
        """
        Perform post-registration bootstrapping for the reactor provider.

        This asynchronous method is called after all service providers have been
        registered. For ReactorProvider, it initializes the Reactor. No additional
        setup is required at this time.

        Returns
        -------
        None
            This method does not return a value.
        """
        await ReactorFacade.pin()

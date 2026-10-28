from __future__ import annotations
from orionis.console.debug.contracts.dumper import IDumper
from orionis.console.debug.dumper import Dumper
from orionis.container.providers.service_provider import ServiceProvider
from orionis.support.facades.debug import Debug

class DumperProvider(ServiceProvider):

    def register(self) -> None:
        """
        Register the dumper contract as a singleton.

        Returns
        -------
        None
            Bind the implementation and the alias used by the facade.
        """
        self.app.singleton(IDumper, Dumper, alias="x-orionis-IDumper")

    async def boot(self) -> None:
        """
        Pin the Debug facade for direct synchronous calls.

        Returns
        -------
        None
            Make the registered service available without deferred dispatch.
        """
        await Debug.pin()

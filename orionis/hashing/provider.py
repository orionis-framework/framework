# ruff: noqa: PLC0415
# Resolve the manager implementation when its service is registered.
"""Service provider for the Orionis hashing system."""

from orionis.container.providers.service_provider import ServiceProvider
from orionis.hashing.contracts.hash_manager import IHashManager
from orionis.support.facades.hash import Hash as HashFacade


class HashProvider(ServiceProvider):
    """
    Service provider for the Orionis hashing system.

    Binds :class:`orionis.hashing.contracts.IHashManager` to
    :class:`orionis.hashing.HashManager` as a singleton and
    pins the :class:`orionis.support.facades.Hash` facade so every ``Hash`` call
    resolves without
    container overhead, including the members that stay synchronous.
    """

    def register(self) -> None:
        """
        Bind IHashManager to HashManager as a singleton.

        Returns
        -------
        None
            No return value.
        """
        from orionis.hashing import HashManager

        self.app.singleton(IHashManager, HashManager)

    async def boot(self) -> None:
        """
        Pin the Hash facade after all services are registered.

        Returns
        -------
        None
            This method does not return a value.
        """
        await HashFacade.pin()

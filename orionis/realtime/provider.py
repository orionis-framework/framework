from orionis.container.providers.service_provider import ServiceProvider
from typing import cast
from orionis.foundation.config.realtime.entities.realtime import RealtimeConfig
from orionis.realtime.contracts.manager import IConnectionManager
from orionis.realtime.manager import ConnectionManager
from orionis.support.facades.realtime import Realtime

class RealtimeProvider(ServiceProvider):
    """Register one worker-local registry and pin the synchronous target facade."""

    __slots__ = ()

    def register(self) -> None:
        """
        Bind validated configuration and the replaceable connection manager.

        Returns
        -------
        None
            Register services without creating any network connections.

        Raises
        ------
        TypeError
            If the configuration mapping or any option has an invalid type.
        ValueError
            If configured limits are outside their accepted ranges.
        """
        configured = self.app.config("realtime") or {}
        config = (
            configured if isinstance(configured, RealtimeConfig)
            else RealtimeConfig(**cast("dict", configured))
        )
        self.app.instance(RealtimeConfig, config)
        self.app.singleton(IConnectionManager, ConnectionManager)

    async def boot(self) -> None:
        """
        Make ``Realtime.hub(...)`` available through the ordinary facade.

        Returns
        -------
        None
            Pin the container-managed singleton once providers are ready.
        """
        await Realtime.pin()

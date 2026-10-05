from runpy import run_path
from typing import cast
from orionis.container.providers.service_provider import ServiceProvider
from orionis.foundation.enums.lifespan import Lifespan
from orionis.mcp.config import McpConfig
from orionis.mcp.contracts.event_bus import IMcpEventBus
from orionis.mcp.contracts.manager import IMcpManager
from orionis.mcp.manager import McpManager
from orionis.mcp.subscriptions.event_bus import InMemoryMcpEventBus
from orionis.support.facades.mcp import Mcp
from orionis.support.facades.router import Route

class McpProvider(ServiceProvider):
    """Register one manager and load declarations before either runtime starts."""

    __slots__ = ("_routes_loaded",)

    def register(self) -> None:
        """
        Bind validated configuration and bounded services without performing I/O.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        configured = self.app.config("mcp") or {}
        config = (
            configured if isinstance(configured, McpConfig)
            else McpConfig(**cast("dict", configured))
        )
        self.app.instance(McpConfig, config)
        self.app.instance(
            IMcpEventBus,
            InMemoryMcpEventBus(
                buffer_size=config.subscription_buffer_size,
                max_listeners=config.max_subscriptions,
            ),
        )
        self.app.singleton(IMcpManager, McpManager)
        self._routes_loaded = False

    async def boot(self) -> None:
        """
        Load AI registrations for HTTP and CLI, including warm HTTP route caches.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        await Route.pin()
        await Mcp.pin()
        if not self._routes_loaded:
            root = self.app.basePath
            for route_file in self.app.routingPaths("ai") or ():
                module = ".".join(route_file.relative_to(root).with_suffix("").parts)
                # Declarations belong to this app even when a previous app loaded
                # the same module or the HTTP route loader restores a cache hit.
                run_path(str(route_file), run_name=module)
            self._routes_loaded = True
        manager = await self.app.make(IMcpManager)
        manager.finalizeRoutes()
        self.app.on(Lifespan.SHUTDOWN, manager.shutdown)

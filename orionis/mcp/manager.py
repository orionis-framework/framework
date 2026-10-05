from __future__ import annotations
import re
from typing import TYPE_CHECKING
from orionis.foundation.contracts.application import IApplication  # noqa: TC001 - Constructor DI.
from orionis.http.routes.contracts.router import IRouter  # noqa: TC001 - Constructor DI.
from orionis.http.routes.functions import normalize_path, normalize_request_path
from orionis.mcp.config import McpConfig  # noqa: TC001 - Constructor DI.
from orionis.mcp.contracts.event_bus import IMcpEventBus  # noqa: TC001 - Constructor DI.
from orionis.mcp.contracts.manager import IMcpManager
from orionis.mcp.routing import McpController
from orionis.mcp.server.compiler import CompiledMcpServer, compile_server
from orionis.mcp.server.primitives import Server
from orionis.mcp.transport.http import McpHttpTransport
from orionis.mcp.transport.stdio import McpStdioTransport

if TYPE_CHECKING:
    from orionis.http.request import Request
    from orionis.http.responses import Response
    from orionis.http.routes.fluent import FluentRoute

_LOCAL_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")

class McpManager(IMcpManager):
    """Own one compiled registry shared by native HTTP, STDIO, DI and the facade."""

    __slots__ = ("_app", "_bus", "_compiled", "_config", "_local", "_router", "_web")

    def __init__(
        self,
        app: IApplication,
        router: IRouter,
        config: McpConfig,
        bus: IMcpEventBus,
    ) -> None:
        """
        Capture application services without opening transports or performing I/O.

        Parameters
        ----------
        app : IApplication
            Application container supplying configuration and dependencies.
        router : IRouter
            Value supplied for ``router``.
        config : McpConfig
            Validated configuration controlling this component.
        bus : IMcpEventBus
            Value supplied for ``bus``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        self._app = app
        self._router = router
        self._config = config
        self._bus = bus
        self._compiled: dict[type[Server], CompiledMcpServer] = {}
        self._web: dict[
            str, tuple[FluentRoute, CompiledMcpServer, McpHttpTransport],
        ] = {}
        self._local: dict[str, CompiledMcpServer] = {}

    def _compile(self, server: type[Server]) -> CompiledMcpServer:
        """
        Validate and compile a server exactly once per application manager.

        Parameters
        ----------
        server : type[Server]
            Value supplied for ``server``.

        Returns
        -------
        CompiledMcpServer
            Result of the operation described above.
        """
        if not isinstance(server, type) or not issubclass(server, Server):
            message = "MCP server registration requires a Server subclass"
            raise TypeError(message)
        if server not in self._compiled:
            self._compiled[server] = compile_server(server)
        return self._compiled[server]

    def web(self, path: str, server: type[Server]) -> FluentRoute:
        """
        Register one native POST endpoint with API authentication semantics.

        Parameters
        ----------
        path : str
            Value supplied for ``path``.
        server : type[Server]
            Value supplied for ``server``.

        Returns
        -------
        FluentRoute
            Result of the operation described above.
        """
        if not isinstance(path, str):
            message = "MCP endpoint paths must be strings"
            raise TypeError(message)
        if not path.strip() or any(character in path for character in "{}?#"):
            message = "MCP endpoint paths must be fixed paths without URI parameters"
            raise ValueError(message)
        path = normalize_path(path)
        self.finalizeRoutes()
        if path in self._web:
            message = f"An MCP HTTP server is already registered at {path!r}"
            raise ValueError(message)
        compiled = self._compile(server)
        route = self._router.post(path, [McpController, "handle"])
        route._kind("api")  # noqa: SLF001 - Native router's registration boundary.
        transport = McpHttpTransport(self._app, compiled, self._config, self._bus)
        self._web[path] = (route, compiled, transport)
        return route

    def local(self, name: str, server: type[Server]) -> None:
        """
        Register an explicit handle without accepting dynamic module imports.

        Parameters
        ----------
        name : str
            Value supplied for ``name``.
        server : type[Server]
            Value supplied for ``server``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        if not isinstance(name, str):
            message = "MCP local handles must be strings"
            raise TypeError(message)
        if _LOCAL_NAME.fullmatch(name) is None:
            message = (
                "MCP local handles must use letters, digits, dots, "
                "underscores or hyphens"
            )
            raise ValueError(message)
        if name in self._local:
            message = f"An MCP local server is already registered as {name!r}"
            raise ValueError(message)
        self._local[name] = self._compile(server)

    def getWebServer(self, path: str) -> CompiledMcpServer:
        """
        Return compiled HTTP metadata by normalized native route path.

        Parameters
        ----------
        path : str
            Value supplied for ``path``.

        Returns
        -------
        CompiledMcpServer
            Compiled HTTP metadata by normalized native route path.
        """
        self.finalizeRoutes()
        return self._web[normalize_request_path(path)][1]

    def finalizeRoutes(self) -> None:
        """
        Index final fluent paths once at boot, preserving constant-time dispatch.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        indexed = {}
        for route, compiled, transport in self._web.values():
            path = normalize_request_path(route.path)
            if any(character in path for character in "{}?#"):
                message = "MCP endpoint prefixes must retain a fixed HTTP path"
                raise ValueError(message)
            if path in indexed:
                message = f"An MCP HTTP server is already registered at {path!r}"
                raise ValueError(message)
            indexed[path] = (route, compiled, transport)
        self._web = indexed

    def getLocalServer(self, name: str) -> CompiledMcpServer:
        """
        Return compiled local metadata by its configured handle.

        Parameters
        ----------
        name : str
            Value supplied for ``name``.

        Returns
        -------
        CompiledMcpServer
            Compiled local metadata by its configured handle.
        """
        return self._local[name]

    def servers(self) -> tuple[tuple[str, str, type[Server]], ...]:
        """
        Return an immutable transport/address/declaration inventory.

        Returns
        -------
        tuple[tuple[str, str, type[Server]], ...]
            An immutable transport/address/declaration inventory.
        """
        self.finalizeRoutes()
        return tuple(
            ("http", path, compiled.definition)
            for path, (_, compiled, _) in self._web.items()
        ) + tuple(
            ("stdio", name, compiled.definition)
            for name, compiled in self._local.items()
        )

    async def dispatchHttp(self, request: Request) -> Response:
        """
        Use the same server and invoker reached by its local registration.

        Parameters
        ----------
        request : Request
            Current request and its trusted execution context.

        Returns
        -------
        Response
            Result of the operation described above.
        """
        transport = self._web[normalize_request_path(request.path)][2]
        return await transport.handle(request)

    async def startLocal(self, name: str) -> None:
        """
        Serve only a configured local handle using native standard streams.

        Parameters
        ----------
        name : str
            Value supplied for ``name``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        compiled = self.getLocalServer(name)
        transport = McpStdioTransport(self._app, compiled, self._config, self._bus)
        await transport.runStandardStreams()

    async def toolsChanged(self, server: type[Server]) -> None:
        """
        Publish a catalog change without retaining the current identity.

        Parameters
        ----------
        server : type[Server]
            Value supplied for ``server``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        await self._publish(server, "notifications/tools/list_changed")

    async def promptsChanged(self, server: type[Server]) -> None:
        """
        Publish a prompt catalog change to the matching server's listeners.

        Parameters
        ----------
        server : type[Server]
            Value supplied for ``server``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        await self._publish(server, "notifications/prompts/list_changed")

    async def resourcesChanged(self, server: type[Server]) -> None:
        """
        Publish a resource catalog change to the matching server's listeners.

        Parameters
        ----------
        server : type[Server]
            Value supplied for ``server``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        await self._publish(server, "notifications/resources/list_changed")

    async def resourceUpdated(self, server: type[Server], uri: str) -> None:
        """
        Publish one changed URI without resolving its content or identity.

        Parameters
        ----------
        server : type[Server]
            Value supplied for ``server``.
        uri : str
            Value supplied for ``uri``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        if not isinstance(uri, str) or not uri:
            message = "A changed resource must have a nonempty URI"
            raise ValueError(message)
        await self._publish(server, "notifications/resources/updated", uri)

    async def _publish(
        self, server: type[Server], method: str, uri: str | None = None,
    ) -> None:
        """
        Scope events to a declaration already registered in this application.

        Parameters
        ----------
        server : type[Server]
            Value supplied for ``server``.
        method : str
            Value supplied for ``method``.
        uri : str | None
            Value supplied for ``uri``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        if server not in self._compiled:
            message = "MCP change notifications require a registered server"
            raise ValueError(message)
        await self._bus.publish(server, method, uri)

    async def shutdown(self) -> None:
        """
        Wake subscriptions so their request owners can complete and clean up.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        await self._bus.shutdown()

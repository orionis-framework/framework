# ruff: noqa: PYI021
# Keep public facade methods documented alongside their static signatures.
import orionis.http as http_module
from orionis.container.facades.facade import Facade
from orionis.http.routes.fluent import FluentRoute
from orionis.mcp.contracts.manager import IMcpManager
from orionis.mcp.server.compiler import CompiledMcpServer
from orionis.mcp.server.primitives import Server

class Mcp(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> type[IMcpManager]:
        """Return the contract registered for this facade in the container."""

    @classmethod
    async def resolve(cls, *args: object, **kwargs: object) -> IMcpManager:
        """Resolve the MCP manager from the application container."""

    @classmethod
    def web(cls, path: str, server: type[Server]) -> FluentRoute:
        """Register one native POST endpoint with API authentication semantics."""

    @classmethod
    def local(cls, name: str, server: type[Server]) -> None:
        """Register an explicit handle without accepting dynamic module imports."""

    @classmethod
    def finalizeRoutes(cls) -> None:
        """Index the final paths of registered HTTP routes."""

    @classmethod
    def getWebServer(cls, path: str) -> CompiledMcpServer:
        """Find the compiled server assigned to an HTTP route."""

    @classmethod
    def getLocalServer(cls, name: str) -> CompiledMcpServer:
        """Find the compiled server assigned to a local handle."""

    @classmethod
    def servers(cls) -> tuple[tuple[str, str, type[Server]], ...]:
        """Return the transport, address, and server class for each registration."""

    @classmethod
    async def dispatchHttp(cls, request: http_module.Request) -> http_module.Response:
        """Dispatch a native request to its registered MCP server."""

    @classmethod
    async def startLocal(cls, name: str) -> None:
        """Serve a registered local server until EOF or cancellation."""

    @classmethod
    async def toolsChanged(cls, server: type[Server]) -> None:
        """Publish a catalog change without retaining the current identity."""

    @classmethod
    async def promptsChanged(cls, server: type[Server]) -> None:
        """Publish a prompt catalog change to the matching server's listeners."""

    @classmethod
    async def resourcesChanged(cls, server: type[Server]) -> None:
        """Publish a resource catalog change to the matching server's listeners."""

    @classmethod
    async def resourceUpdated(cls, server: type[Server], uri: str) -> None:
        """Publish one changed URI without resolving its content or identity."""

    @classmethod
    async def shutdown(cls) -> None:
        """Wake event subscribers so their requests can finish."""

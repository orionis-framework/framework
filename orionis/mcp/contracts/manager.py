from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.http.request import Request
    from orionis.http.responses import Response
    from orionis.http.routes.fluent import FluentRoute
    from orionis.mcp.server.compiler import CompiledMcpServer
    from orionis.mcp.server.primitives import Server


class IMcpManager(ABC):
    """Share compiled servers, native routes, local transports, and change events."""

    __slots__ = ()

    @abstractmethod
    def web(self, path: str, server: type[Server]) -> FluentRoute:
        """Register a server on one native HTTP POST route."""

    @abstractmethod
    def local(self, name: str, server: type[Server]) -> None:
        """Register a server for an explicit local CLI handle."""

    @abstractmethod
    def finalizeRoutes(self) -> None:
        """Index final native route paths after fluent prefixes and groups."""

    @abstractmethod
    def getWebServer(self, path: str) -> CompiledMcpServer:
        """Find the compiled server assigned to an HTTP path."""

    @abstractmethod
    def getLocalServer(self, name: str) -> CompiledMcpServer:
        """Find the compiled server assigned to a local handle."""

    @abstractmethod
    def servers(self) -> tuple[tuple[str, str, type[Server]], ...]:
        """Describe registered transports without exposing mutable registries."""

    @abstractmethod
    async def dispatchHttp(self, request: Request) -> Response:
        """Handle a request through the shared compiled server's HTTP transport."""

    @abstractmethod
    async def startLocal(self, name: str) -> None:
        """Serve one registered local server until EOF or cancellation."""

    @abstractmethod
    async def toolsChanged(self, server: type[Server]) -> None:
        """Publish that an authorized tool catalog may have changed."""

    @abstractmethod
    async def promptsChanged(self, server: type[Server]) -> None:
        """Publish that an authorized prompt catalog may have changed."""

    @abstractmethod
    async def resourcesChanged(self, server: type[Server]) -> None:
        """Publish that an authorized resource catalog may have changed."""

    @abstractmethod
    async def resourceUpdated(self, server: type[Server], uri: str) -> None:
        """Publish a resource change to listeners that requested that URI."""

    @abstractmethod
    async def shutdown(self) -> None:
        """Wake active subscription streams for graceful completion."""

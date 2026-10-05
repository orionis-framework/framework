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
        """
        Register a server on one native HTTP POST route.

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

    @abstractmethod
    def local(self, name: str, server: type[Server]) -> None:
        """
        Register a server for an explicit local CLI handle.

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

    @abstractmethod
    def finalizeRoutes(self) -> None:
        """
        Index final native route paths after fluent prefixes and groups.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """

    @abstractmethod
    def getWebServer(self, path: str) -> CompiledMcpServer:
        """
        Find the compiled server assigned to an HTTP path.

        Parameters
        ----------
        path : str
            Value supplied for ``path``.

        Returns
        -------
        CompiledMcpServer
            Result of the operation described above.
        """

    @abstractmethod
    def getLocalServer(self, name: str) -> CompiledMcpServer:
        """
        Find the compiled server assigned to a local handle.

        Parameters
        ----------
        name : str
            Value supplied for ``name``.

        Returns
        -------
        CompiledMcpServer
            Result of the operation described above.
        """

    @abstractmethod
    def servers(self) -> tuple[tuple[str, str, type[Server]], ...]:
        """
        Describe registered transports without exposing mutable registries.

        Returns
        -------
        tuple[tuple[str, str, type[Server]], ...]
            Result of the operation described above.
        """

    @abstractmethod
    async def dispatchHttp(self, request: Request) -> Response:
        """
        Handle a request through the shared compiled server's HTTP transport.

        Parameters
        ----------
        request : Request
            Current request and its trusted execution context.

        Returns
        -------
        Response
            Result of the operation described above.
        """

    @abstractmethod
    async def startLocal(self, name: str) -> None:
        """
        Serve one registered local server until EOF or cancellation.

        Parameters
        ----------
        name : str
            Value supplied for ``name``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """

    @abstractmethod
    async def toolsChanged(self, server: type[Server]) -> None:
        """
        Publish that an authorized tool catalog may have changed.

        Parameters
        ----------
        server : type[Server]
            Value supplied for ``server``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """

    @abstractmethod
    async def promptsChanged(self, server: type[Server]) -> None:
        """
        Publish that an authorized prompt catalog may have changed.

        Parameters
        ----------
        server : type[Server]
            Value supplied for ``server``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """

    @abstractmethod
    async def resourcesChanged(self, server: type[Server]) -> None:
        """
        Publish that an authorized resource catalog may have changed.

        Parameters
        ----------
        server : type[Server]
            Value supplied for ``server``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """

    @abstractmethod
    async def resourceUpdated(self, server: type[Server], uri: str) -> None:
        """
        Publish a resource change to listeners that requested that URI.

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

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Wake active subscription streams for graceful completion.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """

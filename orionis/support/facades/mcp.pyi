# ruff: noqa: PYI021
# Keep public facade methods documented alongside their static signatures.
from orionis.container.contracts.facade import IFacade
from orionis.http.routes.fluent import FluentRoute
from orionis.mcp.contracts.manager import IMcpManager
from orionis.mcp.server.primitives import Server

class Mcp(IFacade):
    @classmethod
    def getFacadeAccessor(cls) -> type[IMcpManager]:
        """Return the contract registered for this facade in the container."""
    @staticmethod
    def web(path: str, server: type[Server]) -> FluentRoute:
        """Register one native POST endpoint with API authentication semantics."""
    @staticmethod
    def local(name: str, server: type[Server]) -> None:
        """Register an explicit handle without accepting dynamic module imports."""
    @staticmethod
    async def toolsChanged(server: type[Server]) -> None:
        """Publish a catalog change without retaining the current identity."""
    @staticmethod
    async def promptsChanged(server: type[Server]) -> None:
        """Publish a prompt catalog change to the matching server's listeners."""
    @staticmethod
    async def resourcesChanged(server: type[Server]) -> None:
        """Publish a resource catalog change to the matching server's listeners."""
    @staticmethod
    async def resourceUpdated(server: type[Server], uri: str) -> None:
        """Publish one changed URI without resolving its content or identity."""

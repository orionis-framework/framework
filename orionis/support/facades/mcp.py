from orionis.container.facades.facade import Facade
from orionis.mcp.contracts.manager import IMcpManager


class Mcp(Facade):
    """Expose the same MCP manager that application services receive through DI."""

    __slots__ = ()

    @classmethod
    def getFacadeAccessor(cls) -> type[IMcpManager]:
        """Resolve the application-owned MCP manager singleton."""
        return IMcpManager

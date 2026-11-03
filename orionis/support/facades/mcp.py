"""Expose the same MCP manager that application services receive through DI."""

from orionis.container.facades.facade import Facade
from orionis.mcp.contracts.manager import IMcpManager

class Mcp(Facade):
    """Expose the same MCP manager that application services receive through DI."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @classmethod
    def getFacadeAccessor(cls) -> type[IMcpManager]:
        """
        Resolve the application-owned MCP manager singleton.

        Returns
        -------
        type[orionis.mcp.contracts.manager.IMcpManager]
            Result of the operation described above.
        """
        return IMcpManager

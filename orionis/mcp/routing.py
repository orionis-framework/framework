"""An importable native HTTP handler, including after route-cache restore."""

from typing import ClassVar
from orionis.http.request import Request  # noqa: TC001 - Native controller DI.
from orionis.http.responses import Response  # noqa: TC001 - Handler metadata.
from orionis.mcp.contracts.manager import IMcpManager  # noqa: TC001 - Native controller DI.
from orionis.mcp.transport.policy import McpHttpPolicy

class McpController:
    """An importable native HTTP handler, including after route-cache restore."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""
    http_protocol_policy: ClassVar[type[McpHttpPolicy]] = McpHttpPolicy

    async def handle(self, request: Request, manager: IMcpManager) -> Response:
        """
        Delegate the complete MCP envelope to the registered transport.

        Parameters
        ----------
        request : orionis.http.Request
            Current request and its trusted execution context.
        manager : orionis.mcp.contracts.manager.IMcpManager
            Value supplied for ``manager``.

        Returns
        -------
        orionis.http.Response
            Result of the operation described above.
        """
        return await manager.dispatchHttp(request)

from typing import ClassVar
from orionis.http.request import Request  # noqa: TC001 - Native controller DI.
from orionis.http.responses import Response  # noqa: TC001 - Handler metadata.
from orionis.mcp.contracts.manager import IMcpManager  # noqa: TC001 - Native controller DI.
from orionis.mcp.transport.policy import McpHttpPolicy


class McpController:
    """An importable native HTTP handler, including after route-cache restore."""

    __slots__ = ()
    http_protocol_policy: ClassVar[type[McpHttpPolicy]] = McpHttpPolicy

    async def handle(self, request: Request, manager: IMcpManager) -> Response:
        """Delegate the complete MCP envelope to the registered transport."""
        return await manager.dispatchHttp(request)

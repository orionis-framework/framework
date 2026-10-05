from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
import msgspec
from orionis.mcp.config import McpConfig
from orionis.mcp.dispatcher import McpDispatcher
from orionis.mcp.protocol.constants import (
    CLIENT_CAPABILITIES,
    MCP_PROTOCOL_VERSION,
    PROTOCOL_VERSION,
)
from orionis.mcp.server.compiler import CompiledMcpServer, compile_server
from orionis.mcp.subscriptions.event_bus import InMemoryMcpEventBus

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from orionis.container.contracts.container import IContainer
    from orionis.mcp.server.primitives import Server

@dataclass(frozen=True, slots=True)
class McpTestResponse:
    """Decoded result and notifications from a complete wire round trip."""

    message: dict[str, Any]
    notifications: tuple[dict[str, object], ...] = ()

    def assertOk(self) -> None:
        """
        Require a successful protocol and tool result.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        if "error" in self.message or self.message.get("result", {}).get(
            "isError",
            False,
        ):
            error = "Expected a successful MCP result"
            raise AssertionError(error)

    def assertTextContains(self, text: str) -> None:
        """
        Check returned tool text without bypassing response serialization.

        Parameters
        ----------
        text : str
            Value supplied for ``text``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        values = self.message.get("result", {}).get("content", ())
        if not any(text in value.get("text", "") for value in values):
            error = f"Expected MCP text to contain {text!r}"
            raise AssertionError(error)

class McpTestClient:
    """Open scopes on the supplied container; never create a parallel application."""

    __slots__ = ("app", "dispatcher")

    def __init__(
        self,
        app: IContainer,
        server: type[Server] | CompiledMcpServer,
        config: McpConfig | None = None,
    ) -> None:
        """
        Reuse native service bindings and one compiled server.

        Parameters
        ----------
        app : IContainer
            Application container supplying configuration and dependencies.
        server : type[Server] | CompiledMcpServer
            Value supplied for ``server``.
        config : McpConfig | None
            Validated configuration controlling this component.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        self.app = app
        compiled = (
            server if isinstance(server, CompiledMcpServer) else compile_server(server)
        )
        config = config or McpConfig()
        self.dispatcher = McpDispatcher(
            app,
            compiled,
            config,
            InMemoryMcpEventBus(
                config.subscription_buffer_size, config.max_subscriptions,
            ),
        )

    async def stream(
        self,
        method: str,
        params: dict[str, object] | None = None,
        *,
        meta: dict[str, object] | None = None,
        request_id: str | int = 1,
    ) -> AsyncIterator[dict[str, object]]:
        """
        Keep the existing application's scope alive through the entire stream.

        Parameters
        ----------
        method : str
            Value supplied for ``method``.
        params : dict[str, object] | None
            Parameters decoded for the requested operation.
        meta : dict[str, object] | None
            Value supplied for ``meta``.
        request_id : str | int
            Value supplied for ``request_id``.

        Yields
        ------
        dict[str, object]
            Each item produced by the documented iteration.
        """
        metadata = {
            PROTOCOL_VERSION: MCP_PROTOCOL_VERSION,
            CLIENT_CAPABILITIES: {},
            **(meta or {}),
        }
        data = msgspec.json.encode(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": {**(params or {}), "_meta": metadata},
            },
        )
        async with self.app.beginScope():
            result = await self.dispatcher.handle(data)
            if isinstance(result.body, bytes):
                if result.body:
                    yield msgspec.json.decode(result.body)
                return
            try:
                async for message in result.body:
                    if message:
                        yield msgspec.json.decode(message)
            finally:
                close = getattr(result.body, "aclose", None)
                if close is not None:
                    await close()

    async def request(
        self,
        method: str,
        params: dict[str, object] | None = None,
        *,
        meta: dict[str, object] | None = None,
        request_id: str | int = 1,
    ) -> McpTestResponse:
        """
        Collect a finite exchange; use stream() for subscriptions.

        Parameters
        ----------
        method : str
            Value supplied for ``method``.
        params : dict[str, object] | None
            Parameters decoded for the requested operation.
        meta : dict[str, object] | None
            Value supplied for ``meta``.
        request_id : str | int
            Value supplied for ``request_id``.

        Returns
        -------
        McpTestResponse
            Result of the operation described above.
        """
        notifications = []
        final = {}
        async for message in self.stream(
            method,
            params,
            meta=meta,
            request_id=request_id,
        ):
            if "method" in message:
                notifications.append(message)
            else:
                final = message
        return McpTestResponse(final, tuple(notifications))

    async def tool(
        self,
        name: str,
        arguments: dict[str, object] | None = None,
    ) -> McpTestResponse:
        """
        Invoke a tool through JSON-RPC input and output bytes.

        Parameters
        ----------
        name : str
            Value supplied for ``name``.
        arguments : dict[str, object] | None
            Arguments supplied for this operation.

        Returns
        -------
        McpTestResponse
            Result of the operation described above.
        """
        return await self.request(
            "tools/call",
            {"name": name, "arguments": arguments or {}},
        )

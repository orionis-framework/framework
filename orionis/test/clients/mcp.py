"""Exercise MCP requests through the native dispatcher and JSON serialization."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, NotRequired, TypedDict
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


class RpcError(TypedDict):
    """Wire error with an optional data payload."""

    code: int
    """Numeric JSON-RPC error code."""
    message: str
    """Human-readable explanation of the error."""
    data: NotRequired[object]
    """Additional details supplied by the server for this error."""


class RpcSuccess(TypedDict):
    """Successful JSON-RPC response."""

    jsonrpc: Literal["2.0"]
    """JSON-RPC wire protocol version."""
    id: str | int
    """Identifier of the request that produced the result."""
    result: object
    """Decoded return value of the requested method."""


class RpcFailure(TypedDict):
    """JSON-RPC error response, optionally identifying its request."""

    jsonrpc: Literal["2.0"]
    """JSON-RPC wire protocol version."""
    id: NotRequired[str | int]
    """Identifier of the failed request when available."""
    error: RpcError
    """Protocol error reported by the server."""


class RpcNotification(TypedDict):
    """Out-of-band message emitted before the final response."""

    jsonrpc: Literal["2.0"]
    """JSON-RPC wire protocol version."""
    method: str
    """Name of the notification emitted by the server."""
    params: dict[str, object]
    """Arguments carried by this notification."""


class EmptyResponse(TypedDict):
    """No final response arrived on the stream."""


@dataclass(frozen=True, slots=True)
class McpTestResponse:
    """Decoded result and notifications from a complete wire round trip."""

    message: RpcSuccess | RpcFailure | EmptyResponse
    """Final decoded JSON-RPC response, or an empty mapping when none arrived."""
    notifications: tuple[RpcNotification, ...] = ()
    """Decoded notifications received before the final response."""

    def assertOk(self) -> None:
        """
        Require a successful protocol and tool result.

        Returns
        -------
        None
            No return value when the response succeeds.

        Raises
        ------
        AssertionError
            If the result is absent, malformed, or reports a protocol or tool error.
        """
        result = self.message.get("result")
        if (
            "error" in self.message
            or not isinstance(result, dict)
            or result.get("isError", False)
        ):
            error = "Expected a successful MCP result"
            raise AssertionError(error)

    def assertTextContains(self, text: str) -> None:
        """
        Check returned tool text without bypassing response serialization.

        Parameters
        ----------
        text : str
            Substring required in at least one text content block.

        Returns
        -------
        None
            No return value when a matching text block exists.

        Raises
        ------
        AssertionError
            If no valid text block contains the requested substring.
        """
        result = self.message.get("result")
        values = result.get("content", ()) if isinstance(result, dict) else ()
        if not isinstance(values, (list, tuple)) or not any(
            isinstance(value, dict)
            and value.get("type") == "text"
            and isinstance(value.get("text"), str)
            and text in value["text"]
            for value in values
        ):
            error = f"Expected MCP text to contain {text!r}"
            raise AssertionError(error)


class McpTestClient:
    """Open scopes on the supplied container; never create a parallel application."""

    __slots__ = ("app", "dispatcher")
    """Declare the instance attribute slots reserved by this class."""

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
        app : orionis.container.contracts.container.IContainer
            Application container supplying configuration and dependencies.
        server : type[orionis.mcp.server.primitives.Server] | CompiledMcpServer
            Server declaration to compile, or an existing compiled server.
        config : orionis.mcp.config.McpConfig | None, optional
            Protocol limits; use the default configuration when omitted.

        Returns
        -------
        None
            No return value.
        """
        self.app = app
        """Application container supplying configuration and dependencies."""
        compiled = (
            server if isinstance(server, CompiledMcpServer) else compile_server(server)
        )
        config = config or McpConfig()
        self.dispatcher = McpDispatcher(
            app,
            compiled,
            config,
            InMemoryMcpEventBus(
                config.subscription_buffer_size,
                config.max_subscriptions,
            ),
        )
        """Dispatcher sharing this client's configuration and event bus."""

    async def stream(
        self,
        method: str,
        params: dict[str, object] | None = None,
        *,
        meta: dict[str, object] | None = None,
        request_id: str | int = 1,
    ) -> AsyncIterator[RpcSuccess | RpcFailure | RpcNotification]:
        """
        Keep the existing application's scope alive through the entire stream.

        Parameters
        ----------
        method : str
            JSON-RPC method to invoke.
        params : dict[str, object] | None, optional
            Method parameters, defaulting to an empty mapping.
        meta : dict[str, object] | None, optional
            Request metadata overriding the default version and capabilities.
        request_id : str | int, optional
            Correlation identifier, defaulting to 1.

        Yields
        ------
        dict[str, object]
            Each decoded notification or final response in wire order.
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
            JSON-RPC method to invoke.
        params : dict[str, object] | None, optional
            Method parameters, defaulting to an empty mapping.
        meta : dict[str, object] | None, optional
            Request metadata overriding the default version and capabilities.
        request_id : str | int, optional
            Correlation identifier, defaulting to 1.

        Returns
        -------
        orionis.test.McpTestResponse
            Final response and preceding notifications in wire order.
        """
        notifications: list[RpcNotification] = []
        final: RpcSuccess | RpcFailure | EmptyResponse = {}
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
            Registered tool name.
        arguments : dict[str, object] | None, optional
            Tool input fields, defaulting to an empty mapping.

        Returns
        -------
        orionis.test.McpTestResponse
            Serialized tool result and preceding notifications.
        """
        return await self.request(
            "tools/call",
            {"name": name, "arguments": arguments or {}},
        )

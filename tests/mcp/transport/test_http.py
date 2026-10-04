"""Exercise MCP HTTP admission and native response ownership without a server socket."""

import asyncio
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Self
import unittest

import msgspec

from orionis.http.adapters.request.asgi import ASGITransportAdapter
from orionis.http.adapters.response.asgi import ASGIResponseAdapter
from orionis.http.enums.interfaces import Interface
from orionis.http.request import Request
from orionis.http.responses import EventStreamResponse
from orionis.mcp.config import McpConfig
from orionis.mcp.dispatcher import DispatchResult
from orionis.mcp.protocol.codecs import decode_params
from orionis.mcp.protocol.constants import CLIENT_CAPABILITIES, PROTOCOL_VERSION
from orionis.mcp.transport import http as module
from orionis.mcp.transport.headers import compile_header_bindings
from orionis.mcp.transport.http import McpHttpTransport


class _Input:
    """Expose native ASGI body consumption and an independently signaled disconnect."""

    __slots__ = ("body", "disconnect", "reads")

    def __init__(self, body) -> None:
        self.body = body
        self.reads = 0
        self.disconnect = asyncio.Event()

    async def __call__(self) -> dict[str, object]:
        self.reads += 1
        if self.reads == 1:
            return {"type": "http.request", "body": self.body, "more_body": False}
        await self.disconnect.wait()
        return {"type": "http.disconnect"}


class _Messages:
    """Own an iterator whose close is observable even without iteration."""

    __slots__ = ("closed", "messages", "waiting")

    def __init__(self, messages=()) -> None:
        self.messages = iter(messages)
        self.closed = 0
        self.waiting = asyncio.Event()

    def __aiter__(self) -> Self:
        return self

    async def __anext__(self) -> bytes:
        item = next(self.messages, None)
        if item is None:
            raise StopAsyncIteration
        if item == b"wait":
            self.waiting.set()
            await asyncio.Event().wait()
        return item

    async def aclose(self):
        self.closed += 1


@dataclass(slots=True)
class _State:
    """Drive deterministic dispatch results while preserving real transport objects."""

    result: DispatchResult = field(
        default_factory=lambda: DispatchResult(b'{"ok":true}'),
    )
    calls: int = 0


class _Dispatcher:
    """Record only dispatch, leaving envelope and header validation real."""

    __slots__ = ("state",)

    def __init__(self, app, _compiled, _config, _bus) -> None:
        self.state = app

    def decode(self, request):
        """Use real protocol decoders before the deterministic dispatch boundary."""
        return decode_params(request)

    async def dispatch(self, _request, _params, **_options: object):
        self.state.calls += 1
        return self.state.result


class TestHttpTransport(unittest.IsolatedAsyncioTestCase):
    """Check failure statuses, no-body rejection and SSE cleanup/backpressure."""

    def setUp(self):
        """Install the explicit dispatch double and transport state."""
        self.original = module.McpDispatcher
        module.McpDispatcher = _Dispatcher
        self.state = _State()
        self.compiled = SimpleNamespace(tools={}, catalog_tools={})

    def tearDown(self):
        """Restore the shared production dispatcher."""
        module.McpDispatcher = self.original

    def request(
        self,
        *,
        method="POST",
        rpc="server/discover",
        extra=(),
        body=None,
        headers=None,
    ):
        """Build a real Request with a bounded native ASGI body reader."""
        if body is None:
            body = msgspec.json.encode(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": rpc,
                    "params": {
                        "_meta": {
                            PROTOCOL_VERSION: "2026-07-28",
                            CLIENT_CAPABILITIES: {},
                        },
                    },
                },
            )
        incoming = _Input(body)
        fields = {
            b"accept": b"application/json, text/event-stream",
            b"content-type": b"application/json",
            b"mcp-method": rpc.encode(),
            b"mcp-protocol-version": b"2026-07-28",
            **(headers or {}),
        }
        adapter = ASGITransportAdapter(
            {
                "type": "http",
                "method": method,
                "path": "/mcp",
                "scheme": "http",
                "query_string": b"",
                "http_version": "1.1",
                "headers": [
                    *(
                        (key, value) for key, value in fields.items()
                        if value is not None
                    ),
                    *extra,
                ],
            },
        )
        return (
            Request(Interface.ASGI, adapter, receive_or_protocol=incoming),
            adapter,
            incoming,
        )

    def transport(self, **options: object):
        """Create a transport sharing one immutable compiled server reference."""
        return McpHttpTransport(self.state, self.compiled, McpConfig(**options), None)

    async def test_normal_json_is_preencoded_without_double_serialization(self):
        """Keep protocol bytes intact and do not retain the completed request slot."""
        transport = self.transport()
        request, _, incoming = self.request()
        response = await transport.handle(request)
        self.assertEqual(response.getBody(), b'{"ok":true}')
        self.assertEqual(response.getMediaType(), "application/json")
        self.assertEqual(
            (incoming.reads, self.state.calls, transport._active), (1, 1, 0),
        )

    async def test_origins_are_exact_allowlisted_and_checked_before_body(self):
        """Reject null, duplicate and deceptive suffix origins before I/O."""
        transport = self.transport(allowed_origins=("https://trusted.example",))
        for extra in (
            ((b"origin", b"null"),),
            ((b"origin", b"https://trusted.example.evil"),),
            (
                (b"origin", b"https://trusted.example"),
                (b"Origin", b"https://trusted.example"),
            ),
        ):
            request, _, incoming = self.request(extra=extra)
            response = await transport.handle(request)
            self.assertEqual((response.getStatusCode(), incoming.reads), (403, 0))
        request, _, _ = self.request(extra=((b"origin", b"https://trusted.example"),))
        self.assertEqual((await transport.handle(request)).getStatusCode(), 200)

    async def test_method_accept_content_type_and_body_limits(self):
        """Bound framing failures without invoking protocol handlers."""
        transport = self.transport(max_request_size=10)
        request, _, _ = self.request()
        self.assertEqual((await transport.handle(request)).getStatusCode(), 413)
        request, _, incoming = self.request(method="GET")
        response = await transport.handle(request)
        self.assertEqual(response.getStatusCode(), 405)
        self.assertEqual(response.getHeader("allow"), ["POST"])
        self.assertEqual(incoming.reads, 0)
        request, _, _ = self.request(headers={b"accept": b"application/json"})
        self.assertEqual((await transport.handle(request)).getStatusCode(), 406)
        request, _, _ = self.request(extra=((b"Content-Type", b"text/plain"),))
        self.assertEqual((await transport.handle(request)).getStatusCode(), 415)
        self.assertEqual(self.state.calls, 0)

    async def test_unknown_method_and_legacy_headers_have_distinct_statuses(self):
        """Run the header gate before method dispatch, preserving unknown-method 404."""
        transport = self.transport()
        request, _, _ = self.request(rpc="initialize")
        self.assertEqual((await transport.handle(request)).getStatusCode(), 404)
        request, _, _ = self.request(
            rpc="initialize",
            body=b'{"jsonrpc":"2.0","id":1,"method":"initialize"}',
            headers={b"mcp-protocol-version": None},
        )
        response = await transport.handle(request)
        self.assertEqual(response.getStatusCode(), 400)
        self.assertEqual(
            msgspec.json.decode(response.getBody())["error"]["code"], -32020,
        )

    async def test_native_sse_frames_heartbeat_and_closes_source(self):
        """Let the existing ASGI adapter frame, backpressure and close MCP output."""
        source = _Messages((b"", b'{"jsonrpc":"2.0","id":1,"result":{}}'))
        self.state.result = DispatchResult(source)
        transport = self.transport()
        request, adapter, incoming = self.request()
        response = await transport.handle(request)
        self.assertIsInstance(response, EventStreamResponse)
        self.assertEqual(transport._active, 1)
        sent = []

        async def send(message):
            sent.append(message)

        await ASGIResponseAdapter().send(adapter, response, incoming, send)
        bodies = [message["body"] for message in sent if "body" in message]
        self.assertEqual(bodies[0], b": keepalive\n\n")
        self.assertTrue(bodies[1].startswith(b"data: {"))
        self.assertEqual((source.closed, transport._active), (1, 0))

    async def test_unstarted_and_disconnected_sse_release_admission(self):
        """Release subscriptions and slots on unstarted or disconnected streams."""
        transport = self.transport(max_concurrent_requests=1)
        source = _Messages((b"wait",))
        self.state.result = DispatchResult(source)
        request, adapter, incoming = self.request()
        response = await transport.handle(request)
        blocked, _, _ = self.request()
        self.assertEqual((await transport.handle(blocked)).getStatusCode(), 503)
        await response.getStream().aclose()
        self.assertEqual((source.closed, transport._active), (1, 0))
        source = _Messages((b"wait",))
        self.state.result = DispatchResult(source)
        request, adapter, incoming = self.request()
        response = await transport.handle(request)

        async def send(_message):
            return None

        task = asyncio.create_task(
            ASGIResponseAdapter().send(adapter, response, incoming, send),
        )
        await asyncio.wait_for(source.waiting.wait(), 1)
        incoming.disconnect.set()
        await asyncio.wait_for(task, 1)
        self.assertEqual((source.closed, transport._active), (1, 0))

    async def test_compiled_tool_headers_gate_dispatch(self):
        """A valid envelope cannot bypass a tool's compiled mirrored arguments."""
        primitive = SimpleNamespace(
            mirrored_headers=compile_header_bindings(
                {
                    "properties": {
                        "region": {"type": "string", "x-mcp-header": "Region"},
                    },
                },
            ),
        )
        payload = msgspec.json.encode(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "_meta": {PROTOCOL_VERSION: "2026-07-28", CLIENT_CAPABILITIES: {}},
                    "name": "weather",
                    "arguments": {"region": "us-west1"},
                },
            },
        )
        for registry in (self.compiled.tools, self.compiled.catalog_tools):
            registry["weather"] = primitive
            for region in ((), ((b"mcp-param-region", b"wrong"),)):
                request, _, _ = self.request(
                    rpc="tools/call", body=payload,
                    extra=((b"mcp-name", b"weather"), *region),
                )
                response = await self.transport().handle(request)
                self.assertEqual(response.getStatusCode(), 400)
                self.assertEqual(
                    msgspec.json.decode(response.getBody())["error"]["code"], -32020,
                )
                self.assertEqual(self.state.calls, 0)
            request, _, _ = self.request(
                rpc="tools/call", body=payload,
                extra=(
                    (b"mcp-name", b"weather"), (b"mcp-param-region", b"us-west1"),
                ),
            )
            response = await self.transport().handle(request)
            self.assertEqual(response.getStatusCode(), 200)
            self.assertEqual(self.state.calls, 1)
            self.state.calls = 0
            registry.clear()

    async def test_notifications_have_no_response_body_or_dispatch(self):
        """Honor accepted notification framing without creating a request task."""
        request, _, _ = self.request(
            body=b'{"jsonrpc":"2.0","method":"notifications/custom"}',
        )
        response = await self.transport().handle(request)
        self.assertEqual((response.getStatusCode(), response.getBody()), (202, b""))
        self.assertEqual(self.state.calls, 0)

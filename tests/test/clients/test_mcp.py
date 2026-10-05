from contextlib import aclosing
from orionis.container.container import Container
from orionis.container.context.scope import ScopedContext
from orionis.mcp import McpConfig, McpRequest, McpResponse, Server, Tool
from orionis.mcp.protocol.constants import PROTOCOL_VERSION, SUBSCRIPTION_ID
from orionis.mcp.server.compiler import compile_server
from orionis.test import McpTestClient, McpTestResponse, TestCase

class _EchoTool(Tool):
    """Expose a deterministic tool through the native dispatcher."""

    name = "echo"

    def handle(self) -> McpResponse:
        """Return fixed text through the normal response serializer.

        Returns
        -------
        McpResponse
            Text content used to verify a complete wire round trip.
        """
        return McpResponse.text("native test response")

class _Server(Server):
    """Declare a tool and list-change support for native client tests."""

    name = "Native test client"
    tools = (_EchoTool,)
    list_changed = True

class TestMcpTestClient(TestCase):
    """Exercise MCP clients through the standard Orionis test case."""

    def setUp(self) -> None:
        """Create isolated native bindings for each client test.

        Returns
        -------
        None
            Register cleanup for the temporary container's singleton entry.
        """
        class _Container(Container):
            """Keep service bindings local to one client test."""

            __slots__ = ()

        self.app = _Container()
        self.addCleanup(Container._instances.pop, _Container, None)

    async def testCompiledServerAndExplicitOptionsAreReused(self) -> None:
        """Preserve explicit dependencies while exercising real tool serialization.

        Returns
        -------
        None
            Verify container, compiled server, configuration and response types.
        """
        compiled = compile_server(_Server)
        config = McpConfig(max_subscriptions=1)
        client = await self.mcp(compiled, config, app=self.app)
        self.assertIsInstance(client, McpTestClient)
        self.assertIs(client.app, self.app)
        self.assertIs(client.dispatcher.server, compiled)
        self.assertIs(client.dispatcher.config, config)
        response = await client.tool("echo")
        self.assertIsInstance(response, McpTestResponse)
        response.assertOk()
        response.assertTextContains("native test response")
        self.assertEqual(response.notifications, ())

    async def testRequestsPreserveIdsAndValidateMetadata(self) -> None:
        """Retain correlation IDs and pass metadata through the real decoder.

        Returns
        -------
        None
            Verify valid requests succeed and unsupported versions are rejected.
        """
        client = await self.mcp(_Server, app=self.app)
        response = await client.request("server/discover", request_id="exchange")
        response.assertOk()
        self.assertEqual(response.message["id"], "exchange")
        self.assertEqual(response.message["jsonrpc"], "2.0")
        rejected = await client.request(
            "server/discover",
            meta={PROTOCOL_VERSION: "unsupported"},
            request_id=0,
        )
        self.assertEqual(rejected.message["id"], 0)
        self.assertIn("error", rejected.message)

    async def testClientsIsolateSubscriptionsAndRestoreParentScope(self) -> None:
        """Keep subscriptions client-local and release their request scope.

        Returns
        -------
        None
            Verify closing a stream removes its listener and restores the scope.
        """
        first = await self.mcp(_Server, app=self.app)
        second = await self.mcp(_Server, app=self.app)
        parent_scope = ScopedContext.getCurrentScope()
        self.assertIsNot(first.dispatcher.bus, second.dispatcher.bus)
        async with aclosing(first.stream(
            "subscriptions/listen",
            {"notifications": {"toolsListChanged": True}},
            request_id="subscription",
        )) as stream:
            acknowledgement = await anext(stream)
            self.assertEqual(
                acknowledgement["params"]["_meta"][SUBSCRIPTION_ID],
                "subscription",
            )
            self.assertIsNot(ScopedContext.getCurrentScope(), parent_scope)
            request = await self.app.make(McpRequest)
            self.assertEqual(request.method, "subscriptions/listen")
            self.assertEqual(first.dispatcher.bus.listener_count, 1)
            self.assertEqual(second.dispatcher.bus.listener_count, 0)
        self.assertIs(ScopedContext.getCurrentScope(), parent_scope)
        self.assertEqual(first.dispatcher.bus.listener_count, 0)

class TestMcpTestResponse(TestCase):
    """Check assertion failures exposed by the native MCP response."""

    def testAssertOkRejectsProtocolAndToolErrors(self) -> None:
        """Fail the success assertion for either protocol or tool errors.

        Returns
        -------
        None
            Verify both error shapes raise an assertion failure.
        """
        for message in (
            {"error": {"code": -32601, "message": "Unknown method"}},
            {"result": {"isError": True}},
        ):
            response = McpTestResponse(message)
            with self.subTest(message=message), self.assertRaisesRegex(
                AssertionError, "Expected a successful MCP result",
            ):
                response.assertOk()

    def testAssertTextContainsRejectsMissingText(self) -> None:
        """Fail text assertions when content is absent or does not match.

        Returns
        -------
        None
            Verify missing and nonmatching text both produce assertion failures.
        """
        for content in ((), ({"type": "text", "text": "different"},)):
            response = McpTestResponse({"result": {"content": content}})
            with self.subTest(content=content), self.assertRaisesRegex(
                AssertionError, "Expected MCP text to contain",
            ):
                response.assertTextContains("missing")

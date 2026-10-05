import asyncio
from orionis.container.container import Container
from orionis.container.context.scope import ScopedContext
from orionis.mcp.context import McpRequest
from orionis.mcp.responses import McpResponse, Progress
from orionis.mcp.server.primitives import Resource, Server, Tool
from orionis.mcp.streams import OwnedStream
from orionis.schemas import Schema
from orionis.test import TestCase
from tests.mcp.test_streams import _Source

class _RequestSnapshot:
    """A nested native dependency resolved while authorizing a subscription URI."""

    def __init__(self, request: McpRequest) -> None:
        """Retain the exact scoped request supplied by native constructor DI.

        Parameters
        ----------
        request : McpRequest
            Value supplied for ``request``.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        self.request = request

class _AuthorizedResource(Resource):
    """Authorize only when direct and constructor-injected contexts agree."""

    name = "audited-resource"
    uri_template = "users://{identifier}/audit"

    def __init__(self, snapshot: _RequestSnapshot) -> None:
        """Resolve the dependency using the production container.

        Parameters
        ----------
        snapshot : _RequestSnapshot
            Value supplied for ``snapshot``.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        self.snapshot = snapshot

    def authorize(self, request: McpRequest) -> bool:
        """Require URI variables to be available through both native DI paths.

        Parameters
        ----------
        request : McpRequest
            Value supplied for ``request``.

        Returns
        -------
        bool
            Return the result produced by ``authorize``.
        """
        return (
            self.snapshot.request is request
            and request.uri == "users://seven/audit"
            and request.uri_variables.get("identifier") == "seven"
        )

    def handle(self):
        """Return ordinary content if the resource is read directly.

        Returns
        -------
        object
            Return the result produced by ``handle``.
        """
        return McpResponse.text("allowed")

class _FailingStream(Tool):
    """Raise an application error after delivering one legitimate progress update."""

    name = "failing-stream"

    async def handle(self):
        """Exercise deferred tool execution rather than a synchronous call error.

        Yields
        ------
        object
            Values produced by the asynchronous or synchronous fixture.
        """
        yield McpResponse.progress(1, 2, "started")
        message = "secret-database-password-and-private-path"
        raise RuntimeError(message)

class _ProgressInput(Schema):
    """Select a malformed direct dataclass construction for the wire regression."""

    variant: int

class _RawProgress(Tool[_ProgressInput]):
    """Bypass response factories to verify the last protocol boundary."""

    name = "raw-progress"

    async def handle(self, payload: _ProgressInput):
        """Do not allow a public dataclass to bypass numeric and message checks.

        Parameters
        ----------
        payload : _ProgressInput
            Value supplied for ``payload``.

        Yields
        ------
        object
            Values produced by the asynchronous or synchronous fixture.
        """
        values = (
            Progress(float("nan")),
            Progress(True),
            Progress(1, message=42),
        )
        yield McpResponse(progress_update=values[payload.variant])
        yield McpResponse.text("must not be reached")

class _AuditServer(Server):
    """Compile all audit fixtures through the same public declaration API."""

    name = "Audit Edges"
    tools = (_FailingStream, _RawProgress)
    resources = (_AuthorizedResource,)
    resource_subscriptions = True

class TestAuditEdges(TestCase):
    """Run actual wire dispatch in native request scopes without socket fixtures."""

    async def asyncSetUp(self) -> None:
        """Isolate singleton container bookkeeping and the reactor ambient scope.

        Returns
        -------
        None
            Preserve runner state and prepare an isolated native MCP client.
        """
        self.instances = dict(Container._instances)
        self.scope = ScopedContext.setCurrentScope(None)
        self.app = type("_AuditContainer", (Container,), {})()
        self.client = await self.mcp(_AuditServer, app=self.app)

    def tearDown(self):
        """Restore native test-runner state after every fixture.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        Container._instances.clear()
        Container._instances.update(self.instances)
        ScopedContext.reset(self.scope)

    async def test_subscription_authorization_di_and_outer_context_restoration(self):
        """Admit a URI only with matching nested DI, then restore its parent context.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        stream = self.client.stream(
            "subscriptions/listen",
            {"notifications": {"resourceSubscriptions": ["users://seven/audit"]}},
        )
        try:
            acknowledged = await anext(stream)
            self.assertEqual(
                acknowledged["params"]["notifications"]["resourceSubscriptions"],
                ["users://seven/audit"],
            )
            current = await self.app.make(McpRequest)
            self.assertEqual(current.method, "subscriptions/listen")
            self.assertIsNone(current.uri)
            self.assertEqual(dict(current.uri_variables), {})
        finally:
            await stream.aclose()
        self.assertEqual(self.client.dispatcher.bus.listener_count, 0)

    async def test_raw_progress_never_encodes_invalid_json_rpc_notification(self):
        """NaN, boolean numbers and non-string messages become safe tool failures.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        for variant in range(3):
            with self.subTest(variant=variant):
                response = await self.client.request(
                    "tools/call",
                    {"name": "raw-progress", "arguments": {"variant": variant}},
                    meta={"progressToken": "audit"},
                )
                self.assertEqual(response.notifications, ())
                self.assertNotIn("error", response.message)
                self.assertTrue(response.message["result"]["isError"])
                response.assertTextContains("Tool execution failed")
                self.assertNotIn("must not be reached", str(response.message))

    async def test_stream_failure_keeps_safe_tool_error_semantics(self):
        """A deferred exception still ends with isError after valid progress.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        response = await self.client.request(
            "tools/call",
            {"name": "failing-stream"},
            meta={"progressToken": "audit"},
        )
        self.assertEqual(len(response.notifications), 1)
        progress = response.notifications[0]
        self.assertEqual(progress["method"], "notifications/progress")
        self.assertEqual(progress["params"]["progressToken"], "audit")
        self.assertNotIn("error", response.message)
        self.assertTrue(response.message["result"]["isError"])
        response.assertTextContains("Tool execution failed")
        self.assertNotIn("secret-database", str(response.message))

    async def test_concurrent_close_callers_join_one_cleanup_future(self):
        """No closing caller returns while the owned source is still finalizing.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        source = _Source()
        source.release.clear()
        stream = OwnedStream(source)
        first = asyncio.create_task(stream.aclose())
        await source.closing.wait()
        cleanup = stream._cleanup
        second = asyncio.create_task(stream.aclose())
        try:
            await asyncio.sleep(0)
            self.assertIs(stream._cleanup, cleanup)
            self.assertFalse(first.done())
            self.assertFalse(second.done())
            self.assertEqual(source.closes, 0)
        finally:
            source.release.set()
            await asyncio.gather(first, second)
        self.assertEqual(source.closes, 1)
        await stream.aclose()
        self.assertEqual(source.closes, 1)

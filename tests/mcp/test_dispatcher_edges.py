# ruff: noqa: ANN201, ANN202, PT009, TC003
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Compiling tool handlers evaluates their return annotations at runtime.
from collections.abc import AsyncIterator
import msgspec
from orionis.container.container import Container
from orionis.mcp import (
    CacheHint,
    McpConfig,
    McpExtension,
    McpRequest,
    McpResponse,
    Resource,
    Server,
    Tool,
    ToolCatalog,
)
from orionis.mcp.protocol.constants import (
    CLIENT_CAPABILITIES,
    MCP_PROTOCOL_VERSION,
    PROTOCOL_VERSION,
)
from orionis.mcp.protocol.requests import RequestParams
from orionis.mcp.protocol.results import CallToolResult, CompleteResult
from orionis.test import TestCase
from tests.mcp.test_dispatcher import _Elicit, _Prompt, _Weather


class _Params(RequestParams, frozen=True):
    value: int


class _Result(CompleteResult, frozen=True):
    value: int


def _extension(request: McpRequest, params: _Params) -> _Result:
    """Exercise an explicitly negotiated, independently typed extension.

    Parameters
    ----------
    request : McpRequest
        Value supplied for ``request``.
    params : _Params
        Value supplied for ``params``.

    Returns
    -------
    _Result
        Return the result produced by ``_extension``.
    """
    return _Result(value=params.value + int(request.meta.get("offset", 0)))


class _BadOutput(Tool):
    name = "bad-output"
    output = int

    async def handle(self):
        """Omit isError so its UNSET default must still validate output.

        Returns
        -------
        CallToolResult
            Return the result produced by ``handle``.
        """
        return CallToolResult(content=(), structuredContent="not an integer")


class _CacheResource(Resource):
    name = "cache"
    uri = "data://cache"
    cache = CacheHint(ttl_ms=5000, scope="public")

    async def handle(self):
        """Declare a cacheable resource whose retry still must not be cached.

        Returns
        -------
        object
            Return the result produced by ``handle``.
        """
        return McpResponse.text("data")


class _SubscriptionAccess:
    """Keep revocable policy state independently of the subscription snapshot."""

    def __init__(self) -> None:
        """Enable availability and authorization for the initial subscription.

        Returns
        -------
        None
            No return value.
        """
        self.available = True
        self.authorized = True


class _GuardedResource(_CacheResource):
    """Recheck independently mutable policies before announcing resource updates."""

    name = "guarded"
    uri = "data://guarded"

    def shouldRegister(self, access: _SubscriptionAccess) -> bool:
        """Read the current resource availability.

        Parameters
        ----------
        access : _SubscriptionAccess
            Mutable policy fixture.

        Returns
        -------
        bool
            Whether the resource remains visible.
        """
        return access.available

    def authorize(self, access: _SubscriptionAccess) -> bool:
        """Read the current resource authorization.

        Parameters
        ----------
        access : _SubscriptionAccess
            Mutable policy fixture.

        Returns
        -------
        bool
            Whether the caller may still access the resource.
        """
        return access.authorized


class _LargeResult(Tool):
    """Return a structured value large enough to expose duplicate accounting."""

    name = "large-result"

    def handle(self) -> McpResponse:
        """Build the same final payload as the streaming fixture.

        Returns
        -------
        McpResponse
            Independently generated JSON response.
        """
        return McpResponse.structured({"value": "x" * 2048})


class _LargeStream(_LargeResult):
    """Yield the identical result through the streaming path."""

    name = "large-stream"

    async def handle(self) -> AsyncIterator[McpResponse]:
        """Yield one final structured response.

        Yields
        ------
        McpResponse
            Final response without progress notifications.
        """
        yield super().handle()


class _BoundaryServer(Server):
    """Expose policy and response-budget boundaries through real dispatch."""

    name = "Boundary"
    tools = (_LargeResult, _LargeStream)
    resources = (_GuardedResource,)
    list_changed = True
    resource_subscriptions = True


class _Server(Server):
    name = "Dispatcher edges"
    tools = (_BadOutput, ToolCatalog(_Elicit, _Weather))
    resources = (_CacheResource,)
    prompts = (_Prompt,)
    extensions = (
        McpExtension(
            identifier="example.com/arithmetic",
            methods={"example.com/add": _extension},
            decoders={"example.com/add": msgspec.json.Decoder(_Params)},
        ),
    )


class TestDispatcherEdges(TestCase):
    """Test behavior that crosses compiler, protocol and execution boundaries."""

    async def asyncSetUp(self) -> None:
        """Use a real native container with isolated bindings.

        Returns
        -------
        None
            Prepare a native test client on the isolated container.
        """

        class _Container(Container):
            pass

        self.app = _Container()
        self.client = await self.mcp(_Server, app=self.app)

    async def testResourceSubscriptionsRecheckRevokedPolicies(self) -> None:
        """Drop denied updates without closing unrelated subscription filters.

        Returns
        -------
        None
            No return value.
        """
        for policy in ("available", "authorized"):
            with self.subTest(policy=policy):
                access = _SubscriptionAccess()
                client = await self.mcp(_BoundaryServer, app=self.app)
                stream = client.stream(
                    "subscriptions/listen",
                    {
                        "notifications": {
                            "resourceSubscriptions": [_GuardedResource.uri],
                            "toolsListChanged": True,
                        },
                    },
                )
                try:
                    ack = await anext(stream)
                    self.assertEqual(
                        ack["params"]["notifications"]["resourceSubscriptions"],
                        [_GuardedResource.uri],
                    )
                    self.app.instance(_SubscriptionAccess, access, override=True)
                    self.assertIs(await self.app.make(_SubscriptionAccess), access)
                    setattr(access, policy, False)
                    await client.dispatcher.bus.publish(
                        _BoundaryServer,
                        "notifications/resources/updated",
                        _GuardedResource.uri,
                    )
                    await client.dispatcher.bus.publish(
                        _BoundaryServer,
                        "notifications/tools/list_changed",
                    )
                    event = await anext(stream)
                    self.assertEqual(
                        event["method"],
                        "notifications/tools/list_changed",
                    )
                    setattr(access, policy, True)
                    await client.dispatcher.bus.publish(
                        _BoundaryServer,
                        "notifications/resources/updated",
                        _GuardedResource.uri,
                    )
                    event = await anext(stream)
                    self.assertEqual(event["method"], "notifications/resources/updated")
                    self.assertEqual(event["params"]["uri"], _GuardedResource.uri)
                finally:
                    await stream.aclose()
                self.assertEqual(client.dispatcher.bus.listenerCount, 0)

    async def testStructuredStreamingUsesTheFinalWireBudget(self) -> None:
        """Accept the exact wire-size boundary without counting private provenance.

        Returns
        -------
        None
            No return value.
        """
        client = await self.mcp(_BoundaryServer, app=self.app)
        expected = await client.tool("large-result")
        expected.assertOk()
        limit = len(msgspec.json.encode(expected.message))
        for tool in ("large-result", "large-stream"):
            with self.subTest(tool=tool):
                bounded = await self.mcp(
                    _BoundaryServer,
                    McpConfig(max_response_size=limit),
                    app=self.app,
                )
                result = await bounded.tool(tool)
                result.assertOk()
                self.assertEqual(result.message, expected.message)
                rejected = await self.mcp(
                    _BoundaryServer,
                    McpConfig(max_response_size=limit - 1),
                    app=self.app,
                )
                result = await rejected.tool(tool)
                self.assertEqual(result.message["error"]["code"], -32603)

    async def testCatalogLimitCountsProtocolContentNotBuilderProvenance(self) -> None:
        """Apply the catalog output budget to the actual normalized result.

        Returns
        -------
        None
            No return value.
        """
        expected = await self.client.tool("search_tools", {"query": "weather"})
        expected.assertOk()
        payload = {**expected.message["result"], "_meta": {}}
        limit = len(msgspec.json.encode(payload))
        accepted = await self.mcp(
            _Server,
            McpConfig(tool_search_max_output_bytes=limit),
            app=self.app,
        )
        result = await accepted.tool("search_tools", {"query": "weather"})
        result.assertOk()
        self.assertEqual(result.message, expected.message)
        rejected = await self.mcp(
            _Server,
            McpConfig(tool_search_max_output_bytes=limit - 1),
            app=self.app,
        )
        result = await rejected.tool("search_tools", {"query": "weather"})
        self.assertEqual(result.message["error"]["code"], -32602)

    async def testExtensionNegotiationAndTypedParams(self):
        """Extensions require this request's capability and their own decoder.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        denied = await self.client.request("example.com/add", {"value": 3})
        self.assertEqual(denied.message["error"]["code"], -32021)
        meta = {CLIENT_CAPABILITIES: {"extensions": {"example.com/arithmetic": {}}}}
        accepted = await self.client.request("example.com/add", {"value": 3}, meta=meta)
        self.assertEqual(accepted.message["result"]["value"], 3)
        invalid = await self.client.request(
            "example.com/add",
            {"value": "3"},
            meta=meta,
        )
        self.assertEqual(invalid.message["error"]["code"], -32602)

    async def testInvalidDeclaredOutputWithUnsetError(self):
        """Validate successful raw results even when isError was omitted.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        result = await self.client.tool("bad-output")
        self.assertTrue(result.message["result"]["isError"])
        self.assertNotIn("not an integer", str(result.message))

    async def testEmptyInputResponsesDisableResourceCache(self):
        """The presence of a retry field matters even for an empty map.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        ordinary = await self.client.request("resources/read", {"uri": "data://cache"})
        self.assertEqual(ordinary.message["result"]["ttlMs"], 5000)
        retry = await self.client.request(
            "resources/read",
            {"uri": "data://cache", "inputResponses": {}},
        )
        self.assertEqual(retry.message["result"]["ttlMs"], 0)
        self.assertEqual(retry.message["result"]["cacheScope"], "private")

    async def testUnknownCompletionArgumentAndMalformedUri(self):
        """Reject client input rather than turning it into an internal error.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        completion = await self.client.request(
            "completion/complete",
            {
                "ref": {"type": "ref/prompt", "name": "describe"},
                "argument": {"name": "unknown", "value": "x"},
            },
        )
        resource = await self.client.request("resources/read", {"uri": "bad uri"})
        for response in (completion, resource):
            self.assertEqual(response.message["error"]["code"], -32602)

    async def testCatalogLimitsAndValidation(self):
        """Catalog calls cannot bypass argument validation or batch bounds.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        invalid = await self.client.tool(
            "execute_tools",
            {
                "calls": [{"name": "weather", "arguments": {"location": 7}}],
            },
        )
        nested = invalid.message["result"]["structuredContent"]["results"][0]
        self.assertTrue(nested["result"]["isError"])
        limited = await self.mcp(
            _Server,
            McpConfig(tool_search_max_calls=1),
            app=self.app,
        )
        response = await limited.tool(
            "execute_tools",
            {
                "calls": [{"name": "weather"}, {"name": "weather"}],
            },
        )
        self.assertEqual(response.message["error"]["code"], -32602)

    async def testSingleCatalogMrtrAndRetry(self):
        """Surface interim input at the enclosing protocol result boundary.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        params = {"name": "execute_tools", "arguments": {"calls": [{"name": "elicit"}]}}
        result = await self.client.request(
            "tools/call",
            params,
            meta={
                CLIENT_CAPABILITIES: {"elicitation": {"form": {}}},
            },
        )
        self.assertEqual(result.message["result"]["resultType"], "input_required")
        retried = await self.client.request(
            "tools/call",
            {
                **params,
                "inputResponses": {"choice": {"action": "decline"}},
            },
        )
        retried.assertOk()
        self.assertIn("received", str(retried.message))

    async def testSubscriptionCapacityAndUnstartedCleanup(self):
        """Reject admission before SSE begins and release unstarted subscriptions.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        client = await self.mcp(_Server, McpConfig(max_subscriptions=1), app=self.app)
        data = msgspec.json.encode(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "subscriptions/listen",
                "params": {
                    "notifications": {},
                    "_meta": {
                        PROTOCOL_VERSION: MCP_PROTOCOL_VERSION,
                        CLIENT_CAPABILITIES: {},
                    },
                },
            },
        )
        async with self.app.beginScope():
            first = await client.dispatcher.handle(data)
            self.assertTrue(first.streaming)
            self.assertEqual(client.dispatcher.bus.listenerCount, 1)
            async with self.app.beginScope():
                denied = await client.dispatcher.handle(data)
                self.assertEqual(denied.status, 503)
                self.assertFalse(denied.streaming)
            await first.body.aclose()
            self.assertEqual(client.dispatcher.bus.listenerCount, 0)

    async def testCatalogMultiCallInterimDoesNotTriggerBatchReplay(self):
        """Prevent retrying earlier side effects through an ambiguous batch interim.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        response = await self.client.request(
            "tools/call",
            {
                "name": "execute_tools",
                "arguments": {
                    "calls": [
                        {"name": "weather", "arguments": {"location": "x"}},
                        {"name": "elicit"},
                    ],
                },
            },
            meta={CLIENT_CAPABILITIES: {"elicitation": {"form": {}}}},
        )
        self.assertTrue(response.message["result"]["isError"])
        self.assertEqual(response.message["result"]["resultType"], "complete")
        self.assertNotIn("inputRequests", response.message["result"])

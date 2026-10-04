"""Cross-cutting boundaries of the shared dispatcher and catalog execution."""

import unittest

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
from orionis.mcp.testing import McpTestClient
from tests.mcp.test_dispatcher import _Elicit, _Prompt, _Weather


class _Params(RequestParams, frozen=True):
    value: int


class _Result(CompleteResult, frozen=True):
    value: int


def _extension(request: McpRequest, params: _Params) -> _Result:
    """Exercise an explicitly negotiated, independently typed extension."""
    return _Result(value=params.value + int(request.meta.get("offset", 0)))


class _BadOutput(Tool):
    name = "bad-output"
    output = int

    async def handle(self):
        """Omit isError so its UNSET default must still validate output."""
        return CallToolResult(content=(), structuredContent="not an integer")


class _CacheResource(Resource):
    name = "cache"
    uri = "data://cache"
    cache = CacheHint(ttl_ms=5000, scope="public")

    async def handle(self):
        """Declare a cacheable resource whose retry still must not be cached."""
        return McpResponse.text("data")


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


class TestDispatcherEdges(unittest.IsolatedAsyncioTestCase):
    """Test behavior that crosses compiler, protocol and execution boundaries."""

    def setUp(self):
        """Use a real native container with isolated bindings."""

        class _Container(Container):
            pass

        self.app = _Container()
        self.client = McpTestClient(self.app, _Server)

    async def test_extension_negotiation_and_typed_params(self):
        """Extensions require this request's capability and their own decoder."""
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

    async def test_invalid_declared_output_with_unset_error(self):
        """Validate successful raw results even when isError was omitted."""
        result = await self.client.tool("bad-output")
        self.assertTrue(result.message["result"]["isError"])
        self.assertNotIn("not an integer", str(result.message))

    async def test_empty_input_responses_disable_resource_cache(self):
        """The presence of a retry field matters even for an empty map."""
        ordinary = await self.client.request("resources/read", {"uri": "data://cache"})
        self.assertEqual(ordinary.message["result"]["ttlMs"], 5000)
        retry = await self.client.request(
            "resources/read",
            {"uri": "data://cache", "inputResponses": {}},
        )
        self.assertEqual(retry.message["result"]["ttlMs"], 0)
        self.assertEqual(retry.message["result"]["cacheScope"], "private")

    async def test_unknown_completion_argument_and_malformed_uri(self):
        """Reject client input rather than turning it into an internal error."""
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

    async def test_catalog_limits_and_validation(self):
        """Catalog calls cannot bypass argument validation or batch bounds."""
        invalid = await self.client.tool(
            "execute_tools",
            {
                "calls": [{"name": "weather", "arguments": {"location": 7}}],
            },
        )
        nested = invalid.message["result"]["structuredContent"]["results"][0]
        self.assertTrue(nested["result"]["isError"])
        limited = McpTestClient(self.app, _Server, McpConfig(tool_search_max_calls=1))
        response = await limited.tool(
            "execute_tools",
            {
                "calls": [{"name": "weather"}, {"name": "weather"}],
            },
        )
        self.assertEqual(response.message["error"]["code"], -32602)

    async def test_single_catalog_mrtr_and_retry(self):
        """Surface interim input at the enclosing protocol result boundary."""
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

    async def test_subscription_capacity_and_unstarted_cleanup(self):
        """Reject admission before SSE begins and release unstarted subscriptions."""
        client = McpTestClient(self.app, _Server, McpConfig(max_subscriptions=1))
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
            self.assertEqual(client.dispatcher.bus.listener_count, 1)
            async with self.app.beginScope():
                denied = await client.dispatcher.handle(data)
                self.assertEqual(denied.status, 503)
                self.assertFalse(denied.streaming)
            await first.body.aclose()
            self.assertEqual(client.dispatcher.bus.listener_count, 0)

    async def test_catalog_multi_call_interim_does_not_trigger_batch_replay(self):
        """Prevent retrying earlier side effects through an ambiguous batch interim."""
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

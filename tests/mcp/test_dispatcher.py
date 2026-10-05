import asyncio
from orionis.container.container import Container
from orionis.mcp.config import McpConfig
from orionis.mcp.context import McpRequest  # noqa: TC001 - Native DI resolves this type.
from orionis.mcp.protocol.constants import (
    CLIENT_CAPABILITIES,
    SERVER_INFO,
    SUBSCRIPTION_ID,
)
from orionis.mcp.protocol.metadata import PromptArgument
from orionis.mcp.protocol.results import Completion, InputRequiredResult
from orionis.mcp.responses import McpResponse
from orionis.mcp.server.catalog import ToolCatalog
from orionis.mcp.server.primitives import Prompt, Resource, Server, Tool
from orionis.schemas import Schema
from orionis.test import TestCase

class _Repository:
    """A trusted injectable dependency."""

    __slots__ = ()

    def location(self) -> str:
        """Return server-owned data.

        Returns
        -------
        str
            Return the result produced by ``location``.
        """
        return "trusted"

class _Input(Schema):
    location: str

class _Weather(Tool[_Input]):
    name = "weather"

    async def handle(self, payload: _Input, repository: _Repository):
        """Use DI regardless of similarly named client keys.

        Parameters
        ----------
        payload : _Input
            Value supplied for ``payload``.
        repository : _Repository
            Value supplied for ``repository``.

        Returns
        -------
        object
            Return the result produced by ``handle``.
        """
        return McpResponse.text(f"{payload.location}:{repository.location()}")

class _Hidden(_Weather):
    name = "hidden"

    async def shouldRegister(self, request: McpRequest) -> bool:
        """Hide the tool independently on each request.

        Parameters
        ----------
        request : McpRequest
            Value supplied for ``request``.

        Returns
        -------
        bool
            Return the result produced by ``shouldRegister``.
        """
        return request.meta.get("visible") is True

class _Denied(_Weather):
    name = "denied"

    async def authorize(self) -> bool:
        """Deny direct and catalog invocations.

        Returns
        -------
        bool
            Return the result produced by ``authorize``.
        """
        return False

class _Structured(Tool[_Input, list[int]]):
    name = "structured"

    async def handle(self, payload: _Input):
        """Return scalar-compatible modern structured output.

        Parameters
        ----------
        payload : _Input
            Value supplied for ``payload``.

        Returns
        -------
        object
            Return the result produced by ``handle``.
        """
        return McpResponse.structured([len(payload.location)])

class _Stream(Tool):
    name = "stream"

    async def handle(self):
        """Yield progress before final content.

        Yields
        ------
        object
            Values produced by the asynchronous or synchronous fixture.
        """
        yield McpResponse.progress(1, 2)
        yield McpResponse.progress(2, 2)
        yield McpResponse.text("finished")

class _Broken(Tool):
    name = "broken"

    async def handle(self):
        """Throw a secret-bearing internal exception.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        message = "postgresql://secret-db/private/path.py"
        raise RuntimeError(message)

class _Document(Resource):
    name = "document"
    uri = "docs://guide"

    async def handle(self):
        """Read text without filesystem interpretation.

        Returns
        -------
        object
            Return the result produced by ``handle``.
        """
        return McpResponse.text("guide")

class _Profile(Resource):
    name = "profile"
    uri_template = "users://{user_id}/profile"

    async def handle(self, request: McpRequest):
        """Read URI template variables from immutable request context.

        Parameters
        ----------
        request : McpRequest
            Value supplied for ``request``.

        Returns
        -------
        object
            Return the result produced by ``handle``.
        """
        return McpResponse.text(request.params["user_id"])

class _Prompt(Prompt):
    name = "describe"
    description = "Describe a place"
    arguments = (PromptArgument(name="tone", required=True),)

    async def handle(self, request: McpRequest):
        """Return protocol roles and validated prompt arguments.

        Parameters
        ----------
        request : McpRequest
            Value supplied for ``request``.

        Returns
        -------
        object
            Return the result produced by ``handle``.
        """
        return [
            McpResponse.text("Explain").asAssistant(),
            McpResponse.text(request.arguments["tone"]),
        ]

    async def complete(self):
        """Offer bounded suggestions after authorization.

        Returns
        -------
        Completion
            Return the result produced by ``complete``.
        """
        return Completion(values=("formal", "friendly"))

class _Elicit(Tool):
    name = "elicit"

    async def handle(self, request: McpRequest):
        """Return explicit additional-input requests without retaining state.

        Parameters
        ----------
        request : McpRequest
            Value supplied for ``request``.

        Returns
        -------
        object
            Return the result produced by ``handle``.
        """
        if request.input_responses:
            return McpResponse.text("received")
        return InputRequiredResult(
            inputRequests={
                "choice": {
                    "method": "elicitation/create",
                    "params": {
                        "message": "Choose",
                        "requestedSchema": {
                            "type": "object",
                            "properties": {"answer": {"type": "string"}},
                        },
                    },
                },
            },
        )

class _Server(Server):
    name = "Test Server"
    tools = (_Weather, _Hidden, _Denied, _Structured, _Stream, _Broken, _Elicit)
    resources = (_Document, _Profile)
    prompts = (_Prompt,)
    list_changed = True
    resource_subscriptions = True

class _CatalogServer(Server):
    name = "Catalog"
    tools = (ToolCatalog(_Weather, _Hidden, _Denied),)

class TestDispatcher(TestCase):
    """Run production protocol dispatch with actual native DI and scopes."""

    async def asyncSetUp(self) -> None:
        """Provide an isolated native container, never a second Application.

        Returns
        -------
        None
            Prepare a native test client on the isolated container.
        """

        class _TestContainer(Container):
            pass

        self.app = _TestContainer()
        self.client = await self.mcp(_Server, app=self.app)

    async def test_discovery_and_cache_metadata(self):
        """Discovery advertises only implemented modern capabilities.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        response = await self.client.request("server/discover")
        result = response.message["result"]
        self.assertEqual(result["supportedVersions"], ["2026-07-28"])
        self.assertEqual(result["_meta"][SERVER_INFO]["name"], "Test Server")
        self.assertEqual((result["ttlMs"], result["cacheScope"]), (0, "private"))
        self.assertIn("completions", result["capabilities"])

    async def test_dependency_override_cannot_escape_payload(self):
        """A client argument cannot replace a trusted container service.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        response = await self.client.tool(
            "weather",
            {"location": "Bogota", "repository": "evil"},
        )
        response.assertOk()
        response.assertTextContains("Bogota:trusted")
        invalid = await self.client.tool("weather", {"location": 42})
        self.assertTrue(invalid.message["result"]["isError"])

    async def test_availability_authorization_and_statelessness(self):
        """List visibility and direct invocation use the same checks every time.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        listed = await self.client.request("tools/list")
        names = [item["name"] for item in listed.message["result"]["tools"]]
        self.assertNotIn("hidden", names)
        self.assertNotIn("denied", names)
        for name in ("hidden", "denied"):
            denied = await self.client.tool(name, {"location": "x"})
            self.assertIn("error", denied.message)
        visible = await self.client.request(
            "tools/call",
            {"name": "hidden", "arguments": {"location": "x"}},
            meta={"visible": True},
        )
        visible.assertOk()
        hidden_again = await self.client.tool("hidden", {"location": "x"})
        self.assertIn("error", hidden_again.message)

    async def test_progress_requires_token(self):
        """Progress is request-scoped and emitted only with client opt-in.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        silent = await self.client.tool("stream")
        self.assertEqual(silent.notifications, ())
        response = await self.client.request(
            "tools/call",
            {"name": "stream"},
            meta={"progressToken": "job"},
        )
        self.assertEqual(
            [item["params"]["progress"] for item in response.notifications],
            [1, 2],
        )
        response.assertTextContains("finished")

    async def test_resources_templates_and_prompt_roles(self):
        """Exact URIs, templates and prompts normalize to distinct result schemas.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        resource = await self.client.request(
            "resources/read",
            {"uri": "users://42/profile"},
        )
        self.assertEqual(resource.message["result"]["contents"][0]["text"], "42")
        prompt = await self.client.request(
            "prompts/get",
            {"name": "describe", "arguments": {"tone": "friendly"}},
        )
        self.assertEqual(
            [item["role"] for item in prompt.message["result"]["messages"]],
            ["assistant", "user"],
        )
        missing = await self.client.request("prompts/get", {"name": "describe"})
        self.assertEqual(missing.message["error"]["code"], -32602)

    async def test_output_and_sanitized_errors(self):
        """Validate declared structured output and hide internal exception detail.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        result = await self.client.tool("structured", {"location": "abc"})
        self.assertEqual(result.message["result"]["structuredContent"], [3])
        error = await self.client.tool("broken")
        self.assertTrue(error.message["result"]["isError"])
        self.assertNotIn("secret-db", str(error.message))

    async def test_pagination_is_stateless(self):
        """A cursor can continue on a fresh dispatcher with the same definition.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        first = await self.mcp(_Server, McpConfig(default_page_size=2), app=self.app)
        second = await self.mcp(_Server, McpConfig(default_page_size=2), app=self.app)
        page = await first.request("tools/list")
        cursor = page.message["result"]["nextCursor"]
        following = await second.request("tools/list", {"cursor": cursor})
        self.assertTrue(following.message["result"]["tools"])
        self.assertNotEqual(
            page.message["result"]["tools"],
            following.message["result"]["tools"],
        )

    async def test_completion(self):
        """Resolve suggestions through the compiled provider.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        result = await self.client.request(
            "completion/complete",
            {
                "ref": {"type": "ref/prompt", "name": "describe"},
                "argument": {"name": "tone", "value": "f"},
            },
        )
        self.assertEqual(
            result.message["result"]["completion"]["values"],
            ["formal", "friendly"],
        )

    async def test_mrtr_capability_and_retry(self):
        """Additional input is explicit and may be retried on another instance.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        denied = await self.client.tool("elicit")
        self.assertEqual(denied.message["error"]["code"], -32021)
        response = await self.client.request(
            "tools/call",
            {"name": "elicit"},
            meta={CLIENT_CAPABILITIES: {"elicitation": {"form": {}}}},
        )
        self.assertEqual(response.message["result"]["resultType"], "input_required")
        other = await self.mcp(_Server, app=self.app)
        retried = await other.request(
            "tools/call",
            {
                "name": "elicit",
                "inputResponses": {
                    "choice": {"action": "accept", "content": {"answer": "yes"}},
                },
            },
            request_id=2,
        )
        retried.assertTextContains("received")

    async def test_subscriptions_acknowledge_first_and_cleanup(self):
        """Notification correlation uses the original request ID.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        stream = self.client.stream(
            "subscriptions/listen",
            {"notifications": {"toolsListChanged": True}},
            request_id="sub",
        )
        ack = await anext(stream)
        self.assertEqual(ack["params"]["_meta"][SUBSCRIPTION_ID], "sub")
        await self.client.dispatcher.bus.publish(
            _Server,
            "notifications/tools/list_changed",
        )
        change = await anext(stream)
        self.assertEqual(change["method"], "notifications/tools/list_changed")
        await stream.aclose()
        self.assertEqual(self.client.dispatcher.bus.listener_count, 0)

    async def test_catalog_access_cannot_bypass_auth(self):
        """Synthetic tools hide entries and reuse the ordinary invoker.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        client = await self.mcp(_CatalogServer, app=self.app)
        listed = await client.request("tools/list")
        self.assertEqual(
            [item["name"] for item in listed.message["result"]["tools"]],
            ["execute_tools", "search_tools"],
        )
        found = await client.tool("search_tools", {"query": "weather"})
        self.assertEqual(
            found.message["result"]["structuredContent"]["tools"][0]["name"],
            "weather",
        )
        executed = await client.tool(
            "execute_tools",
            {"calls": [{"name": "weather", "arguments": {"location": "x"}}]},
        )
        executed.assertOk()
        denied = await client.tool(
            "execute_tools",
            {"calls": [{"name": "denied", "arguments": {"location": "x"}}]},
        )
        self.assertIn("error", denied.message)

    async def test_concurrent_payloads_remain_isolated(self):
        """Concurrent calls have independent contexts and native scopes.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        results = await asyncio.gather(
            *(self.client.tool("weather", {"location": str(i)}) for i in range(12)),
        )
        self.assertEqual(
            [item.message["result"]["content"][0]["text"] for item in results],
            [f"{i}:trusted" for i in range(12)],
        )

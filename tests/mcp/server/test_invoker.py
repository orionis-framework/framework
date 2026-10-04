"""Exercise the binder against the real Orionis container and request scope."""

import asyncio
import inspect
import unittest

from orionis.container.container import Container
from orionis.container.context.scope import ScopedContext
from orionis.mcp.context import McpRequest, mutable_json
from orionis.mcp.invoker import McpInvoker
from orionis.mcp.server.compiler import compile_server, validate_payload
from orionis.mcp.server.primitives import Server, Tool
from orionis.schemas import Schema


class _Repository:
    """A dependency whose identity must never come from client arguments."""

    __slots__ = ()


class _Input(Schema):
    """A payload is allowed to contain a dependency-looking field name."""

    repository: str


class _InjectedTool(Tool[_Input]):
    """Keep a trusted service and a similarly named payload field distinct."""

    name = "injected"

    async def handle(
        self,
        payload: _Input,
        repository: _Repository,
        *,
        request: McpRequest,
        mode: str = "native",
    ) -> tuple[object, ...]:
        """Expose resolved arguments for the integration test."""
        await asyncio.sleep(0)
        return payload.repository, repository, request.id, mode


class _Server(Server):
    """Test-only immutable registry."""

    name = "Binding"
    tools = (_InjectedTool,)


class TestInvoker(unittest.IsolatedAsyncioTestCase):
    """Run independent call scopes without bootstrapping an HTTP application."""

    def setUp(self):
        """Isolate the container singleton registry and any reactor ambient scope."""
        self.instances = dict(Container._instances)
        self.scope_token = ScopedContext.setCurrentScope(None)
        self.app = type("_McpTestContainer", (Container,), {})()

    def tearDown(self):
        """Restore all shared container test state."""
        Container._instances.clear()
        Container._instances.update(self.instances)
        ScopedContext.reset(self.scope_token)

    async def test_payload_cannot_override_dependency(self):
        """A malicious repository argument remains inside the typed payload."""
        repository = _Repository()
        self.app.instance(_Repository, repository)
        primitive = compile_server(_Server).tools["injected"]
        request = McpRequest(
            id=1, method="tools/call", arguments={"repository": "attacker"},
        )
        payload = validate_payload(primitive, request.arguments)
        instance = await self.app.build(primitive.definition)
        result = await primitive.handler.invoke(instance, self.app, request, payload)
        self.assertEqual(result, ("attacker", repository, 1, "native"))

    async def test_concurrent_scopes_do_not_share_request_or_dependency(self):
        """Native scoped dependencies and immutable requests remain isolated."""
        self.app.scoped(_Repository, _Repository)
        primitive = compile_server(_Server).tools["injected"]

        async def invoke(identifier):
            async with self.app.beginScope():
                request = McpRequest(id=identifier, method="tools/call")
                payload = _Input(str(identifier))
                instance = await self.app.build(primitive.definition)
                return await primitive.handler.invoke(
                    instance, self.app, request, payload,
                )

        first, second = await asyncio.gather(invoke(1), invoke(2))
        self.assertIsNot(first[1], second[1])
        self.assertEqual((first[2], second[2]), (1, 2))

    async def test_generators_are_not_consumed_or_awaited(self):
        """The dispatcher owns generator iteration and lifecycle cleanup."""

        class Streaming:
            async def handle(self):
                """Produce an async iterator, not an awaitable result."""
                yield "part"

        result = await McpInvoker.compile(Streaming, "handle").invoke(
            Streaming(),
            self.app,
            McpRequest(id=1, method="tools/call"),
        )
        self.assertTrue(inspect.isasyncgen(result))
        self.assertEqual(await anext(result), "part")
        await result.aclose()

    def test_variadic_handler_is_rejected(self):
        """Broad kwargs cannot create an alternate payload-to-DI channel."""

        class Unsafe:
            def handle(self, **arguments: object):
                """Declare the unsupported signature."""
                return arguments

        with self.assertRaisesRegex(TypeError, "variadic"):
            McpInvoker.compile(Unsafe, "handle")

    def test_request_detaches_nested_mutable_input(self):
        """Caller mutations cannot change a request while another task reads it."""
        original = {"nested": {"items": [1]}}
        request = McpRequest(id=1, method="tools/call", arguments=original)
        original["nested"]["items"].append(2)
        self.assertEqual(mutable_json(request.arguments), {"nested": {"items": [1]}})
        with self.assertRaises(TypeError):
            request.arguments["nested"]["new"] = True

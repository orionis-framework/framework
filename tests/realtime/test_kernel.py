import asyncio
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
import msgspec
from orionis.container.container import Container
from orionis.container.context.scope import reset_scope, set_current_scope
from orionis.foundation.config.realtime import RealtimeConfig
from orionis.http.routes.route_compiler import RouteCompiler
from orionis.http.routes.route_resolver import RouteResolver
from orionis.http.routes.router import Router
from orionis.realtime import Hub, remote
from orionis.realtime.contracts.manager import IConnectionManager
from orionis.realtime.manager import ConnectionManager
from orionis.test import TestCase
from tests.http.test_kernel import boot_kernel
from tests.http.test_websocket import _ASGIPeer, _RSGIPeer, _ScopedApp

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication

class CalculatorHub(Hub):
    """Exercise preloaded Hub routing through both real transport adapters."""

    __slots__ = ()

    @remote
    async def add(self, a: int, b: int) -> int:
        """
        Return a value while observing converted connection parameters.

        Parameters
        ----------
        a : int
            First client operand.
        b : int
            Second client operand.

        Returns
        -------
        int
            Sum of both operands and the compiled route offset.

        Raises
        ------
        TypeError
            If the route offset was not converted to an integer.
        """
        offset = self.context.socket.routeParams()["offset"]
        if not isinstance(offset, int):
            message = "Expected the compiled integer route parameter"
            raise TypeError(message)
        return a + b + offset

class _HubApp(_ScopedApp):
    """Expose full scope resolution over the real container fixture."""

    __slots__ = ()

    async def make(self, key):
        """
        Resolve framework context and services in the current scope.

        Parameters
        ----------
        key : object
            Service key supplied to the real container.

        Returns
        -------
        object
            Resolved scoped or registered service.
        """
        return await self.container.make(key)

    def getCurrentScope(self):
        """
        Return the real contextvars-backed scope.

        Returns
        -------
        ScopeManager | None
            Active container scope, or None outside a scope.
        """
        return self.container.getCurrentScope()

class _ASGIHubPeer(_ASGIPeer):
    """Queue server events so tests can drive the connection without sleeps."""

    __slots__ = ("output",)

    def __init__(self) -> None:
        """
        Initialize a peer on the parameterized Hub route.

        Returns
        -------
        None
            Prepare the ASGI route and observable output queue.
        """
        super().__init__("/hub/5")
        self.output = asyncio.Queue()

    async def send(self, event: dict) -> None:
        """
        Record events and publish the next observable wire frame.

        Parameters
        ----------
        event : dict
            Server ASGI event.

        Returns
        -------
        None
            Record and enqueue the delivered event.
        """
        await super().send(event)
        self.output.put_nowait(event)

class _RSGIHubPeer(_RSGIPeer):
    """Drive MessagePack through Granian's documented binary transport API."""

    __slots__ = ("output",)

    def __init__(self) -> None:
        """
        Initialize a peer on the parameterized Hub route.

        Returns
        -------
        None
            Prepare the RSGI route and observable output queue.
        """
        super().__init__()
        self.scope.path = "/hub/5"
        self.output = asyncio.Queue()

    async def send_bytes(self, data: bytes) -> None:
        """
        Record a binary message and publish it to the test client.

        Parameters
        ----------
        data : bytes
            Server MessagePack payload.

        Returns
        -------
        None
            Record and enqueue the delivered binary frame.
        """
        self.sent.append(data)
        self.output.put_nowait(data)

class TestHubKernel(TestCase):
    """Verify route preload, both protocols, connection scopes and cleanup."""

    async def makeKernel(self, protocol: str = "json") -> tuple:
        """
        Attach Hub routes to a kernel using an isolated real DI container.

        Parameters
        ----------
        protocol : str, optional
            Route-selected json or msgpack codec.

        Returns
        -------
        tuple
            Initialized kernel, scoped application fixture and connection manager.
        """
        kernel, stub, _, _ = await boot_kernel()
        app = _HubApp(stub)
        route = Router(cast("IApplication", app)).hub(
            "/hub/{offset:int}", CalculatorHub, protocol=protocol,
        )
        compiled, _ = RouteCompiler().compile([route.export()], None)
        self.addCleanup(Container._instances.pop, type(app.container), None)
        manager = ConnectionManager(RealtimeConfig())
        token = set_current_scope(None)
        try:
            app.container.instance(IConnectionManager, manager)
        finally:
            reset_scope(token)
        object.__setattr__(kernel, "_KernelHTTP__app", app)
        object.__setattr__(kernel, "_KernelHTTP__routes", RouteResolver(compiled))
        await object.__getattribute__(kernel, "_KernelHTTP__preloadHandlers")()
        return kernel, app, manager

    async def testAsgiHubRoutePreloadParametersAndCleanup(self) -> None:
        """
        Dispatch a JSON invocation and release both connection and call scopes.

        Returns
        -------
        None
            Verify route parameters, JSON completion and scope disposal.
        """
        kernel, app, manager = await self.makeKernel()
        peer = _ASGIHubPeer()
        owner = asyncio.create_task(
            kernel.handleASGI(peer.scope, peer.receive, peer.send),
        )
        try:
            async with asyncio.timeout(2):
                self.assertEqual((await peer.output.get())["type"], "websocket.accept")
                ready = msgspec.json.decode((await peer.output.get())["text"])
                self.assertEqual(ready["version"], 1)
                peer.events.put_nowait({
                    "type": "websocket.receive",
                    "text": '{"type":"invoke","id":"a","target":"add","args":[2,3]}',
                })
                result = msgspec.json.decode((await peer.output.get())["text"])
                self.assertEqual(
                    result, {"type": "completion", "id": "a", "result": 10},
                )
                peer.events.put_nowait({"type": "websocket.disconnect", "code": 1000})
                await owner
        finally:
            owner.cancel()
            await asyncio.gather(owner, return_exceptions=True)
        self.assertEqual(manager.snapshot(), ())
        self.assertEqual(len(app.scopes), 2)
        self.assertTrue(all(not scope.isActive for scope in app.scopes))
        self.assertFalse(kernel._KernelHTTP__websocket_tasks)

    async def testRsgiHubUsesSameRuntimeWithMessagePack(self) -> None:
        """
        Exercise real RSGI message kinds through the shared Hub lifecycle.

        Returns
        -------
        None
            Verify MessagePack dispatch and connection cleanup through RSGI.
        """
        kernel, app, manager = await self.makeKernel("msgpack")
        peer = _RSGIHubPeer()
        owner = asyncio.create_task(kernel.handleRSGI(peer.scope, peer))
        try:
            async with asyncio.timeout(2):
                ready = msgspec.msgpack.decode(await peer.output.get())
                self.assertEqual(ready["type"], "ready")
                peer.events.put_nowait(SimpleNamespace(
                    kind=1, data=msgspec.msgpack.encode({
                        "type": "invoke", "id": "a", "target": "add", "args": [2, 3],
                    }),
                ))
                result = msgspec.msgpack.decode(await peer.output.get())
                self.assertEqual(result["result"], 10)
                peer.events.put_nowait(SimpleNamespace(kind=0, data=None))
                await owner
        finally:
            owner.cancel()
            await asyncio.gather(owner, return_exceptions=True)
        self.assertEqual(manager.snapshot(), ())
        self.assertTrue(all(not scope.isActive for scope in app.scopes))

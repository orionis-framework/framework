import asyncio
from orionis.http.routes.exceptions.route_not_found import RouteNotFound
from orionis.http.routes.fluent import FluentRoute
from orionis.http.routes.route_compiler import RouteCompiler
from orionis.test import TestCase
from tests.http import test_websocket as websocket_fixtures
from tests.http.test_kernel import boot_kernel, make_asgi_scope
from tests.http.test_websocket import (
    _ASGIPeer,
    waiting_handler,
)

class _SignallingPeer(_ASGIPeer):
    """Signal acceptance without polling the event loop."""

    __slots__ = ("accepted",)

    def __init__(self) -> None:
        """
        Initialize a peer on the fixture's dynamic route.

        Returns
        -------
        None
            Prepare the socket route and acceptance notification event.
        """
        super().__init__("/socket/1")
        self.accepted = asyncio.Event()

    async def send(self, event: dict) -> None:
        """
        Record frames and signal a completed handshake.

        Parameters
        ----------
        event : dict
            Server ASGI event to record.

        Returns
        -------
        None
            Store the event and notify waiters when acceptance completes.
        """
        await super().send(event)
        if event["type"] == "websocket.accept":
            self.accepted.set()

class TestWebSocketShutdown(TestCase):
    """Exercise shutdown against actual kernel connection scopes."""

    async def testHttpCannotUseInternalWebSocketMethod(self) -> None:
        """
        Reject the internal dispatch key when supplied as an HTTP method.

        Returns
        -------
        None
            Verify internal socket dispatch produces an HTTP route error.
        """
        route = FluentRoute("WEBSOCKET", "/socket", waiting_handler)
        compiled, _ = RouteCompiler().compile([route.export()], None)
        kernel, _, _, catch = await boot_kernel(routes=compiled)
        peer = _ASGIPeer()
        scope = make_asgi_scope("/socket")
        scope["method"] = "WEBSOCKET"
        await kernel.handleASGI(scope, peer.receive, peer.send)
        self.assertIsInstance(catch.handled[0], RouteNotFound)
        self.assertTrue(all(e["type"].startswith("http.") for e in peer.sent))

    async def testShutdownJoinsConnectionAndReleasesScope(self) -> None:
        """
        Cancel a blocked receive through the kernel's shutdown hook.

        Returns
        -------
        None
            Verify the connection owner, scope and admission are released.
        """
        fixture = websocket_fixtures.TestWebSocketKernel()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        kernel, app = await fixture.makeKernel(waiting_handler)
        peer = _SignallingPeer()
        owner = asyncio.create_task(
            kernel.handleASGI(peer.scope, peer.receive, peer.send),
        )
        try:
            async with asyncio.timeout(1):
                await peer.accepted.wait()
            self.assertTrue(app.scopes[0].isActive)
            await kernel._KernelHTTP__shutdownWebSockets()
            self.assertTrue(owner.cancelled())
            self.assertFalse(app.scopes[0].isActive)
            self.assertFalse(kernel._KernelHTTP__websocket_tasks)
            self.assertEqual(peer.sent[-1]["type"], "websocket.close")
            await kernel._KernelHTTP__shutdownWebSockets()
        finally:
            owner.cancel()
            await asyncio.gather(owner, return_exceptions=True)

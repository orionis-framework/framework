import asyncio
from collections.abc import Callable  # noqa: TC003 - Runtime test reflection.
from threading import BoundedSemaphore
from types import SimpleNamespace
from typing import TYPE_CHECKING, ClassVar, cast
from orionis.container.container import Container
from orionis.container.context.manager import ScopeManager  # noqa: TC001
from orionis.container.context.scope import get_current_scope
from orionis.foundation.config.http import HTTP, HTTPWebSocket
from orionis.http import WebSocket, WebSocketDisconnected, WebSocketMiddleware
from orionis.http.adapters.request.asgi import ASGITransportAdapter
from orionis.http.adapters.request.rsgi import RSGITransportAdapter
from orionis.http.adapters.websocket.asgi import ASGIWebSocketTransport
from orionis.http.adapters.websocket.rsgi import RSGIWebSocketTransport
from orionis.http.middleware import BaseMiddleware
from orionis.http.routes.fluent import FluentRoute
from orionis.http.routes.route_compiler import RouteCompiler
from orionis.http.routes.route_resolver import RouteResolver
from orionis.http.routes.router import Router
from orionis.http.routes.exceptions.route_not_found import RouteNotFound
from orionis.test import TestCase
from tests.http.test_kernel import (
    _StubApp, _StubRsgiHeaders, boot_kernel, make_asgi_scope,
)

if TYPE_CHECKING:
    from granian._granian import RSGIWebsocketProtocol
    from granian.rsgi import Scope

class _ASGIPeer:
    """Model one server connection with queued events and recorded output."""

    __slots__ = ("events", "fail_send", "scope", "sent")

    def __init__(self, path: str = "/socket", *, denial: bool = False) -> None:
        """Prepare a handshake and a queue that blocks after available messages.

        Parameters
        ----------
        path : str, optional
            WebSocket route path for the connection.
        denial : bool, optional
            Whether the scope supports HTTP handshake denial.

        Returns
        -------
        None
            Initialize the ASGI scope and queued connection event.
        """
        self.scope = make_asgi_scope(path)
        self.scope["type"] = "websocket"
        self.scope["asgi"] = {"spec_version": "2.5"}
        self.scope.pop("method")
        if denial:
            self.scope["extensions"] = {"websocket.http.response": {}}
        self.events = asyncio.Queue()
        self.events.put_nowait({"type": "websocket.connect"})
        self.sent = []
        self.fail_send = False

    async def receive(self) -> dict:
        """Receive queued messages, blocking when the client has no data.

        Returns
        -------
        dict
            Next event queued by the simulated client.
        """
        return await self.events.get()

    async def send(self, event: dict) -> None:
        """Record a server message or simulate a transport disconnection.

        Parameters
        ----------
        event : dict
            ASGI event emitted by the server.

        Returns
        -------
        None
            Append the event to the peer's sent-message history.

        Raises
        ------
        OSError
            If the simulated peer has disconnected.
        """
        if self.fail_send:
            error_msg = "Peer disconnected"
            raise OSError(error_msg)
        self.sent.append(event)

    def socket(self, max_message_size: int = 1024 * 1024) -> WebSocket:
        """Bind the public connection object to the ASGI server callbacks.

        Parameters
        ----------
        max_message_size : int, optional
            Maximum accepted message size in bytes.

        Returns
        -------
        WebSocket
            Connection using this peer's ASGI scope and callbacks.
        """
        return WebSocket(
            ASGIWebSocketTransport(self.scope, self.receive, self.send),
            ASGITransportAdapter(self.scope), max_message_size=max_message_size,
        )

class _RSGIPeer:
    """Model the documented Granian WebsocketProtocol and transport methods."""

    __slots__ = ("accepts", "events", "scope", "sent", "statuses")

    def __init__(self) -> None:
        """Prepare the scope and recording protocol state.

        Returns
        -------
        None
            Initialize the RSGI scope and protocol recorders.
        """
        self.scope = SimpleNamespace(
            proto="ws", method="GET", path="/socket", scheme="http",
            http_version="1.1", rsgi_version="1.6", client="127.0.0.1:42",
            server="127.0.0.1:80", authority=None, query_string="",
            headers=_StubRsgiHeaders({"host": ["orionis.test"]}),
        )
        self.accepts = 0
        self.events = asyncio.Queue()
        self.sent = []
        self.statuses = []

    async def accept(self) -> object:
        """Return this recording transport after accepting the handshake.

        Returns
        -------
        object
            This peer, acting as the accepted protocol transport.
        """
        self.accepts += 1
        return self

    async def receive(self) -> object:
        """Return the next Granian message object.

        Returns
        -------
        object
            Next message queued by the simulated client.
        """
        return await self.events.get()

    async def sendString(self, data: str) -> None:
        """Record the protocol's required text sending method.

        Parameters
        ----------
        data : str
            Text frame sent by the server.

        Returns
        -------
        None
            Append the text frame to the peer's sent-message history.
        """
        self.sent.append(data)

    async def sendBytes(self, data: bytes) -> None:
        """Record the protocol's required binary sending method.

        Parameters
        ----------
        data : bytes
            Binary frame sent by the server.

        Returns
        -------
        None
            Append the binary frame to the peer's sent-message history.
        """
        self.sent.append(data)

    send_str = sendString
    send_bytes = sendBytes

    def close(self, status: int | None) -> None:
        """Record handshake rejection or default connection closure.

        Parameters
        ----------
        status : int | None
            HTTP status used to reject the handshake, if provided.

        Returns
        -------
        None
            Append the closure status to the peer's status history.
        """
        self.statuses.append(status)

    def socket(self, max_message_size: int = 1024 * 1024) -> WebSocket:
        """Bind the public connection object to the RSGI protocol.

        Parameters
        ----------
        max_message_size : int, optional
            Maximum accepted message size in bytes.

        Returns
        -------
        WebSocket
            Connection using this peer's RSGI scope and protocol.
        """
        return WebSocket(
            RSGIWebSocketTransport(cast("RSGIWebsocketProtocol", self)),
            RSGITransportAdapter(cast("Scope", self.scope)),
            max_message_size=max_message_size,
        )

class _BlockingAccept(_ASGIPeer):
    """Pause after the server receives an accept event."""

    __slots__ = ("accept_entered", "release_accept")

    def __init__(self) -> None:
        """Prepare observable synchronization around handshake sending.

        Returns
        -------
        None
            Initialize events for observing and releasing handshake sending.
        """
        super().__init__()
        self.accept_entered = asyncio.Event()
        self.release_accept = asyncio.Event()

    async def send(self, event: dict) -> None:
        """Record events and pause acceptance before the callback completes.

        Parameters
        ----------
        event : dict
            ASGI event emitted by the server.

        Returns
        -------
        None
            Record the event and wait when the handshake is accepted.
        """
        await super().send(event)
        if event["type"] == "websocket.accept":
            self.accept_entered.set()
            await self.release_accept.wait()

class _DisconnectedOnClose(_ASGIPeer):
    """Disconnect after acceptance when the server attempts error closure."""

    __slots__ = ()

    async def send(self, event: dict) -> None:
        """Accept the handshake, then simulate a failed close-frame send.

        Parameters
        ----------
        event : dict
            ASGI event emitted by the server.

        Returns
        -------
        None
            Record the event unless the simulated close send fails.
        """
        if event["type"] == "websocket.close":
            self.fail_send = True
        await super().send(event)

class TestWebSocketTransport(TestCase):
    """Check public messaging, protocol state transitions and disconnects."""

    async def testAsgiRoundTripAndPeerClose(self) -> None:
        """Preserve empty text, binary payloads, JSON and peer close metadata.

        Returns
        -------
        None
            Verify ASGI send, receive, JSON and close behavior.
        """
        peer = _ASGIPeer()
        socket = peer.socket()
        await socket.accept()
        peer.events.put_nowait({"type": "websocket.receive", "text": ""})
        peer.events.put_nowait({"type": "websocket.receive", "bytes": b"data"})
        peer.events.put_nowait({"type": "websocket.receive", "text": '{"ok":true}'})
        self.assertEqual((await socket.receive()).text, "")
        self.assertEqual((await socket.receive()).bytes, b"data")
        self.assertEqual(await socket.receiveJson(), {"ok": True})
        await socket.sendJson({"ok": True})
        await socket.send(b"binary")
        self.assertEqual(peer.sent[-2]["text"], '{"ok":true}')
        self.assertEqual(peer.sent[-1]["bytes"], b"binary")
        peer.events.put_nowait({
            "type": "websocket.disconnect", "code": 1001, "reason": "left",
        })
        message = await socket.receive()
        self.assertTrue(message.isDisconnect())
        self.assertEqual((message.code, message.reason), (1001, "left"))
        self.assertTrue(socket.closed)
        await socket.close()
        self.assertEqual(len(peer.sent), 3)

    async def testRsgiRoundTripAndExplicitProtocolLimit(self) -> None:
        """Map RSGI message kinds and reject unsupported close arguments.

        Returns
        -------
        None
            Verify RSGI frames and the protocol's close-frame limitations.
        """
        peer = _RSGIPeer()
        socket = peer.socket()
        await socket.accept()
        peer.events.put_nowait(SimpleNamespace(kind=2, data="text"))
        peer.events.put_nowait(SimpleNamespace(kind=1, data=b"binary"))
        self.assertEqual((await socket.receive()).text, "text")
        self.assertEqual((await socket.receive()).bytes, b"binary")
        await socket.send("text")
        await socket.send(b"binary")
        self.assertEqual(peer.sent, ["text", b"binary"])
        with self.assertRaises(NotImplementedError):
            await socket.close(code=1001)
        await socket.close()
        self.assertEqual(peer.statuses, [None])
        self.assertEqual(peer.accepts, 1)

    async def testHandshakeRejectionAcrossProtocols(self) -> None:
        """Use HTTP denial status when supported and ASGI's default otherwise.

        Returns
        -------
        None
            Verify rejection behavior for ASGI and RSGI peers.
        """
        for peer in (_ASGIPeer(), _ASGIPeer(denial=True), _RSGIPeer()):
            with self.subTest(protocol=type(peer).__name__):
                socket = peer.socket()
                await socket.reject(status_code=429)
                await socket.reject()
                self.assertTrue(socket.closed)
                self.assertFalse(socket.accepted)
                if isinstance(peer, _RSGIPeer):
                    self.assertEqual(peer.statuses, [429])
                elif peer.scope.get("extensions"):
                    self.assertEqual(peer.sent[0]["status"], 429)
                    self.assertEqual(peer.sent[1]["body"], b"")
                else:
                    self.assertEqual(
                        peer.sent, [{"type": "websocket.close", "code": 1008}],
                    )

    async def testAcceptanceRequiredAndSingleUse(self) -> None:
        """Reject premature messaging, repeated acceptance and invalid data.

        Returns
        -------
        None
            Verify connection state guards and message type validation.
        """
        socket = _ASGIPeer().socket()
        with self.assertRaises(RuntimeError):
            await socket.send("premature")
        with self.assertRaises(RuntimeError):
            await socket.receive()
        await socket.accept()
        with self.assertRaises(RuntimeError):
            await socket.accept()
        with self.assertRaises(RuntimeError):
            await socket.reject()
        with self.assertRaises(TypeError):
            await socket.send(42)
        await socket.close()
        with self.assertRaises(WebSocketDisconnected):
            await socket.send("late")

    async def testSendDisconnectionIsReported(self) -> None:
        """Translate a transport write failure to a terminal disconnect.

        Returns
        -------
        None
            Verify a failed send closes the connection and raises disconnect.
        """
        peer = _ASGIPeer()
        socket = peer.socket()
        await socket.accept()
        peer.fail_send = True
        with self.assertRaises(WebSocketDisconnected):
            await socket.send("message")
        self.assertTrue(socket.closed)

    async def testInboundLimitUsesUtf8BytesAcrossProtocols(self) -> None:
        """Reject text exceeding the configured byte budget on both interfaces.

        Returns
        -------
        None
            Verify UTF-8 payload size enforcement for ASGI and RSGI.
        """
        for peer in (_ASGIPeer(), _RSGIPeer()):
            socket = peer.socket(max_message_size=3)
            await socket.accept()
            event = (
                {"type": "websocket.receive", "text": "éé"}
                if isinstance(peer, _ASGIPeer)
                else SimpleNamespace(kind=2, data="éé")
            )
            peer.events.put_nowait(event)
            with self.assertRaises(WebSocketDisconnected) as caught:
                await socket.receive()
            self.assertEqual(caught.exception.code, 1009)
            self.assertTrue(socket.closed)
            if isinstance(peer, _ASGIPeer):
                self.assertEqual(peer.sent[-1]["code"], 1009)
            else:
                self.assertEqual(peer.statuses, [None])

    async def testConcurrentReceiveIsRejected(self) -> None:
        """Keep one receiver per connection without creating an unbounded queue.

        Returns
        -------
        None
            Verify concurrent reads fail while the active read completes.
        """
        peer = _ASGIPeer()
        socket = peer.socket()
        await socket.accept()
        pending = asyncio.create_task(socket.receive())
        await asyncio.sleep(0)
        try:
            with self.assertRaises(RuntimeError):
                await socket.receive()
            peer.events.put_nowait({"type": "websocket.receive", "text": "first"})
            self.assertEqual((await pending).text, "first")
        finally:
            pending.cancel()
            await socket.close()

    async def testMalformedEventAndInvalidCloseFrame(self) -> None:
        """Reject non-message events, reserved codes and oversized reasons.

        Returns
        -------
        None
            Verify malformed events and invalid close frames are rejected.
        """
        peer = _ASGIPeer()
        socket = peer.socket()
        await socket.accept()
        peer.events.put_nowait({"type": "http.request"})
        with self.assertRaises(RuntimeError):
            await socket.receive()
        with self.assertRaises(ValueError):
            await socket.close(code=1005)
        with self.assertRaises(ValueError):
            await socket.close(reason="é" * 62)
        await socket.close(code=1001, reason="leaving")
        self.assertEqual(peer.sent[-1]["reason"], "leaving")

    async def testConsumedHandshakeCanStillBeRejected(self) -> None:
        """Avoid a second receive after cancellation between connect and accept.

        Returns
        -------
        None
            Verify a consumed handshake can close without another receive.
        """
        peer = _ASGIPeer()
        socket = peer.socket()
        await cast("ASGIWebSocketTransport", socket._transport)._connectEvent()
        await asyncio.wait_for(socket.close(), timeout=1)
        self.assertTrue(socket.closed)

    async def testCancelledAcceptanceClosesWithoutSecondHandshakeReceive(self) -> None:
        """Close a potentially accepted handshake after send cancellation.

        Returns
        -------
        None
            Verify cancellation leaves the connection in a closed state.
        """
        peer = _BlockingAccept()
        socket = peer.socket()
        pending = asyncio.create_task(socket.accept())
        await peer.accept_entered.wait()
        pending.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await pending
        await asyncio.wait_for(socket.close(), timeout=1)
        self.assertTrue(socket.closed)
        self.assertEqual(peer.sent[-1]["type"], "websocket.close")

class _ScopedDependency:
    """Identify the scoped service owned by a single connection."""

    __slots__ = ()

class _ScopedApp(_StubApp):
    """Use the actual container for connection dependencies and lifetime scopes."""

    __slots__ = ("container",)

    def __init__(self, original: _StubApp) -> None:
        """Retain boot collaborators and create an isolated container subclass.

        Parameters
        ----------
        original : _StubApp
            Booted application double providing route and config state.

        Returns
        -------
        None
            Create a container dedicated to this WebSocket test.
        """
        super().__init__(original.builds, original.config_data)
        concrete = type("_WebSocketTestContainer", (Container,), {})
        self.container = concrete()
        self.container.scoped(None, _ScopedDependency)

    def beginScope(self) -> ScopeManager:
        """Record a real scope manager so cleanup can be asserted.

        Returns
        -------
        ScopeManager
            Newly created dependency scope for a connection.
        """
        scope = self.container.beginScope()
        self.scopes.append(scope)
        return scope

    async def build(self, concrete: type) -> object:
        """Resolve user controllers and middleware through real injection.

        Parameters
        ----------
        concrete : type
            Class requested by the application kernel.

        Returns
        -------
        object
            Registered double or container-built instance.
        """
        if concrete in self.builds:
            return self.builds[concrete]
        return await self.container.build(concrete)

    async def invoke(self, function: Callable, **kwargs: object) -> object:
        """Resolve handler arguments from the connection scope.

        Parameters
        ----------
        function : Callable
            Handler whose arguments are resolved by the container.
        **kwargs : object
            Explicit keyword arguments passed to the handler.

        Returns
        -------
        object
            Result returned by the invoked handler.
        """
        return await self.container.invoke(function, **kwargs)

    async def call(self, instance: object, method: str, **kwargs: object) -> object:
        """Invoke controller actions with real dependency injection.

        Parameters
        ----------
        instance : object
            Controller instance receiving the action call.
        method : str
            Name of the controller action to invoke.
        **kwargs : object
            Explicit keyword arguments passed to the action.

        Returns
        -------
        object
            Result returned by the controller action.
        """
        return await self.container.call(instance, method, **kwargs)

class _ConnectionMiddleware(WebSocketMiddleware):
    """Require the same scoped dependency observed by the handler."""

    __slots__ = ("dependency",)

    def __init__(self, dependency: _ScopedDependency) -> None:
        """Retain the connection's injected dependency.

        Parameters
        ----------
        dependency : _ScopedDependency
            Service scoped to the current WebSocket connection.

        Returns
        -------
        None
            Store the dependency for middleware and handler assertions.
        """
        self.dependency = dependency

    async def handle(self, socket: WebSocket, call_next: object) -> None:
        """Add a connection-local marker before advancing the pipeline.

        Parameters
        ----------
        socket : WebSocket
            Active connection receiving the scoped marker.
        call_next : object
            Continuation for the remaining middleware and handler.

        Returns
        -------
        None
            Store the dependency on connection state and advance the pipeline.
        """
        socket.state.dependency = self.dependency
        await call_next()

class _RejectMiddleware(WebSocketMiddleware):
    """Deny a pending connection without calling its handler."""

    __slots__ = ()

    async def handle(self, socket: WebSocket, _call_next: object) -> None:
        """Reject application authorization during the handshake.

        Parameters
        ----------
        socket : WebSocket
            Connection whose handshake is denied.
        _call_next : object
            Unused pipeline continuation.

        Returns
        -------
        None
            Send an unauthorized handshake rejection.
        """
        await socket.reject(status_code=401)

class _DoubleNext(WebSocketMiddleware):
    """Exercise the continuation's single-consumption guard."""

    __slots__ = ()

    async def handle(self, _socket: WebSocket, call_next: object) -> None:
        """Advance twice to expose accidental duplicate dispatch.

        Parameters
        ----------
        _socket : WebSocket
            Unused active connection.
        call_next : object
            Pipeline continuation guarded against repeated calls.

        Returns
        -------
        None
            Attempt to consume the continuation twice.
        """
        await call_next()
        await call_next()

async def echo_handler(socket: WebSocket, room: int = 0) -> None:
    """Accept the connection and echo one message with its converted room ID.

    Parameters
    ----------
    socket : WebSocket
        Connection to accept and use for one message exchange.
    room : int, optional
        Route parameter converted to an integer.

    Returns
    -------
    None
        Send the room ID and received message as JSON.
    """
    await socket.accept()
    await socket.sendJson({"room": room, "message": (await socket.receive()).data})

async def scoped_handler(
    socket: WebSocket, dependency: _ScopedDependency, **_params: object,
) -> None:
    """Verify middleware and handler injection share one service per connection.

    Parameters
    ----------
    socket : WebSocket
        Connection carrying the middleware's scoped dependency.
    dependency : _ScopedDependency
        Dependency injected into the handler for this connection.
    **_params : object
        Additional converted route parameters, unused by this handler.

    Returns
    -------
    None
        Accept the connection and report the shared dependency identity.
    """
    if socket.state.dependency is not dependency:
        error_msg = "Middleware and handler received different scoped dependencies"
        raise RuntimeError(error_msg)
    await socket.accept()
    await socket.sendJson({"dependency": id(dependency)})

async def failure_handler(socket: WebSocket, **_params: object) -> None:
    """Fail after acceptance to exercise error closure and scope cleanup.

    Parameters
    ----------
    socket : WebSocket
        Connection accepted before raising the simulated failure.
    **_params : object
        Route parameters unused by this handler.

    Returns
    -------
    None
        Raise a handler failure after accepting the connection.
    """
    await socket.accept()
    error_msg = "Connection handler failed"
    raise RuntimeError(error_msg)

async def waiting_handler(socket: WebSocket, **_params: object) -> None:
    """Wait for peer data while holding the connection lifetime scope.

    Parameters
    ----------
    socket : WebSocket
        Connection used to wait for the next peer message.
    **_params : object
        Route parameters unused by this handler.

    Returns
    -------
    None
        Keep the connection scope active until a peer message arrives.
    """
    await socket.accept()
    await socket.receive()

class _SocketController:
    """Exercise controller construction and action argument injection."""

    __slots__ = ("socket",)

    def __init__(self, socket: WebSocket) -> None:
        """Retain the exact connection bound in the active scope.

        Parameters
        ----------
        socket : WebSocket
            Connection injected while the request scope is active.

        Returns
        -------
        None
            Store the connection for action-injection assertions.
        """
        self.socket = socket

    async def echo(self, socket: WebSocket, room: int) -> None:
        """Check constructor/action identity before echoing one message.

        Parameters
        ----------
        socket : WebSocket
            Connection injected into the controller action.
        room : int
            Converted route parameter to include in the response.

        Returns
        -------
        None
            Verify connection identity and echo one message.
        """
        if socket is not self.socket:
            error_msg = "Constructor and action received different WebSockets"
            raise RuntimeError(error_msg)
        await echo_handler(socket, room)

class TestWebSocketKernel(TestCase):
    """Check routing and connection lifetimes with actual container injection."""

    apps: ClassVar[list[_ScopedApp]]

    def setUp(self) -> None:
        """Prepare the list of disposable containers for this test.

        Returns
        -------
        None
            Initialize per-test container tracking.
        """
        self.apps = []

    def tearDown(self) -> None:
        """Release the isolated container subclasses after each test.

        Returns
        -------
        None
            Remove each test container from the singleton registry.
        """
        for app in self.apps:
            Container._instances.pop(type(app.container), None)

    async def makeKernel(
        self, action: object = echo_handler, middleware: tuple = (),
    ) -> tuple:
        """Compile a dynamic route and bind a real container behind the kernel.

        Parameters
        ----------
        action : object, optional
            Handler or controller action assigned to the route.
        middleware : tuple, optional
            Middleware classes attached to the route.

        Returns
        -------
        tuple
            Kernel and scoped application double for the test.
        """
        route = FluentRoute("WEBSOCKET", "/socket/{room:int}", action)
        route.middleware(*middleware)
        compiled, _fallback = RouteCompiler().compile([route.export()], None)
        kernel, stub, _responses, _catch = await boot_kernel(routes=compiled)
        app = _ScopedApp(stub)
        kernel._KernelHTTP__app = app
        self.apps.append(app)
        return kernel, app

    async def testAsgiAndRsgiDispatchConvertedRouteParameters(self) -> None:
        """Support both protocols through one handler and scoped connection API.

        Returns
        -------
        None
            Verify route conversion and response dispatch for both protocols.
        """
        kernel, app = await self.makeKernel()
        asgi = _ASGIPeer("/socket/42")
        asgi.events.put_nowait({"type": "websocket.receive", "text": "asgi"})
        await kernel.handleASGI(asgi.scope, asgi.receive, asgi.send)
        self.assertEqual(asgi.sent[1]["text"], '{"room":42,"message":"asgi"}')
        self.assertEqual(asgi.sent[-1]["type"], "websocket.close")
        rsgi = _RSGIPeer()
        rsgi.scope.path = "/socket/12"
        rsgi.events.put_nowait(SimpleNamespace(kind=2, data="rsgi"))
        await kernel.handleRSGI(rsgi.scope, rsgi)
        self.assertEqual(rsgi.sent, ['{"room":12,"message":"rsgi"}'])
        self.assertEqual(rsgi.statuses, [None])
        self.assertTrue(all(not scope.isActive for scope in app.scopes))

    async def testMiddlewareAndHandlersShareIsolatedScopedDependencies(self) -> None:
        """Keep each connection's middleware and DI services private.

        Returns
        -------
        None
            Verify concurrent connections receive separate scoped dependencies.
        """
        kernel, app = await self.makeKernel(scoped_handler, (_ConnectionMiddleware,))
        first, second = _ASGIPeer("/socket/1"), _ASGIPeer("/socket/2")
        await asyncio.gather(
            kernel.handleASGI(first.scope, first.receive, first.send),
            kernel.handleASGI(second.scope, second.receive, second.send),
        )
        self.assertNotEqual(first.sent[1]["text"], second.sent[1]["text"])
        self.assertEqual(len(app.scopes), 2)
        self.assertTrue(all(not scope.isActive for scope in app.scopes))

    async def testControllerConstructorAndActionInjection(self) -> None:
        """Inject one scoped WebSocket into controller and action arguments.

        Returns
        -------
        None
            Verify constructor and action receive the same connection.
        """
        kernel, _app = await self.makeKernel([_SocketController, "echo"])
        peer = _ASGIPeer("/socket/7")
        peer.events.put_nowait({"type": "websocket.receive", "text": "controller"})
        await kernel.handleASGI(peer.scope, peer.receive, peer.send)
        self.assertIn('"room":7', peer.sent[1]["text"])

    async def testFailureClosesConnectionAndScope(self) -> None:
        """Report application errors after sending an internal-error close.

        Returns
        -------
        None
            Verify handler failure closes the connection and its scope.
        """
        kernel, app = await self.makeKernel(failure_handler)
        peer = _ASGIPeer("/socket/1")
        ambient = get_current_scope()
        with self.assertRaisesRegex(RuntimeError, "Connection handler failed"):
            await kernel.handleASGI(peer.scope, peer.receive, peer.send)
        self.assertEqual(peer.sent[-1]["code"], 1011)
        self.assertFalse(app.scopes[0].isActive)
        self.assertIs(get_current_scope(), ambient)

    async def testHandlerErrorSurvivesDisconnectedErrorClose(self) -> None:
        """Preserve a handler failure when sending its error close also fails.

        Returns
        -------
        None
            Verify cleanup and the original exception survive a send failure.
        """
        kernel, app = await self.makeKernel(failure_handler)
        kernel._KernelHTTP__websocket_slots = BoundedSemaphore(1)
        peer = _DisconnectedOnClose("/socket/1")
        ambient = get_current_scope()
        with self.assertRaisesRegex(RuntimeError, "Connection handler failed"):
            await kernel.handleASGI(peer.scope, peer.receive, peer.send)
        self.assertEqual(peer.sent[0]["type"], "websocket.accept")
        self.assertTrue(peer.fail_send)
        self.assertFalse(app.scopes[0].isActive)
        self.assertIs(get_current_scope(), ambient)
        self.assertTrue(kernel._KernelHTTP__websocket_slots.acquire(blocking=False))
        kernel._KernelHTTP__websocket_slots.release()

    async def testCancellationReleasesScopeAndConnectionAdmission(self) -> None:
        """Join cancellation without leaking a scope or admission slot.

        Returns
        -------
        None
            Verify cancellation closes the connection and releases resources.
        """
        kernel, app = await self.makeKernel(waiting_handler)
        kernel._KernelHTTP__websocket_slots = BoundedSemaphore(1)
        peer = _ASGIPeer("/socket/1")
        task = asyncio.create_task(
            kernel.handleASGI(peer.scope, peer.receive, peer.send),
        )
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertFalse(app.scopes[0].isActive)
        self.assertEqual(peer.sent[-1]["type"], "websocket.close")
        self.assertTrue(kernel._KernelHTTP__websocket_slots.acquire(blocking=False))
        kernel._KernelHTTP__websocket_slots.release()

    async def testCapacityRejectsBeforeAllocatingAnotherScope(self) -> None:
        """Reject an excess handshake before allocating another scope.

        Returns
        -------
        None
            Verify capacity rejection uses the supported denial extension.
        """
        kernel, app = await self.makeKernel(waiting_handler)
        kernel._KernelHTTP__websocket_slots = BoundedSemaphore(1)
        first = _ASGIPeer("/socket/1")
        pending = asyncio.create_task(
            kernel.handleASGI(first.scope, first.receive, first.send),
        )
        await asyncio.sleep(0)
        try:
            second = _ASGIPeer("/socket/2", denial=True)
            await kernel.handleASGI(second.scope, second.receive, second.send)
            self.assertEqual(second.sent[0]["status"], 503)
            self.assertEqual(len(app.scopes), 1)
        finally:
            first.events.put_nowait({"type": "websocket.disconnect", "code": 1000})
            await pending

    async def testBrowserOriginGuardAndConfiguredOrigin(self) -> None:
        """Reject an untrusted browser origin before running the handler.

        Returns
        -------
        None
            Verify hostile origins fail and configured origins are accepted.
        """
        kernel, _app = await self.makeKernel()
        hostile = _ASGIPeer("/socket/1", denial=True)
        hostile.scope["headers"].append((b"origin", b"https://hostile.test"))
        await kernel.handleASGI(hostile.scope, hostile.receive, hostile.send)
        self.assertEqual(hostile.sent[0]["status"], 403)
        kernel._KernelHTTP__websocket_config = HTTPWebSocket(
            allow_origins=["https://client.test"],
        )
        allowed = _ASGIPeer("/socket/2")
        allowed.scope["headers"].append((b"origin", b"https://client.test"))
        allowed.events.put_nowait({"type": "websocket.receive", "text": "ok"})
        await kernel.handleASGI(allowed.scope, allowed.receive, allowed.send)
        self.assertEqual(allowed.sent[0]["type"], "websocket.accept")

    async def testConnectionMiddlewareCanRejectAndCannotAdvanceTwice(self) -> None:
        """Allow handshake authorization and enforce single handler dispatch.

        Returns
        -------
        None
            Verify rejection and the continuation's single-use guard.
        """
        kernel, _app = await self.makeKernel(middleware=(_RejectMiddleware,))
        peer = _ASGIPeer("/socket/1", denial=True)
        await kernel.handleASGI(peer.scope, peer.receive, peer.send)
        self.assertEqual(peer.sent[0]["status"], 401)
        kernel, _app = await self.makeKernel(middleware=(_DoubleNext,))
        peer = _ASGIPeer("/socket/1")
        peer.events.put_nowait({"type": "websocket.receive", "text": "once"})
        with self.assertRaisesRegex(RuntimeError, "already been called"):
            await kernel.handleASGI(peer.scope, peer.receive, peer.send)
        self.assertEqual(
            sum(event["type"] == "websocket.send" for event in peer.sent), 1,
        )

    async def testMissingRouteAndGlobalGuardsRejectHandshake(self) -> None:
        """Respect maintenance and route matching before handshake acceptance.

        Returns
        -------
        None
            Verify missing routes and maintenance reject the connection.
        """
        kernel, app = await self.makeKernel()
        missing = _ASGIPeer("/unknown", denial=True)
        await kernel.handleASGI(missing.scope, missing.receive, missing.send)
        self.assertEqual(missing.sent[0]["status"], 404)
        app.maintenance = True
        peer = _ASGIPeer("/socket/1", denial=True)
        await kernel.handleASGI(peer.scope, peer.receive, peer.send)
        self.assertEqual(peer.sent[0]["status"], 503)

    async def testGlobalRateLimitAlsoCountsConnectionHandshakes(self) -> None:
        """Reject excessive handshakes through the configured HTTP limiter.

        Returns
        -------
        None
            Verify WebSocket handshakes consume the shared rate limit.
        """
        kernel, app = await self.makeKernel()
        config = dict(app.config_data["http"])
        config["rate_limit"] = {
            "rate_limit_enabled": True, "rate_limit_requests": 1,
            "rate_limit_window_seconds": 60,
        }
        kernel._KernelHTTP__defaultMiddleware(
            config, kernel._KernelHTTP__default_responses,
        )
        first = _ASGIPeer("/socket/1", denial=True)
        first.events.put_nowait({"type": "websocket.receive", "text": "allowed"})
        await kernel.handleASGI(first.scope, first.receive, first.send)
        self.assertEqual(first.sent[0]["type"], "websocket.accept")
        second = _ASGIPeer("/socket/2", denial=True)
        await kernel.handleASGI(second.scope, second.receive, second.send)
        self.assertEqual(second.sent[0]["status"], 429)

    def testRoutingKeepsHttpAndWebSocketMethodsSeparate(self) -> None:
        """Keep WebSocket routes out of HTTP Allow and fallback matching.

        Returns
        -------
        None
            Verify HTTP method discovery ignores WebSocket-only routes.
        """
        app = SimpleNamespace(routeHealthCheck="/health")
        router = Router(app)
        router.websocket("/shared", echo_handler).name("socket")
        router.get("/shared", echo_handler)
        router.websocket("/only-socket", echo_handler)
        compiled, fallback = RouteCompiler().compile(router.export()["routes"], None)
        resolver = RouteResolver(compiled, fallback=fallback)
        self.assertEqual(resolver.resolve("WEBSOCKET", "/shared").route.name, "socket")
        self.assertEqual(resolver.options("/shared"), ["GET", "HEAD", "OPTIONS"])
        self.assertEqual(resolver.options("/only-socket"), [])
        with self.assertRaises(RouteNotFound):
            resolver.resolve("GET", "/only-socket")

    def testMiddlewareTypesAndConfigurationAreValidated(self) -> None:
        """Reject mixed protocol middleware and invalid operational budgets.

        Returns
        -------
        None
            Verify protocol compatibility and WebSocket limits are validated.
        """
        route = FluentRoute("WEBSOCKET", "/socket", echo_handler)
        route.middleware(BaseMiddleware)
        with self.assertRaises(TypeError):
            RouteCompiler().compile([route.export()], None)
        http_route = FluentRoute("GET", "/socket", echo_handler)
        http_route.middleware(_RejectMiddleware)
        with self.assertRaises(TypeError):
            RouteCompiler().compile([http_route.export()], None)
        with self.assertRaises(ValueError):
            HTTPWebSocket(max_connections=0)
        with self.assertRaises(TypeError):
            HTTPWebSocket(max_message_size=True)
        self.assertEqual(
            HTTP(websocket={"max_connections": 3}).websocket.max_connections, 3,
        )

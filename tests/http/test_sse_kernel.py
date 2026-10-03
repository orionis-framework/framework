import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING, ClassVar, Self
from orionis.background.task import BackgroundTask
from orionis.container.container import Container
from orionis.container.context.scope import get_current_scope
from orionis.http import EventStreamResponse, ServerSentEvent, response
from orionis.http.adapters.response.asgi import ASGIResponseAdapter
from orionis.http.adapters.response.rsgi import RSGIResponseAdapter
from orionis.http.base import BaseController
from orionis.http.request import Request
from orionis.http.routes.fluent import FluentRoute
from orionis.http.routes.route_compiler import RouteCompiler
from orionis.test import TestCase
from tests.http.test_kernel import (
    _StubApp,
    _StubRsgiHeaders,
    _StubRsgiScope,
    boot_kernel,
    make_asgi_scope,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable
    from orionis.container.context.manager import ScopeManager
    from orionis.http.kernel import KernelHTTP


class _ScopedDependency:
    """Identify the service that must survive until response cleanup."""

    __slots__ = ()


class _StreamState:
    """Observe the real request scope from producer, transport, and cleanup."""

    __slots__ = (
        "closed", "container", "dependency", "error", "observations", "release",
        "request", "scope", "started", "waiting",
    )

    def __init__(self, container: Container) -> None:
        """Prepare deterministic producer controls and lifetime observations.

        Parameters
        ----------
        container : Container
            Container resolving services throughout the stream.

        Returns
        -------
        None
            Initialize a producer dedicated to one request.
        """
        self.container = container
        self.dependency = None
        self.request = None
        self.scope = None
        self.error: Exception | None = None
        self.observations: list[tuple[str, bool, object, object, object]] = []
        self.started = asyncio.Event()
        self.waiting = asyncio.Event()
        self.release = asyncio.Event()
        self.closed = 0

    async def observe(self, phase: str) -> None:
        """Resolve the active request and scoped service at a lifecycle boundary.

        Parameters
        ----------
        phase : str
            Boundary identifying the observation.

        Returns
        -------
        None
            Record the current scope and dependencies without faking DI.
        """
        scope = get_current_scope()
        request = await self.container.make(Request)
        dependency = await self.container.make(_ScopedDependency)
        self.observations.append((phase, scope.isActive, scope, request, dependency))

    async def events(self, cursor: int) -> AsyncIterator[ServerSentEvent]:
        """Emit two events with an explicitly controlled pause between them.

        Parameters
        ----------
        cursor : int
            Converted route parameter used as the outgoing event ID.

        Yields
        ------
        ServerSentEvent
            Initial resume marker and a manual comment heartbeat.

        Raises
        ------
        Exception
            Configured producer failure after the first event.
        """
        try:
            await self.observe("produce")
            self.started.set()
            yield ServerSentEvent(
                event="resume",
                id=str(cursor),
                data=self.request.headers.get("Last-Event-ID", "none"),
            )
            self.waiting.set()
            await self.release.wait()
            if self.error is not None:
                raise self.error
            await self.observe("produce")
            yield ServerSentEvent(comment="ping")
        finally:
            self.closed += 1
            await self.observe("cleanup")

    async def background(self) -> None:
        """Resolve the same dependencies after successful streaming delivery.

        Returns
        -------
        None
            Record background execution inside the active request scope.
        """
        await self.observe("background")


async def event_handler(
    request: Request,
    dependency: _ScopedDependency,
    state: _StreamState,
    cursor: int,
) -> EventStreamResponse:
    """Return a native SSE response using injected request-local services.

    Parameters
    ----------
    request : Request
        Real request constructed by the HTTP kernel.
    dependency : _ScopedDependency
        Service owned by this request's container scope.
    state : _StreamState
        Producer controls and observations for this request.
    cursor : int
        Converted integer route parameter.

    Returns
    -------
    EventStreamResponse
        Lazy SSE stream with a background completion callback.
    """
    state.request = request
    state.dependency = dependency
    state.scope = get_current_scope()
    await state.observe("handler")
    return response.eventStream(
        state.events(cursor),
        background=BackgroundTask(state.background),
    )


class _EventController(BaseController):
    """Exercise constructor and action injection through the HTTP dispatcher."""

    __slots__ = ("state",)

    def __init__(
        self, request: Request, dependency: _ScopedDependency, state: _StreamState,
    ) -> None:
        """Record the dependencies supplied when constructing the controller.

        Parameters
        ----------
        request : Request
            Request registered in the active HTTP scope.
        dependency : _ScopedDependency
            Request-local service resolved by the actual container.
        state : _StreamState
            Producer observations owned by this connection.

        Returns
        -------
        None
            Retain the producer without starting iteration or I/O.
        """
        self.state = state
        scope = get_current_scope()
        state.observations.append(
            ("constructor", scope.isActive, scope, request, dependency),
        )

    async def stream(
        self, request: Request, dependency: _ScopedDependency, cursor: int,
    ) -> EventStreamResponse:
        """Return SSE using action parameters resolved independently by DI.

        Parameters
        ----------
        request : Request
            Request injected into the controller action.
        dependency : _ScopedDependency
            Scoped dependency injected into the controller action.
        cursor : int
            Converted route parameter.

        Returns
        -------
        EventStreamResponse
            Lazy producer which retains the controller's original scope.
        """
        return await event_handler(request, dependency, self.state, cursor)


class _SSEApp(_StubApp):
    """Retain kernel fixtures while using actual HTTP scopes and injection."""

    __slots__ = ("container", "state", "states")

    def __init__(self, original: _StubApp) -> None:
        """Create a container whose singleton registry belongs to this fixture.

        Parameters
        ----------
        original : _StubApp
            Booted kernel's configuration and collaborator doubles.

        Returns
        -------
        None
            Prepare isolated DI and the controlled event producer.
        """
        super().__init__(original.builds, original.config_data)

        class _SSEContainer(Container):
            _instances: ClassVar[dict] = {}

        self.container = _SSEContainer()
        self.container.scoped(None, _ScopedDependency)
        self.state = _StreamState(self.container)
        self.states = [self.state]

    def beginScope(self) -> ScopeManager:
        """Bind stream controls inside the existing HTTP request scope.

        Returns
        -------
        ScopeManager
            Production scope manager recorded for lifetime assertions.
        """
        scope = self.container.beginScope()
        scope[_StreamState] = self.states[len(self.scopes)]
        self.scopes.append(scope)
        return scope

    async def build(self, concrete: type) -> object:
        """Construct request controllers using the production container.

        Parameters
        ----------
        concrete : type
            Controller class selected by the boot-time dispatch table.

        Returns
        -------
        object
            New controller with its constructor dependencies injected.
        """
        self.build_calls.append(concrete)
        return await self.container.build(concrete)

    async def call(
        self, instance: object, method: str, **kwargs: object,
    ) -> object:
        """Invoke a controller action through production dependency injection.

        Parameters
        ----------
        instance : object
            Controller built inside the active request scope.
        method : str
            Action name resolved during kernel boot.
        **kwargs : object
            Converted route parameters.

        Returns
        -------
        object
            Action result produced with injected method dependencies.
        """
        return await self.container.call(instance, method, **kwargs)

    async def invoke(self, function: Callable, **kwargs: object) -> object:
        """Invoke the routed handler through production dependency injection.

        Parameters
        ----------
        function : Callable
            Handler resolved by the kernel's real route dispatch table.
        **kwargs : object
            Route parameters converted by Orionis.

        Returns
        -------
        object
            Response returned by the injected handler.
        """
        return await self.container.invoke(function, **kwargs)


class _SSEPeer:
    """Expose ASGI callbacks and Granian's supported RSGI stream operations."""

    __slots__ = (
        "body", "disconnected", "error", "headers", "interface", "messages",
        "state", "status", "watcher_closed", "watching",
    )

    def __init__(self, interface: str, state: _StreamState) -> None:
        """Store protocol observations and deterministic disconnection controls.

        Parameters
        ----------
        interface : str
            ASGI or RSGI entry point exercised by the test.
        state : _StreamState
            Producer whose scope must remain alive during transport sends.

        Returns
        -------
        None
            Prepare an open transport without timers or polling.
        """
        self.interface = interface
        self.state = state
        self.body: list[bytes] = []
        self.messages: list[dict] = []
        self.status = None
        self.headers: dict[str, str] = {}
        self.error: Exception | None = None
        self.disconnected = asyncio.Event()
        self.watching = asyncio.Event()
        self.watcher_closed = asyncio.Event()

    async def dispatch(self, kernel: KernelHTTP, method: str = "GET") -> None:
        """Dispatch an SSE request with a normal Last-Event-ID header.

        Parameters
        ----------
        kernel : KernelHTTP
            Booted production HTTP kernel.
        method : str, optional
            HTTP method sent to the registered GET endpoint.

        Returns
        -------
        None
            Await response delivery and request cleanup.
        """
        if self.interface == "asgi":
            scope = make_asgi_scope("/events/42", method)
            scope["headers"].append((b"last-event-id", b"41"))
            await kernel.handleASGI(scope, self.receive, self.send)
        else:
            scope = _StubRsgiScope("/events/42", method)
            scope.headers = _StubRsgiHeaders({
                "host": ["orionis.test"], "last-event-id": ["41"],
            })
            await kernel.handleRSGI(scope, self)

    async def receive(self) -> dict:
        """Wait for an ASGI disconnect without inventing repeated body events.

        Returns
        -------
        dict
            Supported HTTP disconnect message.
        """
        await self.clientDisconnect()
        return {"type": "http.disconnect"}

    async def clientDisconnect(self) -> None:
        """Wait for the client using Granian's supported disconnect signal.

        Returns
        -------
        None
            Finish only when the test disconnects or the watcher is cancelled.
        """
        self.watching.set()
        try:
            await self.disconnected.wait()
        finally:
            self.watcher_closed.set()

    async def send(self, message: dict) -> None:
        """Record an ASGI message and await any nonempty body send.

        Parameters
        ----------
        message : dict
            Message emitted by Orionis's ASGI response adapter.

        Returns
        -------
        None
            Store response headers, chunks, and the final body marker.
        """
        self.messages.append(message)
        if message["type"] == "http.response.start":
            self.status = message["status"]
            self.headers = {
                name.decode("latin-1"): value.decode("latin-1")
                for name, value in message["headers"]
            }
        elif message["body"]:
            await self.sendBytes(message["body"])

    async def sendBytes(self, chunk: bytes) -> None:
        """Observe the live request scope while sending an encoded event.

        Parameters
        ----------
        chunk : bytes
            SSE bytes sent by either protocol adapter.

        Returns
        -------
        None
            Append one event after successful transport delivery.

        Raises
        ------
        Exception
            Configured transport failure while sending the event.
        """
        await self.state.observe("send")
        if self.error is not None:
            raise self.error
        self.body.append(chunk)

    def responseStream(self, status: int, headers: list[tuple[str, str]]) -> Self:
        """Open an RSGI response stream exposing only supported operations.

        Parameters
        ----------
        status : int
            HTTP response status.
        headers : list[tuple[str, str]]
            RSGI response headers supplied by Orionis.

        Returns
        -------
        Self
            Transport implementing Granian's send_bytes operation.
        """
        self.responseEmpty(status, headers)
        return self

    def responseEmpty(self, status: int, headers: list[tuple[str, str]]) -> None:
        """Record an RSGI response start, including an empty HEAD response.

        Parameters
        ----------
        status : int
            HTTP response status.
        headers : list[tuple[str, str]]
            RSGI response headers supplied by Orionis.

        Returns
        -------
        None
            Store the response metadata without a body.
        """
        self.status = status
        self.headers = dict(headers)

    client_disconnect = clientDisconnect
    response_empty = responseEmpty
    response_stream = responseStream
    send_bytes = sendBytes


class TestSSEKernel(TestCase):
    """Verify SSE routing, dependency lifetime, and both real response adapters."""

    async def makeKernel(
        self, *, controller: bool = False,
    ) -> tuple[KernelHTTP, _SSEApp]:
        """Compile a real Orionis route and install production response adapters.

        Parameters
        ----------
        controller : bool, optional
            Whether to register a controller action instead of a function.

        Returns
        -------
        tuple[KernelHTTP, _SSEApp]
            Booted kernel and its application with actual request scopes.
        """
        handler = [_EventController, "stream"] if controller else event_handler
        route = FluentRoute("GET", "/events/{cursor:int}", handler)
        compiled, _fallback = RouteCompiler().compile([route.export()], None)
        kernel, original, _responses, _catch = await boot_kernel(routes=compiled)
        app = _SSEApp(original)
        kernel._KernelHTTP__app = app
        kernel._KernelHTTP__asgi_adapter = ASGIResponseAdapter()
        kernel._KernelHTTP__rsgi_adapter = RSGIResponseAdapter()
        return kernel, app

    def assertScopeLifetime(self, app: _SSEApp) -> None:
        """Check observations precede the clearing of the original request scope.

        Parameters
        ----------
        app : _SSEApp
            Application whose completed request is being inspected.

        Returns
        -------
        None
            Assert no second scope or replacement dependency was created.
        """
        self.assertEqual(len(app.scopes), 1)
        self.assertFalse(app.state.scope.isActive)
        self.assertIsNone(app.state.scope[Request])
        self.assertIsNone(app.state.scope[_ScopedDependency])
        for phase, active, scope, request, dependency in app.state.observations:
            with self.subTest(phase=phase):
                self.assertTrue(active)
                self.assertIs(scope, app.scopes[0])
                self.assertIs(request, app.state.request)
                self.assertIs(dependency, app.state.dependency)

    async def testScopeSurvivesStreamingAndBackgroundOnBothProtocols(self) -> None:
        """Route SSE with converted parameters and the existing header API.

        Returns
        -------
        None
            Verify encoded events and DI remain valid through background work.
        """
        for interface in ("asgi", "rsgi"):
            with self.subTest(interface=interface):
                kernel, app = await self.makeKernel()
                peer = _SSEPeer(interface, app.state)
                app.state.release.set()
                ambient = get_current_scope()
                await asyncio.wait_for(peer.dispatch(kernel), timeout=2)
                self.assertEqual(peer.status, 200)
                self.assertEqual(
                    peer.headers["content-type"], "text/event-stream; charset=utf-8",
                )
                self.assertNotIn("content-length", peer.headers)
                self.assertEqual(peer.body, [
                    b"event: resume\nid: 42\ndata: 41\n\n", b": ping\n\n",
                ])
                phases = [item[0] for item in app.state.observations]
                self.assertEqual(phases, [
                    "handler", "produce", "send", "produce", "send",
                    "cleanup", "background",
                ])
                self.assertEqual(app.state.closed, 1)
                self.assertTrue(peer.watcher_closed.is_set())
                self.assertScopeLifetime(app)
                self.assertIs(get_current_scope(), ambient)

    async def testDisconnectClosesProducerBeforeLeavingTheRequestScope(self) -> None:
        """Interrupt idle SSE producers through each protocol's disconnect signal.

        Returns
        -------
        None
            Verify prompt cleanup, no second event, and no background execution.
        """
        for interface in ("asgi", "rsgi"):
            with self.subTest(interface=interface):
                kernel, app = await self.makeKernel()
                peer = _SSEPeer(interface, app.state)
                task = asyncio.create_task(peer.dispatch(kernel))
                try:
                    await asyncio.wait_for(app.state.waiting.wait(), timeout=2)
                    await asyncio.wait_for(peer.watching.wait(), timeout=2)
                    self.assertTrue(app.state.scope.isActive)
                    peer.disconnected.set()
                    await asyncio.wait_for(task, timeout=2)
                finally:
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        await task
                self.assertEqual(len(peer.body), 1)
                self.assertEqual(app.state.closed, 1)
                self.assertEqual(app.state.observations[-1][0], "cleanup")
                self.assertTrue(peer.watcher_closed.is_set())
                self.assertFalse(app.state.release.is_set())
                self.assertScopeLifetime(app)

    async def testRequestCancellationPropagatesAfterScopedProducerCleanup(self) -> None:
        """Cancel suspended requests without abandoning the producer or watcher.

        Returns
        -------
        None
            Verify cancellation remains CancelledError and background is skipped.
        """
        for interface in ("asgi", "rsgi"):
            with self.subTest(interface=interface):
                kernel, app = await self.makeKernel()
                peer = _SSEPeer(interface, app.state)
                task = asyncio.create_task(peer.dispatch(kernel))
                try:
                    await asyncio.wait_for(app.state.waiting.wait(), timeout=2)
                    await asyncio.wait_for(peer.watching.wait(), timeout=2)
                    task.cancel()
                    with self.assertRaises(asyncio.CancelledError):
                        await asyncio.wait_for(task, timeout=2)
                finally:
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        await task
                self.assertEqual(app.state.closed, 1)
                self.assertEqual(app.state.observations[-1][0], "cleanup")
                self.assertTrue(peer.watcher_closed.is_set())
                self.assertScopeLifetime(app)

    async def testProducerAndTransportFailuresPreserveErrorsAndCloseScope(self) -> None:
        """Preserve streaming failures after the handler has returned successfully.

        Returns
        -------
        None
            Verify cleanup still resolves DI and failure suppresses background.
        """
        for interface in ("asgi", "rsgi"):
            for failure in ("producer", "transport"):
                with self.subTest(interface=interface, failure=failure):
                    kernel, app = await self.makeKernel()
                    peer = _SSEPeer(interface, app.state)
                    error = RuntimeError(f"{failure} failed")
                    if failure == "producer":
                        app.state.error = error
                    else:
                        peer.error = error
                    app.state.release.set()
                    with self.assertRaises(RuntimeError) as raised:
                        await asyncio.wait_for(peer.dispatch(kernel), timeout=2)
                    self.assertIs(raised.exception, error)
                    self.assertEqual(app.state.closed, 1)
                    self.assertEqual(app.state.observations[-1][0], "cleanup")
                    self.assertTrue(peer.watcher_closed.is_set())
                    self.assertScopeLifetime(app)

    async def testHeadUsesTheGetRouteWithoutStartingTheEventProducer(self) -> None:
        """Send SSE headers for HEAD while leaving the async generator unstarted.

        Returns
        -------
        None
            Preserve the ordinary successful HEAD background and scope behavior.
        """
        for interface in ("asgi", "rsgi"):
            with self.subTest(interface=interface):
                kernel, app = await self.makeKernel()
                peer = _SSEPeer(interface, app.state)
                await asyncio.wait_for(peer.dispatch(kernel, "HEAD"), timeout=2)
                self.assertEqual(peer.status, 200)
                self.assertEqual(peer.body, [])
                self.assertNotIn("content-length", peer.headers)
                self.assertFalse(app.state.started.is_set())
                self.assertFalse(peer.watching.is_set())
                self.assertEqual(app.state.closed, 0)
                self.assertEqual(
                    [item[0] for item in app.state.observations],
                    ["handler", "background"],
                )
                self.assertScopeLifetime(app)

    async def testControllerReceivesConstructorAndMethodDependencies(self) -> None:
        """Resolve the same request and scoped service in the controller and stream.

        Returns
        -------
        None
            Confirm both dependency-injection paths share the request scope.
        """
        for interface in ("asgi", "rsgi"):
            with self.subTest(interface=interface):
                kernel, app = await self.makeKernel(controller=True)
                peer = _SSEPeer(interface, app.state)
                app.state.release.set()
                await asyncio.wait_for(peer.dispatch(kernel), timeout=2)
                self.assertEqual(peer.status, 200)
                self.assertEqual(app.build_calls, [_EventController])
                self.assertEqual(app.state.observations[0][0], "constructor")
                self.assertEqual(app.state.observations[-1][0], "background")
                self.assertEqual(len(peer.body), 2)
                self.assertScopeLifetime(app)

    async def testConcurrentControllersKeepScopesIsolatedDuringDisconnect(self) -> None:
        """Mix successful and disconnected SSE requests on one application.

        Returns
        -------
        None
            Verify 32 concurrent controllers per transport retain distinct scopes.
        """
        connection_count = 32
        for interface in ("asgi", "rsgi"):
            with self.subTest(interface=interface):
                kernel, app = await self.makeKernel(controller=True)
                app.states.extend(
                    _StreamState(app.container) for _ in range(connection_count - 1)
                )
                peers = [_SSEPeer(interface, state) for state in app.states]
                tasks = [asyncio.create_task(peer.dispatch(kernel)) for peer in peers]
                try:
                    async with asyncio.timeout(5):
                        await asyncio.gather(
                            *(state.waiting.wait() for state in app.states),
                        )
                        for index, peer in enumerate(peers):
                            if index % 2:
                                peer.state.release.set()
                            else:
                                peer.disconnected.set()
                        await asyncio.gather(*tasks)
                finally:
                    for state in app.states:
                        state.release.set()
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                self.assertEqual(len(app.scopes), connection_count)
                self.assertEqual(
                    len({id(state.request) for state in app.states}), connection_count,
                )
                self.assertEqual(
                    len({id(state.dependency) for state in app.states}),
                    connection_count,
                )
                for index, peer in enumerate(peers):
                    state = peer.state
                    self.assertFalse(state.scope.isActive)
                    self.assertIsNone(state.scope[Request])
                    self.assertIsNone(state.scope[_ScopedDependency])
                    self.assertEqual(state.closed, 1)
                    self.assertEqual(len(peer.body), 2 if index % 2 else 1)
                    phases = [item[0] for item in state.observations]
                    self.assertEqual("background" in phases, bool(index % 2))
                    for _phase, active, scope, request, service in state.observations:
                        self.assertTrue(active)
                        self.assertIs(scope, state.scope)
                        self.assertIs(request, state.request)
                        self.assertIs(service, state.dependency)

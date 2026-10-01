from __future__ import annotations
import asyncio
from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace
from typing import TYPE_CHECKING
from orionis.http import kernel as kernel_module
from orionis.http.adapters.request.asgi import ASGITransportAdapter
from orionis.http.adapters.response.asgi import ASGIResponseAdapter
from orionis.http.adapters.response.rsgi import RSGIResponseAdapter
from orionis.http.enums.interfaces import Interface
from orionis.http.payload.estructures.headers import Headers
from orionis.http.request import Request
from orionis.http.responses import Response, ResponseTemplate
from orionis.http.routes.fluent import FluentRoute
from orionis.http.routes.route_cache import RouteCache
from orionis.http.routes.route_compiler import RouteCompiler
from orionis.http.routes.router import Router
from orionis.test import TestCase
from tests.http.test_kernel import (
    _RecordingMiddleware,
    _SessionMiddlewareDouble,
    boot_kernel,
    dispatch,
    make_asgi_scope,
    make_route,
    receive_empty,
    send_noop,
    web_handler,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

class _HookResponse(Response):
    """Expose a background hook independent of the optional task attribute."""

    __slots__ = ("calls",)

    async def runBackground(self) -> None:
        """Record an overridden response completion hook.

        Returns
        -------
        None
            The response hook counter is incremented.
        """
        await asyncio.sleep(0)
        self.calls += 1

class _CountingAdapter(ASGITransportAdapter):
    """Record the number of materialized scope snapshots."""

    __slots__ = ("calls",)

    def __init__(self, scope: dict) -> None:
        """Initialize a transport and its snapshot counter.

        Parameters
        ----------
        scope : dict
            Source ASGI request scope.

        Returns
        -------
        None
            The counter starts at zero.
        """
        super().__init__(scope)
        self.calls = 0

    def getScope(self) -> dict:
        """Read a scope snapshot and record the request.

        Returns
        -------
        dict
            Scope returned by the parent adapter.
        """
        self.calls += 1
        return super().getScope()

class TestExecutionResources(TestCase):
    """Cover lazy allocations, immutable templates, and continuation isolation."""

    def testHeaderFlagsAreIndependentOfCallerMutation(self) -> None:
        """Keep the index and format flags consistent after input mutation.

        Returns
        -------
        None
            Header ownership and duplicate preservation are asserted.
        """
        source = [("Host", "first"), ("HOST", "second"), ("X", "café")]
        headers = Headers(source)
        source.append(("Injected", "unsafe\r\nvalue"))
        self.assertFalse(headers.hasInvalidFormat())
        self.assertEqual(headers.count("host"), 2)
        self.assertEqual(headers.getAll("host"), ["first", "second"])
        self.assertEqual(headers.items()[-1], ("X", "café"))
        self.assertTrue(Headers([("X\r", "value")]).hasInvalidFormat())
        self.assertTrue(Headers([(b"x", b"unsafe\n")], decode=True).hasInvalidFormat())
        self.assertEqual(Headers([(b"x", b"caf\xe9")], decode=True).get("X"), "café")

    async def testTransportPreservesOverriddenBackgroundHooks(self) -> None:
        """Execute subclass completion hooks even without a background task.

        Returns
        -------
        None
            ASGI and RSGI preserve hooks for HEAD, buffered, and stream responses.
        """

        def protocol_send(*_args: object) -> None:
            """Accept a buffered RSGI response.

            Parameters
            ----------
            *_args : object
                Status, headers, and optional body supplied by the adapter.

            Returns
            -------
            None
                The test protocol accepts the response.
            """

        def start_stream(*_args: object) -> object:
            """Return a protocol accepting asynchronous output chunks.

            Parameters
            ----------
            *_args : object
                Stream response status and headers.

            Returns
            -------
            object
                Protocol exposing an asynchronous chunk writer.
            """
            return SimpleNamespace(send_bytes=send_noop)

        async def chunks() -> AsyncIterator[bytes]:
            """Yield a single streamed output chunk.

            Yields
            ------
            bytes
                Immutable response content.
            """
            yield b"chunk"

        protocol = SimpleNamespace(
            response_empty=protocol_send,
            response_bytes=protocol_send,
            response_stream=start_stream,
        )
        for interface in ("asgi", "rsgi"):
            for method, kind in (("HEAD", "body"), ("GET", "body"), ("GET", "stream")):
                adapter = ASGITransportAdapter(make_asgi_scope("/", method))
                content = chunks() if kind == "stream" else b"body"
                response = _HookResponse(content)
                response.calls = 0
                if interface == "asgi":
                    await ASGIResponseAdapter().send(
                        adapter, response, receive_empty, send_noop,
                    )
                else:
                    await RSGIResponseAdapter().send(adapter, response, protocol)
                self.assertEqual(response.calls, 1)

    async def testBodyAndScopeAreCreatedOnlyWhenRead(self) -> None:
        """Defer transport scope and body creation while preserving replay.

        Returns
        -------
        None
            Lazy allocation and one transport body read are asserted.
        """
        reads = []

        async def receive() -> dict:
            """Return one complete body message.

            Returns
            -------
            dict
                ASGI request body message.
            """
            reads.append(1)
            return {"type": "http.request", "body": b"payload", "more_body": False}

        adapter = _CountingAdapter(make_asgi_scope("/lazy"))
        request = Request(Interface.ASGI, adapter, receive_or_protocol=receive)
        self.assertEqual(adapter.calls, 0)
        self.assertIsNone(request._Request__body_stream)
        self.assertEqual(request.path, "/lazy")
        self.assertEqual(request.scope["path"], "/lazy")
        self.assertEqual(adapter.calls, 1)
        self.assertEqual(await request.body(), b"payload")
        self.assertEqual(await request.body(), b"payload")
        self.assertEqual(reads, [1])

    def testTemplateOwnsHeadersAndCreatesIsolatedResponses(self) -> None:
        """Share only immutable data between responses created from a template.

        Returns
        -------
        None
            Cookie, header, body, and template isolation are asserted.
        """
        source = {"X-Static": "original", "Set-Cookie": "a=1", "set-cookie": "b=2"}
        template = ResponseTemplate(b"payload", headers=source)
        source["X-Static"] = "changed"
        first, second = template.make(), template.make()
        self.assertIs(first.getBody(), second.getBody())
        first.setHeader("x-static", "request-one")
        first.setCookie("personal", "one")
        self.assertEqual(second.getHeader("x-static"), ["original"])
        self.assertEqual(second.getHeader("set-cookie"), ["a=1", "b=2"])
        self.assertIsNone(second.background)
        with self.assertRaises(FrozenInstanceError):
            template.body = b"changed"

    def testTemplateRawHeadersRespectEveryMutationPath(self) -> None:
        """Keep encoded headers synchronized with list and method mutations.

        Returns
        -------
        None
            Mutated data cannot affect cached template bytes.
        """
        template = ResponseTemplate(headers={"X-One": "a", "X-Two": "b"})
        response = template.make()
        raw = response.getRawHeaders()
        raw.append((b"injected", b"value"))
        self.assertFalse(response.hasHeader("injected"))
        response.setHeader("server", "Orionis ASGI")
        self.assertEqual(response.getRawHeaders()[-1], (b"server", b"Orionis ASGI"))
        response.getHeader("x-one").append("c")
        self.assertEqual(
            response.getRawHeaders()[:2], [(b"x-one", b"a"), (b"x-one", b"c")],
        )
        response.removeHeader("x-two")
        response.addHeader("x-one", "d")
        response.setHeader("x-one", "replaced")
        self.assertEqual(response.getRawHeaders(), [
            (b"x-one", b"replaced"), (b"server", b"Orionis ASGI"),
        ])
        self.assertEqual(
            template.make().getRawHeaders(), [(b"x-one", b"a"), (b"x-two", b"b")],
        )

    async def testConcurrentNextCannotSkipSuspendedMiddleware(self) -> None:
        """Reject duplicate next while a downstream middleware is suspended.

        Returns
        -------
        None
            Exactly one ordered middleware chain reaches the terminal.
        """
        entered, release = asyncio.Event(), asyncio.Event()
        terminals = []

        async def terminal() -> Response:
            """Record terminal dispatch.

            Returns
            -------
            Response
                Successful terminal response.
            """
            terminals.append(1)
            return Response(b"done")

        async def inner(
            _request: Request, call_next: Callable[[], Awaitable[Response]],
        ) -> Response:
            """Suspend before advancing to the terminal.

            Parameters
            ----------
            _request : Request
                Current request.
            call_next : Callable[[], Awaitable[Response]]
                Terminal continuation.

            Returns
            -------
            Response
                Terminal response after release.
            """
            entered.set()
            await release.wait()
            return await call_next()

        async def outer(
            _request: Request, call_next: Callable[[], Awaitable[Response]],
        ) -> Response:
            """Race a duplicate continuation against the waiting inner layer.

            Parameters
            ----------
            _request : Request
                Current request.
            call_next : Callable[[], Awaitable[Response]]
                Inner middleware continuation.

            Returns
            -------
            Response
                The first continuation's response.
            """
            first = asyncio.create_task(call_next())
            await entered.wait()
            try:
                with self.assertRaises(RuntimeError):
                    await call_next()
                self.assertEqual(terminals, [])
            finally:
                release.set()
                result = await first
            return result

        pipeline = kernel_module._MiddlewarePipeline(
            (SimpleNamespace(handle=outer), SimpleNamespace(handle=inner)),
            None, terminal,
        )
        self.assertEqual((await pipeline()).getBody(), b"done")
        self.assertEqual(terminals, [1])

class TestPublicRouteProfile(TestCase):
    """Exercise stateless profiles without weakening existing route defaults."""

    def testPublicProfileSurvivesCompilerAndCache(self) -> None:
        """Persist an explicitly public profile through route compilation.

        Returns
        -------
        None
            Metadata survives cache serialization and restoration.
        """
        route = FluentRoute("GET", "/public", web_handler).public()
        compiled, fallback = RouteCompiler().compile([route.export()], None)
        cache = RouteCache()
        restored, _ = cache.fromCache(cache.toCache(compiled, fallback))
        self.assertTrue(restored["GET"]["static"]["/public"].public)
        self.assertFalse(FluentRoute("GET", "/default", web_handler).export()["public"])

    def testNestedGroupsRespectExplicitChildProfile(self) -> None:
        """Apply public group defaults while retaining explicit child choices.

        Returns
        -------
        None
            Nested and explicit route profile precedence is asserted.
        """
        router = Router(SimpleNamespace(routeHealthCheck="/health"))
        ordinary = router.get("/ordinary", web_handler)
        protected = router.get("/protected", web_handler).public(enabled=False)
        inner = router.group(routes=[ordinary, protected], public=True)
        router.group(prefix="/outer", routes=[inner], public=False)
        self.assertTrue(ordinary.export()["public"])
        self.assertFalse(protected.export()["public"])
        with self.assertRaises(TypeError):
            ordinary.public(enabled="yes")
        with self.assertRaises(TypeError):
            router.group(routes=[ordinary], public="yes")

    async def testPublicRouteSkipsContextButKeepsRouteMiddleware(self) -> None:
        """Omit web or API context only for explicitly public routes.

        Returns
        -------
        None
            Route middleware still runs and request scope stays available.
        """
        for kind in ("web", "api"):
            route = replace(make_route(
                "/public", kind=kind, function="web_handler",
                middlewares=(_RecordingMiddleware,),
            ), public=True)
            routes = {"GET": {"static": {"/public": route}, "dynamic": []}}
            kernel, app, _, _ = await boot_kernel(routes=routes, csrf_enabled=True)
            _RecordingMiddleware.calls = [] # NOSONAR
            _SessionMiddlewareDouble.calls = [] # NOSONAR
            result = await dispatch(kernel, "/public")
            self.assertEqual(result.getBody(), b"web")
            self.assertEqual(result.getHeader("x-route-middleware"), ["1"])
            self.assertEqual(_RecordingMiddleware.calls, ["/public"])
            self.assertEqual(_SessionMiddlewareDouble.calls, [])
            self.assertIsInstance(app.scopes[-1].entries[Request], Request)
            self.assertFalse(hasattr(app.scopes[-1].entries[Request].state, "identity"))

    async def testPublicGroupKeepsApplicationMiddleware(self) -> None:
        """Retain explicitly registered application middleware for public groups.

        Returns
        -------
        None
            The compiled application layer executes for a public child route.
        """
        router = Router(SimpleNamespace(routeHealthCheck="/health"))
        route = router.get("/public", web_handler)
        router.group(routes=[route], public=True)
        routes, _ = RouteCompiler().compile(
            [route.export()], None, app_middleware=[_RecordingMiddleware],
        )
        kernel, _, _, _ = await boot_kernel(routes=routes)
        _RecordingMiddleware.calls = [] # NOSONAR
        result = await dispatch(kernel, "/public")
        self.assertEqual(result.getHeader("x-route-middleware"), ["1"])
        self.assertEqual(_RecordingMiddleware.calls, ["/public"])

    async def testPublicRouteStillRejectsInvalidHeaders(self) -> None:
        """Run global security checks before the public route pipeline.

        Returns
        -------
        None
            Malformed headers are rejected with HTTP 400.
        """
        route = replace(make_route("/public", function="web_handler"), public=True)
        routes = {"GET": {"static": {"/public": route}, "dynamic": []}}
        kernel, _, _, _ = await boot_kernel(routes=routes)
        result = await dispatch(kernel, "/public", headers=[(b"x", b"bad\r\n")])
        self.assertEqual(result.getStatusCode(), 400)

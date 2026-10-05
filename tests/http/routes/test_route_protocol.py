import json
from typing import TYPE_CHECKING
from orionis.http.routes.enums.protocols import RouteProtocol
from orionis.http.routes.enums.route_types import RouteType
from orionis.http.routes.exceptions.method_not_allowed import MethodNotAllowed
from orionis.http.routes.exceptions.route_not_found import RouteNotFound
from orionis.http.routes.route_cache import RouteCache
from orionis.http.routes.route_compiler import RouteCompiler
from orionis.http.routes.route_resolver import RouteResolver
from orionis.http.websocket_middleware import WebSocketMiddleware
from orionis.test import TestCase
from tests.http.routes.test_nested_routing import (
    UserController,
    compile_router,
    make_router,
    route_handler,
)

if TYPE_CHECKING:
    from orionis.http.websocket import WebSocket
    from orionis.http.websocket_middleware import WebSocketNext

class _SocketMiddleware(WebSocketMiddleware):
    """Provide importable connection middleware for route cache coverage."""

    __slots__ = ()

    async def handle(self, socket: WebSocket, call_next: WebSocketNext) -> None:
        """
        Run the next connection handler without modifying its socket.

        Parameters
        ----------
        socket : WebSocket
            Connection passed through without modification.
        call_next : WebSocketNext
            Next connection handler in the middleware pipeline.

        Returns
        -------
        None
            Await completion of the next handler.
        """
        del socket
        await call_next()

class TestRouteProtocol(TestCase):
    """Verify protocol isolation through compilation, resolution and caching."""

    def testProtocolsAllowTheSamePathAndPreserveActionKinds(self) -> None:
        """
        Resolve HTTP and socket handlers independently for one URL.

        Returns
        -------
        None
            Verify protocol-specific action types, HEAD resolution and OPTIONS.
        """
        router = make_router()
        router.get("/shared", route_handler)
        router.websocket("/shared", [UserController, "index"])
        resolver = RouteResolver(compile_router(router))
        http = resolver.resolve("GET", "/shared").route
        socket = resolver.resolve("WEBSOCKET", "/shared").route
        self.assertIs(http.protocol, RouteProtocol.HTTP)
        self.assertIs(socket.protocol, RouteProtocol.WEBSOCKET)
        self.assertIs(http.type, RouteType.FUNCTION)
        self.assertIs(socket.type, RouteType.CONTROLLER)
        self.assertEqual(resolver.options("/shared"), ["GET", "HEAD", "OPTIONS"])
        self.assertIs(resolver.resolve("HEAD", "/shared").route, http)

    def testSocketRoutesNeverParticipateInHttpMethodResolution(self) -> None:
        """
        Keep OPTIONS and method-not-allowed responses scoped to HTTP.

        Returns
        -------
        None
            Verify socket routes never participate in HTTP method resolution.
        """
        router = make_router()
        router.websocket("/socket", route_handler)
        router.websocket("/rooms/{room:int}", route_handler)
        router.get("/http", route_handler)
        router.get("/users/{user:int}", route_handler)
        resolver = RouteResolver(compile_router(router))
        for path in ("/socket", "/rooms/12"):
            with self.subTest(path=path):
                self.assertEqual(resolver.options(path), [])
                for method in ("GET", "HEAD", "POST", "OPTIONS"):
                    with self.assertRaises(RouteNotFound):
                        resolver.resolve(method, path)
        for path in ("/http", "/users/12"):
            with self.subTest(path=path):
                with self.assertRaises(RouteNotFound):
                    resolver.resolve("WEBSOCKET", path)
                with self.assertRaises(MethodNotAllowed):
                    resolver.resolve("POST", path)

    def testDynamicSocketRoutesPreserveParametersAndMiddleware(self) -> None:
        """
        Compile grouped socket parameters and connection middleware.

        Returns
        -------
        None
            Verify converted parameters, middleware and cached resolution.
        """
        router = make_router()
        router.group(
            prefix="/rooms/{room:int}",
            middleware=[_SocketMiddleware],
            routes=[router.websocket("/events/{topic}", route_handler)],
        )
        resolver = RouteResolver(compile_router(router))
        resolved = resolver.resolve("WEBSOCKET", "/rooms/7/events/news")
        self.assertEqual(resolved.params, {"room": 7, "topic": "news"})
        self.assertEqual(resolved.route.compiled_middlewares, (_SocketMiddleware,))
        self.assertIs(
            resolver.resolve("WEBSOCKET", "/rooms/7/events/news"), resolved,
        )

    def testCacheRestoresExplicitProtocolAndIsolatesSocketRoutes(self) -> None:
        """
        Preserve protocol, converters and connection middleware through JSON.

        Returns
        -------
        None
            Verify restored socket routes retain metadata and HTTP isolation.
        """
        router = make_router()
        router.websocket("/socket/{room:int}", route_handler).middleware(
            _SocketMiddleware,
        )
        cache = RouteCache()
        snapshot = json.loads(json.dumps(cache.toCache(compile_router(router), None)))
        restored, fallback = cache.fromCache(snapshot)
        self.assertIsNone(fallback)
        resolver = RouteResolver(restored)
        resolved = resolver.resolve("WEBSOCKET", "/socket/4")
        self.assertIs(resolved.route.protocol, RouteProtocol.WEBSOCKET)
        self.assertEqual(resolved.params, {"room": 4})
        self.assertEqual(resolved.route.compiled_middlewares, (_SocketMiddleware,))
        self.assertEqual(resolver.options("/socket/4"), [])
        with self.assertRaises(RouteNotFound):
            resolver.resolve("GET", "/socket/4")

    def testCacheRejectsIncompatibleVersionsAndMissingProtocol(self) -> None:
        """
        Require an explicit compatible schema before restoring any routes.

        Returns
        -------
        None
            Verify incompatible versions and missing protocols are rejected.
        """
        cache = RouteCache()
        for version in (None, 1, 2, RouteCache.VERSION + 1, float(RouteCache.VERSION)):
            with self.subTest(version=version), self.assertRaises(ValueError):
                cache.fromCache({"version": version, "routes": {}})
        router = make_router()
        router.websocket("/socket", route_handler)
        snapshot = cache.toCache(compile_router(router), None)
        del snapshot["routes"]["WEBSOCKET"]["static"]["/socket"]["protocol"]
        with self.assertRaises(KeyError):
            cache.fromCache(snapshot)
        snapshot["routes"]["WEBSOCKET"]["static"]["/socket"]["protocol"] = "http"
        with self.assertRaises(ValueError):
            cache.fromCache(snapshot)

    def testCacheRejectsContradictoryDispatchBuckets(self) -> None:
        """
        Prevent valid socket metadata from masquerading as an HTTP entry.

        Returns
        -------
        None
            Verify contradictory protocol, path and dispatch buckets are rejected.
        """
        router = make_router()
        router.websocket("/socket", route_handler)
        cache = RouteCache()
        snapshot = cache.toCache(compile_router(router), None)
        socket_route = snapshot["routes"]["WEBSOCKET"]["static"].pop("/socket")
        snapshot["routes"]["GET"]["static"]["/socket"] = socket_route
        with self.assertRaises(ValueError):
            cache.fromCache(snapshot)
        del snapshot["routes"]["GET"]["static"]["/socket"]
        snapshot["routes"]["WEBSOCKET"]["static"]["/other"] = socket_route
        with self.assertRaises(ValueError):
            cache.fromCache(snapshot)
        snapshot["routes"]["WEBSOCKET"]["static"].clear()
        snapshot["routes"]["WEBSOCKET"]["dynamic"].append(socket_route)
        with self.assertRaises(ValueError):
            cache.fromCache(snapshot)

    def testCacheRejectsMissingRequiredEnvelopeFields(self) -> None:
        """
        Avoid silently restoring an empty registry from an incomplete cache.

        Returns
        -------
        None
            Verify required cache envelope fields cannot be omitted.
        """
        cache = RouteCache()
        for field in ("routes", "fallback"):
            snapshot = cache.toCache({}, None)
            del snapshot[field]
            with self.subTest(field=field), self.assertRaises(KeyError):
                cache.fromCache(snapshot)

    def testCompilerRejectsInconsistentProtocolMetadata(self) -> None:
        """
        Prevent a transport marker from contradicting its dispatch table.

        Returns
        -------
        None
            Verify compilation rejects inconsistent protocol metadata.
        """
        router = make_router()
        route = router.websocket("/socket", route_handler).export()
        route["protocol"] = RouteProtocol.HTTP
        with self.assertRaises(ValueError):
            RouteCompiler().compile([route], None)

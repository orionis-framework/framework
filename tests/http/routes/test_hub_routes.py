import json
from typing import cast
from orionis.http.routes.enums.protocols import RouteProtocol
from orionis.http.routes.enums.route_types import RouteType
from orionis.http.routes.exceptions.route_not_found import RouteNotFound
from orionis.http.routes.route_cache import RouteCache
from orionis.http.routes.route_resolver import RouteResolver
from orionis.realtime.hub import Hub
from orionis.test import TestCase
from tests.http.routes.test_nested_routing import (
    compile_router,
    make_router,
    route_handler,
)
from tests.http.routes.test_route_protocol import _SocketMiddleware


class _ChatHub(Hub):
    """Provide an importable Hub class for route compilation and caching."""

    __slots__ = ()


class TestHubRoutes(TestCase):
    """Cover Hub action metadata without importing RPC into raw routing paths."""

    def testHubRouteDefaultsToJsonAndPreservesGroupMetadata(self) -> None:
        """
        Carry converted route parameters and socket middleware into Hub routes.

        Returns
        -------
        None
            Verify Hub metadata, parameter conversion and HTTP isolation.
        """
        router = make_router()
        router.group(
            prefix="/org/{organization:int}",
            middleware=[_SocketMiddleware],
            routes=[router.hub("/chat", _ChatHub).name("chat")],
        )
        resolver = RouteResolver(compile_router(router))
        resolved = resolver.resolve("WEBSOCKET", "/org/4/chat")
        self.assertEqual(resolved.params, {"organization": 4})
        self.assertIs(resolved.route.type, RouteType.HUB)
        self.assertIs(resolved.route.protocol, RouteProtocol.WEBSOCKET)
        self.assertEqual(resolved.route.hub_protocol, "json")
        self.assertEqual(resolved.route.action, {
            "module": __name__, "class": "_ChatHub",
        })
        self.assertEqual(resolved.route.compiled_middlewares, (_SocketMiddleware,))
        self.assertEqual(resolver.options("/org/4/chat"), [])
        with self.assertRaises(RouteNotFound):
            resolver.resolve("GET", "/org/4/chat")

    def testHubCodecAndHandlerMetadataSurviveRouteCache(self) -> None:
        """
        Restore both supported Hub codecs through a JSON cache round trip.

        Returns
        -------
        None
            Verify codec preservation and rejection of invalid cached codecs.
        """
        for protocol in ("json", "msgpack"):
            with self.subTest(protocol=protocol):
                router = make_router()
                router.hub("/chat", _ChatHub, protocol=protocol)
                cache = RouteCache()
                snapshot = json.loads(json.dumps(cache.toCache(
                    compile_router(router), None,
                )))
                restored, _ = cache.fromCache(snapshot)
                route = RouteResolver(restored).resolve("WEBSOCKET", "/chat").route
                self.assertIs(route.type, RouteType.HUB)
                self.assertIs(route.protocol, RouteProtocol.WEBSOCKET)
                self.assertEqual(route.hub_protocol, protocol)
                self.assertEqual(route.action["class"], "_ChatHub")
                snapshot["routes"]["WEBSOCKET"]["static"]["/chat"][
                    "hub_protocol"
                ] = "invalid"
                with self.assertRaises(ValueError):
                    cache.fromCache(snapshot)

    def testInvalidHubRegistrationDoesNotLeaveAnIncompleteRoute(self) -> None:
        """
        Reject unsupported classes and codecs before mutating the router.

        Returns
        -------
        None
            Verify failed registration leaves the route collection unchanged.
        """
        router = make_router()
        count = len(router.export()["routes"])
        for hub in (object, route_handler, _ChatHub()):
            with self.subTest(hub=hub), self.assertRaises(TypeError):
                router.hub("/chat", cast("type[Hub]", hub))
        for protocol in ("signalr", "JSON", "", None):
            with self.subTest(protocol=protocol), self.assertRaises(ValueError):
                router.hub("/chat", _ChatHub, protocol=cast("str", protocol))
        self.assertEqual(len(router.export()["routes"]), count)

    def testRawAndHubEndpointsConflictWithinOneSocketNamespace(self) -> None:
        """
        Reject ambiguous Hub/raw registrations while allowing parallel HTTP.

        Returns
        -------
        None
            Verify socket namespace conflicts do not prohibit HTTP coexistence.
        """
        router = make_router()
        router.get("/chat", route_handler)
        router.hub("/chat", _ChatHub)
        compile_router(router)
        router.websocket("/chat", route_handler)
        with self.assertRaises(ValueError):
            compile_router(router)

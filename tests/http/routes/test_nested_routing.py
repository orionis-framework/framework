from __future__ import annotations
import asyncio
from types import SimpleNamespace
from typing import TYPE_CHECKING
from orionis.http.middleware import BaseMiddleware
from orionis.http.responses import Response
from orionis.http.routes.fluent import FluentRoute
from orionis.http.routes.group import RouteGroup
from orionis.http.routes.route_cache import RouteCache
from orionis.http.routes.route_compiler import RouteCompiler
from orionis.http.routes.route_resolver import RouteResolver
from orionis.http.routes.router import Router
from orionis.support.facades.router import Route
from orionis.test import TestCase
from tests.http._support import replace_attribute
from tests.http.test_kernel import boot_kernel, dispatch

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from orionis.http.request import Request

def route_handler() -> Response:
    """Return the terminal response for routing integration tests."""
    return Response(content="routed")

class UserController:
    """Provide both controller-action and invokable route fixtures."""

    def index(self) -> Response:
        """Return a successful controller response."""
        return route_handler()

    def __call__(self) -> Response:
        """Return a successful invokable response."""
        return route_handler()

class ChildController(UserController):
    """Inherit the invokable action from a parent controller."""

class OneMiddleware(BaseMiddleware):
    """Record middleware nesting on the request itself."""

    async def handle(
        self,
        request: Request,
        call_next: Callable[[], Awaitable[Response]],
    ) -> Response:
        """Record entry and exit around the downstream response."""
        trace = getattr(request.state, "routingTrace", None)
        if trace is None:
            trace = []
            request.state.routingTrace = trace
        trace.append("+" + type(self).__name__)
        await asyncio.sleep(0)
        response = await call_next()
        trace.append("-" + type(self).__name__)
        response.setHeader("x-trace", ",".join(trace))
        return response

class TwoMiddleware(OneMiddleware):
    """Mark the second middleware layer."""

class ThreeMiddleware(OneMiddleware):
    """Mark the third middleware layer."""

class FourMiddleware(OneMiddleware):
    """Mark the fourth middleware layer."""

class Namespace:
    """Group nested importable fixtures."""

    class Controller(UserController):
        """Expose a nested controller with inherited actions."""

    class Middleware(OneMiddleware):
        """Expose a nested middleware class for cache restoration."""

def make_router() -> Router:
    """Build a router with the same default routes as an application."""
    return Router(SimpleNamespace(routeHealthCheck="/up"))

def compile_router(router: Router, middleware: list | None = None) -> dict:
    """Compile the exported routes through the production compiler."""
    exported = router.export()
    compiled, _ = RouteCompiler().compile(
        exported["routes"],
        exported["fallback"],
        middleware,
    )
    return compiled

class TestNestedRouting(TestCase):
    """Exercise composition through the public router and fluent APIs."""

    def testSimpleRoutesAndExistingVerbs(self) -> None:
        """Keep every existing registration method and fluent name working."""
        router = make_router()
        for verb in ("get", "post", "put", "patch", "delete", "query"):
            route = getattr(router, verb)("/users", [UserController, "index"])
            self.assertIs(route.name(f"users.{verb}"), route)
        resolver = RouteResolver(compile_router(router))
        for method in ("GET", "POST", "PUT", "PATCH", "DELETE", "QUERY"):
            self.assertEqual(resolver.resolve(method, "/users").route.method, method)
        self.assertEqual(resolver.resolve("HEAD", "/users").route.method, "GET")
        self.assertEqual(
            resolver.options("/users"),
            ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT", "QUERY"],
        )

    def testLegacySingleMiddlewareGroup(self) -> None:
        """Keep the existing login-style registration expression valid."""
        router = make_router()
        group = router.group(
            middleware=OneMiddleware,
            routes=[
                router.get("/login", [UserController, "index"]),
                router.post("/login", [UserController, "index"]).name("login"),
            ],
        )
        self.assertIsInstance(group, RouteGroup)
        resolver = RouteResolver(compile_router(router))
        for method in ("GET", "POST"):
            route = resolver.resolve(method, "/login").route
            self.assertEqual(route.compiled_middlewares, (OneMiddleware,))
        self.assertEqual(resolver.resolve("POST", "/login").route.name, "login")

    def testNestedPrefixAndMiddlewareInheritance(self) -> None:
        """Flatten parent context before child context and local middleware."""
        router = make_router()
        leaf = router.get("/index", route_handler).middleware(FourMiddleware)
        router.group(
            prefix="admin",
            middleware=[OneMiddleware, TwoMiddleware],
            routes=[
                router.group(prefix="users", middleware=ThreeMiddleware, routes=[leaf]),
            ],
        )
        route = (
            RouteResolver(compile_router(router))
            .resolve(
                "GET",
                "/admin/users/index",
            )
            .route
        )
        self.assertEqual(
            route.compiled_middlewares,
            (
                OneMiddleware,
                TwoMiddleware,
                ThreeMiddleware,
                FourMiddleware,
            ),
        )
        self.assertEqual(leaf.path, "/admin/users/index")

    def testThreeLevelsAndNamedPostRoute(self) -> None:
        """Keep names and methods while composing at least three levels."""
        router = make_router()
        router.group(
            prefix="api",
            routes=[
                router.group(
                    prefix="v1",
                    routes=[
                        router.group(
                            prefix="admin",
                            routes=[
                                router.post("/users", route_handler).name(
                                    "user.create",
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
        route = (
            RouteResolver(compile_router(router))
            .resolve(
                "POST",
                "/api/v1/admin/users",
            )
            .route
        )
        self.assertEqual(route.name, "user.create")
        self.assertEqual(route.compiled_middlewares, ())

    def testDepthDoesNotDependOnPythonRecursion(self) -> None:
        """Compose more levels than Python's normal recursion limit."""
        router = make_router()
        member = router.get("/leaf", route_handler)
        for _ in range(1100):
            member = router.group(prefix="x", routes=[member])
        path = "/x" * 1100 + "/leaf"
        self.assertEqual(
            RouteResolver(compile_router(router))
            .resolve(
                "GET",
                path,
            )
            .route.path,
            path,
        )

    def testAllPrefixSpellingsAndRootPaths(self) -> None:
        """Canonicalize group boundaries once, including whitespace and root."""
        for prefix in ("admin", "/admin", "admin/", "/admin/", " //admin// "):
            with self.subTest(prefix=prefix):
                router = make_router()
                router.group(
                    prefix=prefix,
                    routes=[
                        router.group(
                            prefix="/users/",
                            routes=[
                                router.get("//index//", route_handler),
                                router.post("/", route_handler),
                            ],
                        ),
                    ],
                )
                resolver = RouteResolver(compile_router(router))
                self.assertEqual(
                    resolver.resolve("GET", "/admin/users/index").params, {},
                )
                self.assertEqual(resolver.resolve("POST", "/admin/users").params, {})

    def testGroupsWithoutPrefixesOrMiddleware(self) -> None:
        """Accept optional context and preserve ungrouped sibling routes."""
        for prefix in (None, "", "/", " /// "):
            with self.subTest(prefix=prefix):
                router = make_router()
                router.get("/outside", route_handler)
                router.group(
                    prefix=prefix,
                    routes=[
                        router.group(routes=[router.get("/inside", route_handler)]),
                    ],
                )
                resolver = RouteResolver(compile_router(router))
                for path in ("/outside", "/inside"):
                    self.assertEqual(resolver.resolve("GET", path).route.path, path)

    def testExclusionsAndDeduplicationUseFinalOrder(self) -> None:
        """Apply exclusions after app, parent, child and route composition."""
        router = make_router()
        router.group(
            middleware=[OneMiddleware, TwoMiddleware],
            routes=[
                router.group(
                    middleware=(TwoMiddleware, ThreeMiddleware),
                    routes=[
                        router.get("/guarded", route_handler)
                        .middleware(
                            FourMiddleware,
                            OneMiddleware,
                        )
                        .withOutMiddleware(ThreeMiddleware),
                    ],
                    without_middleware=TwoMiddleware,
                ),
            ],
        )
        route = (
            RouteResolver(compile_router(router, [FourMiddleware]))
            .resolve(
                "GET",
                "/guarded",
            )
            .route
        )
        self.assertEqual(route.compiled_middlewares, (FourMiddleware, OneMiddleware))

    def testGroupExcludesRouteMiddleware(self) -> None:
        """Parent exclusions also remove middleware attached directly to leaves."""
        router = make_router()
        router.group(
            without_middleware=[OneMiddleware],
            routes=[
                router.get("/open", route_handler).middleware(OneMiddleware),
            ],
        )
        self.assertEqual(
            RouteResolver(compile_router(router))
            .resolve(
                "GET",
                "/open",
            )
            .route.compiled_middlewares,
            (),
        )

    def testSetMiddlewareHasStableImportNameOrder(self) -> None:
        """Keep set and frozenset compatibility with repeatable ordering."""
        for middleware in (
            {TwoMiddleware, OneMiddleware},
            frozenset({TwoMiddleware, OneMiddleware}),
        ):
            router = make_router()
            router.group(
                middleware=middleware, routes=[router.get("/x", route_handler)],
            )
            self.assertEqual(
                RouteResolver(compile_router(router))
                .resolve(
                    "GET",
                    "/x",
                )
                .route.compiled_middlewares,
                (OneMiddleware, TwoMiddleware),
            )

    def testFacadeSupportsTheNestedExpression(self) -> None:
        """Forward the public Route facade to nested Router.group calls."""
        router = make_router()
        with replace_attribute(Route, "_pinned_instance", router):
            Route.group(
                prefix="admin",
                routes=[
                    Route.group(
                        prefix="users",
                        routes=[
                            Route.get("/index", [UserController, "index"]).name(
                                "users",
                            ),
                        ],
                    ),
                ],
            )
        self.assertEqual(
            RouteResolver(compile_router(router))
            .resolve(
                "GET",
                "/admin/users/index",
            )
            .route.name,
            "users",
        )

    def testInvalidGroupsDoNotPartiallyApplyContext(self) -> None:
        """Validate the whole group before mutating any already registered leaf."""
        for options in (
            {"prefix": False},
            {"prefix": 0},
            {"middleware": False},
            {"middleware": [OneMiddleware, object]},
            {"without_middleware": 0},
        ):
            with self.subTest(options=options):
                router = make_router()
                route = router.get("/valid", route_handler)
                with self.assertRaises(ValueError):
                    router.group(routes=[route], **options)
                self.assertEqual(route.path, "/valid")
                self.assertEqual(route.export()["middleware"], [])
        router = make_router()
        route = router.get("/valid", route_handler)
        with self.assertRaises(TypeError):
            router.group(prefix="bad", routes=[route, None])
        self.assertEqual(route.path, "/valid")

    def testInvalidMembershipAndDuplicates(self) -> None:
        """Reject empty groups, invalid containers and ambiguous shared leaves."""
        router = make_router()
        for routes in (None, [], (), [RouteGroup(())]):
            with self.subTest(routes=routes), self.assertRaises(ValueError):
                router.group(routes=routes)
        for routes in ("routes", {"route": route_handler}, [42]):
            with self.subTest(routes=routes), self.assertRaises(TypeError):
                router.group(routes=routes)
        route = router.get("/once", route_handler)
        group = router.group(routes=[route])
        with self.assertRaises(ValueError):
            router.group(prefix="bad", routes=[group, route])
        self.assertEqual(route.path, "/once")

    def testExternalRoutesAndTupleMembershipRemainSupported(self) -> None:
        """Register standalone fluent routes supplied through a group."""
        router = make_router()
        router.group(routes=(FluentRoute("GET", "/x", route_handler),))
        self.assertEqual(
            RouteResolver(compile_router(router)).resolve("GET", "/x").params, {},
        )

    def testSiblingGroupsCanStartWithTheSameRelativePath(self) -> None:
        """Defer path collision checks until all group prefixes are known."""
        router = make_router()
        for prefix in ("one", "two"):
            router.group(prefix=prefix, routes=[router.get("/index", route_handler)])
        resolver = RouteResolver(compile_router(router))
        for path in ("/one/index", "/two/index"):
            self.assertEqual(resolver.resolve("GET", path).route.path, path)

    def testDefaultOverrideDoesNotDeleteAPrefixedRoute(self) -> None:
        """Keep a former default path after its fluent route has been prefixed."""
        router = make_router()
        router.get("/robots.txt", route_handler).prefix("admin")
        router.get("/robots.txt/", route_handler)
        resolver = RouteResolver(compile_router(router))
        for path in ("/robots.txt", "/admin/robots.txt"):
            self.assertEqual(resolver.resolve("GET", path).route.path, path)

    def testCompiledStackIsIndependentOfFurtherBuilderMutation(self) -> None:
        """Freeze dispatch middleware even when a builder is subsequently changed."""
        router = make_router()
        leaf = router.get("/x", route_handler).middleware(OneMiddleware)
        resolver = RouteResolver(compile_router(router))
        leaf.middleware(TwoMiddleware)
        route = resolver.resolve("GET", "/x").route
        self.assertEqual(route.compiled_middlewares, (OneMiddleware,))
        self.assertEqual(route.middleware, [OneMiddleware])

class TestNestedRoutingExecution(TestCase):
    """Run compiled groups through the real HTTP kernel and its middleware."""

    async def testConcurrentRequestsKeepMiddlewareOrderAndLocalState(self) -> None:
        """Execute parent-first stacks and unwind without sharing request state."""
        router = make_router()
        router._setKind("api")
        router.group(
            prefix="admin",
            middleware=[OneMiddleware, TwoMiddleware],
            routes=[
                router.group(
                    prefix="users",
                    middleware=[ThreeMiddleware, FourMiddleware],
                    routes=[
                        router.get("/index", [UserController, "index"]),
                    ],
                ),
            ],
        )
        kernel, _, _, _ = await boot_kernel(routes=compile_router(router))
        responses = await asyncio.gather(
            *(dispatch(kernel, "/admin/users/index") for _ in range(8)),
        )
        expected = (
            "+OneMiddleware,+TwoMiddleware,+ThreeMiddleware,+FourMiddleware,"
            "-FourMiddleware,-ThreeMiddleware,-TwoMiddleware,-OneMiddleware"
        )
        for response in responses:
            self.assertEqual(response.getHeader("x-trace"), [expected])

    async def testCachedNestedControllersMiddlewareAndFallbackExecute(self) -> None:
        """Restore nested import names and dispatch inherited invokable actions."""
        router = make_router()
        router._setKind("api")
        router.group(
            prefix="nested",
            middleware=Namespace.Middleware,
            routes=[
                router.get("/controller", [Namespace.Controller, "index"]),
                router.get("/invokable", ChildController),
            ],
        )
        router.fallback(ChildController)
        cache = RouteCache()
        compiled, fallback = cache.fromCache(
            cache.toCache(
                compile_router(router),
                router.export()["fallback"],
            ),
        )
        kernel, _, _, catch = await boot_kernel(routes=compiled, fallback=fallback)
        for path in ("/nested/controller", "/nested/invokable", "/missing"):
            response = await dispatch(kernel, path)
            self.assertEqual(response.getStatusCode(), 200)
        self.assertEqual(catch.handled, [])

from operator import setitem
from uuid import UUID
from orionis.http.routes.exceptions.method_not_allowed import MethodNotAllowed
from orionis.http.routes.exceptions.route_not_found import RouteNotFound
from orionis.http.routes.fluent import FluentRoute
from orionis.http.routes.route_compiler import RouteCompiler
from orionis.http.routes.route_resolver import RouteResolver
from orionis.test import TestCase
from tests.http.routes.test_nested_routing import (
    UserController,
    compile_router,
    make_router,
    route_handler,
)

class TestRouteResolverBehavior(TestCase):
    """Cover dynamic indexes, precedence, failure paths and cache isolation."""

    def testParameterizedGroupPrefixes(self) -> None:
        """Compile inherited path parameters along with local parameters."""
        router = make_router()
        router.group(
            prefix="org/{org:int}",
            routes=[
                router.group(
                    prefix="users",
                    routes=[
                        router.get("/{user:int}", route_handler),
                    ],
                ),
            ],
        )
        resolver = RouteResolver(compile_router(router))
        self.assertEqual(
            resolver.resolve("GET", "/org/3/users/7").params,
            {
                "org": 3,
                "user": 7,
            },
        )

    def testSupportedConverters(self) -> None:
        """Convert every built-in placeholder type using the real matcher."""
        router = make_router()
        for kind in ("str", "int", "slug", "uuid"):
            router.get(f"/{kind}/{{value:{kind}}}", route_handler)
        resolver = RouteResolver(compile_router(router))
        uuid_value = "12345678-1234-1234-1234-123456789abc"
        for kind, raw, expected in (
            ("str", "Any-Text", "Any-Text"),
            ("int", "42", 42),
            ("slug", "a-slug", "a-slug"),
            ("uuid", uuid_value, UUID(uuid_value)),
        ):
            with self.subTest(kind=kind):
                self.assertEqual(
                    resolver.resolve("GET", f"/{kind}/{raw}").params,
                    {
                        "value": expected,
                    },
                )

    def testPartitionedLookupMatchesAnOrderedReference(self) -> None:
        """Compare partitioned resolution against a simple ordered regex scan."""
        router = make_router()
        for index in range(40):
            router.get(f"/r{index}/{{id:int}}", route_handler)
            router.get(f"/r{index}/item-{{slug}}", route_handler)
            router.post(f"/r{index}/{{name}}", route_handler)
        tables = compile_router(router)
        resolver = RouteResolver(tables, hot_cache_size=0)
        for method, suffix in (("GET", "42"), ("GET", "item-test"), ("POST", "name")):
            for index in range(40):
                path = f"/r{index}/{suffix}"
                expected = next(
                    route
                    for route in tables[method]["dynamic"]
                    if route.regex.fullmatch(path)
                )
                self.assertIs(resolver.resolve(method, path).route, expected)
                self.assertEqual(
                    resolver.options(path),
                    (
                        ["GET", "HEAD", "OPTIONS", "POST"]
                        if method == "GET"
                        else ["OPTIONS", "POST"]
                    ),
                )
        with self.assertRaises(RouteNotFound):
            resolver.resolve("GET", "/missing/42")
        with self.assertRaises(MethodNotAllowed):
            resolver.resolve("DELETE", "/r39/42")

    def testWildcardFirstSegmentsPreservePriorityAndRegistrationOrder(self) -> None:
        """Use the ordered matcher whenever a leading parameter can overlap."""
        router = make_router()
        for index in range(20):
            router.get(f"/r{index}/{{id:int}}", route_handler)
        router.get("/{group}/last", route_handler).name("wildcard")
        router.get("/fixed/{slug}", route_handler).name("literal")
        router.get("/fixed/last", route_handler).name("static")
        resolver = RouteResolver(compile_router(router), hot_cache_size=0)
        self.assertEqual(resolver.resolve("GET", "/fixed/last").route.name, "static")
        self.assertEqual(resolver.resolve("GET", "/other/last").route.name, "wildcard")
        self.assertEqual(resolver.resolve("GET", "/fixed/value").route.name, "literal")
        self.assertEqual(resolver.resolve("GET", "/r19/42").params, {"id": 42})

    def testSamePrefixBucketAndMultipleDepths(self) -> None:
        """Retain route selection and extraction in large shared-prefix buckets."""
        router = make_router()
        for index in range(20):
            router.get(f"/api/r{index}/{{id:int}}", route_handler)
        router.get("/api/{id:int}", route_handler)
        resolver = RouteResolver(compile_router(router), hot_cache_size=0)
        self.assertEqual(resolver.resolve("GET", "/api/r19/12").params, {"id": 12})
        self.assertEqual(resolver.resolve("GET", "/api/13").params, {"id": 13})
        with self.assertRaises(RouteNotFound):
            resolver.resolve("GET", "/api/r19/12/extra")

    def testRecursiveLiteralBranchesPreserveRouteSelection(self) -> None:
        """Resolve nested branches whose literal prefixes have different lengths."""
        router = make_router()
        for prefix in ("v1", "version-two"):
            for index in range(24):
                router.get(f"/api/{prefix}/r{index}/{{id:int}}", route_handler)
        tables = compile_router(router)
        resolver = RouteResolver(tables, hot_cache_size=0)
        for prefix in ("v1", "version-two"):
            for index in range(24):
                path = f"/api/{prefix}/r{index}/42"
                expected = next(
                    route for route in tables["GET"]["dynamic"]
                    if route.regex.fullmatch(path)
                )
                result = resolver.resolve("GET", path)
                self.assertIs(result.route, expected)
                self.assertEqual(result.params, {"id": 42})
                self.assertEqual(resolver.options(path), ["GET", "HEAD", "OPTIONS"])
        with self.assertRaises(RouteNotFound):
            resolver.resolve("GET", "/api/v1/missing/42")

    def testMixedBranchesPreserveEqualPriorityRegistrationOrder(self) -> None:
        """Compare overlapping literal and wildcard routes with an ordered scan."""
        for position in (0, 16, 32):
            router = make_router()
            for index in range(33):
                if index == position:
                    router.get("/{group}/last", route_handler)
                if index < 32:
                    router.get(f"/r{index}/{{value}}", route_handler)
            tables = compile_router(router)
            resolver = RouteResolver(tables, hot_cache_size=0)
            for prefix in ("r0", "r15", "r31", "unknown"):
                path = f"/{prefix}/last"
                expected = next(
                    route for route in tables["GET"]["dynamic"]
                    if route.regex.fullmatch(path)
                )
                with self.subTest(position=position, path=path):
                    self.assertIs(resolver.resolve("GET", path).route, expected)
                    self.assertEqual(
                        resolver.options(path), ["GET", "HEAD", "OPTIONS"],
                    )
                    with self.assertRaises(MethodNotAllowed):
                        resolver.resolve("POST", path)
            with self.assertRaises(RouteNotFound):
                resolver.resolve("GET", "/unknown/absent")

    def testMixedPartialSegmentsAndSharedPrefixes(self) -> None:
        """Match wildcard fragments after shared prefixes and literal branches."""
        router = make_router()
        router.get("/api/{stem}-tail/end", route_handler).name("partial")
        for index in range(32):
            router.get(f"/api/r{index}-tail/{{id:int}}", route_handler)
        resolver = RouteResolver(compile_router(router), hot_cache_size=0)
        for prefix in ("r0", "r31", "unknown"):
            result = resolver.resolve("GET", f"/api/{prefix}-tail/end")
            self.assertEqual(result.route.name, "partial")
            self.assertEqual(result.params, {"stem": prefix})
        self.assertEqual(
            resolver.resolve("GET", "/api/r31-tail/42").params, {"id": 42},
        )
        with self.assertRaises(RouteNotFound):
            resolver.resolve("GET", "/api/unknown/end")

    def testManyWildcardAlternativesPreserveOrder(self) -> None:
        """Resolve dense wildcard populations against the same ordered reference."""
        router = make_router()
        for index in range(12):
            router.get(f"/{{group}}/w{index}-{{value}}", route_handler)
            router.get(f"/r{index}/{{value}}", route_handler)
        tables = compile_router(router)
        resolver = RouteResolver(tables, hot_cache_size=0)
        for prefix in ("r0", "r11", "unknown"):
            for index in range(12):
                path = f"/{prefix}/w{index}-text"
                expected = next(
                    route for route in tables["GET"]["dynamic"]
                    if route.regex.fullmatch(path)
                )
                self.assertIs(resolver.resolve("GET", path).route, expected)

    def testWrongMethodsUnknownPathsAndCanonicalRequests(self) -> None:
        """Distinguish 404 from 405 and keep implicit HEAD and path handling."""
        router = make_router()
        router.get("/fixed", route_handler)
        router.post("/items/{id:int}", route_handler)
        resolver = RouteResolver(compile_router(router))
        self.assertEqual(resolver.resolve("head", "fixed/").route.method, "GET")
        for method, path in (
            ("POST", "/fixed"),
            ("GET", "/items/1"),
            ("BREW", "/fixed"),
        ):
            with (
                self.subTest(method=method, path=path),
                self.assertRaises(MethodNotAllowed),
            ):
                resolver.resolve(method, path)
        for path in ("/unknown", "/items/bad", "/items/1\n"):
            with self.subTest(path=path), self.assertRaises(RouteNotFound):
                resolver.resolve("POST", path)
        self.assertEqual(resolver.options("/unknown"), [])

    def testHotCacheCapacityEvictionAndInvalidation(self) -> None:
        """Bound cached results and rebuild only after eviction or invalidation."""
        router = make_router()
        router.get("/items/{id:int}", route_handler)
        resolver = RouteResolver(compile_router(router), hot_cache_size=1)
        first = resolver.resolve("GET", "/items/1")
        self.assertIs(resolver.resolve("GET", "/items/1"), first)
        resolver.resolve("GET", "/items/2")
        self.assertIsNot(resolver.resolve("GET", "/items/1"), first)
        current = resolver.resolve("GET", "/items/1")
        resolver.invalidateCache()
        self.assertIsNot(resolver.resolve("GET", "/items/1"), current)
        uncached = RouteResolver(compile_router(router), hot_cache_size=0)
        self.assertIsNot(
            uncached.resolve("GET", "/items/1"), uncached.resolve("GET", "/items/1"),
        )

    def testCachedParametersCannotBeMutated(self) -> None:
        """Protect both static and dynamic shared results from parameter writes."""
        router = make_router()
        router.get("/static", route_handler)
        router.get("/items/{id:int}", route_handler)
        resolver = RouteResolver(compile_router(router))
        for path in ("/static", "/items/1"):
            resolved = resolver.resolve("GET", path)
            with self.assertRaises(TypeError):
                setitem(resolved.params, "id", 99)
            self.assertEqual(
                dict(resolver.resolve("GET", path).params),
                ({} if path == "/static" else {"id": 1}),
            )

    def testFifoHitsAndChurnPreserveCapacityAndInvalidation(self) -> None:
        """Evict in insertion order across repeated replacements and cache clears."""
        router = make_router()
        router.get("/items/{id:int}", route_handler)
        resolver = RouteResolver(compile_router(router), hot_cache_size=2)
        for offset in range(0, 60, 3):
            first_path = f"/items/{offset}"
            second_path = f"/items/{offset + 1}"
            first = resolver.resolve("GET", first_path)
            second = resolver.resolve("GET", second_path)
            self.assertIs(resolver.resolve("GET", first_path), first)
            resolver.resolve("GET", f"/items/{offset + 2}")
            self.assertIs(resolver.resolve("GET", second_path), second)
            self.assertIsNot(resolver.resolve("GET", first_path), first)
            resolver.invalidateCache()
            self.assertIsNot(resolver.resolve("GET", second_path), second)

    def testInvalidCacheCapacity(self) -> None:
        """Reject capacities that would fail on the first cache insertion."""
        for size in (-1, -100):
            with self.subTest(size=size), self.assertRaises(ValueError):
                RouteResolver({}, hot_cache_size=size)
        for size in (True, "1", 1.2, None):
            with self.subTest(size=size), self.assertRaises(TypeError):
                RouteResolver({}, hot_cache_size=size)

    def testConversionFailureDoesNotEscapeAsServerError(self) -> None:
        """Treat an integer outside Python's conversion limit as unmatched."""
        router = make_router()
        router.get("/items/{id:int}", route_handler)
        with self.assertRaises(RouteNotFound):
            RouteResolver(compile_router(router)).resolve("GET", "/items/" + "9" * 5000)

    def testIntrospectionDoesNotExposeTheStoredRouteCollection(self) -> None:
        """Allow callers to modify allRoutes output without changing dispatch."""
        router = make_router()
        resolver = RouteResolver(compile_router(router))
        routes = resolver.allRoutes()
        routes.clear()
        self.assertEqual(len(resolver.allRoutes()), 4)

class TestInvalidRouteDefinitions(TestCase):
    """Reject definitions before they reach request dispatch."""

    def testMalformedParameterDefinitions(self) -> None:
        """Reject invalid syntax, duplicate names and unsupported converters."""
        for path in (
            "/x/{",
            "/x/}",
            "/x/{id",
            "/x/{id:}",
            "/x/{a-b}",
            "/x/{1id}",
            "/x/{id}/{id}",
            "/x/{id:unknown}",
            "/x/{{id}}",
        ):
            with self.subTest(path=path), self.assertRaises(ValueError):
                RouteCompiler.compilePath(path)

    def testFinalPathAndPatternCollisions(self) -> None:
        """Detect collisions after composing prefixes and parameter names."""
        for paths in (("/same", "/same/"), ("/{id:int}", "/{other:int}")):
            router = make_router()
            for path in paths:
                router.group(prefix="api", routes=[router.get(path, route_handler)])
            with self.assertRaises(ValueError):
                compile_router(router)

    def testAmbiguousNamesAndEmptyNames(self) -> None:
        """Require one nonempty name to identify one path template."""
        router = make_router()
        first = router.get("/first", route_handler).name("shared")
        router.get("/second", route_handler).name("shared")
        with self.assertRaises(ValueError):
            compile_router(router)
        with self.assertRaises(ValueError):
            first.name("  ")

    def testSameNameOnTheSamePathAcrossMethods(self) -> None:
        """Allow GET and POST to share an unambiguous named URL."""
        router = make_router()
        router.get("/login", route_handler).name("login")
        router.post("/login", route_handler).name("login")
        resolver = RouteResolver(compile_router(router))
        self.assertEqual(resolver.resolve("GET", "/login").route.name, "login")
        self.assertEqual(resolver.resolve("POST", "/login").route.name, "login")

    def testInvalidActionsAndPaths(self) -> None:
        """Raise useful errors for unsupported handlers and nonstring paths."""
        router = make_router()
        for action in (None, 42, object, UserController()):
            with self.subTest(action=action), self.assertRaises(TypeError):
                router.get("/invalid", action)
        with self.assertRaises(TypeError):
            router.get(42, route_handler)
        with self.assertRaises(ValueError):
            router.get("/invalid", [UserController, "missing"])

    def testLocalHandlersFailDuringCompilation(self) -> None:
        """Reject a local function before a kernel tries importing it by name."""

        def local_handler() -> None:
            """Supply a nonimportable function."""

        router = make_router()
        router.get("/local", local_handler)
        with self.assertRaisesRegex(ValueError, "importable"):
            compile_router(router)

    def testViewActionCanBeReplacedAndTupleActionsWork(self) -> None:
        """Honor fluent action changes and typed controller/method tuples."""
        router = make_router()
        router.view("/page", "welcome").action(UserController, "index")
        router.get("/tuple", (UserController, "index"))
        resolver = RouteResolver(compile_router(router))
        for path in ("/page", "/tuple"):
            self.assertEqual(
                resolver.resolve("GET", path).route.action["method"], "index",
            )
        for view in ("", " ", 42):
            with self.subTest(view=view), self.assertRaises(ValueError):
                FluentRoute("GET", "/view", view=view)

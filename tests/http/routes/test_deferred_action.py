import json
from orionis.http.routes.enums.route_types import RouteType
from orionis.http.routes.exceptions.fallback_route_already_registered import (
    FallbackRouteAlreadyRegisteredException,
)
from orionis.http.routes.fluent import FluentRoute
from orionis.http.routes.route_cache import RouteCache
from orionis.http.routes.route_compiler import RouteCompiler
from orionis.http.routes.route_resolver import RouteResolver
from orionis.test import TestCase
from tests.http.routes.test_nested_routing import (
    Namespace,
    OneMiddleware,
    TwoMiddleware,
    UserController,
    compile_router,
    make_router,
    route_handler,
)
from tests.http.test_kernel import boot_kernel, dispatch

_VERBS = ("get", "post", "put", "patch", "delete", "query")


class TestDeferredRouteActions(TestCase):
    """Verify route completion before export, cache restoration and dispatch."""

    def testPendingFluentExportsFailUntilAnActionIsAssigned(self) -> None:
        """Reject incomplete omitted/None actions and allow subsequent completion."""
        for args in ((), (None,)):
            route = FluentRoute("post", "//orders//", *args)
            route_id = route.id
            with self.assertRaises(ValueError) as captured:
                route.export()
            message = str(captured.exception)
            self.assertIn("POST", message)
            self.assertIn("/orders", message)
            self.assertIn(".action", message)

            self.assertIs(route.action(UserController, "index"), route)
            exported = route.export()
            self.assertEqual(exported["id"], route_id)
            self.assertIs(exported["class"], UserController)
            self.assertEqual(exported["handler"], "index")
            compiled, _ = RouteCompiler().compile([exported], None)
            resolved = RouteResolver(compiled).resolve("POST", "/orders")
            self.assertEqual(resolved.route.action["method"], "index")

    def testEveryVerbRestoresOmittedAndNoneActionsFromCache(self) -> None:
        """Complete all six verbs and preserve actions and params through JSON."""
        router = make_router()
        for verb in _VERBS:
            register = getattr(router, verb)
            for label, args in (("omitted", ()), ("explicit", (None,))):
                path = f"/{label}/items/{{id:int}}"
                route = register(path, *args)
                route.name(f"items.{verb}.{label}")
                route.action(Namespace.Controller, "index")

        compiled = compile_router(router)
        cache = RouteCache()
        snapshot = json.loads(json.dumps(cache.toCache(compiled, None)))
        restored, fallback = cache.fromCache(snapshot)
        for tables in (compiled, restored):
            resolver = RouteResolver(tables, fallback=fallback)
            for verb in _VERBS:
                for label in ("omitted", "explicit"):
                    resolved = resolver.resolve(
                        verb.upper(), f"/{label}/items/42",
                    )
                    self.assertEqual(resolved.params, {"id": 42})
                    self.assertEqual(resolved.route.method, verb.upper())
                    self.assertEqual(
                        resolved.route.name, f"items.{verb}.{label}",
                    )
                    self.assertEqual(resolved.route.type, RouteType.CONTROLLER)
                    self.assertEqual(resolved.route.action, {
                        "module": Namespace.Controller.__module__,
                        "class": Namespace.Controller.__qualname__,
                        "method": "index",
                    })

    def testRouterExportRejectsAnIncompleteRouteAndCanRecover(self) -> None:
        """Block a pending route from the compiled table without losing it."""
        router = make_router()
        pending = router.delete("/pending").name("pending.delete")
        with self.assertRaises(ValueError) as captured:
            router.export()
        self.assertIn("DELETE", str(captured.exception))
        self.assertIn("/pending", str(captured.exception))
        self.assertIn(".action", str(captured.exception))

        pending.action(UserController, "index")
        resolved = RouteResolver(compile_router(router)).resolve("DELETE", "/pending")
        self.assertEqual(resolved.route.name, "pending.delete")
        self.assertEqual(resolved.route.action["method"], "index")
        exported = router.export()["routes"]
        self.assertEqual(sum(route["id"] == pending.id for route in exported), 1)

    def testPendingRoutesKeepGroupContextAfterCompletionAndCaching(self) -> None:
        """Keep prefixes, names, middleware exclusions and kind while pending."""
        router = make_router()
        router._setKind("api")
        pending = (
            router.patch("/items/{id:int}")
            .prefix("v2")
            .name("items.update")
            .middleware(Namespace.Middleware)
            .withOutMiddleware(TwoMiddleware)
        )
        router.group(
            prefix="api",
            middleware=[OneMiddleware, TwoMiddleware],
            routes=[pending],
        )
        pending.action(Namespace.Controller, "index")
        cache = RouteCache()
        snapshot = json.loads(json.dumps(cache.toCache(compile_router(router), None)))
        restored, _ = cache.fromCache(snapshot)
        resolved = RouteResolver(restored).resolve("PATCH", "/api/v2/items/7")
        self.assertEqual(pending.path, "/api/v2/items/{id:int}")
        self.assertEqual(resolved.params, {"id": 7})
        self.assertEqual(resolved.route.name, "items.update")
        self.assertEqual(resolved.kind, "api")
        self.assertEqual(
            resolved.route.compiled_middlewares,
            (OneMiddleware, Namespace.Middleware),
        )
        self.assertEqual(resolved.route.without_middleware, {TwoMiddleware})
        self.assertEqual(resolved.route.action["method"], "index")

    def testImmediateActionsAndViewsStillExportAndResolve(self) -> None:
        """Keep accepted immediate handlers and handler-free view routes working."""
        router = make_router()
        router.get("/function", route_handler)
        router.get("/invokable", UserController)
        router.get("/list", [UserController, "index"])
        router.get("/tuple", (UserController, "index"))
        router.view("/view", "pages.home")
        resolver = RouteResolver(compile_router(router))
        for path, expected in (
            ("/function", RouteType.FUNCTION),
            ("/invokable", RouteType.INVOKABLE),
            ("/list", RouteType.CONTROLLER),
            ("/tuple", RouteType.CONTROLLER),
            ("/view", RouteType.VIEW),
        ):
            self.assertEqual(resolver.resolve("GET", path).route.type, expected)
        self.assertEqual(
            resolver.resolve("GET", "/view").route.action,
            {"view": "pages.home"},
        )

    def testInvalidNonNoneActionsFailBeforeRegistration(self) -> None:
        """Keep invalid and false-valued actions from becoming pending routes."""
        invalid = (
            (False, TypeError),
            (0, TypeError),
            ("", TypeError),
            (object(), TypeError),
            ([], ValueError),
            ([UserController], ValueError),
            ([UserController, "missing"], ValueError),
            ([UserController, 42], TypeError),
        )
        router = make_router()
        original = router.export()
        for action, error_type in invalid:
            with self.assertRaises(error_type):
                FluentRoute("GET", "/invalid", action)
            for verb in _VERBS:
                with self.assertRaises(error_type):
                    getattr(router, verb)("/invalid", action)
                self.assertEqual(router.export(), original)

    async def testCachedDeferredControllerRunsThroughKernelAndMiddleware(self) -> None:
        """Dispatch an assigned action after cache restoration through the kernel."""
        router = make_router()
        router._setKind("api")
        pending = router.get("/controller").name("deferred.controller")
        router.group(
            prefix="deferred",
            middleware=OneMiddleware,
            routes=[pending],
        )
        pending.action(Namespace.Controller, "index")
        cache = RouteCache()
        snapshot = json.loads(json.dumps(cache.toCache(compile_router(router), None)))
        restored, fallback = cache.fromCache(snapshot)
        kernel, _, _, catch = await boot_kernel(routes=restored, fallback=fallback)
        response = await dispatch(kernel, "/deferred/controller")
        self.assertEqual(response.getStatusCode(), 200)
        self.assertEqual(response.getBody(), b"routed")
        self.assertEqual(
            response.getHeader("x-trace"),
            ["+OneMiddleware,-OneMiddleware"],
        )
        self.assertEqual(catch.handled, [])


class TestRequiredFallbackAction(TestCase):
    """Verify rejected fallbacks leave room for one valid registration."""

    def testMissingAndNoneFallbacksDoNotRegisterOrConsumeTheSlot(self) -> None:
        """Reject missing/None actions and preserve a later valid fallback."""
        router = make_router()
        with self.assertRaises(TypeError):
            router.fallback()
        self.assertEqual(router.export()["fallback"], (None, None))
        with self.assertRaises(TypeError):
            router.fallback(None)
        self.assertEqual(router.export()["fallback"], (None, None))

        router.fallback(route_handler)
        expected = (None, route_handler)
        self.assertEqual(router.export()["fallback"], expected)
        with self.assertRaises(FallbackRouteAlreadyRegisteredException):
            router.fallback(UserController)
        self.assertEqual(router.export()["fallback"], expected)

    async def testValidFallbackFormsSurviveCacheAndKernelDispatch(self) -> None:
        """Restore callable, invokable and controller fallbacks for missing paths."""
        cases = (
            (route_handler, (None, route_handler)),
            (UserController, (UserController, "__call__")),
            ([UserController, "index"], (UserController, "index")),
            ((UserController, "index"), (UserController, "index")),
        )
        for action, expected in cases:
            router = make_router()
            router.fallback(action)
            exported = router.export()
            self.assertEqual(exported["fallback"], expected)
            cache = RouteCache()
            snapshot = json.loads(json.dumps(cache.toCache(
                compile_router(router), exported["fallback"],
            )))
            restored, fallback = cache.fromCache(snapshot)
            self.assertEqual(fallback, expected)
            kernel, _, _, catch = await boot_kernel(
                routes=restored, fallback=fallback,
            )
            response = await dispatch(kernel, "/missing")
            self.assertEqual(response.getStatusCode(), 200)
            self.assertEqual(response.getBody(), b"routed")
            self.assertEqual(catch.handled, [])

import json
from abc import ABC, abstractmethod
from orionis.http.responses import Response  # noqa: TC001 (runtime reflection)
from orionis.http.routes.enums.route_types import RouteType
from orionis.http.routes.fluent import FluentRoute
from orionis.http.routes.functions import is_valid_handler, parse_action
from orionis.http.routes.route_cache import RouteCache
from orionis.http.routes.route_compiler import RouteCompiler
from orionis.http.routes.route_resolver import RouteResolver
from orionis.test import TestCase
from tests.http.routes.test_nested_routing import (
    compile_router,
    make_router,
    route_handler,
)
from tests.http.test_kernel import boot_kernel, dispatch

_VERBS = ("get", "post", "put", "patch", "delete", "query")


class _AbstractActionController(ABC):
    """Expose a concrete handler on a controller that cannot be instantiated."""

    __slots__ = ()

    @abstractmethod
    def required(self) -> None:
        """Require a concrete implementation before constructing the controller."""

    def index(self) -> Response:
        """Return the response shared with routing integration fixtures.

        Returns
        -------
        Response
            Successful response from the inherited action.
        """
        return route_handler()

    def __call__(self) -> Response:
        """Delegate invocation to the concrete handler.

        Returns
        -------
        Response
            Response from index after the class is made concrete.
        """
        return self.index()


class _ConcreteActionController(_AbstractActionController):
    """Complete the abstract controller while retaining its inherited handler."""

    __slots__ = ()

    def required(self) -> None:
        """Complete the controller contract without changing the inherited action."""


class TestAbstractRouteActions(TestCase):
    """Reject abstract action owners before registration and compilation."""

    def testAbstractActionsFailBeforeRouteOrFallbackRegistration(self) -> None:
        """Reject abstract list, tuple and bare actions without consuming routes."""
        actions = (
            [_AbstractActionController, "index"],
            (_AbstractActionController, "index"),
            _AbstractActionController,
        )
        for action in actions:
            self.assertFalse(is_valid_handler(action), msg=repr(action))
            with self.assertRaises(TypeError):
                parse_action(action)
            with self.assertRaises(TypeError):
                FluentRoute("GET", "/rejected", action)

            router = make_router()
            original = router.export()
            for verb in _VERBS:
                with self.assertRaises(TypeError):
                    getattr(router, verb)("/rejected", action)
                self.assertEqual(router.export(), original)
            with self.assertRaises(TypeError):
                router.fallback(action)
            self.assertEqual(router.export(), original)
            router.fallback(route_handler)
            self.assertEqual(router.export()["fallback"], (None, route_handler))

    def testRejectedActionAssignmentsPreservePendingHandlerAndViewState(self) -> None:
        """Keep each fluent state intact when the replacement owner is abstract."""
        pending = FluentRoute("GET", "/pending")
        with self.assertRaises(TypeError):
            pending.action(_AbstractActionController, "index")
        with self.assertRaises(ValueError):
            pending.export()
        pending.action(_ConcreteActionController, "index")
        self.assertIs(pending.export()["class"], _ConcreteActionController)

        existing = FluentRoute(
            "GET", "/existing", [_ConcreteActionController, "index"],
        )
        view = FluentRoute("GET", "/view", view="pages.home")
        for route in (existing, view):
            original = route.export()
            with self.assertRaises(TypeError):
                route.action(_AbstractActionController, "index")
            self.assertEqual(route.export(), original)

    def testCompilerRejectsAnAbstractOwnerInRawRouteData(self) -> None:
        """Reject an abstract owner even when raw data bypasses fluent validation."""
        raw = FluentRoute(
            "GET", "/raw", [_ConcreteActionController, "index"],
        ).export()
        raw["class"] = _AbstractActionController
        with self.assertRaises(TypeError):
            RouteCompiler().compile([raw], None)

    async def testConcreteInheritedActionsSurviveCompilationCacheAndResolution(
        self,
    ) -> None:
        """Accept inherited handlers once every abstract method is implemented."""
        router = make_router()
        router._setKind("api")
        for label, action in (
            ("list", [_ConcreteActionController, "index"]),
            ("tuple", (_ConcreteActionController, "index")),
        ):
            self.assertTrue(is_valid_handler(action), msg=repr(action))
            owner, method = parse_action(action)
            self.assertIs(owner, _ConcreteActionController)
            self.assertEqual(method, "index")
            router.get(f"/concrete/{label}", action).name(f"concrete.{label}")
        router.fallback([_ConcreteActionController, "index"])
        compiled = compile_router(router)
        cache = RouteCache()
        snapshot = json.loads(json.dumps(cache.toCache(
            compiled, router.export()["fallback"],
        )))
        restored, fallback = cache.fromCache(snapshot)
        self.assertEqual(fallback, (_ConcreteActionController, "index"))
        for tables in (compiled, restored):
            resolver = RouteResolver(tables, fallback=fallback)
            for label in ("list", "tuple"):
                resolved = resolver.resolve("GET", f"/concrete/{label}")
                self.assertEqual(resolved.route.type, RouteType.CONTROLLER)
                self.assertEqual(resolved.route.name, f"concrete.{label}")
                self.assertEqual(resolved.route.action, {
                    "module": _ConcreteActionController.__module__,
                    "class": _ConcreteActionController.__qualname__,
                    "method": "index",
                })
        kernel, _, _, catch = await boot_kernel(routes=restored, fallback=fallback)
        for path in ("/concrete/list", "/concrete/tuple", "/missing"):
            response = await dispatch(kernel, path)
            self.assertEqual(response.getStatusCode(), 200)
            self.assertEqual(response.getBody(), b"routed")
        self.assertEqual(catch.handled, [])

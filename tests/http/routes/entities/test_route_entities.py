from types import MappingProxyType
from orionis.http.routes.entities.compiled_route import CompiledRoute
from orionis.http.routes.entities.resolved_route import ResolvedRoute
from orionis.http.routes.enums.route_types import RouteType
from orionis.test import TestCase

def _make_compiled_route(
    path: str = "/users",
    method: str = "GET",
    kind: str = "web",
    name: str | None = "users.index",
) -> CompiledRoute:
    """Return a minimal CompiledRoute for testing purposes."""
    return CompiledRoute(
        path=path,
        method=method,
        type=RouteType.FUNCTION,
        action={"function": "index", "module": "app.controllers"},
        name=name,
        regex=None,
        segment_count=1,
        priority_score=10,
        kind=kind,
    )

class TestCompiledRoute(TestCase):
    """Unit tests for the CompiledRoute frozen dataclass."""

    def testDefaultFieldValues(self) -> None:
        """
        Verify that optional fields default to their documented values.

        Confirms priority_score defaults to 0, kind to 'web', converters
        to an empty dict, middleware to an empty list, without_middleware
        to an empty set, and compiled_middlewares to an empty tuple.
        """
        route = CompiledRoute(
            path="/",
            method="GET",
            type=RouteType.FUNCTION,
            action={"function": "home", "module": "app"},
            name=None,
            regex=None,
            segment_count=0,
        )
        self.assertEqual(route.priority_score, 0)
        self.assertEqual(route.kind, "web")
        self.assertEqual(route.converters, {})
        self.assertEqual(route.middleware, [])
        self.assertEqual(route.without_middleware, set())
        self.assertEqual(route.compiled_middlewares, ())

    def testFieldsAreImmutable(self) -> None:
        """
        Verify that CompiledRoute is frozen and rejects attribute mutation.

        Confirms that assigning to any field raises a FrozenInstanceError.
        """
        from dataclasses import FrozenInstanceError

        route = _make_compiled_route()
        with self.assertRaises(FrozenInstanceError):
            route.path = "/other"  # type: ignore[misc]

    def testFieldsStoredCorrectly(self) -> None:
        """
        Verify that constructor arguments are accessible on the instance.

        Confirms that path, method, type, action, name, segment_count,
        priority_score, and kind are stored without mutation.
        """
        route = _make_compiled_route(
            path="/users",
            method="POST",
            kind="api",
            name="users.store",
        )
        self.assertEqual(route.path, "/users")
        self.assertEqual(route.method, "POST")
        self.assertEqual(route.type, RouteType.FUNCTION)
        self.assertEqual(route.kind, "api")
        self.assertEqual(route.name, "users.store")

    def testNoneNameAllowed(self) -> None:
        """
        Verify that name may be None for anonymous routes.

        Confirms that passing name=None does not raise an error.
        """
        route = _make_compiled_route(name=None)
        self.assertIsNone(route.name)

    def testNoneRegexForStaticRoute(self) -> None:
        """
        Verify that regex is None for a static route.

        Confirms that static routes do not require a compiled pattern.
        """
        route = _make_compiled_route()
        self.assertIsNone(route.regex)

class TestResolvedRoute(TestCase):
    """Unit tests for the ResolvedRoute frozen dataclass."""

    def testKindDelegatesToCompiledRoute(self) -> None:
        """
        Verify that the kind property delegates to the underlying route.

        Confirms that ResolvedRoute.kind returns the same value as
        the nested CompiledRoute.kind field.
        """
        compiled = _make_compiled_route(kind="api")
        resolved = ResolvedRoute(route=compiled, params={})
        self.assertEqual(resolved.kind, "api")

    def testEmptyParamsForStaticRoute(self) -> None:
        """
        Verify that static routes carry an empty params dict.

        Confirms that ResolvedRoute accepts and preserves an empty
        parameter mapping.
        """
        compiled = _make_compiled_route()
        resolved = ResolvedRoute(route=compiled, params={})
        self.assertEqual(resolved.params, {})

    def testParamsStoredForDynamicRoute(self) -> None:
        """
        Verify that path parameters are stored on the resolved route.

        Confirms that a non-empty params dict is preserved as-is.
        """
        compiled = _make_compiled_route(path="/users/{id:int}")
        resolved = ResolvedRoute(route=compiled, params={"id": 42})
        self.assertEqual(resolved.params["id"], 42)

    def testIsFrozen(self) -> None:
        """
        Verify that ResolvedRoute is frozen and rejects attribute mutation.

        Confirms that assigning to the route field raises FrozenInstanceError.
        """
        from dataclasses import FrozenInstanceError

        compiled = _make_compiled_route()
        resolved = ResolvedRoute(route=compiled, params={})
        with self.assertRaises(FrozenInstanceError):
            resolved.params = {"x": 1}  # type: ignore[misc]

    def testRouteFieldPointsToCompiledRoute(self) -> None:
        """
        Verify that the route field stores the exact CompiledRoute instance.

        Confirms object identity between the constructor argument and
        the stored attribute.
        """
        compiled = _make_compiled_route()
        resolved = ResolvedRoute(route=compiled, params={})
        self.assertIs(resolved.route, compiled)

    def testConstructorCopiesMutableParameterSources(self) -> None:
        """Isolate results from external dicts and live read-only mapping views."""
        compiled = _make_compiled_route(path="/users/{id:int}")
        for wrap in (dict, MappingProxyType):
            source = {"id": 42}
            mapping = source if wrap is dict else wrap(source)
            resolved = ResolvedRoute(route=compiled, params=mapping)
            source["id"] = 99
            self.assertEqual(resolved.params, {"id": 42})

    def testConstructorDoesNotRetainAnEmptyMutableSource(self) -> None:
        """Keep empty results isolated when their source mapping later changes."""
        source = {}
        resolved = ResolvedRoute(route=_make_compiled_route(), params=source)
        source["id"] = 99
        self.assertEqual(resolved.params, {})

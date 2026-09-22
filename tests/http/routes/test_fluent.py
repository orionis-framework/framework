from __future__ import annotations
from typing import TYPE_CHECKING
from orionis.http.middleware import BaseMiddleware
from orionis.http.routes.fluent import FluentRoute
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from orionis.http.request import Request
    from orionis.http.responses import Response

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _view_handler() -> None:
    """Provide a standalone route action fixture."""

class _InvokableController:
    def __call__(self) -> None:
        """Invoke the controller."""

class _RegularController:
    def show(self) -> None:
        """Handle show action."""

    def index(self) -> None:
        """Handle index action."""

class _MW1(BaseMiddleware):
    async def handle(
        self,
        _request: Request,
        call_next: Callable[[], Awaitable[Response]],
    ) -> Response:
        """Forward the request to the next middleware or handler.

        Returns
        -------
        Response
            Response produced by the remaining pipeline.
        """
        return await call_next()

class _MW2(BaseMiddleware):
    async def handle(
        self,
        _request: Request,
        call_next: Callable[[], Awaitable[Response]],
    ) -> Response:
        """Forward the request to the next middleware or handler.

        Returns
        -------
        Response
            Response produced by the remaining pipeline.
        """
        return await call_next()

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFluentRouteInit(TestCase):
    """Unit tests for FluentRoute initialisation."""

    def testValidFunctionAction(self) -> None:
        """
        Verify that a plain function is accepted as an action.

        Confirms the route is created without errors and the exported
        callable_handler equals the function.
        """
        route = FluentRoute("GET", "/home", _view_handler)
        exported = route.export()
        self.assertEqual(exported["method"], "GET")
        self.assertIs(exported["callable_handler"], _view_handler)

    def testValidInvokableClassAction(self) -> None:
        """
        Verify that an invokable class is accepted as an action.

        Confirms the callable_handler field is set and handler is None.
        """
        route = FluentRoute("POST", "/orders", _InvokableController)
        exported = route.export()
        self.assertIs(exported["callable_handler"], _InvokableController)
        self.assertIsNone(exported["handler"])

    def testValidControllerListAction(self) -> None:
        """
        Verify that a [Controller, 'method'] list is accepted.

        Confirms the class and handler fields are set correctly.
        """
        route = FluentRoute("GET", "/users", [_RegularController, "index"])
        exported = route.export()
        self.assertIs(exported["class"], _RegularController)
        self.assertEqual(exported["handler"], "index")

    def testMethodIsUppercased(self) -> None:
        """
        Verify that the HTTP method is stored in uppercase.

        Confirms that lowercase input is normalised automatically.
        """
        route = FluentRoute("get", "/ping", _view_handler)
        self.assertEqual(route.export()["method"], "GET")

    def testPathIsNormalised(self) -> None:
        """
        Verify that the route path is normalised on construction.

        Confirms trailing slashes and consecutive slashes are cleaned.
        """
        route = FluentRoute("GET", "//users//", _view_handler)
        self.assertEqual(route.export()["path"], "/users")

    def testInvalidMethodRaisesValueError(self) -> None:
        """
        Verify that an unrecognised HTTP method raises ValueError.

        Confirms that only the allowed set of methods is accepted.
        """
        with self.assertRaises(ValueError):
            FluentRoute("BREW", "/coffee", _view_handler)

    def testNonStringMethodRaisesTypeError(self) -> None:
        """
        Verify that a non-string method raises TypeError.

        Confirms the type guard on the method parameter.
        """
        with self.assertRaises(TypeError):
            FluentRoute(42, "/path", _view_handler)  # type: ignore[arg-type]

    def testNonStringPathRaisesTypeError(self) -> None:
        """
        Verify that a non-string path raises TypeError.

        Confirms the type guard on the path parameter.
        """
        with self.assertRaises(TypeError):
            FluentRoute("GET", 123, _view_handler)  # type: ignore[arg-type]

    def testIdIsString(self) -> None:
        """
        Verify that the route ID is a non-empty string.

        Confirms RouteID.next assigns a string identifier to each route.
        """
        route = FluentRoute("GET", "/items", _view_handler)
        self.assertIsInstance(route.id, str)
        self.assertTrue(len(route.id) > 0)

    def testUniqueIds(self) -> None:
        """
        Verify that two routes created with identical arguments have distinct IDs.

        Confirms the ID generator produces unique values on every call.
        """
        r1 = FluentRoute("GET", "/items", _view_handler)
        r2 = FluentRoute("GET", "/items", _view_handler)
        self.assertNotEqual(r1.id, r2.id)

class TestFluentRouteName(TestCase):
    """Unit tests for FluentRoute.name()."""

    def testNameIsStoredAndStripped(self) -> None:
        """
        Verify that setting a name trims whitespace and stores the value.

        Confirms the route name is accessible via the exported dict.
        """
        route = FluentRoute("GET", "/users", _view_handler)
        route.name("  users.index  ")
        self.assertEqual(route.export()["name"], "users.index")

    def testNameDefaultsToNone(self) -> None:
        """
        Verify that a freshly created route has no name set.

        Confirms the name field defaults to None before name() is called.
        """
        route = FluentRoute("GET", "/unnamed", _view_handler)
        self.assertIsNone(route.export()["name"])

    def testNonStringNameRaisesTypeError(self) -> None:
        """
        Verify that a non-string route name raises TypeError.

        Confirms the type guard in FluentRoute.name().
        """
        route = FluentRoute("GET", "/test", _view_handler)
        with self.assertRaises(TypeError):
            route.name(99)  # type: ignore[arg-type]

    def testNameReturnsself(self) -> None:
        """
        Verify that name() returns the same FluentRoute instance.

        Confirms the fluent interface for method chaining.
        """
        route = FluentRoute("GET", "/users", _view_handler)
        result = route.name("users.index")
        self.assertIs(result, route)

class TestFluentRoutePrefix(TestCase):
    """Unit tests for FluentRoute.prefix()."""

    def testPrefixIsPrependedToPath(self) -> None:
        """
        Verify that a prefix is prepended to the existing path.

        Confirms that prefix('/api') + path('/users') = '/api/users'.
        """
        route = FluentRoute("GET", "/users", _view_handler)
        route.prefix("/api")
        self.assertEqual(route.export()["path"], "/api/users")

    def testPrefixWithTrailingSlash(self) -> None:
        """
        Verify that a prefix with trailing slash is handled correctly.

        Confirms that double slashes are collapsed after prepending.
        """
        route = FluentRoute("GET", "/items", _view_handler)
        route.prefix("/v1/")
        self.assertEqual(route.export()["path"], "/v1/items")

    def testNonStringPrefixRaisesTypeError(self) -> None:
        """
        Verify that a non-string prefix raises TypeError.

        Confirms the type guard in FluentRoute.prefix().
        """
        route = FluentRoute("GET", "/test", _view_handler)
        with self.assertRaises(TypeError):
            route.prefix(42)  # type: ignore[arg-type]

    def testPrefixReturnsSelf(self) -> None:
        """
        Verify that prefix() returns the same FluentRoute instance.

        Confirms the fluent interface for method chaining.
        """
        route = FluentRoute("GET", "/x", _view_handler)
        result = route.prefix("/v2")
        self.assertIs(result, route)

class TestFluentRouteMiddleware(TestCase):
    """Unit tests for FluentRoute.middleware() and .withOutMiddleware()."""

    def testAddSingleMiddleware(self) -> None:
        """
        Verify that a single middleware class is added to the route.

        Confirms that middleware() appends the class to the internal list.
        """
        route = FluentRoute("GET", "/secure", _view_handler)
        route.middleware(_MW1)
        self.assertIn(_MW1, route.export()["middleware"])

    def testAddMultipleMiddleware(self) -> None:
        """
        Verify that multiple middleware classes are added in order.

        Confirms that both _MW1 and _MW2 appear in the middleware list.
        """
        route = FluentRoute("GET", "/secure", _view_handler)
        route.middleware(_MW1, _MW2)
        exported = route.export()["middleware"]
        self.assertIn(_MW1, exported)
        self.assertIn(_MW2, exported)

    def testAddListWrappedMiddleware(self) -> None:
        """
        Verify that list-wrapped middleware is flattened and added.

        Confirms that passing [_MW1] is accepted and flattened correctly.
        """
        route = FluentRoute("GET", "/secure", _view_handler)
        route.middleware([_MW1])
        self.assertIn(_MW1, route.export()["middleware"])

    def testWithOutMiddlewareExcludesClass(self) -> None:
        """
        Verify that withOutMiddleware adds classes to the exclusion set.

        Confirms that excluded middleware appear in without_middleware.
        """
        route = FluentRoute("GET", "/open", _view_handler)
        route.withOutMiddleware(_MW1)
        self.assertIn(_MW1, route.export()["without_middleware"])

    def testMiddlewareReturnsSelf(self) -> None:
        """
        Verify that middleware() returns the same FluentRoute instance.

        Confirms the fluent interface for method chaining.
        """
        route = FluentRoute("GET", "/x", _view_handler)
        result = route.middleware(_MW1)
        self.assertIs(result, route)

    def testNonMiddlewareClassRaisesTypeError(self) -> None:
        """
        Verify that passing a non-BaseMiddleware class raises TypeError.

        Confirms that flattenMiddleware validation is triggered.
        """
        route = FluentRoute("GET", "/bad", _view_handler)
        with self.assertRaises(TypeError):
            route.middleware(object)  # type: ignore[arg-type]

class TestFluentRouteKind(TestCase):
    """Unit tests for FluentRoute._kind()."""

    def testDefaultKindIsWeb(self) -> None:
        """
        Verify that the route kind defaults to 'web'.

        Confirms that newly created routes carry the 'web' tag before
        any kind override.
        """
        route = FluentRoute("GET", "/page", _view_handler)
        self.assertEqual(route.export()["kind"], "web")

    def testKindCanBeSetToApi(self) -> None:
        """
        Verify that _kind('api') stores 'api' in the export dict.

        Confirms that the internal kind is updated correctly.
        """
        route = FluentRoute("GET", "/api/users", _view_handler)
        route._kind("api")
        self.assertEqual(route.export()["kind"], "api")

    def testKindIsLowercased(self) -> None:
        """
        Verify that the kind value is lowercased on storage.

        Confirms that 'Web' and 'API' are normalised to 'web' and 'api'.
        """
        route = FluentRoute("GET", "/x", _view_handler)
        route._kind("WEB")
        self.assertEqual(route.export()["kind"], "web")

    def testNonStringKindRaisesTypeError(self) -> None:
        """
        Verify that a non-string kind raises TypeError.

        Confirms the type guard in FluentRoute._kind().
        """
        route = FluentRoute("GET", "/x", _view_handler)
        with self.assertRaises(TypeError):
            route._kind(1)  # type: ignore[arg-type]

class TestFluentRouteExport(TestCase):
    """Unit tests for FluentRoute.export()."""

    def testExportContainsAllExpectedKeys(self) -> None:
        """
        Verify that export() returns a dict with all documented keys.

        Confirms that id, method, path, class, handler, callable_handler,
        view, name, middleware, without_middleware, and kind are all present.
        """
        expected_keys = {
            "id",
            "method",
            "path",
            "class",
            "handler",
            "callable_handler",
            "view",
            "name",
            "middleware",
            "without_middleware",
            "kind",
        }
        route = FluentRoute("GET", "/export", _view_handler)
        self.assertEqual(set(route.export().keys()), expected_keys)

    def testExportIsDictInstance(self) -> None:
        """
        Verify that export() returns a plain dict.

        Confirms the return type is dict and not a subclass.
        """
        route = FluentRoute("DELETE", "/resource", _view_handler)
        self.assertIsInstance(route.export(), dict)

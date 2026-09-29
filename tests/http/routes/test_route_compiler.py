from orionis.http.routes.enums.route_types import RouteType
from orionis.http.routes.route_compiler import RouteCompiler
from orionis.test import TestCase

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _handler_a() -> None:
    """Provide the first importable route action fixture.

    Returns
    -------
    None
        Completes the operation described above.
    """

def _handler_b() -> None:
    """Provide the second importable route action fixture.

    Returns
    -------
    None
        Completes the operation described above.
    """

def _handler_c() -> None:
    """Provide the third importable route action fixture.

    Returns
    -------
    None
        Completes the operation described above.
    """

def _make_route_dict(
    method: str = "GET",
    path: str = "/users",
    handler: object = None,
    name: str | None = None,
    kind: str = "web",
) -> dict:
    """Return a minimal raw route dict matching the Router.export() shape.

    Parameters
    ----------
    method : str
        Value supplied for ``method``.
    path : str
        Value supplied for ``path``.
    handler : object
        Value supplied for ``handler``.
    name : str | None
        Value supplied for ``name``.
    kind : str
        Value supplied for ``kind``.

    Returns
    -------
    dict
        Value produced by the helper.
    """
    if handler is None:
        handler = _handler_a
    return {
        "id": f"{method}:{path}:pid:ts:1",
        "method": method,
        "path": path,
        "class": None,
        "handler": None,
        "callable_handler": handler,
        "name": name,
        "middleware": [],
        "without_middleware": set(),
        "kind": kind,
    }

# ---------------------------------------------------------------------------
# RouteCompiler.compilePath
# ---------------------------------------------------------------------------

class TestRouteCompilerCompilePath(TestCase):
    """Unit tests for RouteCompiler.compilePath static method."""

    def testStaticPathReturnsIsStaticTrue(self) -> None:
        """Verify that a path without placeholders is classified as static.

        Confirms the first element of the returned tuple is True for
        paths that contain no curly-brace parameters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        is_static, regex, converters = RouteCompiler.compilePath("/users/me")
        self.assertTrue(is_static)
        self.assertIsNone(regex)
        self.assertEqual(converters, {})

    def testDynamicPathReturnsIsStaticFalse(self) -> None:
        """Verify that a path with a placeholder is classified as dynamic.

        Confirms the first element is False and a compiled regex is
        returned for paths containing curly-brace parameters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        is_static, regex, _converters = RouteCompiler.compilePath(
            "/users/{id}",
        )
        self.assertFalse(is_static)
        self.assertIsNotNone(regex)

    def testIntTypedPlaceholderCreatesConverter(self) -> None:
        """Verify that {id:int} produces an int converter.

        Confirms that the converters dict maps the parameter name to the
        int callable.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        _, _, converters = RouteCompiler.compilePath("/items/{id:int}")
        self.assertIn("id", converters)
        self.assertEqual(converters["id"], int)

    def testDefaultTypeIsStr(self) -> None:
        """Verify that a plain {name} placeholder defaults to str conversion.

        Confirms that the str converter is used when no type annotation
        is provided.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        _, _, converters = RouteCompiler.compilePath("/users/{name}")
        self.assertIn("name", converters)
        self.assertEqual(converters["name"], str)

    def testRootPathIsStatic(self) -> None:
        """Verify that the root path '/' is classified as static.

        Confirms that a single-slash path does not trigger dynamic logic.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        is_static, regex, _converters = RouteCompiler.compilePath("/")
        self.assertTrue(is_static)
        self.assertIsNone(regex)

    def testCompiledRegexMatchesPath(self) -> None:
        """Verify that the compiled regex matches a valid URL for the pattern.

        Confirms that the regex produced for '/users/{id:int}' matches
        '/users/42' but not '/users/abc'.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        _, regex, _ = RouteCompiler.compilePath("/users/{id:int}")
        self.assertIsNotNone(regex)
        self.assertIsNotNone(regex.match("/users/42"))
        self.assertIsNone(regex.match("/users/abc"))

    def testMultiplePlaceholders(self) -> None:
        """Verify that multiple placeholders are all captured in converters.

        Confirms that '/posts/{post_id:int}/comments/{comment_id:int}'
        returns converters for both parameters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        _, _, converters = RouteCompiler.compilePath(
            "/posts/{post_id:int}/comments/{comment_id:int}",
        )
        self.assertIn("post_id", converters)
        self.assertIn("comment_id", converters)

# ---------------------------------------------------------------------------
# RouteCompiler.compile
# ---------------------------------------------------------------------------

class TestRouteCompilerCompile(TestCase):
    """Unit tests for RouteCompiler.compile."""

    def testCompileStaticRoute(self) -> None:
        """Verify that a static route is placed in the static bucket.

        Confirms that a path without placeholders lands in
        compiled_routes[method]['static'] under its exact path key.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        compiler = RouteCompiler()
        route = _make_route_dict("GET", "/home")
        compiled, fallback = compiler.compile([route], None)
        self.assertIn("GET", compiled)
        self.assertIn("/home", compiled["GET"]["static"])
        self.assertIsNone(fallback)

    def testCompileDynamicRoute(self) -> None:
        """Verify that a dynamic route is placed in the dynamic list.

        Confirms that a path with a placeholder appears in the dynamic
        list and not the static dict.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        compiler = RouteCompiler()
        route = _make_route_dict("GET", "/users/{id:int}")
        compiled, _ = compiler.compile([route], None)
        self.assertEqual(len(compiled["GET"]["dynamic"]), 1)
        self.assertEqual(len(compiled["GET"]["static"]), 0)

    def testCompiledRouteType(self) -> None:
        """Verify that a plain function action produces RouteType.FUNCTION.

        Confirms the type field on the compiled route entity.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        compiler = RouteCompiler()
        route = _make_route_dict("GET", "/ping", _handler_a)
        compiled, _ = compiler.compile([route], None)
        cr = compiled["GET"]["static"]["/ping"]
        self.assertEqual(cr.type, RouteType.FUNCTION)

    def testStaticRouteConflictRaisesValueError(self) -> None:
        """Verify duplicate static routes raise ``ValueError`` during compilation.

        Confirms that a collision check is performed during compilation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        compiler = RouteCompiler()
        r1 = _make_route_dict("GET", "/dup")
        r2 = _make_route_dict("GET", "/dup", _handler_b)
        with self.assertRaises(ValueError):
            compiler.compile([r1, r2], None)

    def testDynamicCollisionRaisesValueError(self) -> None:
        """Verify two dynamic routes with the same structural pattern raise ValueError.

        Confirms that routes like '/users/{id:int}' and '/users/{uid:int}'
        are detected as collisions.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        compiler = RouteCompiler()
        r1 = _make_route_dict("GET", "/users/{id:int}", _handler_a)
        r2 = _make_route_dict("GET", "/users/{uid:int}", _handler_b)
        with self.assertRaises(ValueError):
            compiler.compile([r1, r2], None)

    def testDynamicRoutesAreSortedByPriorityDescending(self) -> None:
        """Verify that dynamic routes are sorted by priority_score descending.

        Confirms that a more-specific route (higher static segment count)
        appears before a less-specific one after compilation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        compiler = RouteCompiler()
        low = _make_route_dict("GET", "/{any}", _handler_a)
        high = _make_route_dict("GET", "/users/{id:int}", _handler_b)
        compiled, _ = compiler.compile([low, high], None)
        dynamic = compiled["GET"]["dynamic"]
        self.assertGreaterEqual(
            dynamic[0].priority_score,
            dynamic[1].priority_score,
        )

    def testMultipleMethodsCompiledSeparately(self) -> None:
        """Verify that routes with different methods land in separate buckets.

        Confirms that GET and POST routes do not interfere with each other.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        compiler = RouteCompiler()
        get_route = _make_route_dict("GET", "/resource", _handler_a)
        post_route = _make_route_dict(
            "POST", "/resource", _handler_b, kind="api",
        )
        compiled, _ = compiler.compile([get_route, post_route], None)
        self.assertIn("GET", compiled)
        self.assertIn("POST", compiled)

    def testCompiledRouteKindPreserved(self) -> None:
        """Verify that the route kind is stored on the CompiledRoute.

        Confirms that 'api' kind is propagated from the raw dict to the
        compiled entity.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        compiler = RouteCompiler()
        route = _make_route_dict("GET", "/api/items", _handler_a, kind="api")
        compiled, _ = compiler.compile([route], None)
        cr = compiled["GET"]["static"]["/api/items"]
        self.assertEqual(cr.kind, "api")

    def testCompiledRouteNamePreserved(self) -> None:
        """Verify that the route name is stored on the CompiledRoute.

        Confirms that a named route retains its name after compilation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        compiler = RouteCompiler()
        route = _make_route_dict(
            "GET", "/named", _handler_a, name="route.named",
        )
        compiled, _ = compiler.compile([route], None)
        cr = compiled["GET"]["static"]["/named"]
        self.assertEqual(cr.name, "route.named")

    def testEmptyRouteListReturnsEmptyDict(self) -> None:
        """Verify that compiling an empty route list returns an empty dict.

        Confirms the method handles the empty input without errors.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        compiler = RouteCompiler()
        compiled, fallback = compiler.compile([], None)
        self.assertEqual(compiled, {})
        self.assertIsNone(fallback)

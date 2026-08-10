from orionis.http.middleware import BaseMiddleware
from orionis.http.routes.functions import (
    flatten_middleware,
    is_valid_handler,
    normalize_path,
    normalize_request_path,
    parse_action,
    strip_regex_anchors,
)
from orionis.test import TestCase

# ---------------------------------------------------------------------------
# Helpers used across multiple tests
# ---------------------------------------------------------------------------

def _plain_handler() -> None:
    """Standalone function used as a route action fixture."""

async def _async_handler() -> None:
    """Async function used as a route action fixture."""

class _InvokableCtrl:
    def __call__(self) -> None:
        """Invoke the controller."""

class _CtrlWithMethod:
    def index(self) -> None:
        """Handle index action."""

class _CtrlNoCall:
    """Controller that does not define __call__."""

class _ConcreteMiddleware(BaseMiddleware):
    async def handle(self, _request, call_next):  # type: ignore[override]
        """Pass through to the next handler."""
        return await call_next()

# ---------------------------------------------------------------------------
# normalize_path
# ---------------------------------------------------------------------------

class TestNormalizePath(TestCase):
    """Unit tests for the normalize_path route utility."""

    def testSimplePathUnchanged(self) -> None:
        """
        Verify that an already-canonical path is returned unchanged.

        Confirms that '/users/me' passes through without modification.
        """
        self.assertEqual(normalize_path("/users/me"), "/users/me")

    def testLeadingSlashAdded(self) -> None:
        """
        Verify that a leading slash is prepended when absent.

        Confirms that 'users' becomes '/users'.
        """
        self.assertEqual(normalize_path("users"), "/users")

    def testTrailingSlashRemoved(self) -> None:
        """
        Verify that a trailing slash is stripped from non-root paths.

        Confirms that '/users/' becomes '/users'.
        """
        self.assertEqual(normalize_path("/users/"), "/users")

    def testRootPathPreserved(self) -> None:
        """
        Verify that the root path '/' is returned unchanged.

        Confirms that rstrip does not produce an empty string for root.
        """
        self.assertEqual(normalize_path("/"), "/")

    def testConsecutiveSlashesCollapsed(self) -> None:
        """
        Verify that consecutive slashes are collapsed to one.

        Confirms that '//users//me/' is normalised to '/users/me'.
        """
        self.assertEqual(normalize_path("//users//me/"), "/users/me")

    def testLeadingWhitespaceStripped(self) -> None:
        """
        Verify that leading and trailing whitespace is removed.

        Confirms that '  /users  ' is normalised to '/users'.
        """
        self.assertEqual(normalize_path("  /users  "), "/users")

    def testDeepNestedPath(self) -> None:
        """
        Verify that deep nested paths are normalised correctly.

        Confirms a multi-segment path with no abnormalities passes
        through unchanged.
        """
        self.assertEqual(normalize_path("/a/b/c/d"), "/a/b/c/d")

# ---------------------------------------------------------------------------
# normalizeRequestPath
# ---------------------------------------------------------------------------

class TestNormalizeRequestPath(TestCase):
    """Unit tests for the normalizeRequestPath utility."""

    def testEmptyStringBecomesRoot(self) -> None:
        """
        Verify that an empty input becomes '/'.

        Confirms the fast path for missing path values.
        """
        self.assertEqual(normalize_request_path(""), "/")

    def testRootPreserved(self) -> None:
        """
        Verify that '/' is returned unchanged.

        Confirms the root path is not mutated.
        """
        self.assertEqual(normalize_request_path("/"), "/")

    def testLeadingSlashAdded(self) -> None:
        """
        Verify that a leading slash is prepended when absent.

        Confirms that 'users/me' becomes '/users/me'.
        """
        self.assertEqual(normalize_request_path("users/me"), "/users/me")

    def testTrailingSlashRemoved(self) -> None:
        """
        Verify that a trailing slash is stripped from non-root paths.

        Confirms that '/users/' becomes '/users'.
        """
        self.assertEqual(normalize_request_path("/users/"), "/users")

    def testNonRootSingleSegment(self) -> None:
        """
        Verify that a single-segment path without trailing slash is preserved.

        Confirms that '/ping' is returned unchanged.
        """
        self.assertEqual(normalize_request_path("/ping"), "/ping")

# ---------------------------------------------------------------------------
# stripRegexAnchors
# ---------------------------------------------------------------------------

class TestStripRegexAnchors(TestCase):
    """Unit tests for the stripRegexAnchors utility."""

    def testBothAnchorsRemoved(self) -> None:
        """
        Verify that both '^' and '$' anchors are stripped.

        Confirms that '^/users$' becomes '/users'.
        """
        self.assertEqual(strip_regex_anchors("^/users$"), "/users")

    def testOnlyStartAnchorRemoved(self) -> None:
        """
        Verify that only '^' is stripped when '$' is absent.

        Confirms that '^/users' becomes '/users'.
        """
        self.assertEqual(strip_regex_anchors("^/users"), "/users")

    def testOnlyEndAnchorRemoved(self) -> None:
        """
        Verify that only '$' is stripped when '^' is absent.

        Confirms that '/users$' becomes '/users'.
        """
        self.assertEqual(strip_regex_anchors("/users$"), "/users")

    def testNoAnchorsUnchanged(self) -> None:
        """
        Verify that a pattern without anchors is returned unchanged.

        Confirms that '/users' is not modified.
        """
        self.assertEqual(strip_regex_anchors("/users"), "/users")

    def testEmptyStringUnchanged(self) -> None:
        """
        Verify that an empty string is returned unchanged.

        Confirms the guard conditions handle empty input without error.
        """
        self.assertEqual(strip_regex_anchors(""), "")

# ---------------------------------------------------------------------------
# flattenMiddleware
# ---------------------------------------------------------------------------

class TestFlattenMiddleware(TestCase):
    """Unit tests for the flattenMiddleware utility."""

    def testSingleClassPassed(self) -> None:
        """
        Verify that a single middleware class is returned as a one-item list.

        Confirms the simplest usage with a lone class argument.
        """
        result = flatten_middleware(_ConcreteMiddleware)
        self.assertEqual(result, [_ConcreteMiddleware])

    def testMultipleClassesPassed(self) -> None:
        """
        Verify that multiple middleware classes are returned in order.

        Confirms that positional arguments are preserved in insertion order.
        """

        class _MW2(BaseMiddleware):
            async def handle(self, _request, call_next):  # type: ignore[override]
                return await call_next()

        result = flatten_middleware(_ConcreteMiddleware, _MW2)
        self.assertEqual(result, [_ConcreteMiddleware, _MW2])

    def testListWrappedMiddleware(self) -> None:
        """
        Verify that a list-wrapped middleware class is flattened.

        Confirms that passing [MiddlewareClass] is equivalent to passing
        MiddlewareClass directly.
        """
        result = flatten_middleware([_ConcreteMiddleware])
        self.assertEqual(result, [_ConcreteMiddleware])

    def testTupleWrappedMiddleware(self) -> None:
        """
        Verify that a tuple-wrapped middleware class is flattened.

        Confirms that passing (MiddlewareClass,) is accepted.
        """
        result = flatten_middleware((_ConcreteMiddleware,))
        self.assertEqual(result, [_ConcreteMiddleware])

    def testSetWrappedMiddleware(self) -> None:
        """
        Verify that a set-wrapped single middleware class is flattened.

        Confirms that set containers are accepted and produce a one-item
        list when only one class is present.
        """
        result = flatten_middleware({_ConcreteMiddleware})
        self.assertEqual(result, [_ConcreteMiddleware])

    def testFrozensetWrappedMiddleware(self) -> None:
        """
        Verify that a frozenset-wrapped middleware class is flattened.

        Confirms that frozenset containers are supported.
        """
        result = flatten_middleware(frozenset({_ConcreteMiddleware}))
        self.assertEqual(result, [_ConcreteMiddleware])

    def testNonMiddlewareRaisesTypeError(self) -> None:
        """
        Verify that a non-BaseMiddleware class raises TypeError.

        Confirms that invalid entries are rejected with the correct
        exception type.
        """
        with self.assertRaises(TypeError):
            flatten_middleware(object)  # type: ignore[arg-type]

    def testNonClassRaisesTypeError(self) -> None:
        """
        Verify that a non-class callable raises TypeError.

        Confirms that passing a function instead of a class is rejected.
        """
        with self.assertRaises(TypeError):
            flatten_middleware(_plain_handler)  # type: ignore[arg-type]

# ---------------------------------------------------------------------------
# isValidHandler
# ---------------------------------------------------------------------------

class TestIsValidHandler(TestCase):
    """Unit tests for the isValidHandler utility."""

    def testPlainFunctionIsValid(self) -> None:
        """
        Verify that a named plain function is a valid handler.

        Confirms that ordinary def functions return True.
        """
        self.assertTrue(is_valid_handler(_plain_handler))

    def testAsyncFunctionIsValid(self) -> None:
        """
        Verify that an async function is a valid handler.

        Confirms that coroutine functions pass the callable check.
        """
        self.assertTrue(is_valid_handler(_async_handler))

    def testLambdaIsInvalid(self) -> None:
        """
        Verify that a lambda is rejected as a handler.

        Confirms that anonymous lambdas return False.
        """
        self.assertFalse(is_valid_handler(lambda: None))

    def testNonCallableIsInvalid(self) -> None:
        """
        Verify that a non-callable value is rejected.

        Confirms that integers and other non-callables return False.
        """
        self.assertFalse(is_valid_handler(42))  # type: ignore[arg-type]

    def testCoroutineObjectIsInvalid(self) -> None:
        """
        Verify that a coroutine instance (not function) is rejected.

        Confirms that the guard for inspect.iscoroutine fires before
        the callable check.
        """
        coro = _async_handler()
        try:
            self.assertFalse(is_valid_handler(coro))
        finally:
            coro.close()

    def testInvokableClassIsValid(self) -> None:
        """
        Verify that an invokable class instance is a valid handler.

        Confirms that objects with __call__ defined pass the check.
        """
        self.assertTrue(is_valid_handler(_InvokableCtrl()))

# ---------------------------------------------------------------------------
# parseAction
# ---------------------------------------------------------------------------

class TestParseAction(TestCase):
    """Unit tests for the parseAction route-action parser."""

    def testParsePlainFunction(self) -> None:
        """
        Verify that a plain function is parsed to (function, None).

        Confirms the two-tuple returned for the function branch.
        """
        handler, method = parse_action(_plain_handler)
        self.assertIs(handler, _plain_handler)
        self.assertIsNone(method)

    def testParseInvokableClass(self) -> None:
        """
        Verify that an invokable class is parsed to (class, None).

        Confirms that a class defining __call__ is accepted and returned
        in the first tuple position.
        """
        handler, method = parse_action(_InvokableCtrl)
        self.assertIs(handler, _InvokableCtrl)
        self.assertIsNone(method)

    def testParseControllerList(self) -> None:
        """
        Verify that a [Controller, 'method'] list is parsed correctly.

        Confirms the two-tuple returns the class and method string.
        """
        ctrl, method = parse_action([_CtrlWithMethod, "index"])
        self.assertIs(ctrl, _CtrlWithMethod)
        self.assertEqual(method, "index")

    def testNonInvokableClassRaisesTypeError(self) -> None:
        """
        Verify that a bare class without __call__ raises TypeError.

        Confirms the guard for classes that lack an __call__ definition.
        """
        with self.assertRaises(TypeError):
            parse_action(_CtrlNoCall)

    def testListWithWrongLengthRaisesValueError(self) -> None:
        """
        Verify that a list with more or fewer than two elements raises ValueError.

        Confirms that only exactly [Controller, 'method'] is accepted.
        """
        with self.assertRaises(ValueError):
            parse_action([_CtrlWithMethod])

        with self.assertRaises(ValueError):
            parse_action([_CtrlWithMethod, "index", "extra"])

    def testListWithNonClassFirstElementRaisesTypeError(self) -> None:
        """
        Verify that a non-class first element raises TypeError.

        Confirms that the first list element must be a concrete class.
        """
        with self.assertRaises(TypeError):
            parse_action(["not_a_class", "index"])

    def testListWithNonStringSecondElementRaisesTypeError(self) -> None:
        """
        Verify that a non-string second element raises TypeError.

        Confirms that the second list element must be a string method name.
        """
        with self.assertRaises(TypeError):
            parse_action([_CtrlWithMethod, 99])  # type: ignore[list-item]

    def testListWithMissingMethodRaisesValueError(self) -> None:
        """
        Verify that specifying a missing method name raises ValueError.

        Confirms that the parser validates the method exists on the class.
        """
        with self.assertRaises(ValueError):
            parse_action([_CtrlWithMethod, "nonexistent_method"])

    def testLambdaRaisesTypeError(self) -> None:
        """
        Verify that a lambda raises TypeError.

        Confirms that lambdas are rejected as invalid action types.
        """
        with self.assertRaises(TypeError):
            parse_action(lambda: None)

    def testAsyncFunctionIsAccepted(self) -> None:
        """
        Verify that an async function is a valid action.

        Confirms that coroutine functions are parsed to (function, None).
        """
        handler, method = parse_action(_async_handler)
        self.assertIs(handler, _async_handler)
        self.assertIsNone(method)

    def testNonCallableRaisesTypeError(self) -> None:
        """
        Verify that a non-callable non-list value raises TypeError.

        Confirms that arbitrary objects are rejected.
        """
        with self.assertRaises(TypeError):
            parse_action(12345)  # type: ignore[arg-type]

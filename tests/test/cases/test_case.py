import inspect
import re
from orionis.test import TestCase
from orionis.test.cases import TestCase as PackageTestCase
from orionis.test.cases.case import (
    _DEFAULT_PATTERN,
    _LIFECYCLE_HOOKS,
    TestCase as CoreTestCase,
)

# Value returned by the probe method to prove the wrapper forwards results.
_PROBE_RESULT: str = "probe-executed"

# Lifecycle hook names that must never be wrapped by the application invoker.
_EXPECTED_HOOKS: frozenset[str] = frozenset({
    "setUp",
    "tearDown",
    "setUpClass",
    "tearDownClass",
    "asyncSetUp",
    "asyncTearDown",
})

def _probe_method(_self: object) -> str:
    """Return a sentinel value so wrapped execution can be observed."""
    return _PROBE_RESULT

def _make_probe(name: str, member: object) -> type:
    """Create a throwaway TestCase subclass exposing a single member."""
    return type("_Probe", (CoreTestCase,), {name: member})

class TestTestCaseDefinition(TestCase):

    def testDerivesFromIsolatedAsyncioTestCase(self) -> None:
        """
        Derive from the asynchronous test case of the standard library.

        Validates that coroutine test methods are supported natively by
        every Orionis test case.
        """
        ancestors = [base.__name__ for base in CoreTestCase.__mro__]
        self.assertIn("IsolatedAsyncioTestCase", ancestors)

    def testDerivesFromStandardTestCase(self) -> None:
        """
        Derive from the standard library test case.

        Validates that the full assertion API is inherited without
        re-implementation.
        """
        ancestors = [base.__name__ for base in CoreTestCase.__mro__]
        self.assertIn("TestCase", ancestors)

    def testPackageExportsTheSameClass(self) -> None:
        """
        Export a single test case class from every public entry point.

        Validates that the module and package shortcuts resolve to the
        very same object.
        """
        self.assertIs(TestCase, CoreTestCase)
        self.assertIs(PackageTestCase, CoreTestCase)

    def testDefaultPatternIsCompiled(self) -> None:
        """
        Compile the default discovery pattern once at import time.

        Validates that method matching never pays for repeated glob
        translation.
        """
        self.assertIsInstance(_DEFAULT_PATTERN, re.Pattern)
        self.assertIs(CoreTestCase._method_regex, _DEFAULT_PATTERN)

    def testLifecycleHooksAreExcludedFromWrapping(self) -> None:
        """
        Declare the complete catalogue of protected lifecycle hooks.

        Validates that setup and teardown callbacks are never routed
        through the dependency injection container.
        """
        self.assertEqual(_LIFECYCLE_HOOKS, _EXPECTED_HOOKS)

class TestTestCaseMethodPattern(TestCase):

    def tearDown(self) -> None:
        """
        Restore the default discovery pattern after each scenario.

        Guarantees that class level state is never leaked to the tests
        executed afterwards.
        """
        CoreTestCase.setMethodPattern("test*")

    def testCustomPatternReplacesTheDefault(self) -> None:
        """
        Match method names against a freshly supplied glob pattern.

        Validates that the compiled expression reflects the configured
        pattern instead of the default one.
        """
        CoreTestCase.setMethodPattern("check*")
        self.assertIsNotNone(CoreTestCase._method_regex.match("checkSomething"))
        self.assertIsNone(CoreTestCase._method_regex.match("testSomething"))

    def testPatternIsStoredAsCompiledExpression(self) -> None:
        """
        Store the configured pattern as a compiled regular expression.

        Validates that arbitrary glob syntax is translated once and
        reused for every lookup.
        """
        CoreTestCase.setMethodPattern("verify_*")
        self.assertIsInstance(CoreTestCase._method_regex, re.Pattern)
        self.assertIsNotNone(CoreTestCase._method_regex.match("verify_something"))

    def testDefaultPatternIsRestorable(self) -> None:
        """
        Restore the default behaviour by reapplying the default pattern.

        Validates that the engine can hand back control to conventional
        discovery after a custom run.
        """
        CoreTestCase.setMethodPattern("check*")
        CoreTestCase.setMethodPattern("test*")
        self.assertIsNotNone(CoreTestCase._method_regex.match("testSomething"))
        self.assertIsNone(CoreTestCase._method_regex.match("checkSomething"))

class TestTestCaseWrapping(TestCase):

    def tearDown(self) -> None:
        """
        Restore the default discovery pattern after each scenario.

        Guarantees that probes built with custom patterns cannot alter
        the discovery of the remaining tests.
        """
        CoreTestCase.setMethodPattern("test*")

    def testMatchingMethodIsWrapped(self) -> None:
        """
        Wrap the selected method with an asynchronous invoker.

        Validates that the instance shadows the class attribute with a
        coroutine function bound to the application context.
        """
        probe = _make_probe("testProbe", _probe_method)("testProbe")
        self.assertIn("testProbe", probe.__dict__)
        self.assertTrue(inspect.iscoroutinefunction(probe.testProbe))

    def testWrappedMethodKeepsItsIdentity(self) -> None:
        """
        Preserve the name and docstring of the wrapped method.

        Validates that reporting keeps showing the original method
        metadata after wrapping.
        """
        probe = _make_probe("testProbe", _probe_method)("testProbe")
        self.assertEqual(probe.testProbe.__name__, "_probe_method")
        self.assertEqual(probe.testProbe.__doc__, _probe_method.__doc__)

    async def testWrappedMethodRunsThroughTheApplication(self) -> None:
        """
        Execute the wrapped method through the application invoker.

        Validates that the returned value of the original method is
        forwarded to the caller unchanged.
        """
        probe = _make_probe("testProbe", _probe_method)("testProbe")
        self.assertEqual(await probe.testProbe(), _PROBE_RESULT)

    def testNonMatchingMethodIsNotWrapped(self) -> None:
        """
        Leave methods that do not match the pattern untouched.

        Validates that helper methods keep their synchronous behaviour.
        """
        probe = _make_probe("checkProbe", _probe_method)("checkProbe")
        self.assertNotIn("checkProbe", probe.__dict__)
        self.assertEqual(probe.checkProbe(), _PROBE_RESULT)

    def testPrivateMethodIsNotWrapped(self) -> None:
        """
        Leave underscore prefixed methods untouched.

        Validates that internal helpers are excluded even when the
        configured pattern would match them.
        """
        CoreTestCase.setMethodPattern("*")
        probe = _make_probe("_probe", _probe_method)("_probe")
        self.assertNotIn("_probe", probe.__dict__)

    def testLifecycleHookIsNotWrapped(self) -> None:
        """
        Leave lifecycle hooks untouched under a permissive pattern.

        Validates that setup callbacks keep the semantics expected by
        the standard library runner.
        """
        CoreTestCase.setMethodPattern("set*")
        probe = _make_probe("setUp", _probe_method)("setUp")
        self.assertNotIn("setUp", probe.__dict__)

    def testNonCallableAttributeIsNotWrapped(self) -> None:
        """
        Leave non callable attributes untouched.

        Validates that only executable members are routed through the
        application invoker.
        """
        probe = _make_probe("testValue", 7)("testValue")
        self.assertNotIn("testValue", probe.__dict__)
        self.assertEqual(probe.testValue, 7)

    def testDefaultMethodNameIsNotWrapped(self) -> None:
        """
        Leave the default runTest placeholder untouched.

        Validates that instantiating a case without an explicit method
        name performs no wrapping at all.
        """
        probe = _make_probe("testProbe", _probe_method)()
        self.assertNotIn("testProbe", probe.__dict__)

class TestTestCaseResolution(TestCase):

    def testResolveTestReturnsCoroutineFunction(self) -> None:
        """
        Return a coroutine function from the resolver.

        Validates that wrapped methods are always awaited by the
        asynchronous runner.
        """
        probe = _make_probe("testProbe", _probe_method)("testProbe")
        wrapped = probe._resolveTest(_probe_method)
        self.assertTrue(inspect.iscoroutinefunction(wrapped))

    async def testResolveTestExecutesTheWrappedCallable(self) -> None:
        """
        Execute the wrapped callable and forward its produced value.

        Validates that the resolver keeps the calling convention of the
        original bound method intact.
        """
        probe = _make_probe("checkProbe", _probe_method)("checkProbe")
        wrapped = probe._resolveTest(probe.checkProbe)
        self.assertEqual(await wrapped(), _PROBE_RESULT)

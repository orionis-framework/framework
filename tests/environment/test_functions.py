from orionis.environment import functions as functions_module
from orionis.environment.functions import env
from orionis.test import TestCase

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

class _RecordingEnv:
    """Env facade double recording every lookup it receives."""

    __slots__ = ("calls", "value")

    def __init__(self, value: object = None) -> None:
        self.value: object = value
        self.calls: list[tuple[str, object]] = []

    def get(self, key: str, default: object | None = None) -> object:
        """Record the lookup and return the canned value."""
        self.calls.append((key, default))
        return self.value

# ---------------------------------------------------------------------------
# TestEnvHelperDelegation
# ---------------------------------------------------------------------------

class TestEnvHelperDelegation(TestCase):

    def setUp(self) -> None:
        """
        Replace the Env facade with a controllable double.

        Keeps the helper isolated from the real ``.env`` file so the
        delegation contract can be asserted deterministically.
        """
        self._original_facade = functions_module.Env
        self._facade = _RecordingEnv("recorded")
        functions_module.Env = self._facade

    def tearDown(self) -> None:
        """
        Restore the original Env facade after each test.

        Guarantees that module-level state is never leaked to other test
        cases running in the same process.
        """
        functions_module.Env = self._original_facade

    def testForwardsTheRequestedKey(self) -> None:
        """
        Forward the requested key to the facade unchanged.

        Validates that the helper performs no normalisation of its own
        before delegating the lookup.
        """
        env("APP_NAME")
        self.assertEqual(self._facade.calls, [("APP_NAME", None)])

    def testForwardsNoneAsTheImplicitDefault(self) -> None:
        """
        Forward ``None`` when the caller omits a default.

        Validates that the helper always supplies the second positional
        argument expected by the facade.
        """
        env("MISSING_KEY")
        self.assertIsNone(self._facade.calls[0][1])

    def testForwardsTheExplicitDefault(self) -> None:
        """
        Forward the caller-supplied default to the facade.

        Validates that fallback values reach ``Env.get`` untouched.
        """
        env("MISSING_KEY", "fallback")
        self.assertEqual(self._facade.calls, [("MISSING_KEY", "fallback")])

    def testReturnsTheFacadeResultUnchanged(self) -> None:
        """
        Return the exact object produced by the facade.

        Validates that the helper never copies or coerces the resolved
        value before handing it back to the caller.
        """
        expected = [1, 2, 3]
        self._facade.value = expected
        self.assertIs(env("LIST_KEY"), expected)

    def testReturnsNoneWhenTheFacadeResolvesNothing(self) -> None:
        """
        Return ``None`` when the facade resolves nothing.

        Validates that a missing variable without a default surfaces as a
        plain ``None`` instead of an exception.
        """
        self._facade.value = None
        self.assertIsNone(env("MISSING_KEY"))

    def testDelegatesExactlyOncePerCall(self) -> None:
        """
        Delegate exactly one lookup per helper invocation.

        Validates that the helper does not retry or pre-warm the facade,
        which would double the cost of every configuration read.
        """
        env("FIRST_KEY")
        env("SECOND_KEY")
        self.assertEqual(len(self._facade.calls), 2)

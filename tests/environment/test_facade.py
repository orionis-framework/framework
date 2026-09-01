import os
import shutil
import tempfile
from pathlib import Path
from typing import ClassVar
from orionis.environment import facade as facade_module
from orionis.environment.core.dot_env import DotEnv
from orionis.environment.enums import EnvironmentValueType
from orionis.environment.facade import Env
from orionis.support.patterns.singleton.meta import _MISSING
from orionis.test import TestCase

# Message carried by the doubles that make the reader fail on purpose.
_UNAVAILABLE: str = "environment file is unavailable"

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

class _UnavailableDotEnv:
    """Reader double whose construction always fails."""

    __slots__ = ()

    failure: ClassVar[type[Exception]] = OSError

    def __init__(self) -> None:
        raise self.failure(_UNAVAILABLE)

class _OsErrorDotEnv(_UnavailableDotEnv):
    """Reader double failing with a filesystem error."""

    __slots__ = ()

    failure: ClassVar[type[Exception]] = OSError

class _ValueErrorDotEnv(_UnavailableDotEnv):
    """Reader double failing with a decoding error."""

    __slots__ = ()

    failure: ClassVar[type[Exception]] = ValueError

class _RuntimeErrorDotEnv(_UnavailableDotEnv):
    """Reader double failing with an error the facade must not swallow."""

    __slots__ = ()

    failure: ClassVar[type[Exception]] = RuntimeError

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

class _EnvTestCase(TestCase):

    def setUp(self) -> None:
        """
        Install a throwaway `.env` file behind the facade.

        Isolates every test from the repository `.env` file and from the
        process environment shared with the rest of the suite.
        """
        self._previous_singleton = vars(DotEnv)["_singleton_instance"]
        type.__setattr__(DotEnv, "_singleton_instance", _MISSING)
        self._directory = Path(tempfile.mkdtemp())
        self._env_path = self._directory / ".env"
        DotEnv(path=str(self._env_path))
        self._tracked_keys: list[str] = []

    def tearDown(self) -> None:
        """
        Restore the previous singleton and clean every side effect.

        Removes the tracked process variables and the temporary directory
        so no state survives the test case.
        """
        for key in self._tracked_keys:
            os.environ.pop(key, None)
        shutil.rmtree(self._directory, ignore_errors=True)
        type.__setattr__(
            DotEnv,
            "_singleton_instance",
            self._previous_singleton,
        )

    def _trackKey(self, key: str) -> str:
        """
        Register a variable for automatic cleanup after the test.

        Parameters
        ----------
        key : str
            Environment variable name to remove during teardown.

        Returns
        -------
        str
            The same key, so it can be used inline at the call site.
        """
        if key not in self._tracked_keys:
            self._tracked_keys.append(key)
        return key

# ---------------------------------------------------------------------------
# TestEnvGet
# ---------------------------------------------------------------------------

class TestEnvGet(_EnvTestCase):

    def testReturnsTheStoredValue(self) -> None:
        """
        Return the value stored for an existing variable.

        Validates the read path most of the framework configuration
        relies on.
        """
        Env.set(self._trackKey("FACADE_KEY"), "value")
        self.assertEqual(Env.get("FACADE_KEY"), "value")

    def testReturnsNoneForAnUnknownVariable(self) -> None:
        """
        Return ``None`` when the variable is not defined.

        Validates the implicit default of the facade.
        """
        self.assertIsNone(Env.get("UNDEFINED_KEY"))

    def testForwardsTheSuppliedDefault(self) -> None:
        """
        Forward the caller default when the variable is not defined.

        Validates that the fallback reaches the reader untouched, whatever
        its type.
        """
        self.assertEqual(Env.get("UNDEFINED_KEY", "fallback"), "fallback")
        self.assertEqual(Env.get("UNDEFINED_KEY", 7), 7)

    def testAppliesTheDeclaredTypeOnRead(self) -> None:
        """
        Apply the declared type when reading a hinted variable.

        Validates that the facade returns native Python objects rather
        than the raw stored text.
        """
        Env.set(self._trackKey("TYPED_KEY"), 42, "int")
        self.assertEqual(Env.get("TYPED_KEY"), 42)

    def testRejectsAnInvalidVariableName(self) -> None:
        """
        Reject names that break the environment naming convention.

        Validates that key validation errors reach the caller instead of
        being converted into a missing value.
        """
        with self.assertRaises(ValueError):
            Env.get("lower_case")

# ---------------------------------------------------------------------------
# TestEnvSet
# ---------------------------------------------------------------------------

class TestEnvSet(_EnvTestCase):

    def testReportsASuccessfulAssignment(self) -> None:
        """
        Report success after storing a variable.

        Validates the boolean contract exposed by the facade.
        """
        self.assertTrue(Env.set(self._trackKey("FACADE_KEY"), "value"))

    def testRestoresEverySupportedValueType(self) -> None:
        """
        Restore every supported value type through the facade.

        Validates the inferred serialisation for the whole catalogue of
        configuration values.
        """
        for index, value in enumerate(
            ("text", 42, 2.5, True, False, [1, 2], {"a": 1}, (1, 2), {1, 2}),
        ):
            key = self._trackKey(f"FACADE_VALUE_{index}")
            Env.set(key, value, only_os=True)
            self.assertEqual(Env.get(key), value)

    def testHonoursAnEnumeratedTypeHint(self) -> None:
        """
        Honour a type hint expressed as an enumeration member.

        Validates that the hint reaches the reader in the exact form the
        caster expects.
        """
        key = self._trackKey("FACADE_SECRET")
        Env.set(key, "secret", EnvironmentValueType.BASE64, only_os=True)
        self.assertEqual(Env.get(key), "secret")

    def testOverwritesAnExistingValue(self) -> None:
        """
        Overwrite the previous value of an existing variable.

        Validates that repeated assignments never accumulate duplicated
        entries.
        """
        key = self._trackKey("FACADE_KEY")
        Env.set(key, "first")
        Env.set(key, "second")
        self.assertEqual(Env.get(key), "second")

    def testSkipsTheFileWhenOnlyTheProcessIsTargeted(self) -> None:
        """
        Skip the `.env` file when only the process is targeted.

        Validates the ephemeral assignment used for runtime overrides
        that must never be persisted.
        """
        key = self._trackKey("FACADE_EPHEMERAL")
        Env.set(key, "value", only_os=True)
        self.assertNotIn(key, self._env_path.read_text(encoding="utf-8"))
        self.assertEqual(Env.get(key), "value")

# ---------------------------------------------------------------------------
# TestEnvUnset
# ---------------------------------------------------------------------------

class TestEnvUnset(_EnvTestCase):

    def testReportsASuccessfulRemoval(self) -> None:
        """
        Report success after removing a variable.

        Validates the boolean contract exposed by the facade.
        """
        key = self._trackKey("FACADE_KEY")
        Env.set(key, "value")
        self.assertTrue(Env.unset(key))

    def testStopsResolvingTheRemovedVariable(self) -> None:
        """
        Stop resolving a variable once it has been removed.

        Validates that the removal reaches both the file and the process
        environment.
        """
        key = self._trackKey("FACADE_KEY")
        Env.set(key, "value")
        Env.unset(key)
        self.assertIsNone(Env.get(key))
        self.assertNotIn(key, Env.all())

    def testKeepsTheFileEntryWhenOnlyTheProcessIsTargeted(self) -> None:
        """
        Keep the file entry when only the process is targeted.

        Validates the ephemeral removal that hides a value from the
        running process without editing the file.
        """
        key = self._trackKey("FACADE_KEY")
        Env.set(key, "value")
        Env.unset(key, only_os=True)
        self.assertIn(key, Env.all())
        self.assertIsNone(Env.get(key))

    def testTreatsAnUnknownVariableAsAlreadyRemoved(self) -> None:
        """
        Treat an unknown variable as already removed.

        Validates the idempotent contract that lets clean-up routines run
        unconditionally.
        """
        self.assertTrue(Env.unset("UNDEFINED_KEY"))

# ---------------------------------------------------------------------------
# TestEnvAll
# ---------------------------------------------------------------------------

class TestEnvAll(_EnvTestCase):

    def testReturnsAnEmptyMappingForAnEmptyFile(self) -> None:
        """
        Return an empty mapping when the file holds no variables.

        Validates the freshly scaffolded project scenario.
        """
        self.assertEqual(Env.all(), {})

    def testReturnsEveryPersistedVariableParsed(self) -> None:
        """
        Return every persisted variable already parsed.

        Validates that the snapshot is directly usable instead of holding
        raw strings.
        """
        Env.set(self._trackKey("FACADE_NUMBER"), 42)
        Env.set(self._trackKey("FACADE_TEXT"), "text")
        self.assertEqual(
            Env.all(),
            {"FACADE_NUMBER": 42, "FACADE_TEXT": "text"},
        )

# ---------------------------------------------------------------------------
# TestEnvReload
# ---------------------------------------------------------------------------

class TestEnvReload(_EnvTestCase):

    def testReportsASuccessfulReload(self) -> None:
        """
        Report success after reloading the file.

        Validates the boolean contract exposed by the facade.
        """
        self.assertTrue(Env.reload())

    def testPicksUpExternallyAddedVariables(self) -> None:
        """
        Pick up variables added to the file by another process.

        Validates the use case of an operator editing `.env` while the
        application is running.
        """
        key = self._trackKey("FACADE_EXTERNAL")
        self._env_path.write_text(f"{key}=external\n", encoding="utf-8")
        Env.reload()
        self.assertEqual(Env.get(key), "external")

    def testKeepsTheSingletonAlive(self) -> None:
        """
        Keep the underlying reader instance alive across reloads.

        Validates that reloading refreshes the state in place instead of
        rebuilding the singleton.
        """
        before = DotEnv()
        Env.reload()
        self.assertIs(DotEnv(), before)

# ---------------------------------------------------------------------------
# TestEnvReloadFailures
# ---------------------------------------------------------------------------

class _EnvReloadFailureTestCase(TestCase):

    dot_env_double: ClassVar[type] = _OsErrorDotEnv

    def setUp(self) -> None:
        """
        Replace the reader with a double whose construction fails.

        Keeps the failure deterministic without depending on filesystem
        permissions that differ across platforms.
        """
        self._original_dot_env = facade_module.DotEnv
        facade_module.DotEnv = self.dot_env_double

    def tearDown(self) -> None:
        """
        Restore the original reader after each test.

        Guarantees that module-level state is never leaked to other test
        cases running in the same process.
        """
        facade_module.DotEnv = self._original_dot_env

class TestEnvReloadFilesystemFailure(_EnvReloadFailureTestCase):

    dot_env_double: ClassVar[type] = _OsErrorDotEnv

    def testReportsFailureInsteadOfRaising(self) -> None:
        """
        Report failure when the `.env` file cannot be accessed.

        Validates that a broken environment file degrades the reload into
        a ``False`` result instead of crashing the caller.
        """
        self.assertFalse(Env.reload())

class TestEnvReloadDecodingFailure(_EnvReloadFailureTestCase):

    dot_env_double: ClassVar[type] = _ValueErrorDotEnv

    def testReportsFailureInsteadOfRaising(self) -> None:
        """
        Report failure when the `.env` file cannot be decoded.

        Validates that a malformed environment file degrades the reload
        into a ``False`` result instead of crashing the caller.
        """
        self.assertFalse(Env.reload())

class TestEnvReloadUnexpectedFailure(_EnvReloadFailureTestCase):

    dot_env_double: ClassVar[type] = _RuntimeErrorDotEnv

    def testPropagatesUnexpectedFailures(self) -> None:
        """
        Propagate failures outside the handled categories.

        Validates that the facade only absorbs filesystem and decoding
        errors, keeping genuine defects visible.
        """
        with self.assertRaises(RuntimeError):
            Env.reload()

# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from typing import ClassVar
from orionis.environment import Env
from orionis.environment import facade as facade_module
from orionis.environment.core.dot_env import DotEnv
from orionis.environment.enums import EnvironmentValueType
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
        """Raise the configured environment error during construction.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        Exception
            Raised by this helper to exercise the failure path.
        """
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
        """Isolate the file, singleton, and process variables for this test.

        Returns
        -------
        None
            No return value.
        """
        super().setUp()
        self.addCleanup(
            type.__setattr__,
            DotEnv,
            "_singleton_instance",
            vars(DotEnv)["_singleton_instance"],
        )
        type.__setattr__(DotEnv, "_singleton_instance", _MISSING)
        self.enterContext(patch.dict(os.environ))
        os.environ.pop("UNDEFINED_KEY", None)
        self._directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self._env_path = self._directory / ".env"
        DotEnv(path=str(self._env_path))


# ---------------------------------------------------------------------------
# TestEnvGet
# ---------------------------------------------------------------------------


class TestEnvGet(_EnvTestCase):
    def testReturnsTheStoredValue(self) -> None:
        """Return the value stored for an existing variable.

        Validates the read path most of the framework configuration
        relies on.

        Returns
        -------
        None
            No return value.
        """
        Env.set("FACADE_KEY", "value")
        self.assertEqual(Env.get("FACADE_KEY"), "value")

    def testReturnsNoneForAnUnknownVariable(self) -> None:
        """Return ``None`` when the variable is not defined.

        Validates the implicit default of the facade.

        Returns
        -------
        None
            No return value.
        """
        self.assertIsNone(Env.get("UNDEFINED_KEY"))

    def testForwardsTheSuppliedDefault(self) -> None:
        """Forward the caller default when the variable is not defined.

        Validates that the fallback reaches the reader untouched, whatever
        its type.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(Env.get("UNDEFINED_KEY", "fallback"), "fallback")
        self.assertEqual(Env.get("UNDEFINED_KEY", 7), 7)

    def testAppliesTheDeclaredTypeOnRead(self) -> None:
        """Apply the declared type when reading a hinted variable.

        Validates that the facade returns native Python objects rather
        than the raw stored text.

        Returns
        -------
        None
            No return value.
        """
        Env.set("TYPED_KEY", 42, "int")
        self.assertEqual(Env.get("TYPED_KEY"), 42)

    def testRejectsAnInvalidVariableName(self) -> None:
        """Reject names that break the environment naming convention.

        Validates that key validation errors reach the caller instead of
        being converted into a missing value.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(ValueError):
            Env.get("lower_case")


# ---------------------------------------------------------------------------
# TestEnvSet
# ---------------------------------------------------------------------------


class TestEnvSet(_EnvTestCase):
    def testReportsASuccessfulAssignment(self) -> None:
        """Report success after storing a variable.

        Validates the boolean contract exposed by the facade.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(Env.set("FACADE_KEY", "value"))

    def testRestoresEverySupportedValueType(self) -> None:
        """Restore every supported value type through the facade.

        Validates the inferred serialisation for the whole catalogue of
        configuration values.

        Returns
        -------
        None
            No return value.
        """
        for index, value in enumerate(
            ("text", 42, 2.5, True, False, [1, 2], {"a": 1}, (1, 2), {1, 2}),
        ):
            key = f"FACADE_VALUE_{index}"
            Env.set(key, value, only_os=True)
            self.assertEqual(Env.get(key), value)

    def testHonoursAnEnumeratedTypeHint(self) -> None:
        """Honour a type hint expressed as an enumeration member.

        Validates that the hint reaches the reader in the exact form the
        caster expects.

        Returns
        -------
        None
            No return value.
        """
        key = "FACADE_SECRET"
        Env.set(key, "secret", EnvironmentValueType.BASE64, only_os=True)
        self.assertEqual(Env.get(key), "secret")

    def testOverwritesAnExistingValue(self) -> None:
        """Overwrite the previous value of an existing variable.

        Validates that repeated assignments never accumulate duplicated
        entries.

        Returns
        -------
        None
            No return value.
        """
        key = "FACADE_KEY"
        Env.set(key, "first")
        Env.set(key, "second")
        self.assertEqual(Env.get(key), "second")

    def testSkipsTheFileWhenOnlyTheProcessIsTargeted(self) -> None:
        """Skip the `.env` file when only the process is targeted.

        Validates the ephemeral assignment used for runtime overrides
        that must never be persisted.

        Returns
        -------
        None
            No return value.
        """
        key = "FACADE_EPHEMERAL"
        Env.set(key, "value", only_os=True)
        self.assertNotIn(key, self._env_path.read_text(encoding="utf-8"))
        self.assertEqual(Env.get(key), "value")


# ---------------------------------------------------------------------------
# TestEnvUnset
# ---------------------------------------------------------------------------


class TestEnvUnset(_EnvTestCase):
    def testReportsASuccessfulRemoval(self) -> None:
        """Report success after removing a variable.

        Validates the boolean contract exposed by the facade.

        Returns
        -------
        None
            No return value.
        """
        key = "FACADE_KEY"
        Env.set(key, "value")
        self.assertTrue(Env.unset(key))

    def testStopsResolvingTheRemovedVariable(self) -> None:
        """Stop resolving a variable once it has been removed.

        Validates that the removal reaches both the file and the process
        environment.

        Returns
        -------
        None
            No return value.
        """
        key = "FACADE_KEY"
        Env.set(key, "value")
        Env.unset(key)
        self.assertIsNone(Env.get(key))
        self.assertNotIn(key, Env.all())

    def testKeepsTheFileEntryWhenOnlyTheProcessIsTargeted(self) -> None:
        """Keep the file entry when only the process is targeted.

        Validates the ephemeral removal that hides a value from the
        running process without editing the file.

        Returns
        -------
        None
            No return value.
        """
        key = "FACADE_KEY"
        Env.set(key, "value")
        Env.unset(key, only_os=True)
        self.assertIn(key, Env.all())
        self.assertIsNone(Env.get(key))

    def testTreatsAnUnknownVariableAsAlreadyRemoved(self) -> None:
        """Treat an unknown variable as already removed.

        Validates the idempotent contract that lets clean-up routines run
        unconditionally.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(Env.unset("UNDEFINED_KEY"))


# ---------------------------------------------------------------------------
# TestEnvAll
# ---------------------------------------------------------------------------


class TestEnvAll(_EnvTestCase):
    def testReturnsAnEmptyMappingForAnEmptyFile(self) -> None:
        """Return an empty mapping when the file holds no variables.

        Validates the freshly scaffolded project scenario.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(Env.all(), {})

    def testReturnsEveryPersistedVariableParsed(self) -> None:
        """Return every persisted variable already parsed.

        Validates that the snapshot is directly usable instead of holding
        raw strings.

        Returns
        -------
        None
            No return value.
        """
        Env.set("FACADE_NUMBER", 42)
        Env.set("FACADE_TEXT", "text")
        self.assertEqual(
            Env.all(),
            {"FACADE_NUMBER": 42, "FACADE_TEXT": "text"},
        )


# ---------------------------------------------------------------------------
# TestEnvReload
# ---------------------------------------------------------------------------


class TestEnvReload(_EnvTestCase):
    def testPropagatesDecodingFailureFromTheRealFile(self) -> None:
        """Preserve the real reload failure when the selected file is not UTF-8.

        Returns
        -------
        None
            No return value.
        """
        self._env_path.write_bytes(b"ORIONIS_BAD_ENCODING=\xff\xfe\n")
        with self.assertRaises(RuntimeError) as caught:
            Env.reload()
        self.assertIsInstance(caught.exception.__cause__, UnicodeDecodeError)

    def testReportsASuccessfulReload(self) -> None:
        """Report success after reloading the file.

        Validates the boolean contract exposed by the facade.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(Env.reload())

    def testPicksUpExternallyAddedVariables(self) -> None:
        """Pick up variables added to the file by another process.

        Validates the use case of an operator editing `.env` while the
        application is running.

        Returns
        -------
        None
            No return value.
        """
        key = "FACADE_EXTERNAL"
        self._env_path.write_text(f"{key}=external\n", encoding="utf-8")
        Env.reload()
        self.assertEqual(Env.get(key), "external")

    def testKeepsTheSingletonAlive(self) -> None:
        """Keep the underlying reader instance alive across reloads.

        Validates that reloading refreshes the state in place instead of
        rebuilding the singleton.

        Returns
        -------
        None
            No return value.
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
        """Replace the reader with a double whose construction fails.

        Keeps the failure deterministic without depending on filesystem
        permissions that differ across platforms.

        Returns
        -------
        None
            No return value.
        """
        super().setUp()
        self.enterContext(patch.object(facade_module, "DotEnv", self.dot_env_double))


class TestEnvReloadFilesystemFailure(_EnvReloadFailureTestCase):
    dot_env_double: ClassVar[type] = _OsErrorDotEnv

    def testReportsFailureInsteadOfRaising(self) -> None:
        """Report failure when the `.env` file cannot be accessed.

        Validates that a broken environment file degrades the reload into
        a ``False`` result instead of crashing the caller.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Env.reload())


class TestEnvReloadDecodingFailure(_EnvReloadFailureTestCase):
    dot_env_double: ClassVar[type] = _ValueErrorDotEnv

    def testReportsFailureInsteadOfRaising(self) -> None:
        """Report failure when the `.env` file cannot be decoded.

        Validates that a malformed environment file degrades the reload
        into a ``False`` result instead of crashing the caller.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Env.reload())


class TestEnvReloadUnexpectedFailure(_EnvReloadFailureTestCase):
    dot_env_double: ClassVar[type] = _RuntimeErrorDotEnv

    def testPropagatesUnexpectedFailures(self) -> None:
        """Propagate failures outside the handled categories.

        Validates that the facade only absorbs filesystem and decoding
        errors, keeping genuine defects visible.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(RuntimeError):
            Env.reload()


# ---------------------------------------------------------------------------
# TestEnvLayout
# ---------------------------------------------------------------------------


class TestEnvLayout(TestCase):
    def testDeclaresEmptySlots(self) -> None:
        """Declare empty slots for a facade that holds no state.

        Validates that the contract declaring ``__slots__`` is honoured by
        its only implementation.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(Env.__slots__, ())

    def testDoesNotExposeAnInstanceDictionary(self) -> None:
        """Keep instances free of a dictionary.

        Validates that an accidental instantiation cannot be used to hold
        state that the classmethods would ignore.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(hasattr(Env(), "__dict__"))

import os
import shutil
import tempfile
from pathlib import Path
from orionis.environment.core.dot_env import DotEnv
from orionis.environment.enums import EnvironmentValueType
from orionis.support.patterns.singleton.meta import _MISSING
from orionis.test import TestCase

# Path segment used for a `.env` file that can never be created.
_UNREACHABLE_DIRECTORY: str = "missing-directory"

# Path containing a null byte, rejected by every filesystem call.
_MALFORMED_PATH: str = "broken\x00path"

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

class _OpaqueValue:
    """Value outside the supported catalogue with a stable text form."""

    __slots__ = ()

    def __str__(self) -> str:
        """Return the canonical text form of the value."""
        return "opaque-value"

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

class _DotEnvTestCase(TestCase):

    def setUp(self) -> None:
        """
        Install a throwaway `.env` file as the active singleton.

        Isolates every test from the repository `.env` file and from the
        process environment shared with the rest of the suite.
        """
        self._previous_singleton = vars(DotEnv)["_singleton_instance"]
        type.__setattr__(DotEnv, "_singleton_instance", _MISSING)
        self._directory = Path(tempfile.mkdtemp())
        self._env_path = self._directory / ".env"
        self._dot_env = DotEnv(path=str(self._env_path))
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

    def _fileContents(self) -> str:
        """
        Read the raw contents of the temporary `.env` file.

        Returns
        -------
        str
            Everything currently persisted on disk.
        """
        return self._env_path.read_text(encoding="utf-8")

    def _writeRawEntry(self, key: str, raw: str) -> None:
        """
        Publish a raw, unserialised value in the process environment.

        Parameters
        ----------
        key : str
            Environment variable name to publish.
        raw : str
            Exact string the reader must parse.
        """
        os.environ[self._trackKey(key)] = raw

# ---------------------------------------------------------------------------
# TestDotEnvInitialisation
# ---------------------------------------------------------------------------

class TestDotEnvInitialisation(TestCase):

    def setUp(self) -> None:
        """
        Detach the singleton and prepare an empty working directory.

        Allows each test to build its own instance without leaking state
        into the rest of the suite.
        """
        self._previous_singleton = vars(DotEnv)["_singleton_instance"]
        type.__setattr__(DotEnv, "_singleton_instance", _MISSING)
        self._directory = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        """
        Restore the previous singleton and drop the working directory.

        Guarantees that the shared application state is left untouched.
        """
        os.environ.pop("INIT_SEEDED_KEY", None)
        shutil.rmtree(self._directory, ignore_errors=True)
        type.__setattr__(
            DotEnv,
            "_singleton_instance",
            self._previous_singleton,
        )

    def testCreatesTheFileWhenItDoesNotExist(self) -> None:
        """
        Create an empty `.env` file when none is present.

        Validates the bootstrap behaviour of a freshly scaffolded project
        that has no environment file yet.
        """
        target = self._directory / ".env"
        DotEnv(path=str(target))
        self.assertTrue(target.is_file())

    def testKeepsTheContentsOfAnExistingFile(self) -> None:
        """
        Preserve the contents of an existing `.env` file.

        Validates that initialisation never truncates a configuration
        file that already holds values.
        """
        target = self._directory / ".env"
        target.write_text("INIT_SEEDED_KEY=seeded\n", encoding="utf-8")
        DotEnv(path=str(target))
        self.assertIn("INIT_SEEDED_KEY=seeded", target.read_text(encoding="utf-8"))

    def testPublishesFileValuesInTheProcessEnvironment(self) -> None:
        """
        Publish every file value in the process environment.

        Validates the eager load that makes variables visible to code
        reading ``os.environ`` directly.
        """
        target = self._directory / ".env"
        target.write_text("INIT_SEEDED_KEY=seeded\n", encoding="utf-8")
        DotEnv(path=str(target))
        self.assertEqual(os.environ.get("INIT_SEEDED_KEY"), "seeded")

    def testResolvesTheSuppliedPath(self) -> None:
        """
        Resolve the supplied path before touching the filesystem.

        Validates that relative segments are collapsed so the same file is
        used regardless of how the path was spelled.
        """
        nested = self._directory / "nested"
        nested.mkdir()
        DotEnv(path=str(nested / ".." / ".env"))
        self.assertTrue((self._directory / ".env").is_file())

    def testReusesTheSingletonInstance(self) -> None:
        """
        Reuse the same instance for every subsequent construction.

        Validates the singleton contract that keeps one authoritative
        reader per process.
        """
        first = DotEnv(path=str(self._directory / ".env"))
        second = DotEnv(path=str(self._directory / "ignored.env"))
        self.assertIs(first, second)

    def testReportsAnUnreachableFileAsOsError(self) -> None:
        """
        Raise OSError when the `.env` file cannot be created.

        Validates the handler that reports a misconfigured path with the
        offending location included in the message.
        """
        target = self._directory / _UNREACHABLE_DIRECTORY / ".env"
        with self.assertRaises(OSError) as ctx:
            DotEnv(path=str(target))
        self.assertIn("Failed to create or access", str(ctx.exception))

    def testReportsAnyOtherFailureAsRuntimeError(self) -> None:
        """
        Raise RuntimeError for failures that are not filesystem errors.

        Validates the last-resort handler that keeps initialisation from
        leaking arbitrary exception types to the bootstrap sequence.
        """
        with self.assertRaises(RuntimeError) as ctx:
            DotEnv(path=_MALFORMED_PATH)
        self.assertIn("unexpected error occurred", str(ctx.exception))

    def testLeavesNoSingletonBehindAfterAFailure(self) -> None:
        """
        Leave no half-built instance behind when initialisation fails.

        Validates that a later, valid construction is not served with the
        broken instance produced by a failed attempt.
        """
        with self.assertRaises(OSError):
            DotEnv(path=str(self._directory / _UNREACHABLE_DIRECTORY / ".env"))
        self.assertIs(vars(DotEnv)["_singleton_instance"], _MISSING)

# ---------------------------------------------------------------------------
# TestDotEnvSet
# ---------------------------------------------------------------------------

class TestDotEnvSet(_DotEnvTestCase):

    def testReportsASuccessfulAssignment(self) -> None:
        """
        Report success after storing a variable.

        Validates the boolean contract relied upon by the console
        commands that write configuration.
        """
        self.assertTrue(self._dot_env.set(self._trackKey("PLAIN_KEY"), "value"))

    def testPersistsTheValueInTheFile(self) -> None:
        """
        Persist the assigned value in the `.env` file.

        Validates that the variable survives a process restart.
        """
        self._dot_env.set(self._trackKey("PLAIN_KEY"), "value")
        self.assertIn("PLAIN_KEY", self._fileContents())

    def testPublishesTheValueInTheProcessEnvironment(self) -> None:
        """
        Publish the assigned value in the process environment.

        Validates that the change is visible immediately, without waiting
        for a reload.
        """
        self._dot_env.set(self._trackKey("PLAIN_KEY"), "value")
        self.assertEqual(os.environ.get("PLAIN_KEY"), "value")

    def testOverwritesAnExistingValue(self) -> None:
        """
        Overwrite the previous value of an existing variable.

        Validates that repeated assignments never accumulate duplicated
        entries.
        """
        key = self._trackKey("PLAIN_KEY")
        self._dot_env.set(key, "first")
        self._dot_env.set(key, "second")
        self.assertEqual(self._dot_env.get(key), "second")

    def testRestoresEverySupportedValueType(self) -> None:
        """
        Restore every supported value type without a declared hint.

        Validates the inferred serialisation used by the majority of the
        framework configuration entries.
        """
        for index, value in enumerate(
            ("text", 42, 2.5, True, False, [1, 2], {"a": 1}, (1, 2), {1, 2}),
        ):
            key = self._trackKey(f"INFERRED_KEY_{index}")
            self._dot_env.set(key, value, only_os=True)
            self.assertEqual(self._dot_env.get(key), value)

    def testStoresNoneAsTheNullMarker(self) -> None:
        """
        Store ``None`` as the documented null marker.

        Validates that an absent value round trips back to ``None``
        instead of the literal text.
        """
        key = self._trackKey("NULL_KEY")
        self._dot_env.set(key, None, only_os=True)
        self.assertEqual(os.environ.get(key), "null")
        self.assertIsNone(self._dot_env.get(key))

    def testTrimsSurroundingWhitespaceFromStrings(self) -> None:
        """
        Trim surrounding whitespace before storing a string.

        Validates the normalisation that keeps padded editor input out of
        the configuration file.
        """
        key = self._trackKey("PADDED_KEY")
        self._dot_env.set(key, "  padded  ", only_os=True)
        self.assertEqual(self._dot_env.get(key), "padded")

    def testFallsBackToTheTextFormOfUnsupportedValues(self) -> None:
        """
        Fall back to the text form of an unsupported value type.

        Validates the defensive branch that keeps an exotic object from
        breaking the writer when no hint is declared.
        """
        key = self._trackKey("OPAQUE_KEY")
        self._dot_env.set(key, _OpaqueValue(), only_os=True)
        self.assertEqual(self._dot_env.get(key), "opaque-value")

    def testHonoursATextualTypeHint(self) -> None:
        """
        Honour a type hint expressed as a plain string.

        Validates that the stored entry carries the ``"<type>:<value>"``
        prefix understood by the reader.
        """
        key = self._trackKey("HINTED_KEY")
        self._dot_env.set(key, 42, "int", only_os=True)
        self.assertEqual(os.environ.get(key), "int:42")
        self.assertEqual(self._dot_env.get(key), 42)

    def testHonoursAnEnumeratedTypeHint(self) -> None:
        """
        Honour a type hint expressed as an enumeration member.

        Validates that callers may use ``EnvironmentValueType`` instead of
        a raw string.
        """
        key = self._trackKey("ENUM_HINTED_KEY")
        self._dot_env.set(key, "secret", EnvironmentValueType.BASE64, only_os=True)
        self.assertEqual(self._dot_env.get(key), "secret")

    def testSkipsTheFileWhenOnlyTheProcessIsTargeted(self) -> None:
        """
        Skip the `.env` file when only the process is targeted.

        Validates the ephemeral assignment used for values that must not
        be persisted, such as runtime overrides.
        """
        key = self._trackKey("EPHEMERAL_KEY")
        self._dot_env.set(key, "value", only_os=True)
        self.assertNotIn(key, self._fileContents())
        self.assertEqual(os.environ.get(key), "value")

    def testRejectsAnInvalidVariableName(self) -> None:
        """
        Reject names that break the environment naming convention.

        Validates that key validation runs before anything is written to
        disk.
        """
        with self.assertRaises(ValueError):
            self._dot_env.set("lower_case", "value")
        with self.assertRaises(TypeError):
            self._dot_env.set(42, "value")

    def testRejectsAnUnsupportedValueWhenAHintIsDeclared(self) -> None:
        """
        Reject an unsupported value type when a hint is declared.

        Validates that the hinted path runs the value validation that the
        inferred path deliberately skips.
        """
        with self.assertRaises(TypeError):
            self._dot_env.set(self._trackKey("BYTES_KEY"), b"payload", "str")

    def testRejectsAnUnknownTypeHint(self) -> None:
        """
        Reject a hint that names no supported type.

        Validates the ``RuntimeError`` documented for a type hint outside
        the ``EnvironmentValueType`` catalogue.
        """
        with self.assertRaises(RuntimeError):
            self._dot_env.set(self._trackKey("HINTED_KEY"), "value", "complex")

    def testRejectsAValueThatDoesNotFitTheDeclaredHint(self) -> None:
        """
        Reject a value that cannot be serialised for the declared hint.

        Validates the ``ValueError`` documented for a serialisation that
        the caster cannot perform.
        """
        with self.assertRaises(ValueError):
            self._dot_env.set(self._trackKey("HINTED_KEY"), "abc", "int")

# ---------------------------------------------------------------------------
# TestDotEnvGet
# ---------------------------------------------------------------------------

class TestDotEnvGet(_DotEnvTestCase):

    def testReturnsNoneForAnUnknownVariable(self) -> None:
        """
        Return ``None`` when the variable is not defined.

        Validates the implicit default of the reader.
        """
        self.assertIsNone(self._dot_env.get("UNDEFINED_KEY"))

    def testReturnsTheSuppliedDefaultForAnUnknownVariable(self) -> None:
        """
        Return the caller default when the variable is not defined.

        Validates that the fallback is handed back untouched, whatever
        its type.
        """
        self.assertEqual(self._dot_env.get("UNDEFINED_KEY", "fallback"), "fallback")
        self.assertEqual(self._dot_env.get("UNDEFINED_KEY", 7), 7)

    def testResolvesEveryNullSpelling(self) -> None:
        """
        Resolve every accepted null spelling to ``None``.

        Validates the case-insensitive vocabulary that lets a `.env` file
        express an explicitly empty value.
        """
        for index, raw in enumerate(("null", "NONE", " Nan ", "nil")):
            key = f"NULLISH_KEY_{index}"
            self._writeRawEntry(key, raw)
            self.assertIsNone(self._dot_env.get(key))

    def testResolvesAnEmptyValueToNone(self) -> None:
        """
        Resolve an empty entry to ``None``.

        Validates that a declared but blank variable behaves like an
        undefined one.
        """
        self._writeRawEntry("EMPTY_KEY", "")
        self.assertIsNone(self._dot_env.get("EMPTY_KEY"))

    def testResolvesBooleanSpellings(self) -> None:
        """
        Resolve textual booleans regardless of their casing.

        Validates the shortcut applied before literal evaluation.
        """
        self._writeRawEntry("TRUE_KEY", "TRUE")
        self._writeRawEntry("FALSE_KEY", " false ")
        self.assertTrue(self._dot_env.get("TRUE_KEY"))
        self.assertFalse(self._dot_env.get("FALSE_KEY"))

    def testEvaluatesPythonLiterals(self) -> None:
        """
        Evaluate entries that spell a plain Python literal.

        Validates the fallback that restores numbers and containers
        written without a type hint.
        """
        for index, (raw, expected) in enumerate(
            (
                ("42", 42),
                ("2.5", 2.5),
                ("[1, 2]", [1, 2]),
                ("{'a': 1}", {"a": 1}),
                ("(1, 2)", (1, 2)),
            ),
        ):
            key = f"LITERAL_KEY_{index}"
            self._writeRawEntry(key, raw)
            self.assertEqual(self._dot_env.get(key), expected)

    def testResolvesTypedEntries(self) -> None:
        """
        Resolve entries carrying a recognised type prefix.

        Validates the dispatch to the caster for the ``"<type>:<value>"``
        convention.
        """
        self._writeRawEntry("TYPED_KEY", "int:42")
        self.assertEqual(self._dot_env.get("TYPED_KEY"), 42)

    def testKeepsColonBearingTextAsIs(self) -> None:
        """
        Keep colon-bearing text that declares no known type.

        Validates that values such as URLs are never mistaken for typed
        entries nor mangled by literal evaluation.
        """
        self._writeRawEntry("URL_KEY", "https://example.test/path")
        self.assertEqual(
            self._dot_env.get("URL_KEY"),
            "https://example.test/path",
        )

    def testKeepsUnparsableTextAsIs(self) -> None:
        """
        Keep text that is not a valid Python literal.

        Validates the last fallback of the parser, which returns the
        original string instead of failing.
        """
        self._writeRawEntry("TEXT_KEY", "just some text")
        self.assertEqual(self._dot_env.get("TEXT_KEY"), "just some text")

    def testReturnsAlreadyTypedValuesUntouched(self) -> None:
        """
        Return values that already are native Python objects.

        Validates the defensive shortcut of the parser, reached when the
        cached entry was not produced by the file reader.
        """
        parse = self._dot_env._DotEnv__parseValue
        for value in (True, 42, 2.5, {"a": 1}, [1], (1,), {1}):
            self.assertIs(parse(value), value)

    def testRejectsAnInvalidVariableName(self) -> None:
        """
        Reject names that break the environment naming convention.

        Validates that key validation also guards the read path.
        """
        with self.assertRaises(ValueError):
            self._dot_env.get("lower_case")
        with self.assertRaises(TypeError):
            self._dot_env.get(42)

    def testPropagatesDecodingFailuresOfTypedEntries(self) -> None:
        """
        Propagate a typed entry whose value cannot be decoded.

        Validates the ``ValueError`` documented for a stored value that
        does not match its declared type.
        """
        self._writeRawEntry("BROKEN_INT_KEY", "int:abc")
        with self.assertRaises(ValueError):
            self._dot_env.get("BROKEN_INT_KEY")

    def testPropagatesTypeMismatchesOfTypedEntries(self) -> None:
        """
        Propagate a typed entry holding a literal of another type.

        Validates the ``TypeError`` documented for a stored value that is
        incompatible with its declared type.
        """
        self._writeRawEntry("BROKEN_LIST_KEY", "list:{1}")
        with self.assertRaises(TypeError):
            self._dot_env.get("BROKEN_LIST_KEY")

# ---------------------------------------------------------------------------
# TestDotEnvUnset
# ---------------------------------------------------------------------------

class TestDotEnvUnset(_DotEnvTestCase):

    def testReportsASuccessfulRemoval(self) -> None:
        """
        Report success after removing a variable.

        Validates the boolean contract relied upon by the console
        commands that clean configuration.
        """
        key = self._trackKey("REMOVABLE_KEY")
        self._dot_env.set(key, "value")
        self.assertTrue(self._dot_env.unset(key))

    def testRemovesTheVariableFromTheFile(self) -> None:
        """
        Remove the variable from the `.env` file.

        Validates that the deletion survives a process restart.
        """
        key = self._trackKey("REMOVABLE_KEY")
        self._dot_env.set(key, "value")
        self._dot_env.unset(key)
        self.assertNotIn(key, self._fileContents())

    def testRemovesTheVariableFromTheProcessEnvironment(self) -> None:
        """
        Remove the variable from the process environment.

        Validates that the value stops resolving immediately, without
        waiting for a reload.
        """
        key = self._trackKey("REMOVABLE_KEY")
        self._dot_env.set(key, "value")
        self._dot_env.unset(key)
        self.assertNotIn(key, os.environ)
        self.assertIsNone(self._dot_env.get(key))

    def testKeepsTheFileEntryWhenOnlyTheProcessIsTargeted(self) -> None:
        """
        Keep the file entry when only the process is targeted.

        Validates the ephemeral removal used to hide a value from the
        running process without editing the file.
        """
        key = self._trackKey("REMOVABLE_KEY")
        self._dot_env.set(key, "value")
        self._dot_env.unset(key, only_os=True)
        self.assertIn(key, self._fileContents())
        self.assertNotIn(key, os.environ)

    def testTreatsAnUnknownVariableAsAlreadyRemoved(self) -> None:
        """
        Treat an unknown variable as already removed.

        Validates the idempotent contract that lets clean-up routines run
        unconditionally.
        """
        self.assertTrue(self._dot_env.unset("UNDEFINED_KEY"))

    def testRejectsAnInvalidVariableName(self) -> None:
        """
        Reject names that break the environment naming convention.

        Validates that key validation also guards the removal path.
        """
        with self.assertRaises(ValueError):
            self._dot_env.unset("lower_case")
        with self.assertRaises(TypeError):
            self._dot_env.unset(42)

# ---------------------------------------------------------------------------
# TestDotEnvAll
# ---------------------------------------------------------------------------

class TestDotEnvAll(_DotEnvTestCase):

    def testReturnsAnEmptyMappingForAnEmptyFile(self) -> None:
        """
        Return an empty mapping when the file holds no variables.

        Validates the freshly scaffolded project scenario.
        """
        self.assertEqual(self._dot_env.all(), {})

    def testIncludesEveryPersistedVariable(self) -> None:
        """
        Include every variable persisted in the file.

        Validates the snapshot used by the ``about`` console command.
        """
        self._dot_env.set(self._trackKey("FIRST_KEY"), "first")
        self._dot_env.set(self._trackKey("SECOND_KEY"), "second")
        self.assertEqual(
            self._dot_env.all(),
            {"FIRST_KEY": "first", "SECOND_KEY": "second"},
        )

    def testParsesEveryValueToItsNativeType(self) -> None:
        """
        Parse every persisted value back to its native type.

        Validates that the snapshot is directly usable instead of holding
        raw strings.
        """
        self._dot_env.set(self._trackKey("NUMBER_KEY"), 42)
        self._dot_env.set(self._trackKey("FLAG_KEY"), True)
        self._dot_env.set(self._trackKey("ITEMS_KEY"), [1, 2])
        self.assertEqual(
            self._dot_env.all(),
            {"NUMBER_KEY": 42, "FLAG_KEY": True, "ITEMS_KEY": [1, 2]},
        )

    def testExcludesRemovedVariables(self) -> None:
        """
        Exclude variables that were removed from the file.

        Validates that the in-memory cache is kept in sync with every
        deletion.
        """
        key = self._trackKey("TEMPORARY_KEY")
        self._dot_env.set(key, "value")
        self._dot_env.unset(key)
        self.assertNotIn(key, self._dot_env.all())

    def testExcludesProcessOnlyVariables(self) -> None:
        """
        Exclude variables that were never written to the file.

        Validates the documented asymmetry with ``get``, which also sees
        process-only values.
        """
        key = self._trackKey("EPHEMERAL_KEY")
        self._dot_env.set(key, "value", only_os=True)
        self.assertNotIn(key, self._dot_env.all())

    def testResolvesValuelessEntriesToNone(self) -> None:
        """
        Resolve entries declared without a value to ``None``.

        Validates the parser guard reached when the file reader yields a
        missing value for a declared name.
        """
        self._env_path.write_text("BARE_KEY\n", encoding="utf-8")
        self._dot_env.reload()
        self.assertEqual(self._dot_env.all(), {"BARE_KEY": None})

# ---------------------------------------------------------------------------
# TestDotEnvReload
# ---------------------------------------------------------------------------

class TestDotEnvReload(_DotEnvTestCase):

    def testReportsASuccessfulReload(self) -> None:
        """
        Report success after reloading the file.

        Validates the boolean contract exposed through the facade.
        """
        self.assertTrue(self._dot_env.reload())

    def testPicksUpExternallyAddedVariables(self) -> None:
        """
        Pick up variables added to the file by another process.

        Validates the use case of an operator editing `.env` while the
        application is running.
        """
        key = self._trackKey("EXTERNAL_KEY")
        self._env_path.write_text(f"{key}=external\n", encoding="utf-8")
        self._dot_env.reload()
        self.assertEqual(self._dot_env.get(key), "external")

    def testOverridesStaleProcessValues(self) -> None:
        """
        Override values already published in the process environment.

        Validates that the file remains the authoritative source after a
        reload.
        """
        key = self._trackKey("STALE_KEY")
        self._dot_env.set(key, "old")
        self._env_path.write_text(f"{key}=new\n", encoding="utf-8")
        self._dot_env.reload()
        self.assertEqual(self._dot_env.get(key), "new")

    def testRebuildsTheSnapshotFromDisk(self) -> None:
        """
        Rebuild the in-memory snapshot from the file contents.

        Validates that entries deleted externally disappear from the
        snapshot returned by ``all``.
        """
        key = self._trackKey("DROPPED_KEY")
        self._dot_env.set(key, "value")
        self._env_path.write_text("", encoding="utf-8")
        self._dot_env.reload()
        self.assertNotIn(key, self._dot_env.all())

    def testReportsAnUnreadableFileAsRuntimeError(self) -> None:
        """
        Raise RuntimeError when the file cannot be decoded.

        Validates the handler that surfaces a corrupted `.env` file
        instead of leaving the application with stale values.
        """
        self._env_path.write_bytes(b"KEY=\xff\xfe\n")
        with self.assertRaises(RuntimeError) as ctx:
            self._dot_env.reload()
        self.assertIn("while reloading environment variables", str(ctx.exception))

# ---------------------------------------------------------------------------
# TestDotEnvLayout
# ---------------------------------------------------------------------------

class TestDotEnvLayout(_DotEnvTestCase):

    def testDeclaresItsInstanceStateAsSlots(self) -> None:
        """
        Declare the whole instance state as slots.

        Validates that the resolved path and the snapshot are the only
        attributes the reader keeps per instance.
        """
        self.assertEqual(DotEnv.__slots__, ("__cache", "__resolved_path"))

    def testDoesNotExposeAnInstanceDictionary(self) -> None:
        """
        Keep the reader free of an instance dictionary.

        Validates that the singleton cannot accumulate arbitrary
        attributes at runtime.
        """
        self.assertFalse(hasattr(self._dot_env, "__dict__"))
        with self.assertRaises(AttributeError):
            self._dot_env.unexpected_attribute = 1

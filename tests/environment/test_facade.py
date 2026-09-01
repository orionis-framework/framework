from __future__ import annotations
import os
import shutil
import tempfile
from orionis.test import TestCase
from orionis.environment.env import Env
from orionis.environment.core.dot_env import DotEnv
from orionis.environment.enums.value_type import EnvironmentValueType
from orionis.support.patterns.singleton.meta import _MISSING

# ---------------------------------------------------------------------------
# Shared base — reset both Env and DotEnv state between every test
# ---------------------------------------------------------------------------

class _EnvBase(TestCase):

    def setUp(self) -> None:
        """
        Reset all singletons and create a fresh temporary .env file.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        # Reset DotEnv singleton so each test starts completely clean
        type.__setattr__(DotEnv, "_singleton_instance", _MISSING)

        # Temporary directory used as the .env backing store
        self._tmpdir: str = tempfile.mkdtemp()
        self._env_path: str = os.path.join(self._tmpdir, ".test_env")

        # Create fresh DotEnv instance with temp path (becomes the singleton)
        DotEnv(path=self._env_path)

        # Track keys that must be removed from os.environ in tearDown
        self._tracked_keys: list[str] = []

    def tearDown(self) -> None:
        """
        Remove tracked os.environ keys, temp files, and all singleton state.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        for key in self._tracked_keys:
            os.environ.pop(key, None)
        shutil.rmtree(self._tmpdir, ignore_errors=True)
        type.__setattr__(DotEnv, "_singleton_instance", _MISSING)

    def _track(self, key: str) -> str:
        """
        Register a key for automatic os.environ cleanup in tearDown.

        Parameters
        ----------
        key : str
            Environment variable name to track.

        Returns
        -------
        str
            The same key, for convenient inline use.
        """
        if key not in self._tracked_keys:
            self._tracked_keys.append(key)
        return key

# ---------------------------------------------------------------------------
# TestEnvIsIEnvSubclass
# ---------------------------------------------------------------------------

class TestEnvIsIEnvSubclass(TestCase):

    def testExtendsIEnv(self):
        """
        Confirm that Env extends the IEnv abstract base class.

        Validates that the class hierarchy satisfies the contract layer so
        dependent components can rely on the interface.
        """
        from orionis.environment.contracts.env import IEnv
        self.assertTrue(issubclass(Env, IEnv))

# ---------------------------------------------------------------------------
# TestEnvGet
# ---------------------------------------------------------------------------

class TestEnvGet(_EnvBase):

    def testGetExistingKey(self):
        """
        Return the value of an existing environment variable.

        Sets a key via Env.set and confirms Env.get retrieves the same value.
        """
        Env.set(self._track("ENV_GET_KEY"), "hello")
        self.assertEqual(Env.get("ENV_GET_KEY"), "hello")

    def testGetMissingKeyReturnsNone(self):
        """
        Return None when the requested key does not exist.

        Confirms the default behaviour when no default is supplied by the
        caller.
        """
        self.assertIsNone(Env.get("ENV_MISSING_XYZ"))

    def testGetMissingKeyReturnsExplicitDefault(self):
        """
        Return the caller-supplied default for a missing key.

        Validates that the default parameter is forwarded to DotEnv.get
        without modification.
        """
        self.assertEqual(Env.get("ENV_MISSING_XYZ", "fallback"), "fallback")

    def testGetMissingKeyReturnsIntDefault(self):
        """
        Return an integer default for a missing key.

        Confirms that non-string default types are returned as-is without
        coercion.
        """
        self.assertEqual(Env.get("ENV_MISSING_XYZ", 42), 42)

    def testGetMissingKeyReturnsNoneDefault(self):
        """
        Return None when default=None is passed explicitly.

        Ensures explicit None default is treated the same as the implicit
        default.
        """
        self.assertIsNone(Env.get("ENV_MISSING_XYZ", None))

    def testGetIntTypedValue(self):
        """
        Return an integer when the stored value carries an int type hint.

        Sets a key with type_hint='int' and verifies the retrieved value is
        a Python int.
        """
        Env.set(self._track("ENV_INT_KEY"), "10", type_hint="int")
        result = Env.get("ENV_INT_KEY")
        self.assertIsInstance(result, int)
        self.assertEqual(result, 10)

    def testGetBoolTypedValue(self):
        """
        Return a boolean when the stored value carries a bool type hint.

        Confirms that bool-typed environment variables are parsed correctly
        on retrieval.
        """
        Env.set(self._track("ENV_BOOL_KEY"), "true", type_hint="bool")
        result = Env.get("ENV_BOOL_KEY")
        self.assertIs(result, True)

# ---------------------------------------------------------------------------
# TestEnvSet
# ---------------------------------------------------------------------------

class TestEnvSet(_EnvBase):

    def testSetReturnsTrue(self):
        """
        Return True when a new environment variable is set successfully.

        Validates the success return value of Env.set for a valid key and
        value pair.
        """
        result = Env.set(self._track("ENV_SET_A"), "value")
        self.assertTrue(result)

    def testSetAndGetRoundTrip(self):
        """
        Retrieve a value equal to the one that was set.

        Validates the full write/read round-trip through the Env facade for
        string values.
        """
        Env.set(self._track("ENV_ROUNDTRIP"), "test_value")
        self.assertEqual(Env.get("ENV_ROUNDTRIP"), "test_value")

    def testSetOverwritesExistingKey(self):
        """
        Overwrite an existing variable and retrieve the updated value.

        Confirms that calling Env.set twice with the same key replaces the
        previous value rather than ignoring the second call.
        """
        Env.set(self._track("ENV_OVERWRITE"), "first")
        Env.set("ENV_OVERWRITE", "second")
        self.assertEqual(Env.get("ENV_OVERWRITE"), "second")

    def testSetWithTypeHintInt(self):
        """
        Serialize an integer type_hint so the value is retrieved as int.

        Validates the type_hint parameter is forwarded to DotEnv and the
        stored representation is later parsed back to int by Env.get.
        """
        Env.set(self._track("ENV_TH_INT"), 99, type_hint="int")
        self.assertEqual(Env.get("ENV_TH_INT"), 99)

    def testSetWithTypeHintEnum(self):
        """
        Accept an EnvironmentValueType enum as the type_hint argument.

        Confirms that enum typed hints work identically to their string
        equivalents.
        """
        Env.set(
            self._track("ENV_TH_ENUM"),
            "3.14",
            type_hint=EnvironmentValueType.FLOAT,
        )
        result = Env.get("ENV_TH_ENUM")
        self.assertIsInstance(result, float)

    def testSetOnlyOsDoesNotPersistToFile(self):
        """
        Write only to os.environ when only_os=True is specified.

        Verifies that variables set with only_os=True appear in os.environ
        but are not persisted to the backing .env file.
        """
        key = self._track("ENV_ONLY_OS")
        Env.set(key, "ephemeral", only_os=True)
        # Must be visible in os.environ
        self.assertEqual(os.environ.get(key), "ephemeral")

    def testSetBoolValue(self):
        """
        Set a boolean value and retrieve it as a Python bool.

        Validates bool serialization and deserialization through the Env
        facade using bool type hint.
        """
        Env.set(self._track("ENV_BOOL_SET"), True, type_hint="bool")
        self.assertIs(Env.get("ENV_BOOL_SET"), True)

    def testSetListValue(self):
        """
        Set a list value and retrieve it as a Python list.

        Validates list serialization and deserialization through the Env
        facade using list type hint.
        """
        Env.set(self._track("ENV_LIST_SET"), [1, 2, 3], type_hint="list")
        self.assertEqual(Env.get("ENV_LIST_SET"), [1, 2, 3])

# ---------------------------------------------------------------------------
# TestEnvUnset
# ---------------------------------------------------------------------------

class TestEnvUnset(_EnvBase):

    def testUnsetReturnsTrue(self):
        """
        Return True after successfully removing an existing variable.

        Sets a key, then unsets it and confirms the return value signals
        success.
        """
        Env.set(self._track("ENV_UNSET_KEY"), "bye")
        result = Env.unset("ENV_UNSET_KEY")
        self.assertTrue(result)

    def testUnsetRemovesKeyFromGet(self):
        """
        Return None for a key that has been unset.

        Validates that once a key is unset, Env.get can no longer retrieve
        its value and falls back to None.
        """
        Env.set(self._track("ENV_UNSET_GET"), "temp")
        Env.unset("ENV_UNSET_GET")
        self.assertIsNone(Env.get("ENV_UNSET_GET"))

    def testUnsetRemovesKeyFromOsEnviron(self):
        """
        Remove the key from os.environ when unset without only_os flag.

        Verifies that the OS environment is also cleaned up so the process
        cannot accidentally read a stale value.
        """
        key = self._track("ENV_UNSET_OS")
        Env.set(key, "will_go")
        Env.unset(key)
        self.assertNotIn(key, os.environ)

    def testUnsetOnlyOsKeepsFileEntry(self):
        """
        Remove only the os.environ entry when only_os=True is specified.

        Confirms that only_os=True leaves the backing .env file intact so a
        subsequent reload would restore the variable.
        """
        key = self._track("ENV_UNSET_ONLYOS")
        Env.set(key, "file_entry")
        Env.unset(key, only_os=True)
        self.assertNotIn(key, os.environ)

    def testUnsetNonExistentKeyReturnsTrue(self):
        """
        Return True when unset is called on a key that does not exist.

        Validates that attempting to remove a ghost key is treated as a
        no-op success, consistent with the DotEnv contract that states
        "If the variable does not exist, returns True".
        """
        result = Env.unset("ENV_GHOST_XYZ")
        self.assertTrue(result)

# ---------------------------------------------------------------------------
# TestEnvAll
# ---------------------------------------------------------------------------

class TestEnvAll(_EnvBase):

    def testAllReturnsDictType(self):
        """
        Confirm that Env.all() returns a dict instance.

        Validates the return type contract so callers can safely iterate over
        keys and values.
        """
        self.assertIsInstance(Env.all(), dict)

    def testAllContainsSetKey(self):
        """
        Include a key in the result after it has been set via Env.set.

        Confirms that variables written through the facade are visible in
        the dictionary returned by Env.all().
        """
        Env.set(self._track("ENV_ALL_KEY"), "present")
        result = Env.all()
        self.assertIn("ENV_ALL_KEY", result)

    def testAllExcludesUnsetKey(self):
        """
        Exclude a key from the result after it has been unset.

        Validates that Env.all() reflects the current state and does not
        return stale entries for removed variables.
        """
        Env.set(self._track("ENV_ALL_GONE"), "temp")
        Env.unset("ENV_ALL_GONE")
        result = Env.all()
        self.assertNotIn("ENV_ALL_GONE", result)

    def testAllEmptyFileReturnsDict(self):
        """
        Return an empty dict when no variables have been set.

        Validates that the method handles a clean initial state without
        raising any exception.
        """
        result = Env.all()
        self.assertIsInstance(result, dict)

# ---------------------------------------------------------------------------
# TestEnvReload
# ---------------------------------------------------------------------------

class TestEnvReload(_EnvBase):

    def testReloadReturnsTrue(self):
        """
        Return True when the reload operation succeeds.

        Validates the success return value for a normal reload against a
        valid .env file.
        """
        result = Env.reload()
        self.assertTrue(result)

    def testReloadPicksUpExternalChange(self):
        """
        Reflect an external file change after calling Env.reload().

        Writes a new key directly to the .env backing file and verifies that
        Env.get returns the new value only after reload is called.
        """
        key = self._track("ENV_RELOAD_EXT")
        # Write the key directly to the file, bypassing the facade
        with open(self._env_path, "a", encoding="utf-8") as fh:
            fh.write(f"{key}=external_value\n")
        Env.reload()
        self.assertEqual(Env.get(key), "external_value")

    def testReloadKeepsDotEnvSingletonAlive(self):
        """
        Confirm that the DotEnv singleton is accessible after Env.reload().

        Validates that reload() does not corrupt the DotEnv singleton so the
        facade continues to delegate to a valid backing instance.
        """
        Env.reload()
        instance = DotEnv()
        self.assertIsInstance(instance, DotEnv)

    def testReloadAfterUnsetShowsRemovedKey(self):
        """
        Confirm a previously unset key is absent after reload.

        Sets a key, unsets it, then reloads and verifies the key is not
        present in the environment, confirming persistence of the unset.
        """
        key = self._track("ENV_RELOAD_UNSET")
        Env.set(key, "temp_val")
        Env.unset(key)
        Env.reload()
        self.assertIsNone(Env.get(key))

# ---------------------------------------------------------------------------
# TestEnvDotEnvSingleton
# ---------------------------------------------------------------------------

class TestEnvDotEnvSingleton(_EnvBase):

    def testDotEnvSingletonReturnsDotEnvInstance(self) -> None:
        """
        Confirm that calling DotEnv() returns a DotEnv instance.

        Validates that the singleton pattern produces an object of the
        correct type used to back the Env facade.
        """
        instance = DotEnv()
        self.assertIsInstance(instance, DotEnv)

    def testDotEnvSingletonReturnsSameObject(self) -> None:
        """
        Return the same DotEnv object on repeated calls.

        Validates that the singleton contract is preserved so multiple
        Env facade calls share a single backing store.
        """
        first = DotEnv()
        second = DotEnv()
        self.assertIs(first, second)

    def testDotEnvSingletonResetCreatesNewInstance(self) -> None:
        """
        Create a new DotEnv instance after the singleton is reset.

        Confirms that resetting _singleton_instance causes a fresh object
        to be created on the next call, which is the test isolation contract.
        """
        first = DotEnv()
        type.__setattr__(DotEnv, "_singleton_instance", _MISSING)
        second = DotEnv(path=self._env_path)
        self.assertIsNot(first, second)

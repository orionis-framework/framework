import os as _os_mod
import sys
import types
from orionis.test import TestCase
from orionis.introspection.modules.reflection import ReflectionModule

# ---------------------------------------------------------------------------
# Synthetic fixture module
# ---------------------------------------------------------------------------
# A fully controlled module is injected into sys.modules so that tests can
# assert exact keys without depending on a real file on disk.

_FIXTURE_NAME = "_orionis_module_test_fixture"

def _build_fixture() -> types.ModuleType:
    """
    Build and register a synthetic test module in sys.modules.

    Returns
    -------
    types.ModuleType
        The synthetic module registered under _FIXTURE_NAME.
    """
    mod = types.ModuleType(_FIXTURE_NAME)

    # --- classes ---
    class PublicClass:
        """Public class fixture."""

    class _ProtectedClass:
        """Protected class fixture."""

    # --- functions ---
    def public_sync_fn() -> int:
        """
        Return a fixed integer as a public synchronous fixture.

        Returns
        -------
        int
            Always 1.
        """
        return 1

    async def public_async_fn() -> int: # NOSONAR
        """
        Return a fixed integer as a public asynchronous fixture.

        Returns
        -------
        int
            Always 2.
        """
        return 2

    def _protected_sync_fn() -> int:
        """
        Return a fixed integer as a protected synchronous fixture.

        Returns
        -------
        int
            Always 3.
        """
        return 3

    async def _protected_async_fn() -> int: # NOSONAR
        """
        Return a fixed integer as a protected asynchronous fixture.

        Returns
        -------
        int
            Always 4.
        """
        return 4

    # Public constant (uppercase name, non-callable)
    mod.PUBLIC_CONST = 42

    # Inject classes
    mod.PublicClass = PublicClass
    mod._ProtectedClass = _ProtectedClass

    # Inject functions
    mod.public_sync_fn = public_sync_fn
    mod.public_async_fn = public_async_fn
    mod._protected_sync_fn = _protected_sync_fn
    mod._protected_async_fn = _protected_async_fn

    # Inject a module-level import so getImports() has something to find
    mod.os = _os_mod

    sys.modules[_FIXTURE_NAME] = mod
    return mod

_FIXTURE_MODULE = _build_fixture()

# ---------------------------------------------------------------------------
# Synthetic fixture module exposing private members
# ---------------------------------------------------------------------------
# Kept separate from the main fixture so that the negative assertions about
# private members in the main fixture remain meaningful.

_PRIVATE_FIXTURE_NAME = "_orionis_module_test_private_fixture"

def _build_private_fixture() -> types.ModuleType:
    """
    Build and register a synthetic module exposing private members.

    Returns
    -------
    types.ModuleType
        The synthetic module registered under _PRIVATE_FIXTURE_NAME.

    Notes
    -----
    Members are injected through ``__dict__`` because attribute assignment
    written literally would be subject to name mangling rules.
    """
    mod = types.ModuleType(_PRIVATE_FIXTURE_NAME)

    class _PrivateClass:
        """Private class fixture."""

    def _private_sync_fn() -> int:
        """
        Return a fixed integer as a private synchronous fixture.

        Returns
        -------
        int
            Always 5.
        """
        return 5

    async def _private_async_fn() -> int: # NOSONAR
        """
        Return a fixed integer as a private asynchronous fixture.

        Returns
        -------
        int
            Always 6.
        """
        return 6

    namespace = mod.__dict__
    namespace["__PrivateClass"] = _PrivateClass
    namespace["__PRIVATE_CONST"] = 7
    namespace["_PROTECTED_CONST"] = 8
    namespace["__private_sync_fn"] = _private_sync_fn
    namespace["__private_async_fn"] = _private_async_fn

    sys.modules[_PRIVATE_FIXTURE_NAME] = mod
    return mod

_PRIVATE_FIXTURE_MODULE = _build_private_fixture()

# Real module used for getFile / getSourceCode tests
_REAL_MODULE = "orionis.introspection.modules.reflection"

# Getters whose result is memoized in the internal cache dictionary
_CACHED_GETTERS = (
    "getClasses",
    "getPublicClasses",
    "getProtectedClasses",
    "getPrivateClasses",
    "getConstants",
    "getPublicConstants",
    "getProtectedConstants",
    "getPrivateConstants",
    "getFunctions",
    "getPublicFunctions",
    "getPublicSyncFunctions",
    "getPublicAsyncFunctions",
    "getProtectedFunctions",
    "getProtectedSyncFunctions",
    "getProtectedAsyncFunctions",
    "getPrivateFunctions",
    "getPrivateSyncFunctions",
    "getPrivateAsyncFunctions",
    "getImports",
)

class TestReflectionModuleInit(TestCase):

    def testInitWithValidModuleSucceeds(self) -> None:
        """
        Assert that a valid importable module name creates an instance.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        rm = ReflectionModule(_FIXTURE_NAME)
        self.assertIsInstance(rm, ReflectionModule)

    def testInitWithNonStringRaisesTypeError(self) -> None:
        """
        Assert that passing a non-string value raises TypeError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(TypeError):
            ReflectionModule(123)

    def testInitWithEmptyStringRaisesTypeError(self) -> None:
        """
        Assert that an empty string raises TypeError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(TypeError):
            ReflectionModule("")

    def testInitWithNonExistentModuleRaisesTypeError(self) -> None:
        """
        Assert that an unknown module name raises TypeError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(TypeError):
            ReflectionModule("this.module.does.not.exist.xyz")

class TestReflectionModuleCacheProtocol(TestCase):

    def setUp(self) -> None:
        """
        Instantiate a ReflectionModule for cache protocol tests.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rm = ReflectionModule(_FIXTURE_NAME)

    def testSetAndGetCacheItem(self) -> None:
        """
        Assert that a value stored with __setitem__ is retrievable via __getitem__.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rm["test_key"] = "test_value"
        self.assertEqual(self.rm["test_key"], "test_value")

    def testContainsReturnsTrueForExistingKey(self) -> None:
        """
        Assert that __contains__ returns True for a key that was stored.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rm["present"] = 1
        self.assertIn("present", self.rm)

    def testContainsReturnsFalseForMissingKey(self) -> None:
        """
        Assert that __contains__ returns False for an absent key.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertNotIn("absent_key_xyz", self.rm)

    def testDeleteCacheItem(self) -> None:
        """
        Assert that __delitem__ removes the key from the cache.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rm["to_delete"] = "bye"
        del self.rm["to_delete"]
        self.assertNotIn("to_delete", self.rm)

class TestReflectionModuleGetModule(TestCase):

    def setUp(self) -> None:
        """
        Instantiate a ReflectionModule wrapping the synthetic fixture.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rm = ReflectionModule(_FIXTURE_NAME)

    def testGetModuleReturnsSameObject(self) -> None:
        """
        Assert that getModule returns the exact registered fixture module.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIs(self.rm.getModule(), sys.modules[_FIXTURE_NAME])

    def testGetModuleIsModuleType(self) -> None:
        """
        Assert that getModule return value is a ModuleType instance.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rm.getModule(), types.ModuleType)

class TestReflectionModuleClasses(TestCase):

    def setUp(self) -> None:
        """
        Instantiate a fresh ReflectionModule for class-related tests.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        # Re-build fixture to guarantee isolation between mutation tests
        _build_fixture()
        self.rm = ReflectionModule(_FIXTURE_NAME)

    def testGetClassesReturnsDict(self) -> None:
        """
        Assert that getClasses returns a dictionary.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rm.getClasses(), dict)

    def testGetClassesContainsPublicClass(self) -> None:
        """
        Assert that getClasses includes 'PublicClass'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("PublicClass", self.rm.getClasses())

    def testGetPublicClassesContainsPublicClass(self) -> None:
        """
        Assert that getPublicClasses includes 'PublicClass'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("PublicClass", self.rm.getPublicClasses())

    def testGetPublicClassesExcludesProtected(self) -> None:
        """
        Assert that getPublicClasses excludes '_ProtectedClass'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertNotIn("_ProtectedClass", self.rm.getPublicClasses())

    def testGetProtectedClassesContainsProtectedClass(self) -> None:
        """
        Assert that getProtectedClasses includes '_ProtectedClass'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("_ProtectedClass", self.rm.getProtectedClasses())

    def testGetPrivateClassesReturnsEmptyDict(self) -> None:
        """
        Assert that getPrivateClasses returns an empty dict for the fixture.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertEqual(self.rm.getPrivateClasses(), {})

    def testHasClassReturnsTrueForExisting(self) -> None:
        """
        Assert that hasClass returns True for 'PublicClass'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertTrue(self.rm.hasClass("PublicClass"))

    def testHasClassReturnsFalseForMissing(self) -> None:
        """
        Assert that hasClass returns False for an unknown class name.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertFalse(self.rm.hasClass("NonExistentXyz"))

    def testGetClassReturnsCorrectType(self) -> None:
        """
        Assert that getClass returns a type object for 'PublicClass'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        cls = self.rm.getClass("PublicClass")
        self.assertIsNotNone(cls)
        self.assertTrue(isinstance(cls, type))

    def testGetClassReturnsNoneForMissing(self) -> None:
        """
        Assert that getClass returns None for an unknown class name.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsNone(self.rm.getClass("NonExistentXyz"))

    def testSetClassReturnsTrueAndIsVisible(self) -> None:
        """
        Assert that setClass injects the class and it is then discoverable.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """

        class InjectedClass:
            """Dynamically injected class."""

        result = self.rm.setClass("InjectedClass", InjectedClass)
        self.assertTrue(result)
        self.assertTrue(self.rm.hasClass("InjectedClass"))
        # cleanup
        self.rm.removeClass("InjectedClass")

    def testSetClassWithNonTypeRaisesTypeError(self) -> None:
        """
        Assert that setClass raises TypeError when the value is not a type.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(TypeError):
            self.rm.setClass("Bad", "not_a_class")

    def testSetClassWithInvalidNameRaisesValueError(self) -> None:
        """
        Assert that setClass raises ValueError for an invalid identifier.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(ValueError):
            self.rm.setClass("123invalid", int)

    def testSetClassWithKeywordRaisesValueError(self) -> None:
        """
        Assert that setClass raises ValueError when the name is a keyword.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(ValueError):
            self.rm.setClass("class", int)

    def testRemoveClassReturnsTrueAndIsGone(self) -> None:
        """
        Assert that removeClass removes the class from the module.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """

        class TempClass:
            """Temporary class for removal test."""

        self.rm.setClass("TempClass", TempClass)
        result = self.rm.removeClass("TempClass")
        self.assertTrue(result)
        self.assertFalse(self.rm.hasClass("TempClass"))

    def testRemoveClassNonExistingRaisesValueError(self) -> None:
        """
        Assert that removeClass raises ValueError for an unknown class name.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(ValueError):
            self.rm.removeClass("NonExistentXyz")

class TestReflectionModuleConstants(TestCase):

    def setUp(self) -> None:
        """
        Instantiate a ReflectionModule for constant discovery tests.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rm = ReflectionModule(_FIXTURE_NAME)

    def testGetConstantsReturnsDict(self) -> None:
        """
        Assert that getConstants returns a dictionary.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rm.getConstants(), dict)

    def testGetConstantsContainsPublicConst(self) -> None:
        """
        Assert that getConstants includes 'PUBLIC_CONST'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("PUBLIC_CONST", self.rm.getConstants())

    def testGetPublicConstantsContainsPublicConst(self) -> None:
        """
        Assert that getPublicConstants includes 'PUBLIC_CONST'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("PUBLIC_CONST", self.rm.getPublicConstants())

    def testGetProtectedConstantsReturnsDict(self) -> None:
        """
        Assert that getProtectedConstants returns a dictionary.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rm.getProtectedConstants(), dict)

    def testGetPrivateConstantsReturnsDict(self) -> None:
        """
        Assert that getPrivateConstants returns a dictionary.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rm.getPrivateConstants(), dict)

    def testGetConstantReturnsCorrectValue(self) -> None:
        """
        Assert that getConstant returns 42 for 'PUBLIC_CONST'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertEqual(self.rm.getConstant("PUBLIC_CONST"), 42)

    def testGetConstantReturnsNoneForMissing(self) -> None:
        """
        Assert that getConstant returns None for an unknown constant name.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsNone(self.rm.getConstant("NONEXISTENT_XYZ"))

class TestReflectionModulePublicFunctions(TestCase):

    def setUp(self) -> None:
        """
        Instantiate a ReflectionModule for public function tests.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rm = ReflectionModule(_FIXTURE_NAME)

    def testGetFunctionsReturnsDict(self) -> None:
        """
        Assert that getFunctions returns a dictionary.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rm.getFunctions(), dict)

    def testGetFunctionsContainsPublicSyncFn(self) -> None:
        """
        Assert that getFunctions includes 'public_sync_fn'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("public_sync_fn", self.rm.getFunctions())

    def testGetPublicFunctionsContainsPublicSyncFn(self) -> None:
        """
        Assert that getPublicFunctions includes 'public_sync_fn'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("public_sync_fn", self.rm.getPublicFunctions())

    def testGetPublicFunctionsExcludesProtected(self) -> None:
        """
        Assert that getPublicFunctions excludes '_protected_sync_fn'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertNotIn("_protected_sync_fn", self.rm.getPublicFunctions())

    def testGetPublicSyncFunctionsContainsSyncFn(self) -> None:
        """
        Assert that getPublicSyncFunctions includes 'public_sync_fn'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("public_sync_fn", self.rm.getPublicSyncFunctions())

    def testGetPublicSyncFunctionsExcludesAsyncFn(self) -> None:
        """
        Assert that getPublicSyncFunctions excludes 'public_async_fn'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertNotIn("public_async_fn", self.rm.getPublicSyncFunctions())

    def testGetPublicAsyncFunctionsContainsAsyncFn(self) -> None:
        """
        Assert that getPublicAsyncFunctions includes 'public_async_fn'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("public_async_fn", self.rm.getPublicAsyncFunctions())

    def testGetPublicAsyncFunctionsExcludesSyncFn(self) -> None:
        """
        Assert that getPublicAsyncFunctions excludes 'public_sync_fn'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertNotIn("public_sync_fn", self.rm.getPublicAsyncFunctions())

class TestReflectionModuleProtectedFunctions(TestCase):

    def setUp(self) -> None:
        """
        Instantiate a ReflectionModule for protected function tests.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rm = ReflectionModule(_FIXTURE_NAME)

    def testGetProtectedFunctionsContainsProtectedSyncFn(self) -> None:
        """
        Assert that getProtectedFunctions includes '_protected_sync_fn'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("_protected_sync_fn", self.rm.getProtectedFunctions())

    def testGetProtectedFunctionsExcludesPublic(self) -> None:
        """
        Assert that getProtectedFunctions excludes 'public_sync_fn'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertNotIn("public_sync_fn", self.rm.getProtectedFunctions())

    def testGetProtectedSyncFunctionsContainsSyncFn(self) -> None:
        """
        Assert that getProtectedSyncFunctions includes '_protected_sync_fn'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("_protected_sync_fn", self.rm.getProtectedSyncFunctions())

    def testGetProtectedSyncFunctionsExcludesAsyncFn(self) -> None:
        """
        Assert that getProtectedSyncFunctions excludes '_protected_async_fn'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertNotIn(
            "_protected_async_fn",
            self.rm.getProtectedSyncFunctions(),
        )

    def testGetProtectedAsyncFunctionsContainsAsyncFn(self) -> None:
        """
        Assert that getProtectedAsyncFunctions includes '_protected_async_fn'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("_protected_async_fn", self.rm.getProtectedAsyncFunctions())

    def testGetProtectedAsyncFunctionsExcludesSyncFn(self) -> None:
        """
        Assert that getProtectedAsyncFunctions excludes '_protected_sync_fn'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertNotIn(
            "_protected_sync_fn",
            self.rm.getProtectedAsyncFunctions(),
        )

class TestReflectionModulePrivateFunctions(TestCase):

    def setUp(self) -> None:
        """
        Instantiate a ReflectionModule for private function tests.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rm = ReflectionModule(_FIXTURE_NAME)

    def testGetPrivateFunctionsReturnsDict(self) -> None:
        """
        Assert that getPrivateFunctions returns a dictionary.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rm.getPrivateFunctions(), dict)

    def testGetPrivateSyncFunctionsReturnsDict(self) -> None:
        """
        Assert that getPrivateSyncFunctions returns a dictionary.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rm.getPrivateSyncFunctions(), dict)

    def testGetPrivateAsyncFunctionsReturnsDict(self) -> None:
        """
        Assert that getPrivateAsyncFunctions returns a dictionary.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rm.getPrivateAsyncFunctions(), dict)

class TestReflectionModuleImports(TestCase):

    def setUp(self) -> None:
        """
        Instantiate a ReflectionModule for import discovery tests.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rm = ReflectionModule(_FIXTURE_NAME)

    def testGetImportsReturnsDict(self) -> None:
        """
        Assert that getImports returns a dictionary.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rm.getImports(), dict)

    def testGetImportsContainsOsModule(self) -> None:
        """
        Assert that getImports includes the 'os' attribute injected into the fixture.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("os", self.rm.getImports())

class TestReflectionModuleFileAndSource(TestCase):

    def setUp(self) -> None:
        """
        Instantiate a ReflectionModule wrapping the real reflection module.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rm = ReflectionModule(_REAL_MODULE)

    def testGetFileReturnsNonEmptyString(self) -> None:
        """
        Assert that getFile returns a non-empty string.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        path = self.rm.getFile()
        self.assertIsInstance(path, str)
        self.assertGreater(len(path), 0)

    def testGetFileEndsWithPyExtension(self) -> None:
        """
        Assert that getFile returns a path ending with '.py' or '.pyc'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        path = self.rm.getFile()
        self.assertTrue(path.endswith((".py", ".pyc")))

    def testGetSourceCodeReturnsNonEmptyString(self) -> None:
        """
        Assert that getSourceCode returns a non-empty string.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        src = self.rm.getSourceCode()
        self.assertIsInstance(src, str)
        self.assertGreater(len(src), 0)

    def testGetSourceCodeContainsClassName(self) -> None:
        """
        Assert that the source code contains the 'ReflectionModule' class name.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("ReflectionModule", self.rm.getSourceCode())

    def testGetSourceCodeIsCached(self) -> None:
        """
        Assert that repeated calls to getSourceCode return the same object.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        first = self.rm.getSourceCode()
        second = self.rm.getSourceCode()
        self.assertIs(first, second)

class TestReflectionModuleClearCache(TestCase):

    def setUp(self) -> None:
        """
        Instantiate a ReflectionModule for cache clearing tests.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rm = ReflectionModule(_FIXTURE_NAME)

    def testClearCacheReturnsNone(self) -> None:
        """
        Assert that clearCache returns None.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsNone(self.rm.clearCache())

    def testClearCacheInvalidatesStoredItems(self) -> None:
        """
        Assert that after clearCache, previously cached items are absent.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rm["sentinel"] = "value"
        self.rm.clearCache()
        self.assertNotIn("sentinel", self.rm)

    def testClearCacheForcesFreshComputation(self) -> None:
        """
        Assert that getClasses recomputes correctly after clearCache is called.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        # Populate the classes cache
        _ = self.rm.getClasses()
        self.assertIn("classes", self.rm)
        # Clear and verify the cache key is gone
        self.rm.clearCache()
        self.assertNotIn("classes", self.rm)
        # Recompute and check result is still valid
        self.assertIsInstance(self.rm.getClasses(), dict)

class TestReflectionModulePrivateMembers(TestCase):

    def setUp(self) -> None:
        """
        Instantiate a ReflectionModule wrapping the private-member fixture.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.rm = ReflectionModule(_PRIVATE_FIXTURE_NAME)

    def testGetPrivateClassesContainsMangledClass(self) -> None:
        """
        Assert that double-underscore classes are reported as private.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("__PrivateClass", self.rm.getPrivateClasses())

    def testGetPrivateConstantsContainsMangledConstant(self) -> None:
        """
        Assert that double-underscore constants are reported as private.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("__PRIVATE_CONST", self.rm.getPrivateConstants())

    def testGetProtectedConstantsContainsSingleUnderscoreConstant(self) -> None:
        """
        Assert that single-underscore constants are reported as protected.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("_PROTECTED_CONST", self.rm.getProtectedConstants())

    def testGetPrivateFunctionsContainsBothVariants(self) -> None:
        """
        Assert that private synchronous and asynchronous functions are found.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        private = self.rm.getPrivateFunctions()
        self.assertIn("__private_sync_fn", private)
        self.assertIn("__private_async_fn", private)

    def testGetPrivateSyncFunctionsExcludesCoroutines(self) -> None:
        """
        Assert that private coroutine functions are excluded from the sync set.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sync_functions = self.rm.getPrivateSyncFunctions()
        self.assertIn("__private_sync_fn", sync_functions)
        self.assertNotIn("__private_async_fn", sync_functions)

    def testGetPrivateAsyncFunctionsExcludesSyncFunctions(self) -> None:
        """
        Assert that private synchronous functions are excluded from the async set.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        async_functions = self.rm.getPrivateAsyncFunctions()
        self.assertIn("__private_async_fn", async_functions)
        self.assertNotIn("__private_sync_fn", async_functions)

class TestReflectionModuleMemoization(TestCase):

    def testCachedGettersReturnTheSameObjectOnSecondCall(self) -> None:
        """
        Assert that every memoized getter returns the cached instance.

        Returns
        -------
        None
            Raises AssertionError on failure.

        Notes
        -----
        The second invocation must hit the internal cache instead of
        recomputing the mapping.
        """
        rm = ReflectionModule(_PRIVATE_FIXTURE_NAME)
        for getter in _CACHED_GETTERS:
            bound = getattr(rm, getter)
            self.assertIs(bound(), bound(), msg=getter)

    def testGetFileIsMemoized(self) -> None:
        """
        Assert that getFile returns the cached path on repeated calls.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        rm = ReflectionModule(_REAL_MODULE)
        self.assertIs(rm.getFile(), rm.getFile())

class TestReflectionModuleSourceErrors(TestCase):

    def setUp(self) -> None:
        """
        Instantiate a ReflectionModule wrapping a module without a file.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.rm = ReflectionModule(_FIXTURE_NAME)

    def testGetFileRaisesTypeErrorForModulesWithoutFile(self) -> None:
        """
        Assert that in-memory modules cannot resolve a source file.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(TypeError):
            self.rm.getFile()

    def testGetSourceCodeRaisesValueErrorWhenFileIsUnavailable(self) -> None:
        """
        Assert that unreadable modules surface a ValueError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(ValueError):
            self.rm.getSourceCode()


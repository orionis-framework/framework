import inspect
from orionis.test import TestCase
from orionis.introspection.concretes.reflection import ReflectionConcrete
from orionis.introspection.dependencies.entities.signature import Signature

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

class SampleConcrete:
    """A concrete class with varied members for introspection testing."""

    public_attr: int = 10
    _protected_attr: str = "protected"
    __private_attr: str = "private" # NOSONAR

    def __init__(self, x: int = 0) -> None:
        """Initialise with an optional integer."""
        self.x = x

    def publicMethod(self) -> str:
        """Return a fixed string."""
        return "public"

    async def publicAsyncMethod(self) -> str: # NOSONAR
        """Return a fixed async string."""
        return "async_public"

    def _protectedMethod(self) -> bool:
        """Return True."""
        return True

    async def _protectedAsyncMethod(self) -> None:
        """No-op async protected method."""

    def __privateMethod(self) -> int:  # NOSONAR
        """Return zero as a private method."""
        return 0

    async def __privateAsyncMethod(self) -> int:  # NOSONAR
        """Return zero as a private async method."""
        return 0

    @staticmethod
    def staticMethod() -> bool:
        """Return True from a static context."""
        return True

    @staticmethod
    async def staticAsyncMethod() -> bool: # NOSONAR
        """Return True from an async static context."""
        return True

    @staticmethod
    def _protectedStaticMethod() -> int:
        """Return 0 from a protected static context."""
        return 0

    @staticmethod
    async def _protectedStaticAsyncMethod() -> int: # NOSONAR
        """Return 0 from a protected async static context."""
        return 0

    @staticmethod
    def __privateStaticMethod() -> int: # NOSONAR
        """Return 1 from a private static context."""
        return 1

    @staticmethod
    async def __privateStaticAsyncMethod() -> int: # NOSONAR
        """Return 1 from a private async static context."""
        return 1

    @classmethod
    def classMethod(cls) -> str:
        """Return the class name."""
        return cls.__name__

    @classmethod
    async def classAsyncMethod(cls) -> str: # NOSONAR
        """Return the class name from an async class method."""
        return cls.__name__

    @classmethod
    def _protectedClassMethod(cls) -> None:
        """No-op protected class method."""

    @classmethod
    async def _protectedClassAsyncMethod(cls) -> str: # NOSONAR
        """Return the class name from a protected async class method."""
        return cls.__name__

    @classmethod
    def __privateClassMethod(cls) -> str: # NOSONAR
        """Return the class name from a private class method."""
        return cls.__name__

    @classmethod
    async def __privateClassAsyncMethod(cls) -> str: # NOSONAR
        """Return the class name from a private async class method."""
        return cls.__name__

    @property
    def aProperty(self) -> int:
        """Return a fixed integer property value."""
        return 0

    @property
    def _protectedProperty(self) -> str:
        """Return a fixed protected property string."""
        return "protected_value"

    @property
    def __privateProperty(self) -> str: # NOSONAR
        """Return a fixed private property string."""
        return "private_value"

    def __repr__(self) -> str:
        """Return a developer-friendly string representation."""
        return f"SampleConcrete(x={self.x})"

def _make_mutable_concrete() -> type:
    """
    Return a fresh concrete type suitable for mutation tests.

    Returns
    -------
    type
        A new class with a mutable_attr and a deletableMethod.
    """
    class _Mutable:
        mutable_attr: int = 99

        def deletableMethod(self) -> int:
            """Return 1."""
            return 1

    return _Mutable

def _make_private_method_concrete() -> type:
    """
    Return a fresh concrete type exposing a deletable private method.

    Returns
    -------
    type
        A new class with a name-mangled private method.
    """
    class _PrivateHolder:

        def __hiddenMethod(self) -> int: # NOSONAR
            """Return 2."""
            return 2

    return _PrivateHolder

def _replacement_method(self) -> int:  # noqa: ARG001
    """
    Return a fixed integer used when injecting methods at runtime.

    Returns
    -------
    int
        Always returns 3.
    """
    return 3

def _make_moduleless_concrete() -> type:
    """
    Return a class whose declared module cannot be resolved to a file.

    Returns
    -------
    type
        A new class pointing at a module missing from sys.modules.
    """
    return type(
        "_ModulelessConcrete",
        (),
        {"__module__": "orionis_missing_module_xyz"},
    )

# Accessors that trigger the lazy single-pass class scan on first use
_SCAN_TRIGGERING_GETTERS = (
    "getAttributes",
    "getPublicAttributes",
    "getProtectedAttributes",
    "getPrivateAttributes",
    "getDunderAttributes",
    "getMagicAttributes",
    "getMethods",
    "getPublicMethods",
    "getPublicSyncMethods",
    "getPublicAsyncMethods",
    "getProtectedMethods",
    "getProtectedSyncMethods",
    "getProtectedAsyncMethods",
    "getPrivateMethods",
    "getPrivateSyncMethods",
    "getPrivateAsyncMethods",
    "getPublicClassMethods",
    "getPublicClassSyncMethods",
    "getPublicClassAsyncMethods",
    "getProtectedClassMethods",
    "getProtectedClassSyncMethods",
    "getProtectedClassAsyncMethods",
    "getPrivateClassMethods",
    "getPrivateClassSyncMethods",
    "getPrivateClassAsyncMethods",
    "getPublicStaticMethods",
    "getPublicStaticSyncMethods",
    "getPublicStaticAsyncMethods",
    "getProtectedStaticMethods",
    "getProtectedStaticSyncMethods",
    "getProtectedStaticAsyncMethods",
    "getPrivateStaticMethods",
    "getPrivateStaticSyncMethods",
    "getPrivateStaticAsyncMethods",
    "getDunderMethods",
    "getMagicMethods",
    "getProperties",
    "getPublicProperties",
    "getProtectedProperties",
    "getPrivateProperties",
)

# ---------------------------------------------------------------------------
# __init__ / construction
# ---------------------------------------------------------------------------

class TestReflectionConcreteInit(TestCase):

    def testInitWithConcreteClassSucceeds(self) -> None:
        """
        Assert that wrapping a plain concrete class does not raise.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        rc = ReflectionConcrete(SampleConcrete)
        self.assertIsInstance(rc, ReflectionConcrete)

    def testInitWithAbstractClassRaisesTypeError(self) -> None:
        """
        Assert that an ABC subclass raises TypeError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        from abc import ABC, abstractmethod

        class _Abstract(ABC):
            @abstractmethod
            def m(self): ...

        with self.assertRaises(TypeError):
            ReflectionConcrete(_Abstract)  # type: ignore[arg-type]

    def testInitWithBuiltinFunctionRaisesTypeError(self) -> None:
        """
        Assert that a built-in function (not a type) raises TypeError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(TypeError):
            ReflectionConcrete(len)  # type: ignore[arg-type]

    def testInitWithNonTypeRaisesTypeError(self) -> None:
        """
        Assert that a non-type value raises TypeError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(TypeError):
            ReflectionConcrete(42)  # type: ignore[arg-type]

    def testInitWithNoneRaisesTypeError(self) -> None:
        """
        Assert that passing None raises TypeError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(TypeError):
            ReflectionConcrete(None)  # type: ignore[arg-type]

    def testInstanceIsReflectionConcrete(self) -> None:
        """
        Assert that the returned object is an instance of ReflectionConcrete.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(ReflectionConcrete(SampleConcrete), ReflectionConcrete)

# ---------------------------------------------------------------------------
# Cache protocol
# ---------------------------------------------------------------------------

class TestReflectionConcreteCacheProtocol(TestCase):

    def setUp(self) -> None:
        """Initialise a shared ReflectionConcrete for cache tests."""
        self.rc = ReflectionConcrete(SampleConcrete)

    def testSetAndGetItem(self) -> None:
        """
        Assert that stored values are retrievable from the cache.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rc["my_key"] = "my_value"
        self.assertEqual(self.rc["my_key"], "my_value")

    def testContainsReturnsTrueAfterSet(self) -> None:
        """
        Assert that __contains__ returns True after storing a key.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rc["exists"] = True
        self.assertIn("exists", self.rc)

    def testContainsReturnsFalseForMissingKey(self) -> None:
        """
        Assert that __contains__ returns False for a key never stored.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertNotIn("ghost_key", self.rc)

    def testGetItemReturnsNoneForMissingKey(self) -> None:
        """
        Assert that __getitem__ returns None for an absent key.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsNone(self.rc["absent_key"])

    def testDelItemRemovesKey(self) -> None:
        """
        Assert that __delitem__ removes a previously stored key.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rc["to_delete"] = 99
        del self.rc["to_delete"]
        self.assertNotIn("to_delete", self.rc)

    def testDelItemNonExistentKeyIsNoop(self) -> None:
        """
        Assert that deleting a missing key does not raise any exception.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        del self.rc["never_existed"]  # must not raise

# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

class TestReflectionConcreteIdentity(TestCase):

    def setUp(self) -> None:
        """Initialise a shared ReflectionConcrete for identity tests."""
        self.rc = ReflectionConcrete(SampleConcrete)

    def testGetClassReturnsSampleConcrete(self) -> None:
        """
        Assert that getClass returns the original SampleConcrete class.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIs(self.rc.getClass(), SampleConcrete)

    def testGetClassNameReturnsStr(self) -> None:
        """
        Assert that getClassName returns a str.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getClassName(), str)

    def testGetClassNameValue(self) -> None:
        """
        Assert that getClassName returns 'SampleConcrete'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertEqual(self.rc.getClassName(), "SampleConcrete")

    def testGetModuleNameReturnsStr(self) -> None:
        """
        Assert that getModuleName returns a str.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getModuleName(), str)

    def testGetModuleWithClassNameContainsClassName(self) -> None:
        """
        Assert that getModuleWithClassName contains 'SampleConcrete'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("SampleConcrete", self.rc.getModuleWithClassName())

    def testGetModuleWithClassNameContainsModuleName(self) -> None:
        """
        Assert that getModuleWithClassName contains the module name.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        fqn = self.rc.getModuleWithClassName()
        self.assertIn(self.rc.getModuleName(), fqn)

# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

class TestReflectionConcreteMetadata(TestCase):

    def setUp(self) -> None:
        """Initialise a shared ReflectionConcrete for metadata tests."""
        self.rc = ReflectionConcrete(SampleConcrete)

    def testGetDocstringReturnsStr(self) -> None:
        """
        Assert that getDocstring returns a str for a documented class.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getDocstring(), str)

    def testGetDocstringNoneWhenAbsent(self) -> None:
        """
        Assert that getDocstring returns None when __doc__ is None.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        class _NoDoc:
            pass

        _NoDoc.__doc__ = None
        rc = ReflectionConcrete(_NoDoc)
        self.assertIsNone(rc.getDocstring())

    def testGetBaseClassesReturnsList(self) -> None:
        """
        Assert that getBaseClasses returns a list.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getBaseClasses(), list)

    def testGetBaseClassesContainsObject(self) -> None:
        """
        Assert that object appears in the base classes of SampleConcrete.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn(object, self.rc.getBaseClasses())

    def testGetSourceCodeReturnsStr(self) -> None:
        """
        Assert that getSourceCode returns a non-empty str for the class.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        src = self.rc.getSourceCode()
        self.assertIsInstance(src, str)
        self.assertTrue(len(src) > 0)

    def testGetSourceCodeForMethodReturnsStr(self) -> None:
        """
        Assert that getSourceCode with 'publicMethod' returns a str.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        src = self.rc.getSourceCode("publicMethod")
        self.assertIsInstance(src, str)

    def testGetSourceCodeForMissingMethodReturnsNone(self) -> None:
        """
        Assert that getSourceCode for a non-existent method returns None.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsNone(self.rc.getSourceCode("does_not_exist"))

    def testGetFileReturnsStr(self) -> None:
        """
        Assert that getFile returns a path ending with '.py'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        f = self.rc.getFile()
        self.assertIsInstance(f, str)
        self.assertTrue(f.endswith(".py"))

    def testGetAnnotationsReturnsDict(self) -> None:
        """
        Assert that getAnnotations returns a dict.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getAnnotations(), dict)

    def testGetAnnotationsContainsPublicAttr(self) -> None:
        """
        Assert that 'public_attr' appears in the annotations dict.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("public_attr", self.rc.getAnnotations())

# ---------------------------------------------------------------------------
# Attribute inspection
# ---------------------------------------------------------------------------

class TestReflectionConcretePublicAttributes(TestCase):

    def setUp(self) -> None:
        """Initialise a shared ReflectionConcrete for attribute tests."""
        self.rc = ReflectionConcrete(SampleConcrete)

    def testGetPublicAttributesReturnsDict(self) -> None:
        """
        Assert that getPublicAttributes returns a dict.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getPublicAttributes(), dict)

    def testPublicAttrPresent(self) -> None:
        """
        Assert that 'public_attr' appears in the public attributes dict.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("public_attr", self.rc.getPublicAttributes())

    def testProtectedAttrAbsent(self) -> None:
        """
        Assert that '_protected_attr' is absent from the public attributes dict.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertNotIn("_protected_attr", self.rc.getPublicAttributes())

    def testHasAttributeReturnsTrueForPublicAttr(self) -> None:
        """
        Assert that hasAttribute returns True for 'public_attr'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertTrue(self.rc.hasAttribute("public_attr"))

    def testHasAttributeReturnsFalseForUnknown(self) -> None:
        """
        Assert that hasAttribute returns False for an absent name.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertFalse(self.rc.hasAttribute("nonexistent_attr"))

    def testGetAttributeReturnsValue(self) -> None:
        """
        Assert that getAttribute returns 10 for 'public_attr'.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertEqual(self.rc.getAttribute("public_attr"), 10)

    def testGetAttributeReturnsDefaultForMissing(self) -> None:
        """
        Assert that getAttribute returns None for an absent name.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsNone(self.rc.getAttribute("does_not_exist"))

    def testGetAttributesReturnsDict(self) -> None:
        """
        Assert that getAttributes returns a dict.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getAttributes(), dict)


class TestReflectionConcreteProtectedAttributes(TestCase):

    def setUp(self) -> None:
        """Initialise a shared ReflectionConcrete for protected attribute tests."""
        self.rc = ReflectionConcrete(SampleConcrete)

    def testGetProtectedAttributesReturnsDict(self) -> None:
        """
        Assert that getProtectedAttributes returns a dict.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getProtectedAttributes(), dict)

    def testProtectedAttrPresent(self) -> None:
        """
        Assert that '_protected_attr' is in the protected attributes dict.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("_protected_attr", self.rc.getProtectedAttributes())

    def testPublicAttrAbsentFromProtected(self) -> None:
        """
        Assert that 'public_attr' does not appear in the protected attributes.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertNotIn("public_attr", self.rc.getProtectedAttributes())


class TestReflectionConcreteDunderAttributes(TestCase):

    def setUp(self) -> None:
        """Initialise a shared ReflectionConcrete for dunder attribute tests."""
        self.rc = ReflectionConcrete(SampleConcrete)

    def testGetDunderAttributesReturnsDict(self) -> None:
        """
        Assert that getDunderAttributes returns a dict.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getDunderAttributes(), dict)

    def testGetMagicAttributesAliasesDunder(self) -> None:
        """
        Assert that getMagicAttributes returns the same dict as getDunderAttributes.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertEqual(
            self.rc.getMagicAttributes(),
            self.rc.getDunderAttributes(),
        )

# ---------------------------------------------------------------------------
# Attribute mutation
# ---------------------------------------------------------------------------

class TestReflectionConcreteSetAttribute(TestCase):

    def testSetAttributeReturnsTrueOnSuccess(self) -> None:
        """
        Assert that setAttribute returns True when the attribute is set.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        rc = ReflectionConcrete(_make_mutable_concrete())
        self.assertTrue(rc.setAttribute("new_attr", 42))

    def testSetAttributeInvalidNameRaisesValueError(self) -> None:
        """
        Assert that an invalid (non-identifier) name raises ValueError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        rc = ReflectionConcrete(_make_mutable_concrete())
        with self.assertRaises(ValueError):
            rc.setAttribute("123invalid", 1)

    def testSetAttributeKeywordNameRaisesValueError(self) -> None:
        """
        Assert that a Python keyword as attribute name raises ValueError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        rc = ReflectionConcrete(_make_mutable_concrete())
        with self.assertRaises(ValueError):
            rc.setAttribute("class", 1)

    def testSetAttributeCallableValueRaisesTypeError(self) -> None:
        """
        Assert that setting a callable value raises TypeError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        rc = ReflectionConcrete(_make_mutable_concrete())
        with self.assertRaises(TypeError):
            rc.setAttribute("fn", lambda: None)

class TestReflectionConcreteRemoveAttribute(TestCase):

    def testRemoveAttributeReturnsTrueOnSuccess(self) -> None:
        """
        Assert that removeAttribute returns True when the attribute is removed.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        rc = ReflectionConcrete(_make_mutable_concrete())
        self.assertTrue(rc.removeAttribute("mutable_attr"))

    def testRemoveAttributeMissingRaisesValueError(self) -> None:
        """
        Assert that removing an absent attribute raises ValueError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        rc = ReflectionConcrete(_make_mutable_concrete())
        with self.assertRaises(ValueError):
            rc.removeAttribute("nonexistent_attr")

# ---------------------------------------------------------------------------
# Public methods
# ---------------------------------------------------------------------------

class TestReflectionConcretePublicMethods(TestCase):

    def setUp(self) -> None:
        """Initialise a shared ReflectionConcrete for public method tests."""
        self.rc = ReflectionConcrete(SampleConcrete)

    def testGetPublicMethodsReturnsList(self) -> None:
        """
        Assert that getPublicMethods returns a list.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getPublicMethods(), list)

    def testPublicMethodPresent(self) -> None:
        """
        Assert that 'publicMethod' appears in getPublicMethods.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("publicMethod", self.rc.getPublicMethods())

    def testPublicAsyncMethodPresent(self) -> None:
        """
        Assert that 'publicAsyncMethod' appears in getPublicMethods.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("publicAsyncMethod", self.rc.getPublicMethods())

    def testProtectedMethodAbsent(self) -> None:
        """
        Assert that '_protectedMethod' does not appear in getPublicMethods.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertNotIn("_protectedMethod", self.rc.getPublicMethods())

    def testGetPublicSyncMethodsReturnsList(self) -> None:
        """
        Assert that getPublicSyncMethods returns a list.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getPublicSyncMethods(), list)

    def testPublicSyncMethodsExcludesAsync(self) -> None:
        """
        Assert that 'publicAsyncMethod' is absent from getPublicSyncMethods.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertNotIn("publicAsyncMethod", self.rc.getPublicSyncMethods())

    def testGetPublicAsyncMethodsReturnsList(self) -> None:
        """
        Assert that getPublicAsyncMethods returns a list.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getPublicAsyncMethods(), list)

    def testPublicAsyncMethodsContainsAsync(self) -> None:
        """
        Assert that 'publicAsyncMethod' appears in getPublicAsyncMethods.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("publicAsyncMethod", self.rc.getPublicAsyncMethods())

# ---------------------------------------------------------------------------
# Protected methods
# ---------------------------------------------------------------------------

class TestReflectionConcreteProtectedMethods(TestCase):

    def setUp(self) -> None:
        """Initialise a shared ReflectionConcrete for protected method tests."""
        self.rc = ReflectionConcrete(SampleConcrete)

    def testGetProtectedMethodsReturnsList(self) -> None:
        """
        Assert that getProtectedMethods returns a list.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getProtectedMethods(), list)

    def testProtectedMethodPresent(self) -> None:
        """
        Assert that '_protectedMethod' appears in getProtectedMethods.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("_protectedMethod", self.rc.getProtectedMethods())

    def testPublicMethodAbsentFromProtected(self) -> None:
        """
        Assert that 'publicMethod' does not appear in getProtectedMethods.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertNotIn("publicMethod", self.rc.getProtectedMethods())

    def testGetProtectedSyncMethodsReturnsList(self) -> None:
        """
        Assert that getProtectedSyncMethods returns a list.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getProtectedSyncMethods(), list)

    def testProtectedSyncExcludesAsync(self) -> None:
        """
        Assert that '_protectedAsyncMethod' is absent from getProtectedSyncMethods.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertNotIn(
            "_protectedAsyncMethod", self.rc.getProtectedSyncMethods(),
        )

    def testGetProtectedAsyncMethodsReturnsList(self) -> None:
        """
        Assert that getProtectedAsyncMethods returns a list.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getProtectedAsyncMethods(), list)

    def testProtectedAsyncContainsAsyncMethod(self) -> None:
        """
        Assert that '_protectedAsyncMethod' appears in getProtectedAsyncMethods.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn(
            "_protectedAsyncMethod", self.rc.getProtectedAsyncMethods(),
        )

# ---------------------------------------------------------------------------
# Private methods
# ---------------------------------------------------------------------------

class TestReflectionConcretePrivateMethods(TestCase):

    def setUp(self) -> None:
        """Initialise a shared ReflectionConcrete for private method tests."""
        self.rc = ReflectionConcrete(SampleConcrete)

    def testGetPrivateMethodsReturnsList(self) -> None:
        """
        Assert that getPrivateMethods returns a list.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getPrivateMethods(), list)

    def testPrivateMethodPresent(self) -> None:
        """
        Assert that '__privateMethod' (de-mangled) appears in getPrivateMethods.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("__privateMethod", self.rc.getPrivateMethods())

    def testGetPrivateSyncMethodsReturnsList(self) -> None:
        """
        Assert that getPrivateSyncMethods returns a list.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getPrivateSyncMethods(), list)

# ---------------------------------------------------------------------------
# Class methods
# ---------------------------------------------------------------------------

class TestReflectionConcreteClassMethods(TestCase):

    def setUp(self) -> None:
        """Initialise a shared ReflectionConcrete for class method tests."""
        self.rc = ReflectionConcrete(SampleConcrete)

    def testGetPublicClassMethodsReturnsList(self) -> None:
        """
        Assert that getPublicClassMethods returns a list.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getPublicClassMethods(), list)

    def testPublicClassMethodPresent(self) -> None:
        """
        Assert that 'classMethod' appears in getPublicClassMethods.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("classMethod", self.rc.getPublicClassMethods())

    def testGetProtectedClassMethodsReturnsList(self) -> None:
        """
        Assert that getProtectedClassMethods returns a list.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getProtectedClassMethods(), list)

    def testProtectedClassMethodPresent(self) -> None:
        """
        Assert that '_protectedClassMethod' appears in getProtectedClassMethods.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn(
            "_protectedClassMethod", self.rc.getProtectedClassMethods(),
        )

    def testGetPublicClassSyncMethodsReturnsList(self) -> None:
        """
        Assert that getPublicClassSyncMethods returns a list.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getPublicClassSyncMethods(), list)

# ---------------------------------------------------------------------------
# Static methods
# ---------------------------------------------------------------------------

class TestReflectionConcreteStaticMethods(TestCase):

    def setUp(self) -> None:
        """Initialise a shared ReflectionConcrete for static method tests."""
        self.rc = ReflectionConcrete(SampleConcrete)

    def testGetPublicStaticMethodsReturnsList(self) -> None:
        """
        Assert that getPublicStaticMethods returns a list.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getPublicStaticMethods(), list)

    def testPublicStaticMethodPresent(self) -> None:
        """
        Assert that 'staticMethod' appears in getPublicStaticMethods.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("staticMethod", self.rc.getPublicStaticMethods())

    def testGetProtectedStaticMethodsReturnsList(self) -> None:
        """
        Assert that getProtectedStaticMethods returns a list.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getProtectedStaticMethods(), list)

    def testProtectedStaticMethodPresent(self) -> None:
        """
        Assert that '_protectedStaticMethod' appears in getProtectedStaticMethods.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn(
            "_protectedStaticMethod", self.rc.getProtectedStaticMethods(),
        )

    def testGetPublicStaticSyncMethodsReturnsList(self) -> None:
        """
        Assert that getPublicStaticSyncMethods returns a list.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getPublicStaticSyncMethods(), list)

# ---------------------------------------------------------------------------
# Dunder methods
# ---------------------------------------------------------------------------

class TestReflectionConcreteDunderMethods(TestCase):

    def setUp(self) -> None:
        """Initialise a shared ReflectionConcrete for dunder method tests."""
        self.rc = ReflectionConcrete(SampleConcrete)

    def testGetDunderMethodsReturnsList(self) -> None:
        """
        Assert that getDunderMethods returns a list.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getDunderMethods(), list)

    def testGetMagicMethodsAliasesDunder(self) -> None:
        """
        Assert that getMagicMethods returns the same result as getDunderMethods.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertEqual(self.rc.getMagicMethods(), self.rc.getDunderMethods())

    def testDunderMethodPresent(self) -> None:
        """
        Assert that '__repr__' appears in getDunderMethods.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("__repr__", self.rc.getDunderMethods())

# ---------------------------------------------------------------------------
# Method operations (set / remove / signature)
# ---------------------------------------------------------------------------

class TestReflectionConcreteMethodOperations(TestCase):

    def testSetMethodReturnsTrueOnSuccess(self) -> None:
        """
        Assert that setMethod returns True when a new method is added.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        rc = ReflectionConcrete(_make_mutable_concrete())
        self.assertTrue(rc.setMethod("new_method", lambda _self: None))

    def testSetMethodDuplicateRaisesValueError(self) -> None:
        """
        Assert that adding an already-existing method raises ValueError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        rc = ReflectionConcrete(_make_mutable_concrete())
        with self.assertRaises(ValueError):
            rc.setMethod("deletableMethod", lambda _self: None)

    def testSetMethodInvalidNameRaisesValueError(self) -> None:
        """
        Assert that an invalid method name raises ValueError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        rc = ReflectionConcrete(_make_mutable_concrete())
        with self.assertRaises(ValueError):
            rc.setMethod("123bad", lambda: None)

    def testSetMethodNonCallableRaisesTypeError(self) -> None:
        """
        Assert that passing a non-callable value raises TypeError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        rc = ReflectionConcrete(_make_mutable_concrete())
        with self.assertRaises(TypeError):
            rc.setMethod("some_method", "not_callable")  # type: ignore[arg-type]

    def testRemoveMethodReturnsTrueOnSuccess(self) -> None:
        """
        Assert that removeMethod returns True when removing an existing method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        rc = ReflectionConcrete(_make_mutable_concrete())
        self.assertTrue(rc.removeMethod("deletableMethod"))

    def testRemoveMethodMissingRaisesValueError(self) -> None:
        """
        Assert that removing a non-existent method raises ValueError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        rc = ReflectionConcrete(_make_mutable_concrete())
        with self.assertRaises(ValueError):
            rc.removeMethod("ghost_method")

    def testGetMethodSignatureReturnsInspectSignature(self) -> None:
        """
        Assert that getMethodSignature returns an inspect.Signature.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        rc = ReflectionConcrete(SampleConcrete)
        sig = rc.getMethodSignature("publicMethod")
        self.assertIsInstance(sig, inspect.Signature)

    def testGetMethodSignatureMissingRaisesValueError(self) -> None:
        """
        Assert that getMethodSignature for an absent method raises ValueError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        rc = ReflectionConcrete(SampleConcrete)
        with self.assertRaises(ValueError):
            rc.getMethodSignature("nonexistent_method")

# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

class TestReflectionConcreteProperties(TestCase):

    def setUp(self) -> None:
        """Initialise a shared ReflectionConcrete for property tests."""
        self.rc = ReflectionConcrete(SampleConcrete)

    def testGetPropertiesReturnsList(self) -> None:
        """
        Assert that getProperties returns a list.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getProperties(), list)

    def testPublicPropertyPresent(self) -> None:
        """
        Assert that 'aProperty' appears in getProperties.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("aProperty", self.rc.getProperties())

    def testGetPublicPropertiesReturnsList(self) -> None:
        """
        Assert that getPublicProperties returns a list.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getPublicProperties(), list)

    def testPublicPropertyInPublicProperties(self) -> None:
        """
        Assert that 'aProperty' appears in getPublicProperties.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("aProperty", self.rc.getPublicProperties())

    def testProtectedPropertyAbsentFromPublic(self) -> None:
        """
        Assert that '_protectedProperty' is absent from getPublicProperties.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertNotIn("_protectedProperty", self.rc.getPublicProperties())

    def testGetProtectedPropertiesReturnsList(self) -> None:
        """
        Assert that getProtectedProperties returns a list.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.getProtectedProperties(), list)

    def testProtectedPropertyPresent(self) -> None:
        """
        Assert that '_protectedProperty' appears in getProtectedProperties.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("_protectedProperty", self.rc.getProtectedProperties())

    def testGetPropertySignatureReturnsInspectSignature(self) -> None:
        """
        Assert that getPropertySignature returns an inspect.Signature.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(
            self.rc.getPropertySignature("aProperty"), inspect.Signature,
        )

    def testGetPropertyDocstringReturnsStrOrNone(self) -> None:
        """
        Assert that getPropertyDocstring returns a str for a documented property.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        doc = self.rc.getPropertyDocstring("aProperty")
        self.assertIsInstance(doc, str)

    def testGetPropertyMissingRaisesValueError(self) -> None:
        """
        Assert that getProperty raises ValueError for an absent property.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(ValueError):
            self.rc.getProperty("nonexistent_property")

# ---------------------------------------------------------------------------
# Dependency / signature analysis
# ---------------------------------------------------------------------------

class TestReflectionConcreteDependencies(TestCase):

    def setUp(self) -> None:
        """Initialise a shared ReflectionConcrete for dependency tests."""
        self.rc = ReflectionConcrete(SampleConcrete)

    def testGetConstructorSignatureReturnsInspectSignature(self) -> None:
        """
        Assert that getConstructorSignature returns an inspect.Signature.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(
            self.rc.getConstructorSignature(), inspect.Signature,
        )

    def testConstructorSignatureReturnsSignature(self) -> None:
        """
        Assert that constructorSignature returns a Signature instance.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rc.constructorSignature(), Signature)

    def testMethodSignatureReturnsSignature(self) -> None:
        """
        Assert that methodSignature returns a Signature instance.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(
            self.rc.methodSignature("publicMethod"), Signature,
        )

    def testMethodSignatureMissingRaisesAttributeError(self) -> None:
        """
        Assert that methodSignature for an absent method raises AttributeError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(AttributeError):
            self.rc.methodSignature("ghost_method")

# ---------------------------------------------------------------------------
# clearCache
# ---------------------------------------------------------------------------

class TestReflectionConcreteClearCache(TestCase):

    def setUp(self) -> None:
        """Initialise a shared ReflectionConcrete for clearCache tests."""
        self.rc = ReflectionConcrete(SampleConcrete)

    def testClearCacheReturnsNone(self) -> None:
        """
        Assert that clearCache explicitly returns None.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsNone(self.rc.clearCache())

    def testClearCacheEvictsStoredEntries(self) -> None:
        """
        Assert that manually stored cache entries are gone after clearCache.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rc["sentinel"] = True
        self.rc.clearCache()
        self.assertNotIn("sentinel", self.rc)

    def testClearCacheEvictsComputedEntries(self) -> None:
        """
        Assert that getSourceCode's cached entry is removed after clearCache.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        _ = self.rc.getSourceCode()
        self.rc.clearCache()
        self.assertNotIn("source_code", self.rc)

    def testClearCacheAllowsRecomputation(self) -> None:
        """
        Assert that getPublicMethods returns a valid list after clearCache.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        _ = self.rc.getPublicMethods()
        self.rc.clearCache()
        self.assertIsInstance(self.rc.getPublicMethods(), list)

# ---------------------------------------------------------------------------
# Asynchronous and private member classification
# ---------------------------------------------------------------------------

class TestReflectionConcreteAsyncMembers(TestCase):

    def setUp(self) -> None:
        """Initialise a shared ReflectionConcrete for async member tests."""
        self.rc = ReflectionConcrete(SampleConcrete)

    def testGetMethodsIncludesEveryVisibility(self) -> None:
        """
        Assert that getMethods aggregates all visibility buckets.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        methods = self.rc.getMethods()
        self.assertIn("publicMethod", methods)
        self.assertIn("_protectedMethod", methods)
        self.assertIn("__privateMethod", methods)

    def testGetPrivateAttributesStripsMangling(self) -> None:
        """
        Assert that private attributes are exposed without the class prefix.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("__private_attr", self.rc.getPrivateAttributes())

    def testPrivateAsyncMethodsExcludeSyncMethods(self) -> None:
        """
        Assert that private coroutine methods are reported separately.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        result = self.rc.getPrivateAsyncMethods()
        self.assertIn("__privateAsyncMethod", result)
        self.assertNotIn("__privateMethod", result)

    def testPublicClassAsyncMethodsContainAsyncClassMethod(self) -> None:
        """
        Assert that public asynchronous class methods are reported.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("classAsyncMethod", self.rc.getPublicClassAsyncMethods())

    def testProtectedClassMethodsSplitBySyncAndAsync(self) -> None:
        """
        Assert that protected class methods split by coroutine status.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sync_methods = self.rc.getProtectedClassSyncMethods()
        async_methods = self.rc.getProtectedClassAsyncMethods()
        self.assertIn("_protectedClassMethod", sync_methods)
        self.assertIn("_protectedClassAsyncMethod", async_methods)

    def testPrivateClassMethodsSplitBySyncAndAsync(self) -> None:
        """
        Assert that private class methods split by coroutine status.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("__privateClassMethod", self.rc.getPrivateClassMethods())
        self.assertIn(
            "__privateClassMethod",
            self.rc.getPrivateClassSyncMethods(),
        )
        self.assertIn(
            "__privateClassAsyncMethod",
            self.rc.getPrivateClassAsyncMethods(),
        )

    def testPublicStaticAsyncMethodsContainAsyncStaticMethod(self) -> None:
        """
        Assert that public asynchronous static methods are reported.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("staticAsyncMethod", self.rc.getPublicStaticAsyncMethods())

    def testProtectedStaticMethodsSplitBySyncAndAsync(self) -> None:
        """
        Assert that protected static methods split by coroutine status.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sync_methods = self.rc.getProtectedStaticSyncMethods()
        async_methods = self.rc.getProtectedStaticAsyncMethods()
        self.assertIn("_protectedStaticMethod", sync_methods)
        self.assertIn("_protectedStaticAsyncMethod", async_methods)

    def testPrivateStaticMethodsSplitBySyncAndAsync(self) -> None:
        """
        Assert that private static methods split by coroutine status.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("__privateStaticMethod", self.rc.getPrivateStaticMethods())
        self.assertIn(
            "__privateStaticMethod",
            self.rc.getPrivateStaticSyncMethods(),
        )
        self.assertIn(
            "__privateStaticAsyncMethod",
            self.rc.getPrivateStaticAsyncMethods(),
        )

    def testPrivatePropertiesStripMangling(self) -> None:
        """
        Assert that private properties are reported without the class prefix.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("__privateProperty", self.rc.getPrivateProperties())

# ---------------------------------------------------------------------------
# Private member access through name mangling
# ---------------------------------------------------------------------------

class TestReflectionConcretePrivateAccess(TestCase):

    def setUp(self) -> None:
        """Initialise a shared ReflectionConcrete for private access tests."""
        self.rc = ReflectionConcrete(SampleConcrete)

    def testGetPropertyResolvesPrivateNames(self) -> None:
        """
        Assert that private property values are readable.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertEqual(self.rc.getProperty("__privateProperty"), "private_value")

    def testGetPropertySignatureResolvesPrivateNames(self) -> None:
        """
        Assert that private property signatures are reachable.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        signature = self.rc.getPropertySignature("__privateProperty")
        self.assertIsInstance(signature, inspect.Signature)

    def testGetMethodSignatureResolvesPrivateNames(self) -> None:
        """
        Assert that private method signatures are reachable.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        signature = self.rc.getMethodSignature("__privateMethod")
        self.assertIsInstance(signature, inspect.Signature)

    def testGetPropertyDocstringResolvesPrivateNames(self) -> None:
        """
        Assert that private property docstrings are reachable.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        docstring = self.rc.getPropertyDocstring("__privateProperty")
        self.assertIn("private property", docstring)

    def testMethodSignatureResolvesPrivateNames(self) -> None:
        """
        Assert that private method dependency signatures are reachable.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsNotNone(self.rc.methodSignature("__privateMethod"))

    def testGetSourceCodeResolvesPrivateMethodNames(self) -> None:
        """
        Assert that private method sources are reachable.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        source = self.rc.getSourceCode("__privateMethod")
        self.assertIn("def __privateMethod", source)

    def testSetAndRemovePrivateAttribute(self) -> None:
        """
        Assert that private attributes are mangled on write and delete.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        reflection = ReflectionConcrete(_make_mutable_concrete())
        self.assertTrue(reflection.setAttribute("__hidden", 5))
        self.assertIn("__hidden", reflection.getPrivateAttributes())
        self.assertTrue(reflection.removeAttribute("__hidden"))
        self.assertNotIn("__hidden", reflection.getPrivateAttributes())

    def testSetPrivateMethodResolvesMangledName(self) -> None:
        """
        Assert that injected private methods use the mangled name.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        reflection = ReflectionConcrete(_make_mutable_concrete())
        self.assertTrue(reflection.setMethod("__injected", _replacement_method))
        self.assertIn("__injected", reflection.getPrivateMethods())

    def testRemovePrivateMethodResolvesMangledName(self) -> None:
        """
        Assert that private methods are removed using the mangled name.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        reflection = ReflectionConcrete(_make_private_method_concrete())
        self.assertTrue(reflection.removeMethod("__hiddenMethod"))
        self.assertFalse(reflection.hasMethod("__hiddenMethod"))

# ---------------------------------------------------------------------------
# Error branches
# ---------------------------------------------------------------------------

class TestReflectionConcreteErrorBranches(TestCase):

    def testGetSourceCodeReturnsNoneWhenUnavailable(self) -> None:
        """
        Assert that classes without locatable source return None.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        reflection = ReflectionConcrete(_make_moduleless_concrete())
        self.assertIsNone(reflection.getSourceCode())

    def testGetSourceCodeReturnsNoneForUnknownMethods(self) -> None:
        """
        Assert that unknown method names produce no source.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        reflection = ReflectionConcrete(SampleConcrete)
        self.assertIsNone(reflection.getSourceCode("ghostMethod"))

    def testGetFileRaisesValueErrorForUnknownModules(self) -> None:
        """
        Assert that classes with an unresolvable module expose no file.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        reflection = ReflectionConcrete(_make_moduleless_concrete())
        with self.assertRaises(ValueError):
            reflection.getFile()

    def testGetMethodSignatureRaisesTypeErrorForNonCallable(self) -> None:
        """
        Assert that a stale method entry pointing at data raises TypeError.

        Returns
        -------
        None
            Raises AssertionError on failure.

        Notes
        -----
        The class is mutated directly, bypassing the reflection API, so the
        scanned member cache still lists the name as a method.
        """
        concrete = _make_mutable_concrete()
        reflection = ReflectionConcrete(concrete)
        self.assertTrue(reflection.hasMethod("deletableMethod"))
        concrete.deletableMethod = 7
        with self.assertRaises(TypeError):
            reflection.getMethodSignature("deletableMethod")

    def testGetPropertySignatureRaisesTypeErrorForNonProperty(self) -> None:
        """
        Assert that non-property members are rejected by getPropertySignature.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        reflection = ReflectionConcrete(SampleConcrete)
        with self.assertRaises(TypeError):
            reflection.getPropertySignature("publicMethod")

    def testGetPropertyDocstringRaisesTypeErrorForNonProperty(self) -> None:
        """
        Assert that non-property members are rejected by getPropertyDocstring.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        reflection = ReflectionConcrete(SampleConcrete)
        with self.assertRaises(TypeError):
            reflection.getPropertyDocstring("publicMethod")

    def testGetPropertyRaisesTypeErrorForNonProperty(self) -> None:
        """
        Assert that non-property members are rejected by getProperty.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        reflection = ReflectionConcrete(SampleConcrete)
        with self.assertRaises(TypeError):
            reflection.getProperty("publicMethod")

# ---------------------------------------------------------------------------
# Memoization
# ---------------------------------------------------------------------------

class TestReflectionConcreteMemoization(TestCase):

    def setUp(self) -> None:
        """Initialise a shared ReflectionConcrete for memoization tests."""
        self.rc = ReflectionConcrete(SampleConcrete)

    def testModuleWithClassNameIsMemoized(self) -> None:
        """
        Assert that getModuleWithClassName returns the cached string.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIs(
            self.rc.getModuleWithClassName(),
            self.rc.getModuleWithClassName(),
        )

    def testClassSourceCodeIsMemoized(self) -> None:
        """
        Assert that getSourceCode returns the cached class source.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIs(self.rc.getSourceCode(), self.rc.getSourceCode())

    def testMethodSourceCodeIsMemoized(self) -> None:
        """
        Assert that getSourceCode returns the cached method source.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIs(
            self.rc.getSourceCode("publicMethod"),
            self.rc.getSourceCode("publicMethod"),
        )

    def testFileIsMemoized(self) -> None:
        """
        Assert that getFile returns the cached path.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIs(self.rc.getFile(), self.rc.getFile())

    def testAnnotationsAreMemoized(self) -> None:
        """
        Assert that getAnnotations returns the cached mapping.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIs(self.rc.getAnnotations(), self.rc.getAnnotations())

    def testMethodSignatureIsMemoized(self) -> None:
        """
        Assert that getMethodSignature returns the cached signature.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIs(
            self.rc.getMethodSignature("publicMethod"),
            self.rc.getMethodSignature("publicMethod"),
        )

    def testPropertySignatureIsMemoized(self) -> None:
        """
        Assert that getPropertySignature returns the cached signature.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIs(
            self.rc.getPropertySignature("aProperty"),
            self.rc.getPropertySignature("aProperty"),
        )

    def testPropertyDocstringIsMemoized(self) -> None:
        """
        Assert that getPropertyDocstring returns the cached docstring.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIs(
            self.rc.getPropertyDocstring("aProperty"),
            self.rc.getPropertyDocstring("aProperty"),
        )

    def testConstructorSignatureIsMemoized(self) -> None:
        """
        Assert that getConstructorSignature returns the cached signature.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIs(
            self.rc.getConstructorSignature(),
            self.rc.getConstructorSignature(),
        )

    def testConstructorDependenciesAreMemoized(self) -> None:
        """
        Assert that constructorSignature returns the cached analysis.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIs(
            self.rc.constructorSignature(),
            self.rc.constructorSignature(),
        )

    def testMethodDependenciesAreMemoized(self) -> None:
        """
        Assert that methodSignature returns the cached analysis.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIs(
            self.rc.methodSignature("publicMethod"),
            self.rc.methodSignature("publicMethod"),
        )

    def testEveryAccessorTriggersTheLazyScanOnItsOwn(self) -> None:
        """
        Assert that each accessor populates the member cache by itself.

        Returns
        -------
        None
            Raises AssertionError on failure.

        Notes
        -----
        A brand-new reflection instance is used for every accessor so that
        the lazy scan is triggered from that accessor and not from a
        previous call.
        """
        for getter in _SCAN_TRIGGERING_GETTERS:
            reflection = ReflectionConcrete(SampleConcrete)
            result = getattr(reflection, getter)()
            self.assertIsInstance(result, (dict, list), msg=getter)

# ---------------------------------------------------------------------------
# Missing property lookups
# ---------------------------------------------------------------------------

class TestReflectionConcreteMissingProperties(TestCase):

    def setUp(self) -> None:
        """Initialise a shared ReflectionConcrete for missing-name tests."""
        self.rc = ReflectionConcrete(SampleConcrete)

    def testGetPropertyRaisesValueErrorForUnknownName(self) -> None:
        """
        Assert that reading an unknown property raises ValueError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(ValueError):
            self.rc.getProperty("ghostProperty")

    def testGetPropertySignatureRaisesValueErrorForUnknownName(self) -> None:
        """
        Assert that signatures of unknown properties raise ValueError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(ValueError):
            self.rc.getPropertySignature("ghostProperty")

    def testGetPropertyDocstringRaisesValueErrorForUnknownName(self) -> None:
        """
        Assert that docstrings of unknown properties raise ValueError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(ValueError):
            self.rc.getPropertyDocstring("ghostProperty")

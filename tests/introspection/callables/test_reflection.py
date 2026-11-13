# ruff: noqa: ARG001, E731, PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# An unused defaulted parameter and an assigned lambda are reflection targets.

import inspect
import types
from orionis.introspection.callables.reflection import ReflectionCallable
from orionis.introspection.dependencies.entities.signature import Signature
from orionis.test import TestCase

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _simple_function(x: int, y: str = "hello") -> bool:
    """Return whether x is positive.

    Parameters
    ----------
    x : int
        Value supplied for ``x``.
    y : str
        Value supplied for ``y``.

    Returns
    -------
    bool
        Value produced by the helper.
    """
    return x > 0


def _no_doc_function() -> None:
    """Provide a callable whose runtime docstring is absent.

    Returns
    -------
    None
        No return value.
    """


_no_doc_function.__doc__ = None

_lambda = lambda a, b: a + b


class _SampleClass:
    def regularMethod(self, value: int) -> int:
        """Return value doubled.

        Parameters
        ----------
        value : int
            Value supplied for ``value``.

        Returns
        -------
        int
            Value produced by the helper.
        """
        return value * 2

    @staticmethod
    def staticMethod(n: int) -> int:
        """Return n plus one.

        Parameters
        ----------
        n : int
            Value supplied for ``n``.

        Returns
        -------
        int
            Value produced by the helper.
        """
        return n + 1


# Function whose code object points at a synthetic file, so that the
# interpreter cannot recover its source lines.
_sourceless_function = types.FunctionType(
    _simple_function.__code__.replace(co_filename="<orionis-missing-source>"),
    {"__name__": "orionis_missing_source"},
    "_sourceless_function",
)

# ---------------------------------------------------------------------------
# __init__ / construction
# ---------------------------------------------------------------------------


class TestReflectionCallableInit(TestCase):
    def testInitWithRegularFunctionSucceeds(self) -> None:
        """
        Assert that wrapping a plain function does not raise.

        Returns
        -------
        None
            No return value.
        """
        rc = ReflectionCallable(_simple_function)
        self.assertIsInstance(rc, ReflectionCallable)

    def testInitWithLambdaSucceeds(self) -> None:
        """
        Assert that wrapping a lambda does not raise.

        Returns
        -------
        None
            No return value.
        """
        rc = ReflectionCallable(_lambda)
        self.assertIsInstance(rc, ReflectionCallable)

    def testInitWithBoundMethodSucceeds(self) -> None:
        """
        Assert that wrapping a bound instance method does not raise.

        Returns
        -------
        None
            No return value.
        """
        obj = _SampleClass()
        rc = ReflectionCallable(obj.regularMethod)
        self.assertIsInstance(rc, ReflectionCallable)

    def testInitWithStaticMethodFunctionSucceeds(self) -> None:
        """
        Assert that wrapping a static method function does not raise.

        Returns
        -------
        None
            No return value.
        """
        rc = ReflectionCallable(_SampleClass.staticMethod)
        self.assertIsInstance(rc, ReflectionCallable)

    def testInitWithNonCallableRaisesTypeError(self) -> None:
        """
        Assert that passing a plain integer raises TypeError.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(TypeError):
            ReflectionCallable(42)  # type: ignore[arg-type]

    def testInitWithClassRaisesTypeError(self) -> None:
        """
        Assert that passing a class object (no __code__) raises TypeError.

        Returns
        -------
        None
            No return value.
        """

        class _Plain:
            pass

        with self.assertRaises(TypeError):
            ReflectionCallable(_Plain)  # type: ignore[arg-type]

    def testInitWithBuiltinRaisesTypeError(self) -> None:
        """
        Assert that passing a built-in function raises TypeError.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(TypeError):
            ReflectionCallable(len)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Cache protocol  (__getitem__, __setitem__, __contains__, __delitem__)
# ---------------------------------------------------------------------------


class TestReflectionCallableCacheProtocol(TestCase):
    def setUp(self) -> None:
        """Initialise a shared ReflectionCallable for cache tests.

        Returns
        -------
        None
            No return value.
        """
        self.rc = ReflectionCallable(_simple_function)

    def testSetAndGetItem(self) -> None:
        """
        Assert that __setitem__ stores and __getitem__ retrieves the value.

        Returns
        -------
        None
            No return value.
        """
        self.rc["my_key"] = "my_value"
        self.assertEqual(self.rc["my_key"], "my_value")

    def testContainsReturnsTrueAfterSet(self) -> None:
        """
        Assert that __contains__ returns True after storing a key.

        Returns
        -------
        None
            No return value.
        """
        self.rc["exists"] = True
        self.assertIn("exists", self.rc)

    def testContainsReturnsFalseForMissingKey(self) -> None:
        """
        Assert that __contains__ returns False for a key never stored.

        Returns
        -------
        None
            No return value.
        """
        self.assertNotIn("ghost_key", self.rc)

    def testGetItemReturnNoneForMissingKey(self) -> None:
        """
        Assert that __getitem__ returns None for an absent key.

        Returns
        -------
        None
            No return value.
        """
        self.assertIsNone(self.rc["absent_key"])

    def testDelItemRemovesKey(self) -> None:
        """
        Assert that __delitem__ removes a previously stored key.

        Returns
        -------
        None
            No return value.
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
            No return value.
        """
        del self.rc["never_existed"]  # must not raise


# ---------------------------------------------------------------------------
# Identity methods
# ---------------------------------------------------------------------------


class TestReflectionCallableIdentity(TestCase):
    def setUp(self) -> None:
        """Initialise a shared ReflectionCallable for identity tests.

        Returns
        -------
        None
            No return value.
        """
        self.rc = ReflectionCallable(_simple_function)

    def testGetCallableReturnsSameObject(self) -> None:
        """
        Assert that getCallable returns the exact same function object.

        Returns
        -------
        None
            No return value.
        """
        self.assertIs(self.rc.getCallable(), _simple_function)

    def testGetNameMatchesFunctionName(self) -> None:
        """
        Assert that getName returns '_simple_function'.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(self.rc.getName(), "_simple_function")

    def testGetModuleNameReturnsStr(self) -> None:
        """
        Assert that getModuleName returns a str.

        Returns
        -------
        None
            No return value.
        """
        self.assertIsInstance(self.rc.getModuleName(), str)

    def testGetModuleWithCallableNameFormat(self) -> None:
        """
        Assert that getModuleWithCallableName uses 'module.name' format.

        Returns
        -------
        None
            No return value.
        """
        fqn = self.rc.getModuleWithCallableName()
        module, _, name = fqn.rpartition(".")
        self.assertEqual(name, "_simple_function")
        self.assertEqual(module, self.rc.getModuleName())


# ---------------------------------------------------------------------------
# Docstring
# ---------------------------------------------------------------------------


class TestReflectionCallableDocstring(TestCase):
    def testGetDocstringReturnsStr(self) -> None:
        """
        Assert that getDocstring returns a str for a documented function.

        Returns
        -------
        None
            No return value.
        """
        rc = ReflectionCallable(_simple_function)
        self.assertIsInstance(rc.getDocstring(), str)

    def testGetDocstringContainsContent(self) -> None:
        """
        Assert that getDocstring returns the actual docstring text.

        Returns
        -------
        None
            No return value.
        """
        rc = ReflectionCallable(_simple_function)
        self.assertIn("positive", rc.getDocstring())

    def testGetDocstringEmptyWhenAbsent(self) -> None:
        """
        Assert that getDocstring returns an empty string when no docstring exists.

        Returns
        -------
        None
            No return value.
        """
        rc = ReflectionCallable(_no_doc_function)
        self.assertEqual(rc.getDocstring(), "")


# ---------------------------------------------------------------------------
# Source code
# ---------------------------------------------------------------------------


class TestReflectionCallableSourceCode(TestCase):
    def setUp(self) -> None:
        """Initialise a shared ReflectionCallable for source-code tests.

        Returns
        -------
        None
            No return value.
        """
        self.rc = ReflectionCallable(_simple_function)

    def testGetSourceCodeReturnsStr(self) -> None:
        """
        Assert that getSourceCode returns a str.

        Returns
        -------
        None
            No return value.
        """
        self.assertIsInstance(self.rc.getSourceCode(), str)

    def testGetSourceCodeContainsFunctionName(self) -> None:
        """
        Assert that getSourceCode contains the function definition keyword.

        Returns
        -------
        None
            No return value.
        """
        source = self.rc.getSourceCode()
        self.assertIn("def _simple_function", source)

    def testGetSourceCodeIsCached(self) -> None:
        """
        Assert that repeated calls return the identical string object.

        Returns
        -------
        None
            No return value.
        """
        first = self.rc.getSourceCode()
        second = self.rc.getSourceCode()
        self.assertIs(first, second)

    def testGetSourceCodeRaisesAttributeErrorWhenUnavailable(self) -> None:
        """
        Assert that unreadable sources are reported as AttributeError.

        Returns
        -------
        None
            No return value.
        """
        rc = ReflectionCallable(_sourceless_function)
        with self.assertRaises(AttributeError):
            rc.getSourceCode()


# ---------------------------------------------------------------------------
# File path
# ---------------------------------------------------------------------------


class TestReflectionCallableFile(TestCase):
    def setUp(self) -> None:
        """Initialise a shared ReflectionCallable for file-path tests.

        Returns
        -------
        None
            No return value.
        """
        self.rc = ReflectionCallable(_simple_function)

    def testGetFileReturnsStr(self) -> None:
        """
        Assert that getFile returns a str.

        Returns
        -------
        None
            No return value.
        """
        self.assertIsInstance(self.rc.getFile(), str)

    def testGetFileEndsPy(self) -> None:
        """
        Assert that getFile returns a path ending with '.py'.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(self.rc.getFile().endswith(".py"))

    def testGetFileIsCached(self) -> None:
        """
        Assert that repeated calls to getFile return the same object.

        Returns
        -------
        None
            No return value.
        """
        first = self.rc.getFile()
        second = self.rc.getFile()
        self.assertIs(first, second)


# ---------------------------------------------------------------------------
# Signature
# ---------------------------------------------------------------------------


class TestReflectionCallableSignature(TestCase):
    def setUp(self) -> None:
        """Initialise a ReflectionCallable for signature tests.

        Returns
        -------
        None
            No return value.
        """
        self.rc = ReflectionCallable(_simple_function)

    def testGetSignatureReturnsInspectSignature(self) -> None:
        """
        Assert that getSignature returns an inspect.Signature instance.

        Returns
        -------
        None
            No return value.
        """
        self.assertIsInstance(self.rc.getSignature(), inspect.Signature)

    def testGetSignatureContainsParamX(self) -> None:
        """
        Assert that 'x' is present in the signature parameters.

        Returns
        -------
        None
            No return value.
        """
        self.assertIn("x", self.rc.getSignature().parameters)

    def testGetSignatureContainsParamY(self) -> None:
        """
        Assert that 'y' is present in the signature parameters.

        Returns
        -------
        None
            No return value.
        """
        self.assertIn("y", self.rc.getSignature().parameters)

    def testGetSignatureParamYHasDefault(self) -> None:
        """
        Assert that parameter 'y' has the default value 'hello'.

        Returns
        -------
        None
            No return value.
        """
        param_y = self.rc.getSignature().parameters["y"]
        self.assertEqual(param_y.default, "hello")

    def testGetSignatureIsCached(self) -> None:
        """
        Assert that repeated calls return the identical Signature object.

        Returns
        -------
        None
            No return value.
        """
        first = self.rc.getSignature()
        second = self.rc.getSignature()
        self.assertIs(first, second)

    def testGetSignatureForLambda(self) -> None:
        """
        Assert that getSignature works correctly for a lambda.

        Returns
        -------
        None
            No return value.
        """
        rc = ReflectionCallable(_lambda)
        sig = rc.getSignature()
        self.assertIn("a", sig.parameters)
        self.assertIn("b", sig.parameters)


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


class TestReflectionCallableDependencies(TestCase):
    def testGetDependenciesReturnsSignature(self) -> None:
        """
        Assert that getDependencies returns a Signature instance.

        Returns
        -------
        None
            No return value.
        """
        rc = ReflectionCallable(_simple_function)
        result = rc.getDependencies()
        self.assertIsInstance(result, Signature)

    def testGetDependenciesIsCached(self) -> None:
        """
        Assert that repeated calls return the identical Signature object.

        Returns
        -------
        None
            No return value.
        """
        rc = ReflectionCallable(_simple_function)
        first = rc.getDependencies()
        second = rc.getDependencies()
        self.assertIs(first, second)

    def testGetDependenciesNoArgsFunction(self) -> None:
        """
        Assert that a function with no parameters reports no required args.

        Returns
        -------
        None
            No return value.
        """

        def _bare() -> None:
            """Run the bare helper.

            Returns
            -------
            None
                No return value.
            """

        rc = ReflectionCallable(_bare)
        deps = rc.getDependencies()
        self.assertTrue(deps.noArgumentsRequired())


# ---------------------------------------------------------------------------
# clearCache
# ---------------------------------------------------------------------------


class TestReflectionCallableClearCache(TestCase):
    def setUp(self) -> None:
        """Initialise a shared ReflectionCallable for clearCache tests.

        Returns
        -------
        None
            No return value.
        """
        self.rc = ReflectionCallable(_simple_function)

    def testClearCacheReturnsNone(self) -> None:
        """
        Assert that clearCache explicitly returns None.

        Returns
        -------
        None
            No return value.
        """
        self.assertIsNone(self.rc.clearCache())

    def testClearCacheEvictsStoredEntries(self) -> None:
        """
        Assert that manually stored cache entries are gone after clearCache.

        Returns
        -------
        None
            No return value.
        """
        self.rc["my_key"] = "value"
        self.rc.clearCache()
        self.assertNotIn("my_key", self.rc)

    def testClearCacheEvictsComputedEntries(self) -> None:
        """
        Assert that entries populated by getSourceCode are removed after clearCache.

        Returns
        -------
        None
            No return value.
        """
        _ = self.rc.getSourceCode()
        self.rc.clearCache()
        self.assertNotIn("source_code", self.rc)

    def testClearCacheAllowsRecomputation(self) -> None:
        """
        Assert that getSignature still works correctly after clearCache.

        Returns
        -------
        None
            No return value.
        """
        _ = self.rc.getSignature()
        self.rc.clearCache()
        sig = self.rc.getSignature()
        self.assertIsInstance(sig, inspect.Signature)


# ---------------------------------------------------------------------------
# Bound method specific behaviour
# ---------------------------------------------------------------------------


class TestReflectionCallableBoundMethod(TestCase):
    def setUp(self) -> None:
        """Initialise a bound method ReflectionCallable.

        Returns
        -------
        None
            No return value.
        """
        self.obj = _SampleClass()
        self.rc = ReflectionCallable(self.obj.regularMethod)

    def testGetNameReturnsBoundMethodName(self) -> None:
        """
        Assert that getName returns 'regularMethod' for a bound method.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(self.rc.getName(), "regularMethod")

    def testGetSignatureExcludesSelf(self) -> None:
        """
        Assert that the signature of a bound method omits 'self'.

        Returns
        -------
        None
            No return value.
        """
        params = self.rc.getSignature().parameters
        self.assertNotIn("self", params)
        self.assertIn("value", params)

    def testGetSourceCodeContainsMethodName(self) -> None:
        """
        Assert that getSourceCode contains 'regularMethod'.

        Returns
        -------
        None
            No return value.
        """
        self.assertIn("regularMethod", self.rc.getSourceCode())

import inspect
from abc import ABC
from orionis.introspection.callables.contracts.reflection import (
    IReflectionCallable,
)
from orionis.test import TestCase

# ---------------------------------------------------------------------------
# Minimal concrete implementation used only in contract tests
# ---------------------------------------------------------------------------

class _StubCallable(IReflectionCallable):
    """Minimal concrete stub that satisfies all abstract methods."""

    def getCallable(self) -> callable:
        """Implement the ``getCallable`` contract stub.

        Returns
        -------
        callable
            Value produced by the helper.
        """
        return lambda: None

    def getName(self) -> str:
        """Implement the ``getName`` contract stub.

        Returns
        -------
        str
            Value produced by the helper.
        """
        return "stub"

    def getModuleName(self) -> str:
        """Implement the ``getModuleName`` contract stub.

        Returns
        -------
        str
            Value produced by the helper.
        """
        return "stub_module"

    def getModuleWithCallableName(self) -> str:
        """Implement the ``getModuleWithCallableName`` contract stub.

        Returns
        -------
        str
            Value produced by the helper.
        """
        return "stub_module.stub"

    def getDocstring(self) -> str:
        """Implement the ``getDocstring`` contract stub.

        Returns
        -------
        str
            Value produced by the helper.
        """
        return "stub docstring"

    def getSourceCode(self) -> str:
        """Implement the ``getSourceCode`` contract stub.

        Returns
        -------
        str
            Value produced by the helper.
        """
        return "def stub(): pass"

    def getFile(self) -> str:
        """Implement the ``getFile`` contract stub.

        Returns
        -------
        str
            Value produced by the helper.
        """
        return "/stub/file.py"

    def getSignature(self) -> inspect.Signature:
        """Implement the ``getSignature`` contract stub.

        Returns
        -------
        inspect.Signature
            Value produced by the helper.
        """
        return inspect.signature(lambda: None)

    def getDependencies(self):
        """Implement the ``getDependencies`` contract stub.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return

    def clearCache(self) -> None:
        """Implement the ``clearCache`` contract stub.

        Returns
        -------
        None
            Completes the operation described above.
        """

# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------

class TestIReflectionCallableIsABC(TestCase):

    def testIsAbstractBaseClass(self) -> None:
        """
        Assert that IReflectionCallable inherits from ABC.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertTrue(issubclass(IReflectionCallable, ABC))

    def testCannotInstantiateDirectly(self) -> None:
        """
        Assert that instantiating IReflectionCallable directly raises TypeError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(TypeError):
            IReflectionCallable()  # type: ignore[abstract]

    def testConcreteSubclassInstantiates(self) -> None:
        """
        Assert that a concrete subclass implementing all methods can be created.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        stub = _StubCallable()
        self.assertIsInstance(stub, IReflectionCallable)

class TestIReflectionCallableAbstractMethods(TestCase):

    def testGetCallableIsAbstract(self) -> None:
        """
        Assert that getCallable is registered as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("getCallable", IReflectionCallable.__abstractmethods__)

    def testGetNameIsAbstract(self) -> None:
        """
        Assert that getName is registered as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("getName", IReflectionCallable.__abstractmethods__)

    def testGetModuleNameIsAbstract(self) -> None:
        """
        Assert that getModuleName is registered as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("getModuleName", IReflectionCallable.__abstractmethods__)

    def testGetModuleWithCallableNameIsAbstract(self) -> None:
        """
        Assert that getModuleWithCallableName is registered as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn(
            "getModuleWithCallableName",
            IReflectionCallable.__abstractmethods__,
        )

    def testGetDocstringIsAbstract(self) -> None:
        """
        Assert that getDocstring is registered as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("getDocstring", IReflectionCallable.__abstractmethods__)

    def testGetSourceCodeIsAbstract(self) -> None:
        """
        Assert that getSourceCode is registered as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("getSourceCode", IReflectionCallable.__abstractmethods__)

    def testGetFileIsAbstract(self) -> None:
        """
        Assert that getFile is registered as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("getFile", IReflectionCallable.__abstractmethods__)

    def testGetSignatureIsAbstract(self) -> None:
        """
        Assert that getSignature is registered as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("getSignature", IReflectionCallable.__abstractmethods__)

    def testGetDependenciesIsAbstract(self) -> None:
        """
        Assert that getDependencies is registered as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("getDependencies", IReflectionCallable.__abstractmethods__)

    def testClearCacheIsAbstract(self) -> None:
        """
        Assert that clearCache is registered as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("clearCache", IReflectionCallable.__abstractmethods__)

class TestIReflectionCallablePartialImplementation(TestCase):

    def testMissingOneMethodRaisesTypeError(self) -> None:
        """
        Assert that a subclass missing clearCache cannot be instantiated.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """

        class _Partial(IReflectionCallable):
            def getCallable(self):
                """Implement the ``getCallable`` contract stub.

                Returns
                -------
                object
                    Value produced by the helper.
                """
                return

            def getName(self):
                """Implement the ``getName`` contract stub.

                Returns
                -------
                object
                    Value produced by the helper.
                """
                return ""

            def getModuleName(self):
                """Implement the ``getModuleName`` contract stub.

                Returns
                -------
                object
                    Value produced by the helper.
                """
                return ""

            def getModuleWithCallableName(self):
                """Implement the ``getModuleWithCallableName`` contract stub.

                Returns
                -------
                object
                    Value produced by the helper.
                """
                return ""

            def getDocstring(self):
                """Implement the ``getDocstring`` contract stub.

                Returns
                -------
                object
                    Value produced by the helper.
                """
                return ""

            def getSourceCode(self):
                """Implement the ``getSourceCode`` contract stub.

                Returns
                -------
                object
                    Value produced by the helper.
                """
                return ""

            def getFile(self):
                """Implement the ``getFile`` contract stub.

                Returns
                -------
                object
                    Value produced by the helper.
                """
                return ""

            def getSignature(self):
                """Implement the ``getSignature`` contract stub.

                Returns
                -------
                object
                    Value produced by the helper.
                """
                return

            def getDependencies(self):
                """Implement the ``getDependencies`` contract stub.

                Returns
                -------
                object
                    Value produced by the helper.
                """
                return

            # clearCache intentionally omitted

        with self.assertRaises(TypeError):
            _Partial()

class TestIReflectionCallableStubContract(TestCase):

    def setUp(self) -> None:
        """Initialise a shared stub instance for contract return-type tests.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.stub = _StubCallable()

    def testGetCallableReturnsCallable(self) -> None:
        """
        Assert that getCallable returns a callable object.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertTrue(callable(self.stub.getCallable()))

    def testGetNameReturnsStr(self) -> None:
        """
        Assert that getName returns a str.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.getName(), str)

    def testGetModuleNameReturnsStr(self) -> None:
        """
        Assert that getModuleName returns a str.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.getModuleName(), str)

    def testGetModuleWithCallableNameReturnsStr(self) -> None:
        """
        Assert that getModuleWithCallableName returns a str.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.getModuleWithCallableName(), str)

    def testGetDocstringReturnsStr(self) -> None:
        """
        Assert that getDocstring returns a str.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.getDocstring(), str)

    def testGetSourceCodeReturnsStr(self) -> None:
        """
        Assert that getSourceCode returns a str.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.getSourceCode(), str)

    def testGetFileReturnsStr(self) -> None:
        """
        Assert that getFile returns a str.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.getFile(), str)

    def testGetSignatureReturnsInspectSignature(self) -> None:
        """
        Assert that getSignature returns an inspect.Signature.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.getSignature(), inspect.Signature)

    def testClearCacheReturnsNone(self) -> None:
        """
        Assert that clearCache returns None.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsNone(self.stub.clearCache())

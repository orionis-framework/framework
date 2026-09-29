from abc import ABC
from orionis.test import TestCase
from orionis.introspection.dependencies.contracts.reflection import (
    IReflectDependencies,
)
from orionis.introspection.dependencies.entities.signature import (
    Signature,
)

class _StubDeps(IReflectDependencies):

    def _emptySig(self) -> Signature:
        """
        Build and return an empty Signature instance.

        Returns
        -------
        Signature
            A Signature with no resolved, unresolved, or ordered entries.
        """
        return Signature(resolved={}, unresolved={}, ordered={})

    def constructorSignature(self) -> Signature:
        """
        Return an empty Signature for the constructor.

        Returns
        -------
        Signature
            Always an empty Signature instance.
        """
        return self._emptySig()

    def methodSignature(self, _method_name: str) -> Signature:
        """
        Return an empty Signature for any named method.

        Parameters
        ----------
        method_name : str
            Name of the method whose signature is requested.

        Returns
        -------
        Signature
            Always an empty Signature instance.
        """
        return self._emptySig()

    def callableSignature(self) -> Signature:
        """
        Return an empty Signature for a callable target.

        Returns
        -------
        Signature
            Always an empty Signature instance.
        """
        return self._emptySig()

class _OnlyConstructor(IReflectDependencies):

    def constructorSignature(self) -> Signature:
        """
        Return an empty Signature for the constructor.

        Returns
        -------
        Signature
            Always an empty Signature instance.
        """
        return Signature(resolved={}, unresolved={}, ordered={})

class TestIReflectDependenciesIsABC(TestCase):

    def testIsABC(self) -> None:
        """
        Assert that IReflectDependencies is a subclass of ABC.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertTrue(issubclass(IReflectDependencies, ABC))

    def testDirectInstantiationRaisesTypeError(self) -> None:
        """
        Assert that direct instantiation raises TypeError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(TypeError):
            IReflectDependencies()

    def testStubCanBeInstantiated(self) -> None:
        """
        Assert that a full stub implementation can be instantiated.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        stub = _StubDeps()
        self.assertIsInstance(stub, IReflectDependencies)

class TestIReflectDependenciesAbstractMethods(TestCase):

    def _assertAbstract(self, name: str) -> None:
        """
        Assert that the named method appears in __abstractmethods__.

        Parameters
        ----------
        name : str
            Method name to check.

        Returns
        -------
        None
            Raises AssertionError if the method is not abstract.
        """
        self.assertIn(name, IReflectDependencies.__abstractmethods__)

    def testConstructorSignatureIsAbstract(self) -> None:
        """
        Assert that constructorSignature is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("constructorSignature")

    def testMethodSignatureIsAbstract(self) -> None:
        """
        Assert that methodSignature is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("methodSignature")

    def testCallableSignatureIsAbstract(self) -> None:
        """
        Assert that callableSignature is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("callableSignature")

class TestIReflectDependenciesPartialImplementation(TestCase):

    def testPartialStubRaisesTypeError(self) -> None:
        """
        Assert that a class implementing only one method raises TypeError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(TypeError):
            _OnlyConstructor()


class TestIReflectDependenciesStubReturnTypes(TestCase):

    def setUp(self) -> None:
        """
        Instantiate the stub before each test.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.stub = _StubDeps()

    def testConstructorSignatureReturnsSignature(self) -> None:
        """
        Assert that constructorSignature returns a Signature instance.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.constructorSignature(), Signature)

    def testMethodSignatureReturnsSignature(self) -> None:
        """
        Assert that methodSignature returns a Signature instance.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.methodSignature("any"), Signature)

    def testCallableSignatureReturnsSignature(self) -> None:
        """
        Assert that callableSignature returns a Signature instance.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.callableSignature(), Signature)

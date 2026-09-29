import inspect
from orionis.support.inspirational.contracts.inspire import IInspire
from orionis.test import TestCase

class _ConcreteInspire(IInspire):
    """Minimal concrete implementation of IInspire for contract testing."""

    def random(self) -> dict:
        """Return the fixed quote used by the contract test.

        Returns
        -------
        dict
            Value produced by the helper.
        """
        return {"quote": "Stub quote.", "author": "Stub Author"}

class _NonImplementingSubclass(IInspire):
    """Subclass that intentionally does NOT implement random()."""

# ===========================================================================
# TestIInspireContract
# ===========================================================================

class TestIInspireContract(TestCase):

    def testIInspireIsAbstractClass(self) -> None:
        """
        Test that IInspire cannot be instantiated directly (it is abstract).

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(TypeError):
            IInspire()  # type: ignore[abstract]

    def testIInspireHasRandomAbstractMethod(self) -> None:
        """
        Test that 'random' is declared as an abstract method on IInspire.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertIn("random", IInspire.__abstractmethods__)

    def testNonImplementingSubclassCannotBeInstantiated(self) -> None:
        """
        Test that a subclass that does not implement random() raises TypeError.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(TypeError):
            _NonImplementingSubclass()  # type: ignore[abstract]

    def testConcreteSubclassCanBeInstantiated(self) -> None:
        """
        Test that a fully implemented subclass can be instantiated.

        Returns
        -------
        None
            This method does not return a value.
        """
        instance = _ConcreteInspire()
        self.assertIsInstance(instance, IInspire)

    def testConcreteSubclassRandomReturnsDict(self) -> None:
        """
        Test that the concrete implementation of random() returns a dict.

        Returns
        -------
        None
            This method does not return a value.
        """
        instance = _ConcreteInspire()
        result = instance.random()
        self.assertIsInstance(result, dict)

    def testRandomMethodSignatureAcceptsNoExtraArgs(self) -> None:
        """
        Test that IInspire.random is declared with only 'self' as parameter.

        Returns
        -------
        None
            This method does not return a value.
        """
        sig = inspect.signature(IInspire.random)
        params = list(sig.parameters.keys())
        self.assertEqual(params, ["self"])

    def testIInspireIsSubclassOfABC(self) -> None:
        """
        Test that IInspire inherits from ABC (is a proper abstract base class).

        Returns
        -------
        None
            This method does not return a value.
        """
        from abc import ABC
        self.assertTrue(issubclass(IInspire, ABC))

    def testAbstractMethodsSetContainsOnlyRandom(self) -> None:
        """
        Test that __abstractmethods__ on IInspire contains exactly 'random'.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertEqual(IInspire.__abstractmethods__, frozenset({"random"}))

    def testConcreteSubclassIsInstanceOfIInspire(self) -> None:
        """
        Test that a concrete subclass object passes isinstance check against IInspire.

        Returns
        -------
        None
            This method does not return a value.
        """
        instance = _ConcreteInspire()
        self.assertIsInstance(instance, IInspire)

    def testRandomIsMarkedAbstractViaDecorator(self) -> None:
        """
        Test that the 'random' method on IInspire has __isabstractmethod__ == True.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertTrue(getattr(IInspire.random, "__isabstractmethod__", False))

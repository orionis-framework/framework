import inspect
from abc import ABC
from orionis.encrypter.contracts.encrypter import IEncrypter
from orionis.encrypter.encrypter import Encrypter
from orionis.test import TestCase

# Methods every implementation must provide.
_ABSTRACT_METHODS: frozenset[str] = frozenset({"decrypt", "encrypt"})

class _ConcreteEncrypter(IEncrypter):
    """Minimal implementation used to exercise the contract structurally."""

    __slots__ = ()

    def encrypt(self, _plaintext: str) -> str:
        """
        Return a fixed placeholder instead of a ciphertext.

        Parameters
        ----------
        _plaintext : str
            Ignored by this structural double.

        Returns
        -------
        str
            An empty string.
        """
        return ""

    def decrypt(self, _payload: str) -> str:
        """
        Return a fixed placeholder instead of a plaintext.

        Parameters
        ----------
        _payload : str
            Ignored by this structural double.

        Returns
        -------
        str
            An empty string.
        """
        return ""

class TestIEncrypterDefinition(TestCase):

    def testIsAnAbstractBaseClass(self) -> None:
        """Derive from the abstract base class machinery.

        Validates that the contract cannot be used as a plain mixin.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(IEncrypter, ABC))

    def testCannotBeInstantiatedDirectly(self) -> None:
        """Refuse instantiation while abstract methods remain unimplemented.

        Validates the contract is enforced at construction time.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            IEncrypter()  # type: ignore[abstract]

    def testDeclaresEmptySlots(self) -> None:
        """Declare empty slots so implementations can stay dictionary free.

        Validates the requirement that makes the slots of Encrypter
        effective instead of decorative.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(IEncrypter.__dict__.get("__slots__"), ())

    def testExposesExactlyTheExpectedAbstractMethods(self) -> None:
        """Publish encrypt and decrypt as the only abstract members.

        Validates the surface every implementation has to cover.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(IEncrypter.__abstractmethods__, _ABSTRACT_METHODS)

    def testAbstractMethodsCarryNoImplementation(self) -> None:
        """Keep the abstract methods free of executable bodies.

        Validates that no dead code hides behind the contract.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for name in _ABSTRACT_METHODS:
            source = inspect.getsource(getattr(IEncrypter, name))
            self.assertNotIn("return", source)

class TestIEncrypterImplementations(TestCase):

    def testEncrypterMatchesTheContractSignatures(self) -> None:
        """Keep the parameters of the service aligned with the contract.

        Validates that callers relying on the contract can invoke the
        concrete implementation unchanged.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for name in _ABSTRACT_METHODS:
            expected = inspect.signature(getattr(IEncrypter, name))
            actual = inspect.signature(getattr(Encrypter, name))
            self.assertEqual(
                list(expected.parameters),
                list(actual.parameters),
            )

    def testConcreteSubclassSatisfiesTheContract(self) -> None:
        """Instantiate a subclass that implements every abstract method.

        Validates that the contract is satisfiable with the declared
        signatures alone.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        instance = _ConcreteEncrypter()
        self.assertIsInstance(instance, IEncrypter)
        self.assertEqual(instance.encrypt("value"), "")
        self.assertEqual(instance.decrypt("value"), "")

    def testConcreteSubclassInheritsTheSlotsGuarantee(self) -> None:
        """Keep implementations free of an attribute dictionary.

        Validates that the empty slots of the contract propagate to
        subclasses declaring their own slots.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(hasattr(_ConcreteEncrypter(), "__dict__"))

import ast
import inspect
import textwrap
from abc import ABC
from orionis.hashing.contracts.hasher import IHasher
from orionis.hashing.hashers.argon2_hasher import Argon2Hasher
from orionis.hashing.hashers.bcrypt_hasher import BcryptHasher
from orionis.test import TestCase

# Methods every hashing driver must provide.
_ABSTRACT_METHODS: frozenset[str] = frozenset(
    {"check", "getAlgorithm", "make", "needsRehash", "setRounds"},
)

# Concrete drivers shipped by the framework.
_DRIVERS: tuple[type[IHasher], ...] = (Argon2Hasher, BcryptHasher)


def abstract_body_statements(method: object) -> list[ast.stmt]:
    """
    Return the statements declared inside the body of a method.

    Parameters
    ----------
    method : object
        Function object whose source is parsed.

    Returns
    -------
    list[ast.stmt]
        Statements found in the body, empty when the source does not
        define a plain function.
    """
    node = ast.parse(textwrap.dedent(inspect.getsource(method))).body[0]
    return node.body if isinstance(node, ast.FunctionDef) else []


class TestIHasherDefinition(TestCase):

    def testIsAnAbstractBaseClass(self) -> None:
        """
        Derive from the abstract base class machinery.

        Validates that the contract cannot be used as a plain mixin.
        """
        self.assertTrue(issubclass(IHasher, ABC))

    def testCannotBeInstantiatedDirectly(self) -> None:
        """
        Refuse instantiation while abstract methods remain unimplemented.

        Validates that the contract is enforced at construction time.
        """
        with self.assertRaises(TypeError):
            IHasher()  # type: ignore[abstract]

    def testDeclaresEmptySlots(self) -> None:
        """
        Declare empty slots so implementations stay dictionary free.

        Validates the requirement that makes the slots of every driver
        effective instead of decorative.
        """
        self.assertEqual(IHasher.__dict__.get("__slots__"), ())

    def testExposesExactlyTheExpectedAbstractMethods(self) -> None:
        """
        Publish the hashing operations as the only abstract members.

        Validates the surface every driver has to cover.
        """
        self.assertEqual(IHasher.__abstractmethods__, _ABSTRACT_METHODS)

    def testAbstractMethodsCarryNoImplementation(self) -> None:
        """
        Keep the abstract methods free of executable bodies.

        Validates that no dead code hides behind the contract.
        """
        for name in _ABSTRACT_METHODS:
            statements = abstract_body_statements(getattr(IHasher, name))
            self.assertEqual(len(statements), 1, msg=name)
            self.assertIsInstance(statements[0], ast.Expr, msg=name)


class TestIHasherImplementations(TestCase):

    def testEveryDriverImplementsTheContract(self) -> None:
        """
        Register both shipped drivers as implementations.

        Validates that the manager can treat them interchangeably.
        """
        for driver in _DRIVERS:
            self.assertTrue(issubclass(driver, IHasher))

    def testEveryDriverMatchesTheContractSignatures(self) -> None:
        """
        Keep the parameters of the drivers aligned with the contract.

        Validates that callers relying on the contract can invoke any
        driver unchanged.
        """
        for driver in _DRIVERS:
            for name in _ABSTRACT_METHODS:
                expected = inspect.signature(getattr(IHasher, name))
                actual = inspect.signature(getattr(driver, name))
                self.assertEqual(
                    list(expected.parameters),
                    list(actual.parameters),
                    msg=f"{driver.__name__}.{name}",
                )

    def testEveryDriverLeavesTheAbstractSetEmpty(self) -> None:
        """
        Implement every abstract member in the shipped drivers.

        Validates that no driver is instantiable only by accident.
        """
        for driver in _DRIVERS:
            self.assertEqual(driver.__abstractmethods__, frozenset())

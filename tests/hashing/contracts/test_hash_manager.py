import ast
import inspect
import textwrap
from orionis.hashing.contracts.hash_manager import IHashManager
from orionis.hashing.contracts.hasher import IHasher
from orionis.hashing.hash_manager import HashManager
from orionis.test import TestCase

# Members the manager adds on top of the plain hashing contract.
_MANAGER_METHODS: frozenset[str] = frozenset({"driver", "getDefaultDriver"})


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


class TestIHashManagerDefinition(TestCase):

    def testExtendsTheHasherContract(self) -> None:
        """
        Extend the plain hashing contract instead of duplicating it.

        Validates that the manager can stand in for a single driver.
        """
        self.assertTrue(issubclass(IHashManager, IHasher))

    def testCannotBeInstantiatedDirectly(self) -> None:
        """
        Refuse instantiation while abstract methods remain unimplemented.

        Validates that the contract is enforced at construction time.
        """
        with self.assertRaises(TypeError):
            IHashManager()  # type: ignore[abstract]

    def testDeclaresEmptySlots(self) -> None:
        """
        Declare empty slots so implementations stay dictionary free.

        Validates the requirement that makes the slots of HashManager
        effective instead of decorative.
        """
        self.assertEqual(IHashManager.__dict__.get("__slots__"), ())

    def testAddsOnlyTheDriverResolutionMembers(self) -> None:
        """
        Publish driver resolution as the only additional surface.

        Validates that the manager contract inherits every hashing
        operation and adds nothing else.
        """
        self.assertEqual(
            IHashManager.__abstractmethods__,
            IHasher.__abstractmethods__ | _MANAGER_METHODS,
        )

    def testAbstractMethodsCarryNoImplementation(self) -> None:
        """
        Keep the added abstract methods free of executable bodies.

        Validates that no dead code hides behind the contract.
        """
        for name in _MANAGER_METHODS:
            statements = abstract_body_statements(getattr(IHashManager, name))
            self.assertEqual(len(statements), 1, msg=name)
            self.assertIsInstance(statements[0], ast.Expr, msg=name)


class TestIHashManagerImplementation(TestCase):

    def testManagerImplementsTheContract(self) -> None:
        """
        Register HashManager as the implementation of the contract.

        Validates the binding published by the service provider.
        """
        self.assertTrue(issubclass(HashManager, IHashManager))

    def testManagerLeavesTheAbstractSetEmpty(self) -> None:
        """
        Implement every abstract member in the manager.

        Validates that the manager is instantiable by design and not by
        accident.
        """
        self.assertEqual(HashManager.__abstractmethods__, frozenset())

    def testManagerMatchesTheContractSignatures(self) -> None:
        """
        Keep the parameters of the manager aligned with the contract.

        Validates that callers relying on the contract can invoke the
        manager unchanged.
        """
        for name in IHashManager.__abstractmethods__:
            expected = inspect.signature(getattr(IHashManager, name))
            actual = inspect.signature(getattr(HashManager, name))
            self.assertEqual(
                list(expected.parameters),
                list(actual.parameters),
                msg=name,
            )

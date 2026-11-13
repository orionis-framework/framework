# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
import inspect
from orionis.hashing.contracts.hash_manager import IHashManager
from orionis.hashing.contracts.hasher import IHasher
from orionis.hashing.hash_manager import HashManager
from orionis.test import TestCase

# Members the manager adds on top of the plain hashing contract.
_MANAGER_METHODS: frozenset[str] = frozenset({"driver", "getDefaultDriver"})


class TestIHashManagerDefinition(TestCase):
    def testExtendsTheHasherContract(self) -> None:
        """Extend the plain hashing contract instead of duplicating it.

        Validates that the manager can stand in for a single driver.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(issubclass(IHashManager, IHasher))

    def testCannotBeInstantiatedDirectly(self) -> None:
        """Refuse instantiation while abstract methods remain unimplemented.

        Validates that the contract is enforced at construction time.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(TypeError):
            IHashManager()  # type: ignore[abstract]

    def testDeclaresEmptySlots(self) -> None:
        """Declare empty slots so implementations stay dictionary free.

        Validates the requirement that makes the slots of HashManager
        effective instead of decorative.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(IHashManager.__dict__.get("__slots__"), ())

    def testAddsOnlyTheDriverResolutionMembers(self) -> None:
        """Publish driver resolution as the only additional surface.

        Validates that the manager contract inherits every hashing
        operation and adds nothing else.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(
            IHashManager.__abstractmethods__,
            IHasher.__abstractmethods__ | _MANAGER_METHODS,
        )

    def testPartialImplementationsRemainAbstract(self) -> None:
        """Require both driver-resolution members before allowing instantiation.

        Returns
        -------
        None
            No return value.
        """
        for missing in _MANAGER_METHODS:
            with self.subTest(missing=missing):
                methods = {
                    name: getattr(HashManager, name)
                    for name in IHashManager.__abstractmethods__
                    if name != missing
                }
                incomplete = type("IncompleteHashManager", (IHashManager,), methods)
                with self.assertRaises(TypeError):
                    incomplete()


class TestIHashManagerImplementation(TestCase):
    def testManagerImplementsTheContract(self) -> None:
        """Register HashManager as the implementation of the contract.

        Validates the binding published by the service provider.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(issubclass(HashManager, IHashManager))

    def testManagerLeavesTheAbstractSetEmpty(self) -> None:
        """Implement every abstract member in the manager.

        Validates that the manager is instantiable by design and not by
        accident.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(HashManager.__abstractmethods__, frozenset())

    def testManagerMatchesTheContractSignatures(self) -> None:
        """Keep the parameters of the manager aligned with the contract.

        Validates that callers relying on the contract can invoke the
        manager unchanged.

        Returns
        -------
        None
            No return value.
        """
        for name in IHashManager.__abstractmethods__:
            expected = inspect.signature(getattr(IHashManager, name), eval_str=True)
            actual = inspect.signature(getattr(HashManager, name), eval_str=True)
            self.assertEqual(
                expected.replace(parameters=tuple(expected.parameters.values())[1:]),
                actual.replace(parameters=tuple(actual.parameters.values())[1:]),
                msg=name,
            )

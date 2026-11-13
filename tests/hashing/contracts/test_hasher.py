# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
import inspect
from abc import ABC
from orionis.hashing.contracts.hasher import IHasher
from orionis.hashing.hashers.argon2_hasher import Argon2Hasher
from orionis.hashing.hashers.bcrypt_hasher import BcryptHasher
from orionis.test import TestCase

# Methods every hashing driver must provide.
_ABSTRACT_METHODS: frozenset[str] = frozenset(
    {"check", "getAlgorithm", "make", "needsRehash", "setRounds"},
)

# Operations that burn the configured cost and must never block the loop.
_ASYNC_METHODS: frozenset[str] = frozenset({"check", "make"})

# Concrete drivers shipped by the framework.
_DRIVERS: tuple[type[IHasher], ...] = (Argon2Hasher, BcryptHasher)


class TestIHasherDefinition(TestCase):
    def testIsAnAbstractBaseClass(self) -> None:
        """Derive from the abstract base class machinery.

        Validates that the contract cannot be used as a plain mixin.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(issubclass(IHasher, ABC))

    def testCannotBeInstantiatedDirectly(self) -> None:
        """Refuse instantiation while abstract methods remain unimplemented.

        Validates that the contract is enforced at construction time.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(TypeError):
            IHasher()  # type: ignore[abstract]

    def testDeclaresEmptySlots(self) -> None:
        """Declare empty slots so implementations stay dictionary free.

        Validates the requirement that makes the slots of every driver
        effective instead of decorative.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(IHasher.__dict__.get("__slots__"), ())

    def testExposesExactlyTheExpectedAbstractMethods(self) -> None:
        """Publish the hashing operations as the only abstract members.

        Validates the surface every driver has to cover.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(IHasher.__abstractmethods__, _ABSTRACT_METHODS)

    def testPartialImplementationsRemainAbstract(self) -> None:
        """Require every hashing operation before allowing instantiation.

        Returns
        -------
        None
            No return value.
        """
        for missing in _ABSTRACT_METHODS:
            with self.subTest(missing=missing):
                methods = {
                    name: getattr(Argon2Hasher, name)
                    for name in _ABSTRACT_METHODS
                    if name != missing
                }
                incomplete = type("IncompleteHasher", (IHasher,), methods)
                with self.assertRaises(TypeError):
                    incomplete()

    def testDeclaresTheCostlyOperationsAsCoroutines(self) -> None:
        """Declare hashing and verification as coroutine functions.

        Validates the contract that lets every driver move its cost to a
        worker thread instead of stalling the event loop.

        Returns
        -------
        None
            No return value.
        """
        for name in _ASYNC_METHODS:
            self.assertTrue(
                inspect.iscoroutinefunction(getattr(IHasher, name)),
                msg=name,
            )


class TestIHasherImplementations(TestCase):
    def testEveryDriverImplementsTheContract(self) -> None:
        """Register both shipped drivers as implementations.

        Validates that the manager can treat them interchangeably.

        Returns
        -------
        None
            No return value.
        """
        for driver in _DRIVERS:
            self.assertTrue(issubclass(driver, IHasher))

    def testEveryDriverMatchesTheContractSignatures(self) -> None:
        """Keep the parameters of the drivers aligned with the contract.

        Validates that callers relying on the contract can invoke any
        driver unchanged.

        Returns
        -------
        None
            No return value.
        """
        for driver in _DRIVERS:
            for name in _ABSTRACT_METHODS:
                expected = inspect.signature(getattr(IHasher, name), eval_str=True)
                actual = inspect.signature(getattr(driver, name), eval_str=True)
                self.assertEqual(
                    expected.replace(
                        parameters=tuple(expected.parameters.values())[1:],
                    ),
                    actual.replace(parameters=tuple(actual.parameters.values())[1:]),
                    msg=f"{driver.__name__}.{name}",
                )

    def testEveryDriverLeavesTheAbstractSetEmpty(self) -> None:
        """Implement every abstract member in the shipped drivers.

        Validates that no driver is instantiable only by accident.

        Returns
        -------
        None
            No return value.
        """
        for driver in _DRIVERS:
            self.assertEqual(driver.__abstractmethods__, frozenset())

    def testEveryDriverKeepsTheCostlyOperationsAsynchronous(self) -> None:
        """Implement hashing and verification as coroutine functions.

        Validates that a driver never silently turns an awaited call into
        a blocking one.

        Returns
        -------
        None
            No return value.
        """
        for driver in _DRIVERS:
            for name in _ASYNC_METHODS:
                self.assertTrue(
                    inspect.iscoroutinefunction(getattr(driver, name)),
                    msg=f"{driver.__name__}.{name}",
                )

from __future__ import annotations
from abc import ABC
from orionis.session.contracts.store import ISessionStore
from orionis.session.stores.cache import CacheSessionStore
from orionis.session.stores.database import DatabaseSessionStore
from orionis.session.stores.file import FileSessionStore
from orionis.session.stores.memory import MemorySessionStore
from orionis.test import TestCase

class _PartialStore(ISessionStore):
    """Deliberately incomplete store used to prove the contract is enforced."""

    __slots__ = ()

    async def read(self, session_id: str) -> None:
        """Return nothing for *session_id*."""

    async def write(self, record: object) -> None:
        """Discard *record*."""

class TestISessionStoreContract(TestCase):
    """Unit tests for the ISessionStore abstract contract."""

    def testContractIsAbstract(self) -> None:
        """
        Declare ISessionStore as an abstract base class.

        Validates that the contract participates in the ABC machinery
        instead of being a plain class.
        """
        self.assertIn(
            ABC.__name__,
            [base.__name__ for base in ISessionStore.__mro__],
        )

    def testContractCannotBeInstantiated(self) -> None:
        """
        Reject direct instantiation of the contract.

        Validates that every backing store must provide a concrete
        implementation.
        """
        with self.assertRaises(TypeError):
            ISessionStore()  # type: ignore[abstract]

    def testContractDeclaresEmptySlots(self) -> None:
        """
        Keep the contract slot-free so stores stay dictless.

        Validates that ``__slots__`` is empty, otherwise every store
        instance would carry a per-instance dictionary.
        """
        self.assertEqual(ISessionStore.__slots__, ())

    def testContractDeclaresExpectedMembers(self) -> None:
        """
        Expose exactly the four persistence operations.

        Validates that the store surface stays limited to read, write,
        delete and garbage collection.
        """
        self.assertEqual(
            set(ISessionStore.__abstractmethods__),
            {"read", "write", "delete", "gc"},
        )

    def testPartialImplementationCannotBeInstantiated(self) -> None:
        """
        Reject a store that skips part of the contract.

        Validates that omitting ``delete`` and ``gc`` keeps the subclass
        abstract.
        """
        with self.assertRaises(TypeError):
            _PartialStore()  # type: ignore[abstract]

    def testEveryBuiltInStoreImplementsTheContract(self) -> None:
        """
        Register all shipped stores as concrete implementations.

        Validates that the manager can wire any configured driver.
        """
        for store in (
            CacheSessionStore,
            DatabaseSessionStore,
            FileSessionStore,
            MemorySessionStore,
        ):
            self.assertTrue(issubclass(store, ISessionStore))
            self.assertEqual(store.__abstractmethods__, frozenset())

    def testMemoryStoreInstancesHaveNoInstanceDictionary(self) -> None:
        """
        Build stores without a per-instance dictionary.

        Validates that the empty contract slots keep concrete stores
        allocation-friendly.
        """
        self.assertFalse(hasattr(MemorySessionStore(), "__dict__"))

# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify session storage contracts and isolated persistence behavior."""

from __future__ import annotations
from abc import ABC
import inspect
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
        """Return nothing for *session_id*.

        Parameters
        ----------
        session_id : str
            Value supplied for ``session_id``.

        Returns
        -------
        None
            No return value.
        """

    async def write(self, record: object) -> None:
        """Discard *record*.

        Parameters
        ----------
        record : object
            Value supplied for ``record``.

        Returns
        -------
        None
            No return value.
        """


class TestISessionStoreContract(TestCase):
    """Unit tests for the ISessionStore abstract contract."""

    def testContractRequiresEveryPersistenceOperation(self) -> None:
        """Reject complete omission and partial implementations of the contract.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(issubclass(ISessionStore, ABC))
        self.assertEqual(
            set(ISessionStore.__abstractmethods__),
            {"read", "write", "update", "delete", "gc"},
        )
        for implementation in (ISessionStore, _PartialStore):
            with (
                self.subTest(implementation=implementation.__name__),
                self.assertRaises(TypeError),
            ):
                implementation()

    def testContractDeclaresEmptySlots(self) -> None:
        """Keep the contract slot-free so stores stay dictless.

        Validates that ``__slots__`` is empty, otherwise every store
        instance would carry a per-instance dictionary.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(ISessionStore.__slots__, ())

    def testEveryBuiltInStoreImplementsTheContract(self) -> None:
        """Register all shipped stores as concrete implementations.

        Validates that the manager can wire any configured driver.

        Returns
        -------
        None
            No return value.
        """
        for store in (
            CacheSessionStore,
            DatabaseSessionStore,
            FileSessionStore,
            MemorySessionStore,
        ):
            self.assertTrue(issubclass(store, ISessionStore))
            self.assertEqual(store.__abstractmethods__, frozenset())
            for name in ISessionStore.__abstractmethods__:
                with self.subTest(store=store.__name__, method=name):
                    self.assertTrue(inspect.iscoroutinefunction(getattr(store, name)))

    def testMemoryStoreInstancesHaveNoInstanceDictionary(self) -> None:
        """Build stores without a per-instance dictionary.

        Validates that the empty contract slots keep concrete stores
        allocation-friendly.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(hasattr(MemorySessionStore(), "__dict__"))

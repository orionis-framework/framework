# ruff: noqa: PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
import asyncio
import tests.orm.factories.test_factory as factory_fixtures
from orionis.orm.factories import Sequence
from orionis.orm.factories.exceptions import (
    FactoryConfigurationException,
    FactoryDefinitionException,
)
from orionis.test import TestCase


async def _async_sequence_entry(index: int) -> dict[str, object]:
    """Produce an invalid asynchronous sequence entry.

    Parameters
    ----------
    index : int
        Index supplied by a sequence callback.

    Returns
    -------
    dict of str to object
        Attributes produced only after an asynchronous suspension.
    """
    await asyncio.sleep(0)
    return {"index": index}


class _AsyncSequenceEntry:
    """Expose an asynchronous callable object for registration validation."""

    __slots__ = ()

    async def __call__(self, index: int) -> dict[str, object]:
        """Produce attributes asynchronously through the callable protocol.

        Parameters
        ----------
        index : int
            Index supplied by a sequence callback.

        Returns
        -------
        dict of str to object
            Asynchronously generated attributes.
        """
        return await _async_sequence_entry(index)


class TestSequenceGeneration(TestCase):
    """Test public generation without requiring database resolution."""

    def testSequenceCyclesAndContinuesAcrossReusedFactory(self) -> None:
        """Advance a factory-local index across batches and strategy calls.

        Returns
        -------
        None
            No return value.
        """
        factory = factory_fixtures.UserFactory().sequence(
            Sequence({"active": True}, {"active": False}),
        )
        self.assertEqual(
            [user.active for user in factory.count(3).make()],
            [True, False, True],
        )
        self.assertFalse(factory.count(1).make().active)

    def testCallableSequenceReceivesMonotonicallyIncreasingIndex(self) -> None:
        """Pass the absolute generation index to callable sequence entries.

        Returns
        -------
        None
            No return value.
        """
        factory = (
            factory_fixtures.UserFactory()
            .sequence(Sequence(factory_fixtures._indexed_email))
            .count(3)
        )
        self.assertEqual(
            [user.email for user in factory.make()],
            [f"user{index}@example.test" for index in range(1, 4)],
        )
        self.assertEqual(factory.count(1).make().email, "user4@example.test")
        factory.sequence(Sequence(factory_fixtures._indexed_email))
        self.assertEqual(factory.make().email, "user1@example.test")

    def testSharedSequenceHasIndependentFactoryCursors(self) -> None:
        """Reuse a sequence value without sharing iteration state.

        Returns
        -------
        None
            No return value.
        """
        sequence = Sequence(factory_fixtures._indexed_email)
        first = factory_fixtures.UserFactory().sequence(sequence)
        second = factory_fixtures.UserFactory().sequence(sequence)
        self.assertEqual(first.make().email, second.make().email)
        first.make()
        self.assertEqual(second.make().email, "user2@example.test")

    def testSequenceSnapshotsNestedMappings(self) -> None:
        """Protect reused sequence items from external and generated mutations.

        Returns
        -------
        None
            No return value.
        """
        item = {"profile": {"tags": ["sequence"]}}
        sequence = Sequence(item)
        item["profile"]["tags"].append("outside")
        factory = factory_fixtures.UserFactory().sequence(sequence)
        factory.make().profile["tags"].append("model")
        self.assertEqual(factory.make().profile, {"tags": ["sequence"]})

    def testResolveRejectsInvalidIndices(self) -> None:
        """Reject negative, boolean, and non-integer sequence positions.

        Returns
        -------
        None
            No return value.
        """
        sequence = Sequence({"active": True})
        for index in (-1, True, False, 1.5, "1", None):
            with self.assertRaises(FactoryConfigurationException):
                sequence.resolve(index)

    def testResolveUsesAbsoluteIndicesAndReturnsDetachedValues(self) -> None:
        """Cycle static entries while passing absolute indices to callbacks.

        Returns
        -------
        None
            No return value.
        """
        sequence = Sequence({"values": []}, lambda index: {"index": index})
        first = sequence.resolve(0)
        first["values"].append("changed")
        self.assertEqual(sequence.resolve(2), {"values": []})
        self.assertEqual(sequence.resolve(3), {"index": 3})

    def testRejectsInvalidEntriesAndAsynchronousCallbacks(self) -> None:
        """Reject empty, malformed, and asynchronous sequence declarations.

        Returns
        -------
        None
            No return value.
        """
        for entries in (
            (),
            (None,),
            ({1: "value"},),
            (_async_sequence_entry,),
            (_AsyncSequenceEntry(),),
        ):
            with self.assertRaises(FactoryConfigurationException):
                Sequence(*entries)

    def testRejectsInvalidCallbackResultsAtResolution(self) -> None:
        """Validate values produced by a synchronous sequence callback.

        Returns
        -------
        None
            No return value.
        """
        sequence = Sequence(lambda _index: {1: "value"})
        with self.assertRaises(FactoryDefinitionException):
            sequence.resolve(0)

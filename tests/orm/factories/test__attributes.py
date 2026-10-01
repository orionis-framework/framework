import asyncio
from inspect import CORO_CLOSED, getcoroutinestate
import tests.orm.factories.test_factory as factory_fixtures
from orionis.orm.factories._attributes import copy_attributes
from orionis.orm.factories.exceptions import FactoryDefinitionException
from orionis.test import TestCase

class TestAttributeCopyProtocols(TestCase):
    """Test public generation without requiring database resolution."""

    def testAttributeCopiesHonorCustomMappingProtocols(self) -> None:
        """Keep dictionary subclasses on their native deep-copy protocol.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        source = factory_fixtures._CopyAwareMapping({"original": True})
        copied = copy_attributes(source, "Definition")
        self.assertIsInstance(copied, factory_fixtures._CopyAwareMapping)
        self.assertEqual(copied, {"copied": True})
        self.assertEqual(source, {"original": True})

    def testAtomicValuesRemainDetachedFromTheirSourceMapping(self) -> None:
        """Copy valid scalar dictionaries without retaining the source mapping.

        Returns
        -------
        None
            Verify scalar values and empty dictionaries are independently copied.
        """
        source = {
            "empty": None,
            "enabled": True,
            "count": 3,
            "ratio": 1.5,
            "value": "text",
            "data": b"data",
            "complex": complex(1, 2),
        }
        copied = copy_attributes(source, "Attributes")
        self.assertEqual(copied, source)
        self.assertIsNot(copied, source)
        copied["count"] = 9
        self.assertEqual(source["count"], 3)
        empty: dict[str, object] = {}
        self.assertIsNot(copy_attributes(empty, "Attributes"), empty)

    def testNestedCopiesPreserveCyclesAndAliasesWithinOneResult(self) -> None:
        """Detach a nested graph while preserving its internal references.

        Returns
        -------
        None
            Verify cycles and shared nested objects never point to caller state.
        """
        shared: list[str] = []
        source: dict[str, object] = {"first": shared, "second": shared}
        source["self"] = source
        copied = copy_attributes(source, "Attributes")
        self.assertIs(copied["self"], copied)
        self.assertIs(copied["first"], copied["second"])
        self.assertIsNot(copied["first"], shared)
        copied["first"].append("changed")
        self.assertEqual(shared, [])

    def testInvalidShapesAndKeysReportTheirSource(self) -> None:
        """Reject non-dictionaries and non-string attribute names.

        Returns
        -------
        None
            Verify both plain and custom dictionary guards preserve context.
        """

        class _Mapping(dict):
            __slots__ = ()

        for invalid in (None, [], (), "values", {1: "value"}, _Mapping({1: "value"})):
            with self.assertRaisesRegex(FactoryDefinitionException, "Attributes"):
                copy_attributes(invalid, "Attributes")

    def testRejectedCoroutineIsClosed(self) -> None:
        """Close an invalid asynchronous result before rejecting its shape.

        Returns
        -------
        None
            Verify rejection does not leave an unawaited coroutine behind.
        """
        pending = asyncio.sleep(0, result={"name": "discarded"})
        with self.assertRaises(FactoryDefinitionException):
            copy_attributes(pending, "Attributes")
        self.assertEqual(getcoroutinestate(pending), CORO_CLOSED)

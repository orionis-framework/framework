from __future__ import annotations
import uuid
from datetime import UTC, date, datetime
from typing import ClassVar
import tests.orm.test_events as feature_fixtures
import tests.orm.test_state as state_fixtures
from orionis.orm import Integer, Model, StrictJson, String, Text
from orionis.orm.attributes import get_cast_handler, serialize_for_storage
from orionis.orm.exceptions import OrmException
from orionis.orm.schema.types import Uuid
from orionis.test import TestCase

class _Doc(Model):
    id = Integer().primary().autoIncrement()
    body = Text().nullable()
    payload = StrictJson().nullable()
    token = Uuid().nullable()
    label = String().nullable()

    casts: ClassVar[dict[str, str]] = {"body": "json"}

class TestCastHandlers(TestCase):
    def testIntAndFloatCasts(self) -> None:
        """Cast textual and numeric inputs to int and float.

        Validates the numeric cast handlers.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(get_cast_handler("int")("42"), 42)
        self.assertEqual(get_cast_handler("float")("2.5"), 2.5)

    def testBoolCastHandlesTextualForms(self) -> None:
        """Interpret common textual forms as booleans.

        Validates the truthy string table and fallbacks.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        handler = get_cast_handler("bool")
        for truthy in ("1", "true", "YES", " on "):
            self.assertTrue(handler(truthy))
        for falsy in ("0", "false", "off", ""):
            self.assertFalse(handler(falsy))
        self.assertTrue(handler(1))
        self.assertFalse(handler(0))

    def testDatetimeCastAcceptsMultipleShapes(self) -> None:
        """Cast datetimes from instances, ISO strings, and timestamps.

        Validates every accepted datetime input shape.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        handler = get_cast_handler("datetime")
        now = datetime.now(UTC)
        self.assertIs(handler(now), now)
        parsed = handler("2026-07-24T10:30:00")
        self.assertEqual(parsed, datetime(2026, 7, 24, 10, 30))
        stamped = handler(0)
        self.assertEqual(stamped, datetime.fromtimestamp(0, tz=UTC))

    def testDateCastAcceptsMultipleShapes(self) -> None:
        """Cast dates from datetimes, dates, and ISO strings.

        Validates every accepted date input shape.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        handler = get_cast_handler("date")
        today = date(2026, 7, 24)
        self.assertEqual(handler("2026-07-24"), today)
        self.assertEqual(handler(today), today)
        moment = datetime(2026, 7, 24, 8, 0)
        self.assertEqual(handler(moment), today)

    def testJsonCastDecodesStringsOnly(self) -> None:
        """Decode JSON strings and pass decoded structures through.

        Validates the JSON cast idempotency.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        handler = get_cast_handler("json")
        self.assertEqual(handler('{"a": 1}'), {"a": 1})
        self.assertEqual(handler(b"[1, 2]"), [1, 2])
        self.assertEqual(handler({"a": 1}), {"a": 1})

    def testUuidCastAcceptsStringAndInstance(self) -> None:
        """Cast UUIDs from strings and pass instances through.

        Validates the UUID cast idempotency.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        handler = get_cast_handler("uuid")
        value = uuid.uuid4()
        self.assertIs(handler(value), value)
        self.assertEqual(handler(str(value)), value)

    def testUnsupportedCastRaises(self) -> None:
        """Raise OrmException for unsupported cast names.

        Validates the cast registry guard.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(OrmException):
            get_cast_handler("decimal128")

    def testGetCastHandlerNormalizesCaseAndWhitespace(self) -> None:
        """Normalize cast names before looking them up in the registry.

        Validates that surrounding whitespace and casing never prevent
        a declared cast from resolving to its handler.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIs(get_cast_handler(" INT "), get_cast_handler("int"))
        self.assertIs(get_cast_handler("Bool"), get_cast_handler("bool"))

class TestSerializeForStorage(TestCase):
    def testJsonStructureOnNonJsonColumnIsDumped(self) -> None:
        """Serialize structures targeting non-JSON columns to strings.

        Validates the storage-side JSON encoding rule.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        meta = _Doc.__meta__
        result = serialize_for_storage(meta, {"body": {"a": 1}})
        self.assertEqual(result["body"], '{"a": 1}')

    def testStructureOnJsonColumnPassesThrough(self) -> None:
        """Keep structures intact when the column is a JSON column.

        Validates the JSON column passthrough.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        meta = _Doc.__meta__
        payload = {"a": 1}
        result = serialize_for_storage(meta, {"payload": payload})
        self.assertIs(result["payload"], payload)

    def testUuidOnNonUuidColumnIsStringified(self) -> None:
        """Serialize UUIDs targeting non-UUID columns to strings.

        Validates the storage-side UUID encoding rule.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        meta = _Doc.__meta__
        value = uuid.uuid4()
        result = serialize_for_storage(meta, {"label": value})
        self.assertEqual(result["label"], str(value))

    def testUuidOnUuidColumnPassesThrough(self) -> None:
        """Keep UUID instances intact for UUID columns.

        Validates the UUID column passthrough.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        meta = _Doc.__meta__
        value = uuid.uuid4()
        result = serialize_for_storage(meta, {"token": value})
        self.assertIs(result["token"], value)

    def testNoneAndUnknownColumnsPassThrough(self) -> None:
        """Keep None values and unknown columns untouched.

        Validates the serialization fallbacks.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        meta = _Doc.__meta__
        result = serialize_for_storage(meta, {"body": None, "ghost": 5})
        self.assertIsNone(result["body"])
        self.assertEqual(result["ghost"], 5)

class TestAttributeHelpers(TestCase):
    def testGetAttributeReturnsDefaultWhenAbsent(self) -> None:
        """Return the provided default for missing attributes.

        Validates the getAttribute fallback.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        doc = _Doc()
        self.assertIsNone(doc.getAttribute("label"))
        self.assertEqual(doc.getAttribute("label", "n/a"), "n/a")

    def testSetAttributeAppliesDeclaredCast(self) -> None:
        """Apply declared casts on direct attribute assignment.

        Validates the assignment-time cast path.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        doc = _Doc()
        doc.body = '{"k": true}'
        self.assertEqual(doc.body, {"k": True})

    def testSerializeMatchesToDict(self) -> None:
        """Keep serialize() aligned with toDict().

        Validates the collection serialization hook.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        doc = _Doc({"label": "x"})
        self.assertEqual(doc.serialize(), doc.toDict())

class TestAccessorsAndMutators(feature_fixtures._ModelFeatureTestCase):
    """Attribute transformation on read and write."""

    async def testAccessorTransformsStoredValue(self) -> None:
        """Serve a stored value through its accessor.

        Validates ``get<Name>Attribute``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        account = await feature_fixtures.Account.query().firstOrFail()
        self.assertEqual(account.role, "ADMIN")
        self.assertEqual(account.getOriginal("role"), "admin")

    async def testMutatorTransformsAssignedValue(self) -> None:
        """Transform a value before it is stored.

        Validates ``set<Name>Attribute``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        account = feature_fixtures.Account({"first_name": "Cid", "last_name": "Kane"})
        account.secret = "plain"  # noqa: S105
        self.assertEqual(account.getOriginal("secret"), None)
        self.assertEqual(account._attributes["secret"], "nialp")

    async def testComputedAttributeNeedsNoColumn(self) -> None:
        """Expose an attribute backed only by an accessor.

        Validates accessor-only attributes.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        account = await feature_fixtures.Account.query().firstOrFail()
        self.assertEqual(account.display_name, "Ada Lovelace")

    async def testAppendsAreSerializedAndHiddenIsHonored(self) -> None:
        """Add appended attributes and drop hidden ones on serialization.

        Validates ``appends`` together with ``hidden``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        account = await feature_fixtures.Account.query().firstOrFail()
        data = account.toDict()
        self.assertEqual(data["display_name"], "Ada Lovelace")
        self.assertEqual(data["role"], "ADMIN")
        self.assertNotIn("secret", data)

class TestSerializationIsolation(TestCase):
    """Exercise attribute state and serialization without database access."""

    def testSerializationReturnsIndependentMapping(self) -> None:
        """Keep serialization result edits outside the attribute store.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        record = state_fixtures._Record({"name": "original"})
        result = record.toDict()
        result["name"] = "changed"
        self.assertEqual(record.name, "original")
        values = {"name": "original", "unknown": {"nested": True}}
        stored = serialize_for_storage(record.__meta__, values)
        self.assertEqual(stored, values)
        self.assertIsNot(stored, values)

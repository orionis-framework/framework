from __future__ import annotations
from dataclasses import fields, is_dataclass
from datetime import UTC, datetime, timedelta
from orionis.session.entities.record import SessionRecord
from orionis.test import TestCase

class TestSessionRecord(TestCase):
    """Unit tests for the SessionRecord dataclass."""

    def testRecordStoresIdentifier(self) -> None:
        """
        Persist the session identifier in the id field.

        Validates that the id argument supplied at construction is
        stored verbatim and accessible as an attribute.
        """
        record = SessionRecord(
            id="my-id",
            data={},
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        self.assertEqual(record.id, "my-id")

    def testRecordStoresData(self) -> None:
        """
        Persist the data payload in the data field.

        Validates that arbitrary key-value pairs supplied at construction
        are stored and accessible without modification.
        """
        payload = {"user_id": 7, "role": "editor"}
        record = SessionRecord(
            id="d",
            data=payload,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        self.assertEqual(record.data, payload)

    def testRecordStoresExpiresAt(self) -> None:
        """
        Store the expires_at timestamp accurately.

        Validates that the datetime supplied at construction is
        preserved without alteration.
        """
        ts = datetime(2030, 1, 1, tzinfo=UTC)
        record = SessionRecord(id="e", data={}, expires_at=ts)
        self.assertEqual(record.expires_at, ts)

    def testRecordEmptyDataIsAllowed(self) -> None:
        """
        Accept an empty data dictionary without error.

        Validates that SessionRecord does not enforce a non-empty payload
        since new sessions legitimately start with no data.
        """
        record = SessionRecord(
            id="empty",
            data={},
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )
        self.assertEqual(record.data, {})

    def testRecordIsDataclass(self) -> None:
        """
        Verify that SessionRecord behaves as a dataclass.

        Validates that two records with equal fields compare as equal,
        confirming standard dataclass __eq__ semantics.
        """
        ts = datetime.now(UTC) + timedelta(hours=1)
        r1 = SessionRecord(id="x", data={"a": 1}, expires_at=ts)
        r2 = SessionRecord(id="x", data={"a": 1}, expires_at=ts)
        self.assertTrue(is_dataclass(SessionRecord))
        self.assertEqual(r1, r2)

    def testRecordDeclaresExactlyThreeFields(self) -> None:
        """
        Expose only the identifier, payload and expiry fields.

        Validates that the exchange currency between the manager and
        the stores stays minimal.
        """
        names = [f.name for f in fields(SessionRecord)]
        self.assertEqual(names, ["id", "data", "expires_at"])

    def testRecordUsesSlots(self) -> None:
        """
        Build the record without a per-instance dictionary.

        Validates that ``slots=True`` is honoured so records stay cheap
        to allocate on every request.
        """
        record = SessionRecord(
            id="slots",
            data={},
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        self.assertFalse(hasattr(record, "__dict__"))

    def testRecordIsMutable(self) -> None:
        """
        Allow stores to reassign fields after construction.

        Validates that the record is a plain (non-frozen) dataclass, so
        the manager can rewrite an identifier in place.
        """
        record = SessionRecord(
            id="mutable",
            data={},
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        record.id = "changed"
        self.assertEqual(record.id, "changed")

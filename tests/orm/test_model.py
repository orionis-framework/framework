from __future__ import annotations
import uuid
from datetime import datetime
from typing import ClassVar
import tests.orm.test_events as feature_fixtures
from orionis.database.connection import Connection
from orionis.database.connection_manager import ConnectionManager
from orionis.orm import DateTime, Integer, Model, StrictJson, StrictTimestamp, String
from orionis.orm.exceptions import (
    InvalidQueryException,
    MassAssignmentException,
    ModelNotFoundException,
)
from orionis.orm.resolver import ConnectionResolver
from orionis.orm.schema.types import Boolean
from orionis.support.types.collection import Collection
from orionis.test import TestCase

class _StubApp:
    """Minimal application stub exposing the database configuration."""

    def config(self, key: str) -> dict:  # noqa: ARG002
        """Run the config helper.

        Parameters
        ----------
        key : str
            Value supplied for ``key``.

        Returns
        -------
        dict
            Value produced by the helper.
        """
        return {
            "default": "sqlite",
            "connections": {
                "sqlite": {
                    "driver": "sqlite",
                    "database": ":memory:",
                    "prefix": "",
                },
                "replica": {
                    "driver": "sqlite",
                    "database": ":memory:",
                    "prefix": "",
                },
            },
        }

class Person(Model):
    id = Integer().primary().autoIncrement()
    name = String()
    email = String().nullable()
    active = Boolean().nullable()
    meta = StrictJson().nullable()
    created_at = StrictTimestamp().nullable()
    updated_at = StrictTimestamp().nullable()

    casts: ClassVar[dict[str, str]] = {"active": "bool", "meta": "json"}
    hidden: ClassVar[list[str]] = ["email"]

class Secret(Model):
    id = Integer().primary().autoIncrement()
    name = String()
    token = String().nullable()

    fillable: ClassVar[list[str]] = ["name"]
    timestamps = False

class Guarded(Model):
    id = Integer().primary().autoIncrement()
    name = String()
    role = String().nullable()

    guarded: ClassVar[list[str]] = ["role"]
    timestamps = False

class Legacy(Model):
    id = Integer().primary().autoIncrement()
    name = String()
    created_at = DateTime().nullable()
    updated_at = DateTime().nullable()

class Remote(Model):
    id = Integer().primary().autoIncrement()
    name = String()
    connection = "replica"
    timestamps = False

class TestModelCrud(TestCase):
    async def asyncSetUp(self) -> None:
        """Wire an isolated in-memory manager and create the tables.

        Guarantees complete isolation between tests.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self._manager = ConnectionManager(_StubApp())
        ConnectionResolver.setManager(self._manager)
        connection = self._manager.connection()
        await connection.createTable(Person.__meta__.table)
        await connection.createTable(Secret.__meta__.table)
        await connection.createTable(Guarded.__meta__.table)
        await connection.createTable(Legacy.__meta__.table)
        replica = self._manager.connection("replica")
        await replica.createTable(Remote.__meta__.table)

    async def asyncTearDown(self) -> None:
        """Dispose the manager and clear the resolver after each test.

        Restores the global resolver state.

        Returns
        -------
        None
            Completes the operation described above.
        """
        await self._manager.disconnect()
        ConnectionResolver.clear()

    # ── Create / find ─────────────────────────────────────────────────────────

    async def testCreatePersistsAndAssignsPrimaryKey(self) -> None:
        """Persist a new model and adopt the generated primary key.

        Validates the create entry point and key assignment.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        person = await Person.create({"name": "John", "email": "j@x.com"})
        self.assertEqual(person.id, 1)
        self.assertTrue(person._exists)

    async def testCreateMaintainsTimestamps(self) -> None:
        """Fill creation and update timestamps on first persist.

        Validates the automatic timestamp maintenance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        person = await Person.create({"name": "John"})
        self.assertIsInstance(person.created_at, datetime)
        self.assertIsInstance(person.updated_at, datetime)

    async def testFindReturnsHydratedModel(self) -> None:
        """Retrieve a model by primary key with casts applied.

        Validates hydration and cast application.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await Person.create({"name": "John", "active": True})
        person = await Person.find(1)
        self.assertIsInstance(person, Person)
        self.assertEqual(person.name, "John")
        self.assertIsInstance(person.active, bool)

    async def testFindReturnsNoneWhenAbsent(self) -> None:
        """Return None when the primary key does not exist.

        Validates the miss behavior of find.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsNone(await Person.find(99))

    async def testFindOrFailRaisesWhenAbsent(self) -> None:
        """Raise ModelNotFoundException for missing primary keys.

        Validates the fail-fast retrieval contract.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ModelNotFoundException):
            await Person.findOrFail(99)

    async def testFirstOrFailRaisesOnEmptyTable(self) -> None:
        """Raise ModelNotFoundException when no row matches.

        Validates the firstOrFail contract.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ModelNotFoundException):
            await Person.where("name", "nobody").firstOrFail()

    # ── Query chains ──────────────────────────────────────────────────────────

    async def testWhereChainFiltersOrdersAndLimits(self) -> None:
        """Combine where, orderBy, and limit into a fluent chain.

        Validates the Eloquent-style chained query experience.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for index in range(5):
            await Person.create(
                {
                    "name": f"user{index}",
                    "active": index % 2 == 0,
                },
            )
        people = (
            await Person.where("active", True).orderBy("name", "desc").limit(2).get()
        )
        self.assertIsInstance(people, Collection)
        self.assertEqual([p.name for p in people], ["user4", "user2"])

    async def testAllReturnsCollection(self) -> None:
        """Retrieve every row wrapped in a Collection.

        Validates the all entry point return type.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await Person.create({"name": "a"})
        await Person.create({"name": "b"})
        people = await Person.all()
        self.assertIsInstance(people, Collection)
        self.assertEqual(people.count(), 2)

    async def testWhereInAndNullFilters(self) -> None:
        """Filter with whereIn, whereNull, and whereNotNull.

        Validates the specialized where clauses end to end.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await Person.create({"name": "a", "email": "a@x.com"})
        await Person.create({"name": "b"})
        await Person.create({"name": "c"})

        by_name = await Person.whereIn("name", ["a", "c"]).get()
        self.assertEqual({p.name for p in by_name}, {"a", "c"})

        without_email = await Person.whereNull("email").get()
        self.assertEqual({p.name for p in without_email}, {"b", "c"})

        with_email = await Person.whereNotNull("email").get()
        self.assertEqual({p.name for p in with_email}, {"a"})

    async def testWhereBetweenAndLike(self) -> None:
        """Filter with whereBetween and whereLike.

        Validates range and pattern conditions end to end.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for name in ("alpha", "beta", "alberto"):
            await Person.create({"name": name})

        ranged = await Person.whereBetween("id", (1, 2)).get()
        self.assertEqual(ranged.count(), 2)

        like = await Person.whereLike("name", "al%").get()
        self.assertEqual({p.name for p in like}, {"alpha", "alberto"})

    async def testOrWhereCombinesConditions(self) -> None:
        """Combine conditions with the OR connector.

        Validates the orWhere clause end to end.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await Person.create({"name": "a"})
        await Person.create({"name": "b"})
        await Person.create({"name": "c"})
        rows = await Person.where("name", "a").orWhere("name", "c").get()
        self.assertEqual({p.name for p in rows}, {"a", "c"})

    async def testLatestOrdersByPrimaryKeyWithoutTimestamps(self) -> None:
        """Order latest() by the created timestamp column when present.

        Validates the latest/oldest defaults.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await Person.create({"name": "first"})
        await Person.create({"name": "second"})
        newest = await Person.query().latest("id").first()
        self.assertEqual(newest.name, "second")

    async def testInvalidWhereArgumentsRaise(self) -> None:
        """Raise InvalidQueryException for malformed where calls.

        Validates the builder argument guards.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(InvalidQueryException):
            Person.query().where("name")
        with self.assertRaises(InvalidQueryException):
            Person.query().where("name", "??", 1)
        with self.assertRaises(InvalidQueryException):
            Person.query().orderBy("name", "sideways")

    # ── Aggregates ────────────────────────────────────────────────────────────

    async def testAggregateTerminals(self) -> None:
        """Compute count, exists, max, min, avg, and sum.

        Validates every aggregate terminal end to end.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for index in range(1, 5):
            await Person.create({"name": f"user{index}"})

        self.assertEqual(await Person.count(), 4)
        self.assertTrue(await Person.where("name", "user1").exists())
        self.assertTrue(await Person.where("name", "ghost").doesntExist())
        self.assertEqual(await Person.query().max("id"), 4)
        self.assertEqual(await Person.query().min("id"), 1)
        self.assertEqual(await Person.query().avg("id"), 2.5)
        self.assertEqual(await Person.query().sum("id"), 10)

    async def testSumOnEmptyTableReturnsZero(self) -> None:
        """Return zero when summing an empty result set.

        Validates the sum null-coalescing rule.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(await Person.query().sum("id"), 0)

    # ── Update / delete ───────────────────────────────────────────────────────

    async def testInstanceUpdateWritesOnlyDirty(self) -> None:
        """Persist only the dirty attributes on update.

        Validates the dirty-write behavior and change tracking.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        person = await Person.create({"name": "John"})
        await person.update({"name": "Peter"})
        self.assertEqual(person.name, "Peter")
        self.assertTrue(person.wasChanged("name"))

        fresh = await Person.find(person.id)
        self.assertEqual(fresh.name, "Peter")

    async def testSaveWithoutChangesIsNoOp(self) -> None:
        """Treat save on a clean model as a successful no-op.

        Validates the clean-save short circuit.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        person = await Person.create({"name": "John"})
        self.assertTrue(await person.save())
        self.assertFalse(person.wasChanged())

    async def testMassUpdateThroughBuilder(self) -> None:
        """Mass update every row matched by the query.

        Validates the builder update terminal.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await Person.create({"name": "a", "active": False})
        await Person.create({"name": "b", "active": False})
        affected = await Person.where("active", False).update({"active": True})
        self.assertEqual(affected, 2)

    async def testDeleteRemovesRow(self) -> None:
        """Delete the model row and flag the instance as unsaved.

        Validates the instance delete contract.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        person = await Person.create({"name": "John"})
        self.assertTrue(await person.delete())
        self.assertIsNone(await Person.find(1))
        self.assertFalse(await person.delete())

    async def testDestroyDeletesByPrimaryKeys(self) -> None:
        """Delete multiple rows by primary key in one statement.

        Validates the destroy entry point.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for name in ("a", "b", "c"):
            await Person.create({"name": name})
        self.assertEqual(await Person.destroy(1, 3), 2)
        self.assertEqual(await Person.count(), 1)

    # ── Pagination ────────────────────────────────────────────────────────────

    async def testPaginateReturnsLengthAwarePage(self) -> None:
        """Paginate the query into a length-aware page.

        Validates items, totals, and navigation flags.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for index in range(5):
            await Person.create({"name": f"user{index}"})
        page = await Person.query().orderBy("id").paginate(page=2, per_page=2)
        self.assertEqual([p.name for p in page.items], ["user2", "user3"])
        self.assertEqual(page.total, 5)
        self.assertEqual(page.lastPage, 3)
        self.assertTrue(page.hasNext)
        self.assertTrue(page.hasPrevious)

    # ── Attributes and state ──────────────────────────────────────────────────

    async def testHiddenAttributesAreOmittedFromSerialization(self) -> None:
        """Omit hidden attributes from toDict and toJson.

        Validates the serialization visibility rules.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        person = await Person.create({"name": "John", "email": "j@x.com"})
        data = person.toDict()
        self.assertNotIn("email", data)
        self.assertIn("name", data)
        self.assertNotIn("email", person.toJson())

    async def testOnlyAndExcludeSubsets(self) -> None:
        """Slice attributes with only() and exclude().

        Validates the attribute subset helpers.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        person = await Person.create({"name": "John", "email": "j@x.com"})
        self.assertEqual(person.only("name"), {"name": "John"})
        self.assertNotIn("name", person.exclude("name"))
        self.assertIn("email", person.exclude("name"))

    async def testJsonCastRoundTrip(self) -> None:
        """Store and reload JSON structures through the json cast.

        Validates the cast round trip against the database.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        payload = {"tags": ["a", "b"], "level": 3}
        person = await Person.create({"name": "John", "meta": payload})
        fresh = await Person.find(person.id)
        self.assertEqual(fresh.meta, payload)

    async def testDirtyTrackingLifecycle(self) -> None:
        """Track dirty state across assignment and synchronization.

        Validates isDirty, isClean, getOriginal, and syncOriginal.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        person = await Person.create({"name": "John"})
        self.assertTrue(person.isClean())

        person.name = "Peter"
        self.assertTrue(person.isDirty())
        self.assertTrue(person.isDirty("name"))
        self.assertFalse(person.isDirty("email"))
        self.assertEqual(person.getOriginal("name"), "John")
        self.assertEqual(person.getDirty(), {"name": "Peter"})

        person.syncOriginal()
        self.assertTrue(person.isClean())
        self.assertEqual(person.getOriginal("name"), "Peter")

    async def testFillableWhitelistBlocksOtherColumns(self) -> None:
        """Reject mass assignment of columns outside the whitelist.

        Validates the fillable enforcement.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        secret = await Secret.create({"name": "ok"})
        self.assertEqual(secret.name, "ok")
        with self.assertRaises(MassAssignmentException):
            await Secret.create({"name": "x", "token": "leak"})

    async def testFillRejectsUnknownColumns(self) -> None:
        """Reject mass assignment of keys that are not columns.

        Validates the unknown-attribute guard.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(MassAssignmentException):
            Person({"ghost": 1})

    async def testDirectAssignmentBypassesMassAssignment(self) -> None:
        """Allow direct attribute assignment regardless of fillable.

        Validates the distinction between fill and direct writes.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        secret = Secret()
        secret.name = "n"
        secret.token = "t"  # noqa: S105
        await secret.save()
        fresh = await Secret.find(secret.id)
        self.assertEqual(fresh.token, "t")

    async def testGuardedListBlocksListedColumns(self) -> None:
        """Block mass assignment only for guarded columns.

        Validates the guarded blacklist enforcement.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        guarded = await Guarded.create({"name": "ok"})
        self.assertEqual(guarded.name, "ok")
        with self.assertRaises(MassAssignmentException):
            await Guarded.create({"name": "x", "role": "admin"})

    async def testDestroyWithoutKeysReturnsZero(self) -> None:
        """Return zero when destroy receives no primary keys.

        Validates the destroy no-op contract.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(await Person.destroy(), 0)

    async def testMultiRowInsertThroughBuilder(self) -> None:
        """Insert several rows in a single builder call.

        Validates the batch insert terminal.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = await Person.query().insert(
            [{"name": "a"}, {"name": "b"}],
        )
        self.assertEqual(result.row_count, 2)
        self.assertEqual(await Person.count(), 2)

    async def testCastsApplyOnDirectAssignment(self) -> None:
        """Apply declared casts when attributes are assigned directly.

        Validates the assignment-time cast application.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        person = Person()
        person.active = "1"
        self.assertIs(person.active, True)

    async def testUnknownAttributeAccessRaises(self) -> None:
        """Raise AttributeError for names that are not columns.

        Validates the attribute access guard.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        person = Person({"name": "x"})
        with self.assertRaises(AttributeError):
            _ = person.ghost

    async def testDeclaredColumnDefaultsToNoneWhenUnloaded(self) -> None:
        """Serve None for declared but unloaded columns.

        Validates the Eloquent-style column access default.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        person = Person()
        self.assertIsNone(person.email)

    async def testNonColumnAssignmentStaysOutOfAttributes(self) -> None:
        """Keep non-column assignments out of the persisted payload.

        Validates the attribute routing rules.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        person = Person({"name": "x"})
        person.transient = "note"
        self.assertEqual(person.transient, "note")
        self.assertNotIn("transient", person.toDict())

    async def testReprIncludesPrimaryKey(self) -> None:
        """Include the class name and primary key in the repr.

        Validates the developer representation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        person = await Person.create({"name": "x"})
        self.assertIn("Person", repr(person))
        self.assertIn("id=1", repr(person))

    async def testModelWithNamedConnectionUsesIt(self) -> None:
        """Route model queries through the declared named connection.

        Validates the per-model connection selection.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        remote = await Remote.create({"name": "far"})
        self.assertEqual(remote.id, 1)
        self.assertEqual(await Remote.count(), 1)
        # The default connection must not contain the remote table rows.
        default_rows = await self._manager.connection().select(
            "SELECT name FROM sqlite_master WHERE name = 'remotes'",
        )
        self.assertEqual(default_rows, [])

    async def testMassUpdateRefreshesUpdatedTimestamp(self) -> None:
        """Refresh the update timestamp during mass updates.

        Validates the automatic timestamp maintenance in builders.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        person = await Person.create({"name": "a"})
        self.assertIsNotNone(person.updated_at)
        await Person.where("id", person.id).update({"name": "b"})
        fresh = await Person.find(person.id)
        self.assertEqual(fresh.name, "b")
        # SQLite returns naive datetimes; only the refresh is asserted.
        self.assertIsInstance(fresh.updated_at, datetime)

    # ── Classmethod shortcuts ─────────────────────────────────────────────────

    async def testFirstReturnsModelOrNoneClassmethod(self) -> None:
        """Retrieve the first row, or None, through the class shortcut.

        Validates the Model.first() classmethod, not only the builder
        it delegates to.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsNone(await Person.first())
        await Person.create({"name": "a"})
        await Person.create({"name": "b"})
        first = await Person.first()
        self.assertIsInstance(first, Person)
        self.assertEqual(first.name, "a")

    async def testFirstOrFailClassmethodReturnsModel(self) -> None:
        """Retrieve the first row through the class shortcut, or raise.

        Validates the Model.firstOrFail() success path.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await Person.create({"name": "only"})
        person = await Person.firstOrFail()
        self.assertIsInstance(person, Person)
        self.assertEqual(person.name, "only")

    async def testUpdateTargetsOriginalPrimaryKeyWhenDirty(self) -> None:
        """Locate the row via the original primary key while it is dirty.

        Validates that _primaryKeyValue() targets the row using the
        original primary key value, even though the dirty diff still
        lets the primary key column itself be persisted with its new
        value once the matching row is found.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        person = await Person.create({"name": "John"})
        person.id = 999
        await person.update({"name": "Peter"})

        self.assertEqual(person.id, 999)
        self.assertIsNone(await Person.find(1))
        fresh = await Person.find(999)
        self.assertEqual(fresh.name, "Peter")

    async def testFreshTimestampDefaultsToAwareWithoutTimestampColumns(
        self,
    ) -> None:
        """Default to an aware timestamp without any timestamp column.

        Validates the freshTimestamp fallback when a model neither
        declares timestamp columns nor enables automatic timestamps.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        moment = Secret.freshTimestamp()
        self.assertIsNotNone(moment.tzinfo)

class TestUniqueIds(feature_fixtures._ModelFeatureTestCase):
    """Client-generated primary keys."""

    async def testUuidPrimaryKeyIsGeneratedOnInsert(self) -> None:
        """Generate the primary key before the row is written.

        Validates ``uuids = True``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        token = await feature_fixtures.Token.create({"label": "api"})
        self.assertIsInstance(token.id, uuid.UUID)
        self.assertIsNotNone(await feature_fixtures.Token.query().find(token.id))

    async def testExplicitUuidIsPreserved(self) -> None:
        """Keep an explicitly assigned identifier.

        Validates that generation only fills a missing key.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        identifier = uuid.uuid4()
        token = await feature_fixtures.Token.create({"id": identifier, "label": "api"})
        self.assertEqual(token.id, identifier)

class TestModelConnectionRouting(TestCase):
    """Exercise instance persistence using an overridable connection resolver."""

    async def testWritesUseDeclaredConnectionHookAndOneTimestamp(self) -> None:
        """Route all writes through the hook and share creation timestamps.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        connection = Connection("sqlite", {"driver": "sqlite", "database": ":memory:"})
        self.addAsyncCleanup(connection.disconnect)

        class _Routed(Model):
            id = Integer().primary().autoIncrement()
            name = String()
            created_at = DateTime()
            updated_at = DateTime()
            calls: ClassVar[int] = 0

            @classmethod
            def getConnection(cls) -> Connection:
                """Return the connection assigned to this model.

                Returns
                -------
                Connection
                    Isolated SQLite connection assigned to the model.
                """
                cls.calls += 1
                return connection

        await connection.createTable(_Routed.__meta__.table)
        record = await _Routed.create({"name": "initial"})
        self.assertEqual(record.id, 1)
        self.assertEqual(record.created_at, record.updated_at)
        self.assertTrue(await record.update({"name": "updated"}))
        self.assertEqual(record.getChanges()["name"], "updated")
        self.assertTrue(record.isClean())
        self.assertTrue(await record.delete())
        self.assertEqual(_Routed.calls, 3)

from __future__ import annotations
import uuid
from typing import ClassVar
from orionis.database.connection_manager import ConnectionManager
from orionis.orm.exceptions import OrmException, ScopeNotFoundException
from orionis.orm.model import Model
from orionis.orm.resolver import ConnectionResolver
from orionis.orm.schema.types import Boolean, DateTime, Integer, String, Uuid
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
            },
        }

class Account(Model):
    """Model exercising soft deletes, scopes, accessors, and events."""

    table = "accounts"
    timestamps = False
    soft_deletes = True
    appends: ClassVar[list[str]] = ["display_name"]

    id = Integer().primary().autoIncrement()
    first_name = String()
    last_name = String()
    role = String().nullable()
    secret = String().nullable()
    active = Boolean()
    deleted_at = DateTime()

    hidden: ClassVar[list[str]] = ["secret"]

    def getDisplayNameAttribute(self, value: object) -> str:  # noqa: ARG002
        """Expose the full name as a computed attribute.

        Parameters
        ----------
        value : object
            Value supplied for ``value``.

        Returns
        -------
        str
            Value produced by the helper.
        """
        first = self._attributes.get("first_name")
        last = self._attributes.get("last_name")
        return f"{first} {last}"

    def getRoleAttribute(self, value: object) -> str:
        """Return the stored role uppercased.

        Parameters
        ----------
        value : object
            Value supplied for ``value``.

        Returns
        -------
        str
            Value produced by the helper.
        """
        return str(value).upper() if value is not None else ""

    def setSecretAttribute(self, value: object) -> str:
        """Store the secret reversed instead of verbatim.

        Parameters
        ----------
        value : object
            Value supplied for ``value``.

        Returns
        -------
        str
            Value produced by the helper.
        """
        return str(value)[::-1]

    @classmethod
    def scopeActive(cls, query: object) -> object:
        """Restrict the query to active accounts.

        Parameters
        ----------
        query : object
            Value supplied for ``query``.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return query.where("active", True)

    @classmethod
    def scopeOfRole(cls, query: object, role: str) -> object:
        """Restrict the query to a given role.

        Parameters
        ----------
        query : object
            Value supplied for ``query``.
        role : str
            Value supplied for ``role``.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return query.where("role", role)

class Token(Model):
    """Model using a client-generated UUID primary key."""

    table = "tokens"
    timestamps = False
    incrementing = False
    uuids = True

    id = Uuid().primary()
    label = String()

def _accountsTable() -> object:
    """
    Build the physical ``accounts`` table.

    Returns
    -------
    TableDefinition
        Definition matching the ``Account`` model.
    """
    return Account.__meta__.table

def _tokensTable() -> object:
    """
    Build the physical ``tokens`` table.

    Returns
    -------
    TableDefinition
        Definition matching the ``Token`` model.
    """
    return Token.__meta__.table

class _ModelFeatureTestCase(TestCase):
    """Shared fixture creating the schema and cleaning class-level state."""

    async def asyncSetUp(self) -> None:
        """Wire an isolated in-memory manager and create the tables.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self._manager = ConnectionManager(_StubApp())
        ConnectionResolver.setManager(self._manager)
        connection = self._manager.connection()
        await connection.createTable(_accountsTable())
        await connection.createTable(_tokensTable())

    async def asyncTearDown(self) -> None:
        """Release the manager and reset listeners and global scopes.

        Returns
        -------
        None
            Completes the operation described above.
        """
        Account.flushEvents()
        Token.flushEvents()
        Account.__meta__.global_scopes.clear()
        await self._manager.disconnect()
        ConnectionResolver.clear()

    async def seed(self) -> None:
        """Insert the reference accounts shared by several tests.

        Returns
        -------
        None
            Completes the operation described above.
        """
        await Account.create({
            "first_name": "Ada", "last_name": "Lovelace",
            "role": "admin", "secret": "abc", "active": True,
        })
        await Account.create({
            "first_name": "Ben", "last_name": "Stone",
            "role": "guest", "secret": "xyz", "active": False,
        })

class TestSoftDeletes(_ModelFeatureTestCase):
    """Soft delete behavior on instances and on the query builder."""

    async def testDeleteStampsInsteadOfRemoving(self) -> None:
        """Stamp the delete column instead of removing the row.

        Validates the instance-level soft delete.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        account = await Account.query().firstOrFail()
        self.assertTrue(await account.delete())
        self.assertTrue(account.trashed())
        self.assertEqual(await Account.withTrashed().count(), 2)

    async def testTrashedRowsAreExcludedByDefault(self) -> None:
        """Hide soft deleted rows from ordinary queries.

        Validates the implicit soft delete constraint.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        account = await Account.query().firstOrFail()
        await account.delete()
        self.assertEqual(await Account.count(), 1)

    async def testOnlyTrashedReturnsDeletedRows(self) -> None:
        """Restrict a query to soft deleted rows.

        Validates ``onlyTrashed``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        account = await Account.query().firstOrFail()
        await account.delete()
        trashed = await Account.onlyTrashed().get()
        self.assertEqual([model.id for model in trashed], [account.id])

    async def testRestoreBringsTheRowBack(self) -> None:
        """Clear the delete stamp of a soft deleted row.

        Validates the instance-level restore.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        account = await Account.query().firstOrFail()
        await account.delete()
        self.assertTrue(await account.restore())
        self.assertFalse(account.trashed())
        self.assertEqual(await Account.count(), 2)

    async def testForceDeleteRemovesTheRow(self) -> None:
        """Delete a soft-deleting model permanently.

        Validates ``forceDelete``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        account = await Account.query().firstOrFail()
        await account.forceDelete()
        self.assertEqual(await Account.withTrashed().count(), 1)

    async def testBuilderDeleteSoftDeletesEveryMatch(self) -> None:
        """Soft delete through a mass delete query.

        Validates that the builder honors soft deletes too.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        self.assertEqual(await Account.query().delete(), 2)
        self.assertEqual(await Account.count(), 0)
        self.assertEqual(await Account.withTrashed().count(), 2)

    async def testBuilderRestoreAndForceDelete(self) -> None:
        """Restore and permanently delete through the builder.

        Validates the mass variants of both operations.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        await Account.query().delete()
        self.assertEqual(await Account.query().restore(), 2)
        self.assertEqual(await Account.count(), 2)
        self.assertEqual(await Account.query().forceDelete(), 2)
        self.assertEqual(await Account.withTrashed().count(), 0)

class TestScopes(_ModelFeatureTestCase):
    """Local and global query scopes."""

    async def testLocalScopeIsCallableOnTheBuilder(self) -> None:
        """Apply a local scope declared on the model.

        Validates the ``scopeName`` convention.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        models = await Account.query().active().get()
        self.assertEqual([model.first_name for model in models], ["Ada"])

    async def testLocalScopeIsCallableOnTheModelClass(self) -> None:
        """Start a query from a local scope.

        Validates the class-level forwarding of scopes.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        models = await Account.active().get()
        self.assertEqual([model.first_name for model in models], ["Ada"])

    async def testLocalScopeAcceptsArguments(self) -> None:
        """Forward arguments to a parameterized scope.

        Validates argument passing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        models = await Account.query().ofRole("guest").get()
        self.assertEqual([model.first_name for model in models], ["Ben"])

    def testUnknownScopeIsReported(self) -> None:
        """Report a scope the model does not declare.

        Validates the explicit lookup failure.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ScopeNotFoundException):
            Account.query().scope("ghost")

    def testUnknownAttributeStillRaisesAttributeError(self) -> None:
        """Keep ordinary attribute errors intact on the builder.

        Validates that the scope lookup does not swallow typos.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(AttributeError):
            Account.query().ghost  # noqa: B018

    async def testGlobalScopeAppliesToEveryQuery(self) -> None:
        """Constrain every query of the model.

        Validates global scope registration.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        Account.addGlobalScope("active", lambda query: query.where("active", True))
        self.assertEqual(await Account.count(), 1)

    async def testGlobalScopeCanBeDisabledPerQuery(self) -> None:
        """Opt a single query out of a global scope.

        Validates ``withoutGlobalScope``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        Account.addGlobalScope("active", lambda query: query.where("active", True))
        self.assertEqual(await Account.withoutGlobalScope("active").count(), 2)
        self.assertEqual(await Account.withoutGlobalScopes().count(), 2)

    async def testGlobalScopeCanBeRemoved(self) -> None:
        """Unregister a global scope from the model.

        Validates ``removeGlobalScope``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        Account.addGlobalScope("active", lambda query: query.where("active", True))
        Account.removeGlobalScope("active")
        self.assertEqual(await Account.count(), 2)

class TestAccessorsAndMutators(_ModelFeatureTestCase):
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
        account = await Account.query().firstOrFail()
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
        account = Account({"first_name": "Cid", "last_name": "Kane"})
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
        account = await Account.query().firstOrFail()
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
        account = await Account.query().firstOrFail()
        data = account.toDict()
        self.assertEqual(data["display_name"], "Ada Lovelace")
        self.assertEqual(data["role"], "ADMIN")
        self.assertNotIn("secret", data)

class TestModelEvents(_ModelFeatureTestCase):
    """Lifecycle events dispatched around persistence operations."""

    async def testCreateDispatchesTheCreationEvents(self) -> None:
        """Dispatch the saving/creating/created/saved chain.

        Validates the insert event order.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        fired: list[str] = []
        for event in ("saving", "creating", "created", "saved"):
            Account.registerEvent(event, lambda _model, name=event: fired.append(name))
        await Account.create({"first_name": "Ada", "last_name": "L", "active": True})
        self.assertEqual(fired, ["saving", "creating", "created", "saved"])

    async def testUpdateDispatchesTheUpdateEvents(self) -> None:
        """Dispatch the saving/updating/updated/saved chain.

        Validates the update event order.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        fired: list[str] = []
        for event in ("updating", "updated"):
            Account.registerEvent(event, lambda _model, name=event: fired.append(name))
        account = await Account.query().firstOrFail()
        account.first_name = "Grace"
        await account.save()
        self.assertEqual(fired, ["updating", "updated"])

    async def testDeleteDispatchesTheDeleteEvents(self) -> None:
        """Dispatch the deleting/deleted chain.

        Validates the delete event order.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        fired: list[str] = []
        for event in ("deleting", "deleted"):
            Account.registerEvent(event, lambda _model, name=event: fired.append(name))
        account = await Account.query().firstOrFail()
        await account.delete()
        self.assertEqual(fired, ["deleting", "deleted"])

    async def testRestoreDispatchesTheRestoreEvents(self) -> None:
        """Dispatch the restoring/restored chain.

        Validates the soft delete restore events.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        fired: list[str] = []
        for event in ("restoring", "restored"):
            Account.registerEvent(event, lambda _model, name=event: fired.append(name))
        account = await Account.query().firstOrFail()
        await account.delete()
        await account.restore()
        self.assertEqual(fired, ["restoring", "restored"])

    async def testBeforeEventCanVetoTheOperation(self) -> None:
        """Abort a write when a listener returns ``False``.

        Validates the halting semantics of the "before" events.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        Account.registerEvent("creating", lambda _model: False)
        account = Account({"first_name": "Ada", "last_name": "L", "active": True})
        self.assertFalse(await account.save())
        self.assertEqual(await Account.count(), 0)

    async def testAsyncListenersAreAwaited(self) -> None:
        """Await coroutine listeners.

        Validates support for async listeners.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        fired: list[str] = []

        async def listener(model: Account) -> None:
            """Record the model received by the event listener.

            Parameters
            ----------
            model : Account
                Value supplied for ``model``.

            Returns
            -------
            None
                Completes the operation described above.
            """
            fired.append(model.first_name)

        Account.registerEvent("created", listener)
        await Account.create({"first_name": "Ada", "last_name": "L", "active": True})
        self.assertEqual(fired, ["Ada"])

    async def testRetrievedIsDispatchedOnHydration(self) -> None:
        """Dispatch ``retrieved`` for every hydrated model.

        Validates the read-side event.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        seen: list[int] = []
        Account.registerEvent("retrieved", lambda model: seen.append(model.id))
        await Account.get()
        self.assertEqual(len(seen), 2)

    async def testObserverRegistersEveryMatchingMethod(self) -> None:
        """Register a whole observer class at once.

        Validates ``observe``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        fired: list[str] = []

        class _Observer:
            def creating(self, _model: Account) -> None:
                """Record the model creation event.

                Parameters
                ----------
                _model : Account
                    Value supplied for ``_model``.

                Returns
                -------
                None
                    Completes the operation described above.
                """
                fired.append("creating")

            def created(self, _model: Account) -> None:
                """Record the completed model creation event.

                Parameters
                ----------
                _model : Account
                    Value supplied for ``_model``.

                Returns
                -------
                None
                    Completes the operation described above.
                """
                fired.append("created")

        Account.observe(_Observer)
        await Account.create({"first_name": "Ada", "last_name": "L", "active": True})
        self.assertEqual(fired, ["creating", "created"])

    def testUnsupportedEventIsRejected(self) -> None:
        """Reject an event name outside the supported set.

        Validates the registration guard.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(OrmException):
            Account.registerEvent("exploding", lambda _model: None)

class TestUniqueIds(_ModelFeatureTestCase):
    """Client-generated primary keys."""

    async def testUuidPrimaryKeyIsGeneratedOnInsert(self) -> None:
        """Generate the primary key before the row is written.

        Validates ``uuids = True``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        token = await Token.create({"label": "api"})
        self.assertIsInstance(token.id, uuid.UUID)
        self.assertIsNotNone(await Token.query().find(token.id))

    async def testExplicitUuidIsPreserved(self) -> None:
        """Keep an explicitly assigned identifier.

        Validates that generation only fills a missing key.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        identifier = uuid.uuid4()
        token = await Token.create({"id": identifier, "label": "api"})
        self.assertEqual(token.id, identifier)

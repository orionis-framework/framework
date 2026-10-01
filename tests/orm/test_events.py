from __future__ import annotations
from typing import ClassVar
import tests.orm.test_state as state_fixtures
from orionis.database.connection_manager import ConnectionManager
from orionis.orm import DateTime, Integer, Model, String
from orionis.orm.exceptions import OrmException
from orionis.orm.resolver import ConnectionResolver
from orionis.orm.schema.types import Boolean, Uuid
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
        await connection.createTable(Account.__meta__.table)
        await connection.createTable(Token.__meta__.table)

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
        await Account.create(
            {
                "first_name": "Ada",
                "last_name": "Lovelace",
                "role": "admin",
                "secret": "abc",
                "active": True,
            },
        )
        await Account.create(
            {
                "first_name": "Ben",
                "last_name": "Stone",
                "role": "guest",
                "secret": "xyz",
                "active": False,
            },
        )

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

class TestModelEventInheritance(TestCase):
    """Exercise instance persistence using an overridable connection resolver."""

    async def testInheritedListenersRunOncePerRegistration(self) -> None:
        """Preserve explicit duplicates without multiplying inherited listeners.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """

        class _Ancestor(state_fixtures._Record):
            pass

        seen = []
        listener = seen.append
        _Ancestor.registerEvent("saving", listener)
        _Ancestor.registerEvent("saving", listener)

        class _Left(_Ancestor):
            pass

        class _Right(_Ancestor):
            pass

        class _Diamond(_Left, _Right):
            pass

        class _Descendant(_Diamond):
            pass

        record = _Descendant()
        await record.fireEvent("saving")
        self.assertEqual(seen, [record, record])

    async def testFlushedListenersStayAbsentFromDescendants(self) -> None:
        """Keep cleared inherited listeners out of newly declared descendants.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """

        class _Ancestor(state_fixtures._Record):
            pass

        _Ancestor.registerEvent("saving", lambda _model: False)

        class _Parent(_Ancestor):
            pass

        _Parent.flushEvents("saving")

        class _Descendant(_Parent):
            pass

        self.assertTrue(await _Descendant().fireEvent("saving"))
        self.assertFalse(await _Ancestor().fireEvent("saving"))

    async def testListenersRegisteredDuringDispatchWaitUntilNextEvent(self) -> None:
        """Dispatch an immutable listener snapshot while registration changes.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """

        class _Observed(state_fixtures._Record):
            pass

        seen = []

        def register_during_dispatch(record: Model) -> None:
            """Append the next listener during an existing dispatch.

            Parameters
            ----------
            record : Model
                Value supplied for ``record``.

            Returns
            -------
            None
                Completes the operation described above.
            """
            seen.append("first")
            type(record).registerEvent("saved", lambda _model: seen.append("next"))

        _Observed.registerEvent("saved", register_during_dispatch)
        await _Observed().fireEvent("saved")
        self.assertEqual(seen, ["first"])
        await _Observed().fireEvent("saved")
        self.assertEqual(seen, ["first", "first", "next"])

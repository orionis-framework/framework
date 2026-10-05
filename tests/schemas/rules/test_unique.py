import asyncio
from typing import TYPE_CHECKING, Annotated
from orionis.container.container import Container
from orionis.database.connection import Connection
from orionis.http.request import Request
from orionis.orm.exceptions import OrmConfigurationException
from orionis.orm.query.expressions import InsertPlan
from orionis.orm.resolver import ConnectionResolver
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import Integer, String
from orionis.schemas.exceptions.validation import ValidationException
from orionis.schemas.rules.unique import Unique
from orionis.schemas.schema import Schema
from orionis.schemas.validator import Schema as Validator
from orionis.test import TestCase

if TYPE_CHECKING:
    from orionis.orm.query.expressions import SelectPlan

class _UniquePayload(Schema):
    """Combine a database rule with an independently converted field."""

    code: Annotated[str, Unique("unique_values", "code")]
    quantity: int = 1

class _NestedPayload(Schema):
    """Allow a nested schema or a scalar union member."""

    child: _UniquePayload | int

class _SchemaContainer(Container):
    """Keep validation bindings independent of the application's container."""

    __slots__ = ()

class _SchemaRequest(Request):
    """Supply a request body without constructing a transport."""

    __slots__ = ("_data",)

    def __init__(self, data: dict[str, object]) -> None:
        """Retain the body used by container-injected schema validation.

        Parameters
        ----------
        data : dict[str, object]
            Decoded request payload.

        Returns
        -------
        None
            The request body is ready for validation.
        """
        self._data = data

    async def data(self) -> dict[str, object]:
        """Return the test-owned decoded request body.

        Returns
        -------
        dict[str, object]
            Payload supplied when constructing the request.
        """
        return self._data

def _receive_payload(payload: _UniquePayload) -> _UniquePayload:
    """Return the typed payload injected by the container.

    Parameters
    ----------
    payload : _UniquePayload
        Schema instance resolved from the active request scope.

    Returns
    -------
    _UniquePayload
        Validated instance supplied by dependency injection.
    """
    return payload

class _WaitingConnection:
    """Hold a database probe until its caller releases it."""

    __slots__ = ("entered", "release")

    def __init__(self) -> None:
        """Create the admission and release events.

        Returns
        -------
        None
            The connection is ready to suspend its first query.
        """
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def select(self, _plan: SelectPlan) -> list[dict[str, object]]:
        """Wait for release and report no conflicting rows.

        Parameters
        ----------
        _plan : SelectPlan
            Query prepared by the uniqueness rule.

        Returns
        -------
        list[dict[str, object]]
            Empty result after the caller releases the query.
        """
        self.entered.set()
        await self.release.wait()
        return []

class _ConnectionManager:
    """Resolve only the test-owned connection, without constructing engines."""

    __slots__ = ("current",)

    def __init__(self, connection: Connection) -> None:
        """Retain the connection associated with this test.

        Parameters
        ----------
        connection : Connection
            In-memory connection created by the test.

        Returns
        -------
        None
            Connection resolution is ready.
        """
        self.current: Connection | _WaitingConnection = connection

    def connection(self, _name: str | None = None) -> Connection | _WaitingConnection:
        """Return the connection owned by the current test.

        Parameters
        ----------
        _name : str | None, optional
            Connection name supplied by the rule.

        Returns
        -------
        Connection | _WaitingConnection
            Current database connection or controlled query double.
        """
        return self.current

class TestUniqueAsync(TestCase):
    """Verify transaction visibility and nonblocking uniqueness checks."""

    async def asyncSetUp(self) -> None:
        """Create a private SQLite database and install its resolver.

        Returns
        -------
        None
            A fresh table and connection are available to the rule.
        """
        try:
            self._previous = ConnectionResolver.manager()
        except OrmConfigurationException:
            self._previous = None
        self._connection = Connection(
            "sqlite", {"driver": "sqlite", "database": ":memory:", "prefix": ""},
        )
        columns = {"id": Integer().primary().autoIncrement(), "code": String()}
        for name, column in columns.items():
            column.name = name
        self._table = TableDefinition(
            name="unique_values", columns=columns, primary_key="id",
        )
        await self._connection.createTable(self._table)
        self._manager = _ConnectionManager(self._connection)
        ConnectionResolver.setManager(self._manager)

    async def asyncTearDown(self) -> None:
        """Restore the application resolver and release the test database.

        Returns
        -------
        None
            No connection or resolver state remains owned by the test.
        """
        if self._previous is None:
            ConnectionResolver.clear()
        else:
            ConnectionResolver.setManager(self._previous)
        Container._instances.pop(_SchemaContainer, None)
        await self._connection.disconnect()

    async def testSeesUncommittedRowsAndHonorsTheExcludedRow(self) -> None:
        """Check the current transaction without opening an isolated connection.

        Returns
        -------
        None
            Uncommitted duplicates fail while the excluded row remains valid.
        """
        async with self._connection.transaction():
            inserted = await self._connection.insert(InsertPlan(
                table=self._table, values=[{"code": "taken"}],
            ))
            rule = Unique("unique_values", "code")
            self.assertFalse(await rule.enforceAsync("code", "taken", None))
            self.assertTrue(await rule.enforceAsync("code", "available", None))
            ignored = Unique("unique_values", "code", ignore=inserted.last_insert_id)
            self.assertTrue(await ignored.enforceAsync("code", "taken", None))

    async def testProbeYieldsControlToTheCurrentLoop(self) -> None:
        """Keep the event loop available while a database probe is suspended.

        Returns
        -------
        None
            The query and its release event execute in the same event loop.
        """
        connection = _WaitingConnection()
        self._manager.current = connection
        rule = Unique("unique_values", "code")
        pending = asyncio.create_task(rule.enforceAsync("code", "available", None))
        try:
            await asyncio.wait_for(connection.entered.wait(), timeout=1)
            self.assertFalse(pending.done())
        finally:
            connection.release.set()
            result = await pending
        self.assertTrue(result)

    async def testMissingValueDoesNotQueryTheConnection(self) -> None:
        """Leave missing values to the schema's type validation.

        Returns
        -------
        None
            The rule accepts None without starting a database query.
        """
        connection = _WaitingConnection()
        self._manager.current = connection
        self.assertTrue(await Unique("unique_values", "code").enforceAsync(
            "code", None, None,
        ))
        self.assertFalse(connection.entered.is_set())

    async def testValidatorReportsTypeAndDatabaseFailuresTogether(self) -> None:
        """Await valid fields even when a sibling fails conversion.

        Returns
        -------
        None
            Both field errors are reported inside the current transaction.
        """
        async with self._connection.transaction():
            await self._connection.insert(InsertPlan(
                table=self._table, values=[{"code": "taken"}],
            ))
            with self.assertRaises(ValidationException) as caught:
                await Validator.validateAsync(
                    {"code": "taken", "quantity": "invalid"}, _UniquePayload,
                )
            self.assertEqual(set(caught.exception.errors), {"code", "quantity"})

    async def testValidatorAwaitsNestedRulesOnBothConversionPaths(self) -> None:
        """Preserve asynchronous nested failures with and without type errors.

        Returns
        -------
        None
            Nested database failures retain their fully qualified field names.
        """
        await self._connection.insert(InsertPlan(
            table=self._table, values=[{"code": "taken"}],
        ))
        for quantity in (1, "invalid"):
            with self.assertRaises(ValidationException) as caught:
                await Validator.validateAsync(
                    {"child": {"code": "taken", "quantity": quantity}},
                    _NestedPayload,
                )
            self.assertIn("child.code", caught.exception.errors)
            self.assertEqual("child.quantity" in caught.exception.errors, quantity != 1)

    async def testScalarUnionMemberNeedsNoSchemaTraversal(self) -> None:
        """Accept a scalar alternative without inspecting it as a schema.

        Returns
        -------
        None
            Both validator entry points preserve the scalar union member.
        """
        self.assertEqual(Validator.validate({"child": 3}, _NestedPayload).child, 3)
        self.assertEqual(
            (await Validator.validateAsync({"child": 3}, _NestedPayload)).child, 3,
        )

    async def testValidatorPropagatesCancellationWhileTheQueryWaits(self) -> None:
        """Let cancellation reach a pending native database rule.

        Returns
        -------
        None
            Cancellation propagates without being converted to validation errors.
        """
        connection = _WaitingConnection()
        self._manager.current = connection
        pending = asyncio.create_task(Validator.validateAsync(
            {"code": "available"}, _UniquePayload,
        ))
        try:
            await asyncio.wait_for(connection.entered.wait(), timeout=1)
        finally:
            pending.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await pending

    async def testContainerAwaitsTheRuleBeforeInjectingThePayload(self) -> None:
        """Resolve a schema through the actual container while its rule suspends.

        Returns
        -------
        None
            Injection completes only after the nonblocking query finishes.
        """
        connection = _WaitingConnection()
        self._manager.current = connection
        container = _SchemaContainer()
        async with container.beginScope():
            container.instance(Request, _SchemaRequest({"code": "available"}))
            pending = asyncio.create_task(container.invoke(_receive_payload))
            try:
                await asyncio.wait_for(connection.entered.wait(), timeout=1)
                self.assertFalse(pending.done())
            finally:
                connection.release.set()
                payload = await pending
            self.assertIsInstance(payload, _UniquePayload)
            self.assertEqual(payload.code, "available")

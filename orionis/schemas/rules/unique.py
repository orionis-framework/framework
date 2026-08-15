import asyncio
from typing import TYPE_CHECKING
from orionis.aio.loop import Loop
from orionis.database.connection import Connection
from orionis.orm.query.raw_builder import RawQueryBuilder
from orionis.orm.resolver import ConnectionResolver
from orionis.schemas.rule import Rule

if TYPE_CHECKING:
    from orionis.orm.query.expressions import SelectPlan

def _has_running_loop() -> bool:
    """
    Report whether the calling thread already runs an event loop.

    Returns
    -------
    bool
        Return ``True`` when a loop is running in the current thread.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True

class Unique(Rule):
    """
    Ensure a value is not already stored in a database column.

    The rule pipeline is synchronous while the ORM is async-only, so the
    lookup is bridged with :meth:`orionis.aio.loop.Loop.runSync`. The
    calling thread blocks until the query resolves, which is why the check
    is scoped to a single row probe.
    """

    # ruff: noqa: ARG002

    __message__ = "Value must be unique."
    __code__ = "unique"

    __slots__ = ("_column", "_connection", "_ignore", "_ignore_column", "_table")

    def __init__(  # noqa: PLR0913
        self,
        table: str,
        column: str,
        *,
        ignore: object = None,
        ignore_column: str = "id",
        connection: str | None = None,
        message: str | None = None,
    ) -> None:
        """
        Initialize the rule with the database table and column to check.

        Parameters
        ----------
        table : str
            Logical table name, without the connection prefix.
        column : str
            Column name within the table.
        ignore : object, optional
            Row identifier excluded from the lookup, so updating a record
            does not clash with itself.
        ignore_column : str, optional
            Column ``ignore`` is matched against.
        connection : str | None, optional
            Named connection to query, or ``None`` for the default one.
        message : str | None, optional
            Override message used when validation fails.

        Returns
        -------
        None
            This method initializes the instance and returns None.
        """
        super().__init__(message=message)
        self._table: str = table
        self._column: str = column
        self._ignore: object = ignore
        self._ignore_column: str = ignore_column
        self._connection: str | None = connection

    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value as unique.

        Parameters
        ----------
        field : str
            Field name associated with the value.
        value : object
            Value to validate.
        instance : object
            Owning object instance. This argument is accepted for
            interface compatibility.

        Returns
        -------
        bool
            Return ``True`` when the value passes validation.
        """
        # Leave missing values to the type layer, which already reports them.
        if value is None:
            return True

        plan = self.__plan(value)

        # A running loop means ``runSync`` bridges to a worker thread with its
        # own loop. Pooled connections belong to the caller's loop and drivers
        # such as asyncpg reject cross-loop use ("another operation is in
        # progress"), so the probe gets a throwaway connection instead.
        if _has_running_loop():
            return not Loop.runSync(self.__existsIsolated(plan))

        return not Loop.runSync(self.__existsShared(plan))

    def __plan(self, value: object) -> SelectPlan:
        """
        Build the query plan probing for a conflicting row.

        Parameters
        ----------
        value : object
            Value searched for in the configured column.

        Returns
        -------
        SelectPlan
            Plan matching at most one row that breaks uniqueness.
        """
        builder = RawQueryBuilder().table(self._table)
        builder.where(self._column, "=", value)

        # Exclude the row being updated so it never clashes with itself.
        if self._ignore is not None:
            builder.where(self._ignore_column, "!=", self._ignore)

        plan = builder.toPlan()
        plan.limit_value = 1
        return plan

    async def __existsShared(self, plan: SelectPlan) -> bool:
        """
        Run the probe on the connection shared by the application.

        Parameters
        ----------
        plan : SelectPlan
            Plan matching the rows that break uniqueness.

        Returns
        -------
        bool
            Return ``True`` when a conflicting row exists.
        """
        connection = ConnectionResolver.connection(self._connection)
        return bool(await connection.select(plan))

    async def __existsIsolated(self, plan: SelectPlan) -> bool:
        """
        Run the probe on a connection owned by the calling event loop.

        Parameters
        ----------
        plan : SelectPlan
            Plan matching the rows that break uniqueness.

        Returns
        -------
        bool
            Return ``True`` when a conflicting row exists.
        """
        manager = ConnectionResolver.manager()
        name = self._connection or manager.getDefaultName()
        connection = Connection(name, manager.configFor(name))
        try:
            return bool(await connection.select(plan))
        finally:
            # Never leave the engine behind: it belongs to this short-lived loop.
            await connection.disconnect()

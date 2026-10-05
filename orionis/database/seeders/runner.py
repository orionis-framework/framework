import time
from typing import TYPE_CHECKING, Any
from orionis.database.contracts.connection import IConnection
from orionis.database.contracts.connection_manager import IConnectionManager
from orionis.database.exceptions import QueryException
from orionis.database.migrations.context import migration_connection_scope
from orionis.database.seeders.events import NO_EVENTS, SeederEvents
from orionis.database.seeders.seeder import Seeder
from orionis.foundation.contracts.application import IApplication
from orionis.introspection.modules.inspector import ModuleInspector
from orionis.introspection.modules.reflection import ReflectionModule
from orionis.orm.query.expressions import (
    InsertPlan,
    OrderClause,
    SelectPlan,
    SortDirection,
    UpdatePlan,
    WhereClause,
)
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import BigInteger, Integer, String

if TYPE_CHECKING:
    from pathlib import Path

class _ClaimFailed(Exception):
    """Signal that inserting a seeder claim failed inside a transaction."""

    __slots__ = ("error",)

    def __init__(self, error: QueryException) -> None:
        """
        Retain the query error that prevented a seeder claim.

        Parameters
        ----------
        error : QueryException
            Query failure that prevented the claim.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        self.error = error
        super().__init__(str(error))

def _build_seeders_table() -> TableDefinition:
    """
    Build the persistent seeder tracking table definition.

    Returns
    -------
    TableDefinition
        Table with a unique seeder name, batch and completion timestamp.
    """
    id_column: ColumnDefinition = Integer().primary().autoIncrement()
    id_column.name = "id"

    seeder_column: ColumnDefinition = String(255).unique()
    seeder_column.name = "seeder"

    batch_column: ColumnDefinition = Integer()
    batch_column.name = "batch"

    seeded_at_column: ColumnDefinition = BigInteger()
    seeded_at_column.name = "seeded_at"

    return TableDefinition(
        name="seeders",
        columns={
            "id": id_column,
            "seeder": seeder_column,
            "batch": batch_column,
            "seeded_at": seeded_at_column,
        },
        primary_key="id",
    )

_SEEDERS_TABLE: TableDefinition = _build_seeders_table()

class SeederRunner:
    """
    Apply new seeders exactly once on the selected database connection.

    Files under ``database/seeders`` are discovered in lexical filename
    order. The application container builds each seeder so constructors can
    receive dependencies. Each seeder and its tracking row commit in the same
    transaction. The unique tracking key acts as a database-level claim when
    runs overlap.
    """

    # The container resolves constructor dependencies from runtime types.
    # ruff: noqa: TC001

    __slots__ = ("__app", "__conn_manager", "__discovered_cache")

    def __init__(
        self,
        app: IApplication,
        conn_manager: IConnectionManager,
    ) -> None:
        """
        Initialize the runner with the application and connection manager.

        Parameters
        ----------
        app : IApplication
            Application providing the seeder directory.
        conn_manager : IConnectionManager
            Manager resolving configured database connections.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        self.__app = app
        self.__conn_manager = conn_manager
        self.__discovered_cache: dict[str, type[Seeder]] | None = None

    async def seed(
        self,
        *,
        connection: str | None = None,
        events: SeederEvents | None = None,
    ) -> list[str]:
        """
        Run every discovered seeder that has no committed tracking row.

        Parameters
        ----------
        connection : str or None, optional
            Named database connection, or the configured default.
        events : SeederEvents or None, optional
            Progress callbacks for executed seeders.

        Returns
        -------
        list of str
            Seeder names completed by this call, in execution order.
        """
        target = self.__conn_manager.connection(connection)
        await self.__ensureTrackingTable(target)

        ran = await self.__getRan(target)
        ran_names = {row["seeder"] for row in ran}
        pending = [
            (name, cls)
            for name, cls in self.__discover().items()
            if name not in ran_names
        ]
        if not pending:
            return []

        batch = max((int(row["batch"]) for row in ran), default=0) + 1
        reporter = events or NO_EVENTS
        applied: list[str] = []
        for name, seeder_cls in pending:
            if await self.__runStep(target, name, seeder_cls, batch, reporter):
                applied.append(name)
        return applied

    async def __ensureTrackingTable(self, connection: IConnection) -> None:
        """
        Create the tracking table, tolerating a concurrent creator.

        Parameters
        ----------
        connection : IConnection
            Selected database connection.

        Returns
        -------
        None
            The table is available for tracking operations.
        """
        try:
            await connection.createTable(_SEEDERS_TABLE)
        except QueryException as exc:
            # createTable checks for existence before issuing DDL. Another
            # process may create it between those statements on a fresh DB.
            try:
                await self.__getRan(connection)
            except QueryException:
                raise exc from None

    def __seedersPath(self) -> Path:
        """
        Return the application's configured seeder directory.

        Returns
        -------
        Path
            Absolute path under ``database/seeders``.
        """
        return self.__app.path("database_seeders")

    def __discover(self) -> dict[str, type[Seeder]]:
        """
        Find local Seeder subclasses in deterministic filename order.

        Returns
        -------
        dict of str to type of Seeder
            Seeder classes keyed by persisted filename stem.

        Raises
        ------
        ValueError
            If more than one class resolves to the same persisted name.
        """
        if self.__discovered_cache is not None:
            return self.__discovered_cache

        path = self.__seedersPath()
        if not path.is_dir():
            self.__discovered_cache = {}
            return self.__discovered_cache

        modules = ModuleInspector.discoverModules(
            base_path=self.__app.basePath,
            target_path=path,
        )
        found: dict[str, type[Seeder]] = {}
        for module_name in modules:
            stem = module_name.rsplit(".", 1)[-1]
            if stem == "__init__":
                continue
            rf_module = ReflectionModule(module_name)
            for obj in rf_module.getClasses().values():
                if obj.__module__ != module_name or not issubclass(obj, Seeder):
                    continue
                previous = found.get(stem)
                if previous is not None:
                    error_msg = (
                        f"Ambiguous seeder '{stem}': "
                        f"{previous.__module__}.{previous.__name__} and "
                        f"{module_name}.{obj.__name__}."
                    )
                    raise ValueError(error_msg)
                found[stem] = obj

        self.__discovered_cache = dict(sorted(found.items()))
        return self.__discovered_cache

    async def __getRan(self, connection: IConnection) -> list[dict[str, Any]]:
        """
        Read committed tracking rows in insertion order.

        Parameters
        ----------
        connection : IConnection
            Connection holding the tracking table.

        Returns
        -------
        list of dict
            Tracking rows ordered by primary key.
        """
        return await connection.select(
            SelectPlan(
                table=_SEEDERS_TABLE,
                columns=("id", "seeder", "batch", "seeded_at"),
                orders=[OrderClause("id", SortDirection.ASC)],
            ),
        )

    async def __isRecorded(self, connection: IConnection, name: str) -> bool:
        """
        Check whether another transaction committed this seeder.

        Parameters
        ----------
        connection : IConnection
            Connection holding the tracking table.
        name : str
            Seeder filename stem.

        Returns
        -------
        bool
            Whether the tracking row is committed.
        """
        rows = await connection.select(
            SelectPlan(
                table=_SEEDERS_TABLE,
                columns=("id",),
                wheres=[WhereClause(column="seeder", value=name)],
                limit_value=1,
            ),
        )
        return bool(rows)

    async def __runStep(
        self,
        connection: IConnection,
        name: str,
        seeder_cls: type[Seeder],
        batch: int,
        events: SeederEvents,
    ) -> bool:
        """
        Claim, run and commit one seeder and its tracking row.

        Parameters
        ----------
        connection : IConnection
            Connection shared by the seeder and tracking transaction.
        name : str
            Persisted seeder filename stem.
        seeder_cls : type of Seeder
            Class to instantiate and execute.
        batch : int
            Batch assigned to this invocation.
        events : SeederEvents
            Progress callbacks.

        Returns
        -------
        bool
            Whether this call executed the seeder.
        """
        started_at = time.perf_counter()
        started = False
        try:
            async with connection.transaction():
                try:
                    await connection.insert(
                        InsertPlan(
                            table=_SEEDERS_TABLE,
                            values=[{
                                "seeder": name,
                                "batch": batch,
                                "seeded_at": 0,
                            }],
                        ),
                    )
                except QueryException as exc:
                    raise _ClaimFailed(exc) from exc

                events.started(name)
                started = True
                with migration_connection_scope(connection):
                    seeder = await self.__app.build(seeder_cls)
                    await seeder.run()
                await connection.update(
                    UpdatePlan(
                        table=_SEEDERS_TABLE,
                        values={"seeded_at": int(time.time())},
                        wheres=[WhereClause(column="seeder", value=name)],
                    ),
                )
        except _ClaimFailed as exc:
            if await self.__isRecorded(connection, name):
                return False
            events.started(name)
            events.failed(name, time.perf_counter() - started_at)
            raise exc.error from exc
        except Exception:
            if started:
                events.failed(name, time.perf_counter() - started_at)
            raise

        events.succeeded(name, time.perf_counter() - started_at)
        return True

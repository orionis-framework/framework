import time
from heapq import nlargest
from typing import TYPE_CHECKING, Any
from orionis.database.contracts.connection import IConnection
from orionis.database.contracts.connection_manager import IConnectionManager
from orionis.database.contracts.migration import Migration
from orionis.database.contracts.migrator import IMigrator
from orionis.database.exceptions import MigrationNotFoundException
from orionis.database.migrations.context import migration_connection_scope
from orionis.database.migrations.events import NO_EVENTS, MigrationEvents
from orionis.foundation.contracts.application import IApplication
from orionis.introspection.modules.inspector import ModuleInspector
from orionis.introspection.modules.reflection import ReflectionModule
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import BigInteger, Integer, String

if TYPE_CHECKING:
    from pathlib import Path

# Name of the table used to track already-applied migrations.
_MIGRATIONS_TABLE: str = "migrations"

def _build_migrations_table(table: str) -> TableDefinition:
    """
    Build the table definition for the migrations tracking table.

    Parameters
    ----------
    table : str
        Logical table name for tracked migrations.

    Returns
    -------
    TableDefinition
        Definition with ``id`` (primary key), ``migration`` (unique
        name), ``batch`` and ``migrated_at`` (epoch seconds) columns.
    """
    # Create primary key column with auto-increment.
    id_column: ColumnDefinition = Integer()
    id_column = id_column.primary().autoIncrement()
    id_column = id_column.comment("Primary key for migrations table.")
    id_column.name = "id"

    migration_column: ColumnDefinition = String(255)
    migration_column = migration_column.unique()
    migration_column = migration_column.comment("Name of the migration file.")
    migration_column.name = "migration"

    batch_column: ColumnDefinition = Integer()
    batch_column = batch_column.comment("Batch number of the migration.")
    batch_column.name = "batch"

    migrated_at_column: ColumnDefinition = BigInteger()
    migrated_at_column = migrated_at_column.comment("Timestamp in epoch seconds.")
    migrated_at_column.name = "migrated_at"

    return TableDefinition(
        name=table,
        columns={
            "id": id_column,
            "migration": migration_column,
            "batch": batch_column,
            "migrated_at": migrated_at_column,
        },
        primary_key="id",
    )

# Define the columns used to track applied migrations.
_MIGRATIONS_TABLE_DEFINITION: TableDefinition = _build_migrations_table(
    _MIGRATIONS_TABLE,
)

class Migrator(IMigrator):
    """
    Runner applying and reverting the application migrations.

    Migrations are discovered under ``database/migrations`` and applied
    in filename order, which is chronological because filenames carry a
    zero-padded sequential prefix. Each migration runs inside its own
    transaction together with its tracking record, so a failure never
    leaves the tracking table claiming a migration that did not fully
    apply.
    """

    # ruff: noqa: TC001

    __slots__ = ("__app", "__conn_manager", "__discovered_cache")

    def __init__(
        self,
        app: IApplication,
        conn_manager: IConnectionManager,
    ) -> None:
        """
        Initialize the migrator.

        Parameters
        ----------
        app : IApplication
            Application instance used to resolve the migrations directory.
        conn_manager : IConnectionManager
            Connection manager used to resolve the database connection.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.__app = app
        self.__conn_manager = conn_manager
        self.__discovered_cache: dict[str, type[Migration]] | None = None

    # ── Public operations ───────────────────────────────────────────────────

    async def migrate(
        self,
        *,
        connection: str | None = None,
        events: MigrationEvents | None = None,
    ) -> list[str]:
        """
        Apply every migration that has not been run yet.

        Parameters
        ----------
        connection : str or None, optional
            Named connection to migrate, or ``None`` for the default one.
        events : MigrationEvents or None, optional
            Progress callbacks reported for each migration.

        Returns
        -------
        list of str
            Names of the migrations applied, in the order they ran.

        Raises
        ------
        Exception
            Any exception raised by a migration ``up`` method aborts the
            run and propagates to the caller.
        """
        target = self.__connection(connection)
        await self.__ensureMigrationsTable(target)

        ran = await self.__getRan(target)
        ran_names = {row["migration"] for row in ran}
        pending = [
            (name, cls)
            for name, cls in self.__discover().items()
            if name not in ran_names
        ]
        if not pending:
            return []

        batch = self.__nextBatch(ran)
        reporter = events or NO_EVENTS
        applied: list[str] = []
        for name, migration_cls in pending:
            await self.__runStep(target, name, migration_cls, batch, reporter)
            applied.append(name)
        return applied

    async def rollback(
        self,
        steps: int = 1,
        *,
        connection: str | None = None,
        events: MigrationEvents | None = None,
    ) -> list[str]:
        """
        Revert the most recently applied migration batches.

        Parameters
        ----------
        steps : int, optional
            Number of batches to roll back, starting from the most
            recent one. Defaults to ``1``.
        connection : str or None, optional
            Named connection to roll back, or ``None`` for the default.
        events : MigrationEvents or None, optional
            Progress callbacks reported for each migration.

        Returns
        -------
        list of str
            Names of the migrations reverted, most recent first.

        Raises
        ------
        ValueError
            If ``steps`` is not a positive integer.
        MigrationNotFoundException
            If a recorded migration has no matching migration file.
        """
        if not isinstance(steps, int) or isinstance(steps, bool) or steps < 1:
            error_msg = "The 'steps' argument must be a positive integer."
            raise ValueError(error_msg)
        return await self.__revert(steps, connection, events)

    async def reset(
        self,
        *,
        connection: str | None = None,
        events: MigrationEvents | None = None,
    ) -> list[str]:
        """
        Revert every migration recorded on the connection.

        Parameters
        ----------
        connection : str or None, optional
            Named connection to reset, or ``None`` for the default one.
        events : MigrationEvents or None, optional
            Progress callbacks reported for each migration.

        Returns
        -------
        list of str
            Names of the migrations reverted, most recent first.

        Raises
        ------
        MigrationNotFoundException
            If a recorded migration has no matching migration file.
        """
        return await self.__revert(None, connection, events)

    async def refresh(
        self,
        steps: int | None = None,
        *,
        connection: str | None = None,
        events: MigrationEvents | None = None,
    ) -> list[str]:
        """
        Roll back migrations and immediately apply them again.

        Parameters
        ----------
        steps : int or None, optional
            Number of batches to roll back first; ``None`` rolls back
            every recorded migration.
        connection : str or None, optional
            Named connection to refresh, or ``None`` for the default.
        events : MigrationEvents or None, optional
            Progress callbacks reported for each migration.

        Returns
        -------
        list of str
            Names of the migrations re-applied, in the order they ran.

        Raises
        ------
        ValueError
            If ``steps`` is not a positive integer.
        """
        if steps is None:
            await self.reset(connection=connection, events=events)
        else:
            await self.rollback(steps, connection=connection, events=events)
        return await self.migrate(connection=connection, events=events)

    async def fresh(
        self,
        *,
        connection: str | None = None,
        events: MigrationEvents | None = None,
    ) -> list[str]:
        """
        Drop the tracking table and apply every migration from scratch.

        Unlike :meth:`refresh`, the tracking table itself is dropped, so
        the whole history is rebuilt as a single first batch.

        Parameters
        ----------
        connection : str or None, optional
            Named connection to rebuild, or ``None`` for the default.
        events : MigrationEvents or None, optional
            Progress callbacks reported for each migration.

        Returns
        -------
        list of str
            Names of the migrations applied, in the order they ran.
        """
        target = self.__connection(connection)
        await self.reset(connection=connection, events=events)
        await target.dropTable(_MIGRATIONS_TABLE)
        return await self.migrate(connection=connection, events=events)

    async def status(
        self,
        *,
        connection: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Report which migrations are applied and which are pending.

        Parameters
        ----------
        connection : str or None, optional
            Named connection to inspect, or ``None`` for the default.

        Returns
        -------
        list of dict
            One entry per discovered migration with ``migration``,
            ``ran`` and ``batch`` keys, in chronological order.
        """
        target = self.__connection(connection)
        await self.__ensureMigrationsTable(target)
        batches = {
            row["migration"]: row["batch"] for row in await self.__getRan(target)
        }
        return [
            {
                "migration": name,
                "ran": name in batches,
                "batch": batches.get(name),
            }
            for name in self.__discover()
        ]

    # ── Internal orchestration ──────────────────────────────────────────────

    async def __revert(
        self,
        steps: int | None,
        connection: str | None,
        events: MigrationEvents | None,
    ) -> list[str]:
        """
        Roll back the recorded migrations of the selected batches.

        Parameters
        ----------
        steps : int or None
            Number of most recent batches to revert; ``None`` reverts
            every recorded migration.
        connection : str or None
            Named connection to roll back, or ``None`` for the default.
        events : MigrationEvents or None
            Progress callbacks reported for each migration.

        Returns
        -------
        list of str
            Names of the migrations reverted, most recent first.

        Raises
        ------
        MigrationNotFoundException
            If a recorded migration has no matching migration file.
        """
        target = self.__connection(connection)
        await self.__ensureMigrationsTable(target)

        ran = await self.__getRan(target)
        if not ran:
            return []

        rows = self.__selectBatches(ran, steps)
        discovered = self.__discover()
        # Resolve all recorded classes before changing the schema.
        for row in rows:
            name = row["migration"]
            if name not in discovered:
                error_msg = f"Migration class for '{name}' could not be found."
                raise MigrationNotFoundException(error_msg)

        reporter = events or NO_EVENTS
        reverted: list[str] = []
        for row in rows:
            name = row["migration"]
            await self.__runStep(target, name, discovered[name], None, reporter)
            reverted.append(name)
        return reverted

    @staticmethod
    def __selectBatches(
        ran: list[dict[str, Any]],
        steps: int | None,
    ) -> list[dict[str, Any]]:
        """
        Pick the recorded rows belonging to the batches being reverted.

        Parameters
        ----------
        ran : list of dict
            Every recorded migration in ascending ``id`` order.
        steps : int or None
            Number of most recent batches to select; ``None`` selects
            all of them.

        Returns
        -------
        list of dict
            Selected rows, most recently applied first.
        """
        # Read the recorded application order from newest to oldest.
        if steps is None:
            return list(reversed(ran))
        targets = set(nlargest(steps, {row["batch"] for row in ran}))
        return [row for row in reversed(ran) if row["batch"] in targets]

    async def __runStep(
        self,
        connection: IConnection,
        name: str,
        migration_cls: type[Migration],
        batch: int | None,
        events: MigrationEvents,
    ) -> None:
        """
        Run one migration and its tracking write atomically.

        Parameters
        ----------
        connection : IConnection
            Connection the migration runs against.
        name : str
            Migration name.
        migration_cls : type of Migration
            Migration class to instantiate and run.
        batch : int or None
            Batch number to record when applying; ``None`` reverts the
            migration instead.
        events : MigrationEvents
            Progress callbacks reported for this migration.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        Exception
            Any exception raised by the migration propagates after the
            transaction is rolled back and the failure is reported.
        """
        events.started(name)
        started_at = time.perf_counter()
        try:
            # The schema change and its tracking record share one
            # transaction, so a failure can never record a migration
            # that did not fully apply on engines with transactional DDL.
            with migration_connection_scope(connection):
                async with connection.transaction():
                    instance = migration_cls()
                    if batch is None:
                        await instance.down()
                        await self.__deleteRecord(connection, name)
                    else:
                        await instance.up()
                        await self.__insertRecord(connection, name, batch)
        except Exception:
            events.failed(name, time.perf_counter() - started_at)
            raise
        events.succeeded(name, time.perf_counter() - started_at)

    # ── Discovery ───────────────────────────────────────────────────────────

    def __connection(self, name: str | None) -> IConnection:
        """
        Resolve the connection migrations run against.

        Parameters
        ----------
        name : str or None
            Named connection, or ``None`` for the default one.

        Returns
        -------
        IConnection
            Connection bound to its configuration.

        Raises
        ------
        ConnectionNotFoundException
            If the connection is not declared in the configuration.
        """
        return self.__conn_manager.connection(name)

    def __migrationsPath(self) -> Path:
        """
        Return the directory holding migration files.

        Returns
        -------
        Path
            Absolute path to the ``database_migrations`` directory under
            the application base path.
        """
        return self.__app.path("database_migrations")

    def __discover(self) -> dict[str, type[Migration]]:
        """
        Discover migration classes defined under the migrations directory.

        The result is cached on the instance after the first call, since
        the migrations directory does not change during a process
        lifetime and discovery involves filesystem traversal, module
        imports, and reflection. Only classes defined in a migration
        module are eligible; package initializers and reexports are ignored.

        Returns
        -------
        dict of str to type
            Migration classes keyed by module file stem, ordered
            chronologically (filenames are zero-padded sequential ids).

        Raises
        ------
        ValueError
            If multiple classes share a persisted migration name.
        """
        # Reuse the previously discovered migrations, if any.
        if self.__discovered_cache is not None:
            return self.__discovered_cache

        migrations_path = self.__migrationsPath()
        if not migrations_path.is_dir():
            self.__discovered_cache = {}
            return self.__discovered_cache

        modules = ModuleInspector.discoverModules(
            base_path=self.__app.basePath,
            target_path=migrations_path,
        )

        found: dict[str, type[Migration]] = {}
        for module_name in modules:
            stem = module_name.rsplit(".", 1)[-1]
            if stem == "__init__":
                continue
            rf_module = ReflectionModule(module_name)
            for obj in rf_module.getClasses().values():
                if obj.__module__ != module_name or not issubclass(obj, Migration):
                    continue
                previous = found.get(stem)
                if previous is not None:
                    error_msg = (
                        f"Ambiguous migration '{stem}': "
                        f"{previous.__module__}.{previous.__name__} and "
                        f"{module_name}.{obj.__name__}."
                    )
                    raise ValueError(error_msg)
                found[stem] = obj

        self.__discovered_cache = dict(sorted(found.items()))
        return self.__discovered_cache

    # ── Tracking table ──────────────────────────────────────────────────────

    async def __ensureMigrationsTable(self, connection: IConnection) -> None:
        """
        Create the migrations tracking table if it does not already exist.

        Parameters
        ----------
        connection : IConnection
            Connection used to perform the schema operation.

        Returns
        -------
        None
            This method does not return a value.
        """
        await connection.createTable(_MIGRATIONS_TABLE_DEFINITION)

    async def __getRan(self, connection: IConnection) -> list[dict[str, Any]]:
        """
        Return every recorded migration, ordered by application order.

        Parameters
        ----------
        connection : IConnection
            Connection used to run the query.

        Returns
        -------
        list of dict
            Rows with ``id``, ``migration``, and ``batch`` keys.
        """
        return await connection.select(
            f"""
            SELECT
                id,
                migration,
                batch FROM {_MIGRATIONS_TABLE}
            ORDER BY id ASC
            """,
        )

    @staticmethod
    def __nextBatch(ran: list[dict[str, Any]]) -> int:
        """
        Compute the batch number to assign to a new migration run.

        Parameters
        ----------
        ran : list of dict
            Previously recorded migrations.

        Returns
        -------
        int
            ``1`` when nothing has run yet, otherwise the highest
            recorded batch plus one.
        """
        if not ran:
            return 1
        return max(row["batch"] for row in ran) + 1

    async def __insertRecord(
        self,
        connection: IConnection,
        name: str,
        batch: int,
    ) -> None:
        """
        Record a migration as applied.

        Parameters
        ----------
        connection : IConnection
            Connection used to run the statement.
        name : str
            Migration name to record.
        batch : int
            Batch number the migration belongs to.

        Returns
        -------
        None
            This method does not return a value.
        """
        await connection.execute(
            f"""
            INSERT INTO {_MIGRATIONS_TABLE} (
                migration,
                batch,
                migrated_at
            ) VALUES (
                :migration,
                :batch,
                :migrated_at
            )
            """,
            {
                "migration": name,
                "batch": batch,
                "migrated_at": int(time.time()),
            },
        )

    async def __deleteRecord(self, connection: IConnection, name: str) -> None:
        """
        Remove a migration's tracking record.

        Parameters
        ----------
        connection : IConnection
            Connection used to run the statement.
        name : str
            Migration name to remove.

        Returns
        -------
        None
            This method does not return a value.
        """
        await connection.execute(
            f"DELETE FROM {_MIGRATIONS_TABLE} WHERE migration = :migration",
            {"migration": name},
        )

import sys
from dataclasses import dataclass
from itertools import chain
from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.base.command import BaseCommand
from orionis.console.commands.db._inspection import DatabaseInspector
from orionis.console.enums.actions import ArgumentAction
from orionis.database.contracts.connection_manager import IConnectionManager

@dataclass(frozen=True, slots=True)
class WipeResult:
    """Store counts for objects removed by a database wipe."""

    tables: int
    views: int
    types: int

class DatabaseWiper:
    """Remove user-defined objects from a selected connection."""

    __slots__ = ("_inspector",)

    def __init__(self, inspector: DatabaseInspector) -> None:
        """
        Keep the inspector used for the wipe.

        Parameters
        ----------
        inspector : DatabaseInspector
            Inspector for the target database connection.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        self._inspector = inspector

    async def wipe(self) -> WipeResult:
        """
        Remove all discoverable user objects from the selected database.

        Returns
        -------
        WipeResult
            Number of tables, views, and types found before removal.
        """
        inspector = self._inspector
        views = await inspector.listViews()
        materialized_views = await inspector.listMaterializedViews()
        tables = await inspector.listTables()
        types = await inspector.listTypes()
        domains = await inspector.listDomains()
        driver = inspector.driver
        connection = inspector.connection
        if driver in {"pgsql", "sqlserver"}:
            # The shared inspector reports schema and object as one string.
            # More than one separator is ambiguous and could target another
            # database on SQL Server. Refuse before the first DDL statement.
            names = chain(views, materialized_views, tables, types, domains)
            if any(name.count(".") != 1 for name in names):
                error_msg = (
                    "Cannot wipe a schema-qualified object whose name "
                    "contains a period."
                )
                raise ValueError(error_msg)

        if driver == "sqlite":
            # Deferring checks until commit allows even cyclic foreign keys to
            # be removed after every user table has been dropped.
            async with connection.transaction():
                await connection.statement("PRAGMA defer_foreign_keys = ON")
                await self._dropViews(views)
                await self._dropTables(tables)
        elif driver == "mysql":
            await self._wipeMysql(views, tables)
        elif driver == "pgsql":
            async with connection.transaction():
                await self._dropMaterializedViews(materialized_views)
                await self._dropViews(views, cascade=True)
                await self._dropTables(tables, cascade=True)
                await self._dropDomains(domains)
                await self._dropTypes(types, cascade=True)
        elif driver == "sqlserver":
            types = await self._orderSqlserverTypes(types)
            async with connection.transaction():
                await self._dropSqlserverViews(views)
                await self._disableSqlserverTemporalTables(tables)
                await self._dropSqlserverForeignKeys(tables)
                await self._dropTables(tables)
                await self._dropTypes(types)
        elif driver == "oracle":
            # Oracle DDL commits implicitly and cannot be rolled back as a
            # group. Check type dependencies before the first destructive DDL.
            types = await self._prepareOracleTypes(
                tables, views, materialized_views, types,
            )
            await self._dropMaterializedViews(materialized_views)
            # A materialized view built on a pre-existing table leaves that
            # table in place; the catalog exposes it after the view is gone.
            tables = await inspector.listTables()
            await self._dropViews(views)
            await self._dropTables(tables)
            await self._dropTypes(types)
        else:
            error_msg = f"Database wipe is unsupported for driver '{driver}'."
            raise ValueError(error_msg)

        return WipeResult(
            len(tables),
            len(views) + len(materialized_views),
            len(types) + len(domains),
        )

    async def _wipeMysql(self, views: list[str], tables: list[str]) -> None:
        """
        Temporarily disable foreign-key checks while removing MySQL objects.

        Parameters
        ----------
        views : list[str]
            Names of views to drop.
        tables : list[str]
            Names of tables to drop.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        connection = self._inspector.connection
        # MySQL DDL commits implicitly, but the framework transaction keeps
        # the same physical connection checked out until checks are restored.
        async with connection.transaction():
            previous = await connection.select(
                """
                SELECT @@SESSION.foreign_key_checks AS enabled
                """,
            )
            if not previous:
                error_msg = "Unable to read MySQL foreign-key check state."
                raise RuntimeError(error_msg)
            enabled = int(previous[0]["enabled"])
            if enabled not in (0, 1):
                error_msg = "Invalid MySQL foreign-key check state."
                raise RuntimeError(error_msg)
            await connection.statement("SET FOREIGN_KEY_CHECKS = 0")
            try:
                await self._dropViews(views)
                await self._dropTables(tables)
            finally:
                await connection.statement(f"SET FOREIGN_KEY_CHECKS = {enabled}")

    async def _dropMaterializedViews(self, views: list[str]) -> None:
        """
        Drop materialized views before regular views and tables.

        Parameters
        ----------
        views : list[str]
            Materialized view names to remove.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        for name in views:
            quoted = self._inspector.quoteIdentifier(name)
            sql = (
                f"DROP MATERIALIZED VIEW {quoted}"
                if self._inspector.driver == "oracle"
                else f"DROP MATERIALIZED VIEW IF EXISTS {quoted} CASCADE"
            )
            await self._inspector.connection.statement(sql)

    async def _dropDomains(self, domains: list[str]) -> None:
        """
        Drop PostgreSQL domains.

        Parameters
        ----------
        domains : list[str]
            Domain names to remove.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        for name in domains:
            quoted = self._inspector.quoteIdentifier(name)
            await self._inspector.connection.statement(
                f"DROP DOMAIN IF EXISTS {quoted} CASCADE",
            )

    async def _dropViews(
        self,
        views: list[str],
        *,
        cascade: bool = False,
    ) -> None:
        """
        Drop listed views.

        Parameters
        ----------
        views : list[str]
            View names to remove.
        cascade : bool, optional
            Whether to cascade dependent objects when supported by the database.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        driver = self._inspector.driver
        for name in views:
            quoted = self._inspector.quoteIdentifier(name)
            if driver == "oracle":
                sql = f"DROP VIEW {quoted}"
            else:
                sql = f"DROP VIEW IF EXISTS {quoted}"
            if cascade:
                sql += " CASCADE" # NOSONAR
            await self._inspector.connection.statement(sql)

    async def _dropTables(
        self,
        tables: list[str],
        *,
        cascade: bool = False,
    ) -> None:
        """
        Drop listed tables.

        Parameters
        ----------
        tables : list[str]
            Table names to remove.
        cascade : bool, optional
            Whether to cascade dependent objects when supported by the database.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        driver = self._inspector.driver
        for name in tables:
            quoted = self._inspector.quoteIdentifier(name)
            if driver == "oracle":
                sql = f"DROP TABLE {quoted} CASCADE CONSTRAINTS PURGE"
            else:
                sql = f"DROP TABLE IF EXISTS {quoted}"
            if cascade:
                sql += " CASCADE"
            await self._inspector.connection.statement(sql)

    async def _dropTypes(
        self,
        types: list[str],
        *,
        cascade: bool = False,
    ) -> None:
        """
        Drop listed schema types.

        Parameters
        ----------
        types : list[str]
            Type names to remove.
        cascade : bool, optional
            Whether to cascade dependent objects when supported by the database.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        driver = self._inspector.driver
        for name in types:
            quoted = self._inspector.quoteIdentifier(name)
            if driver == "oracle":
                sql = f"DROP TYPE {quoted}"
            else:
                sql = f"DROP TYPE IF EXISTS {quoted}"
            if cascade:
                sql += " CASCADE"
            await self._inspector.connection.statement(sql)

    async def _orderSqlserverTypes(self, types: list[str]) -> list[str]:
        """
        Order SQL Server user-defined types before their dependencies.

        Parameters
        ----------
        types : list[str]
            User-defined type names to remove.

        Returns
        -------
        list[str]
            Type names in a safe drop order.
        """
        if not types:
            return []
        rows = await self._inspector.connection.select(
            """
            SELECT
                SCHEMA_NAME(tt.schema_id) AS dependent_schema,
                tt.name AS dependent_type,
                SCHEMA_NAME(t.schema_id) AS referenced_schema,
                t.name AS referenced_type
            FROM sys.table_types AS tt
            JOIN sys.columns AS c ON c.object_id = tt.type_table_object_id
            JOIN sys.types AS t ON t.user_type_id = c.user_type_id
            WHERE t.is_user_defined = 1
            """,
        )
        selected = set(types)
        dependencies: dict[str, set[str]] = {name: set() for name in types}
        for row in rows:
            dependent = f"{row['dependent_schema']}.{row['dependent_type']}"
            referenced = f"{row['referenced_schema']}.{row['referenced_type']}"
            if dependent in selected and referenced in selected:
                dependencies[dependent].add(referenced)
        return self._dependencyOrder(
            dependencies,
            "SQL Server user-defined type dependencies contain a cycle.",
        )

    async def _prepareOracleTypes(
        self,
        tables: list[str],
        views: list[str],
        materialized_views: list[str],
        types: list[str],
    ) -> list[str]:
        """
        Validate and order Oracle types for safe deletion.

        Parameters
        ----------
        tables : list[str]
            Tables included in the wipe scope.
        views : list[str]
            Views included in the wipe scope.
        materialized_views : list[str]
            Materialized views included in the wipe scope.
        types : list[str]
            Type names to validate and order.

        Returns
        -------
        list[str]
            Ordered type names safe to drop.
        """
        if not types:
            return []
        rows = await self._inspector.connection.select(
            """
            SELECT
                owner,
                name,
                type AS object_type,
                referenced_owner,
                referenced_name
            FROM all_dependencies
            WHERE referenced_owner = USER
                AND referenced_type = 'TYPE'
            """,
        )
        selected_types = set(types)
        selected_tables = set(tables)
        selected_views = set(views)
        selected_materialized_views = set(materialized_views)
        if selected_materialized_views:
            containers = await self._inspector.connection.select(
                """
                SELECT mview_name, container_name
                FROM user_mviews
                """,
            )
            selected_tables.update(
                str(row["container_name"])
                for row in containers
                if row["mview_name"] in selected_materialized_views
                and row["container_name"] is not None
            )
        allowed_dependents = {
            "TYPE BODY": selected_types,
            "TABLE": selected_tables | selected_materialized_views,
            "VIEW": selected_views,
            "MATERIALIZED VIEW": selected_materialized_views,
        }
        dependencies: dict[str, set[str]] = {name: set() for name in types}
        for row in rows:
            referenced = str(row["referenced_name"])
            if referenced not in selected_types:
                continue
            dependent = str(row["name"])
            kind = str(row["object_type"])
            own_schema = row["owner"] == row["referenced_owner"]
            if own_schema and kind == "TYPE" and dependent in selected_types:
                if dependent != referenced:
                    dependencies[dependent].add(referenced)
            elif own_schema and dependent in allowed_dependents.get(kind, ()):
                continue
            else:
                error_msg = (
                    f"Cannot wipe Oracle type '{referenced}': dependent "
                    f"{kind.lower()} '{dependent}' is outside the wipe scope."
                )
                raise RuntimeError(error_msg)

        return self._dependencyOrder(
            dependencies,
            "Cannot wipe Oracle types with circular dependencies without FORCE.",
        )

    @staticmethod
    def _dependencyOrder( # NOSONAR
        dependencies: dict[str, set[str]],
        cycle_error: str,
    ) -> list[str]:
        """
        Order objects so dependencies are removed after their dependents.

        Parameters
        ----------
        dependencies : dict[str, set[str]]
            Mapping of each object to the objects it depends on.
        cycle_error : str
            Error message to raise when a dependency cycle is detected.

        Returns
        -------
        list[str]
            Objects ordered for safe removal.
        """
        dependent_counts = dict.fromkeys(dependencies, 0)
        for referenced_types in dependencies.values():
            for referenced in referenced_types:
                if referenced in dependencies:
                    dependent_counts[referenced] += 1
        ready = sorted(
            name for name, count in dependent_counts.items() if count == 0
        )
        ordered: list[str] = []
        while ready:
            ordered.extend(ready)
            next_ready: list[str] = []
            for name in ready:
                for referenced in dependencies[name]:
                    if referenced in dependencies:
                        dependent_counts[referenced] -= 1
                        if dependent_counts[referenced] == 0:
                            next_ready.append(referenced)
            ready = sorted(next_ready)
        if len(ordered) != len(dependencies):
            raise RuntimeError(cycle_error)
        return ordered

    async def _dropSqlserverViews(self, views: list[str]) -> None:
        """
        Drop SQL Server views in dependency-safe order.

        Parameters
        ----------
        views : list[str]
            View names to remove.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        if not views:
            return
        rows = await self._inspector.connection.select(
            """
            SELECT
                s.name AS schema_name,
                v.name AS view_name,
                rs.name AS referenced_schema,
                rv.name AS referenced_view
            FROM sys.sql_expression_dependencies AS d
            JOIN sys.views AS v ON v.object_id = d.referencing_id
            JOIN sys.schemas AS s ON s.schema_id = v.schema_id
            JOIN sys.views AS rv ON rv.object_id = d.referenced_id
            JOIN sys.schemas AS rs ON rs.schema_id = rv.schema_id
            """,
        )
        selected = set(views)
        dependencies: dict[str, set[str]] = {name: set() for name in views}
        for row in rows:
            referencing = f"{row['schema_name']}.{row['view_name']}"
            referenced = f"{row['referenced_schema']}.{row['referenced_view']}"
            if referencing in selected and referenced in selected:
                dependencies[referencing].add(referenced)
        await self._dropViews(self._dependencyOrder(
            dependencies,
            "SQL Server view dependencies contain a cycle.",
        ))

    async def _disableSqlserverTemporalTables(self, tables: list[str]) -> None:
        """
        Disable system versioning for temporal tables before dropping them.

        Parameters
        ----------
        tables : list[str]
            Table names to prepare.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        if not tables:
            return
        rows = await self._inspector.connection.select(
            """
            SELECT s.name AS schema_name, t.name AS table_name
            FROM sys.tables AS t
            JOIN sys.schemas AS s ON s.schema_id = t.schema_id
            WHERE t.temporal_type = 2
                AND t.is_ms_shipped = 0
            """,
        )
        selected = set(tables)
        for row in rows:
            name = f"{row['schema_name']}.{row['table_name']}"
            if name in selected:
                quoted = self._inspector.quoteIdentifier(name)
                await self._inspector.connection.statement(
                    f"ALTER TABLE {quoted} SET (SYSTEM_VERSIONING = OFF)",
                )

    async def _dropSqlserverForeignKeys(self, tables: list[str]) -> None:
        """
        Remove foreign keys before dropping SQL Server tables.

        Parameters
        ----------
        tables : list[str]
            Table names whose keys are removed.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        if not tables:
            return
        rows = await self._inspector.connection.select(
            """
            SELECT
                s.name AS schema_name,
                t.name AS table_name,
                fk.name AS constraint_name
            FROM sys.foreign_keys AS fk
            JOIN sys.tables AS t ON t.object_id = fk.parent_object_id
            JOIN sys.schemas AS s ON s.schema_id = t.schema_id
            WHERE t.is_ms_shipped = 0
            """,
        )
        selected = set(tables)
        for row in rows:
            name = f"{row['schema_name']}.{row['table_name']}"
            if name in selected:
                table = self._inspector.quoteIdentifier(name)
                constraint = self._inspector.quoteIdentifier(
                    row["constraint_name"], qualified=False,
                )
                await self._inspector.connection.statement(
                    f"ALTER TABLE {table} DROP CONSTRAINT {constraint}",
                )

class DbWipeCommand(BaseCommand):
    """Wipe a database connection after confirmation."""

    # ruff: noqa: TC001

    signature: str = "db:wipe"
    description: str = "Drop all user tables, views, and types in a database."
    arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags=["--database", "-d"],
            type_=str,
            required=False,
            help="Named connection to wipe; defaults to the default one.",
            dest="database",
        ),
        Argument(
            name_or_flags="--force",
            action=ArgumentAction.STORE_TRUE,
            default=False,
            help="Wipe without an interactive confirmation.",
        ),
    ]

    async def handle(self, conn_manager: IConnectionManager) -> int:
        """
        Confirm and wipe the selected database connection.

        Parameters
        ----------
        conn_manager : IConnectionManager
            Manager resolving the requested database connection.

        Returns
        -------
        int
            Exit status code: ``0`` on success or cancellation, and ``1`` when
            confirmation is required in a non-interactive session.
        """
        name = self.getArgument("database") or conn_manager.getDefaultName()
        if not self.getArgument("force", default=False):
            if not sys.stdin.isatty():
                self.error(
                    "db:wipe requires --force when no terminal is attached.",
                )
                return 1
            if not self.confirm(
                f"Drop all user tables, views, and types on '{name}'?",
                default=False,
            ):
                self.info("Database wipe cancelled.")
                return 0

        inspector = DatabaseInspector(conn_manager, name)
        result = await DatabaseWiper(inspector).wipe()
        self.success(
            f"Wiped '{name}': {result.tables} table(s), "
            f"{result.views} view(s), {result.types} type(s).",
        )
        return 0

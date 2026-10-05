from __future__ import annotations
from typing import TYPE_CHECKING, Any
from sqlalchemy.exc import SQLAlchemyError
from orionis.database.dialect import resolve_driver
from orionis.database.exceptions import QueryException

if TYPE_CHECKING:
    from orionis.database.contracts.connection import IConnection
    from orionis.database.contracts.connection_manager import IConnectionManager

class DatabaseInspector:
    """Inspect user objects without opening a separate database engine."""

    __slots__ = ("config", "connection", "driver", "name")

    def __init__(
        self,
        manager: IConnectionManager,
        name: str | None = None,
    ) -> None:
        """
        Bind inspection to a named connection.

        Parameters
        ----------
        manager : IConnectionManager
            Manager that resolves database configurations and connections.
        name : str | None, optional
            Named connection, or the configured default.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        self.name = name or manager.getDefaultName()
        self.config = manager.configFor(self.name)
        self.driver = resolve_driver(self.config)
        self.connection: IConnection = manager.connection(self.name)

    def quoteIdentifier(self, name: str, *, qualified: bool = True) -> str:
        """
        Quote a catalog identifier using the selected SQL dialect.

        Parameters
        ----------
        name : str
            Identifier returned by the database catalog.
        qualified : bool, optional
            Whether to split a schema-qualified identifier.

        Returns
        -------
        str
            Identifier escaped for use in a SQL statement.

        Raises
        ------
        ValueError
            If an identifier or one of its components is empty.
        """
        driver = self.driver
        parts = (
            name.split(".")
            if qualified and driver in {"pgsql", "sqlserver"}
            else (name,)
        )
        if "" in parts:
            msg = "A database object name cannot be empty."
            raise ValueError(msg)
        if driver == "mysql":
            return ".".join(f"`{part.replace('`', '``')}`" for part in parts)
        if driver == "sqlserver":
            return ".".join(f"[{part.replace(']', ']]')}]" for part in parts)
        return ".".join('"' + part.replace('"', '""') + '"' for part in parts)

    async def listTables(self) -> list[str]:
        """
        List non-system tables visible on the selected database.

        Returns
        -------
        list[str]
            Table names in catalog order.
        """
        if self.driver == "sqlite":
            rows = await self.connection.select(
                """
                SELECT name
                FROM sqlite_schema
                WHERE type = 'table' AND name NOT GLOB 'sqlite_*'
                ORDER BY name
                """,
            )
        elif self.driver == "pgsql":
            rows = await self.connection.select(
                """
                SELECT n.nspname || '.' || c.relname AS name
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind IN ('r', 'p')
                  AND NOT c.relispartition
                  AND LEFT(n.nspname, 3) <> 'pg_'
                  AND n.nspname <> 'information_schema'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM pg_depend d
                      WHERE d.classid = 'pg_class'::regclass
                        AND d.objid = c.oid
                        AND d.deptype = 'e'
                  )
                ORDER BY name
                """,
            )
        elif self.driver == "mysql":
            rows = await self.connection.select(
                """
                SELECT table_name AS name
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """,
            )
        elif self.driver == "sqlserver":
            rows = await self.connection.select(
                """
                SELECT SCHEMA_NAME(schema_id) + '.' + name AS name
                FROM sys.tables
                WHERE is_ms_shipped = 0
                ORDER BY name
                """,
            )
        else:
            rows = await self.connection.select(
                """
                SELECT t.table_name AS name
                FROM user_tables t
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM user_mviews m
                    WHERE m.container_name = t.table_name
                )
                ORDER BY t.table_name
                """,
            )
        return [str(row["name"]) for row in rows]

    async def listViews(self) -> list[str]:
        """
        List user views visible on the selected database.

        Returns
        -------
        list[str]
            View names in catalog order.
        """
        if self.driver == "sqlite":
            rows = await self.connection.select(
                """
                SELECT name
                FROM sqlite_schema
                WHERE type = 'view' AND name NOT GLOB 'sqlite_*'
                ORDER BY name
                """,
            )
        elif self.driver == "pgsql":
            rows = await self.connection.select(
                """
                SELECT n.nspname || '.' || c.relname AS name
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind = 'v'
                  AND LEFT(n.nspname, 3) <> 'pg_'
                  AND n.nspname <> 'information_schema'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM pg_depend d
                      WHERE d.classid = 'pg_class'::regclass
                        AND d.objid = c.oid
                        AND d.deptype = 'e'
                  )
                ORDER BY name
                """,
            )
        elif self.driver == "mysql":
            rows = await self.connection.select(
                """
                SELECT table_name AS name
                FROM information_schema.views
                WHERE table_schema = DATABASE()
                ORDER BY table_name
                """,
            )
        elif self.driver == "sqlserver":
            rows = await self.connection.select(
                """
                SELECT SCHEMA_NAME(schema_id) + '.' + name AS name
                FROM sys.views
                WHERE is_ms_shipped = 0
                ORDER BY name
                """,
            )
        else:
            rows = await self.connection.select(
                """
                SELECT view_name AS name
                FROM user_views
                ORDER BY view_name
                """,
            )
        return [str(row["name"]) for row in rows]

    async def listMaterializedViews(self) -> list[str]:
        """
        List materialized views outside system schemas.

        Returns
        -------
        list[str]
            Materialized view names in catalog order.
        """
        if self.driver == "pgsql":
            rows = await self.connection.select(
                """
                SELECT n.nspname || '.' || c.relname AS name
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind = 'm'
                  AND LEFT(n.nspname, 3) <> 'pg_'
                  AND n.nspname <> 'information_schema'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM pg_depend d
                      WHERE d.classid = 'pg_class'::regclass
                        AND d.objid = c.oid
                        AND d.deptype = 'e'
                  )
                ORDER BY name
                """,
            )
        elif self.driver == "oracle":
            rows = await self.connection.select(
                """
                SELECT mview_name AS name
                FROM user_mviews
                ORDER BY mview_name
                """,
            )
        else:
            return []
        return [str(row["name"]) for row in rows]

    async def viewCounts(self) -> tuple[int, int]:
        """
        Count ordinary and materialized views without loading their names.

        Returns
        -------
        tuple[int, int]
            Ordinary view count followed by materialized view count.
        """
        driver = self.driver
        if driver == "sqlite":
            rows = await self.connection.select(
                """
                SELECT COUNT(*) AS view_count
                FROM sqlite_schema
                WHERE type = 'view' AND name NOT GLOB 'sqlite_*'
                """,
            )
        elif driver == "pgsql":
            rows = await self.connection.select(
                """
                SELECT c.relkind AS kind, COUNT(*) AS object_count
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind IN ('v', 'm')
                  AND LEFT(n.nspname, 3) <> 'pg_'
                  AND n.nspname <> 'information_schema'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM pg_depend d
                      WHERE d.classid = 'pg_class'::regclass
                        AND d.objid = c.oid
                        AND d.deptype = 'e'
                  )
                GROUP BY c.relkind
                """,
            )
            counts = {row["kind"]: int(row["object_count"]) for row in rows}
            return counts.get("v", 0), counts.get("m", 0)
        elif driver == "mysql":
            rows = await self.connection.select(
                """
                SELECT COUNT(*) AS view_count
                FROM information_schema.views
                WHERE table_schema = DATABASE()
                """,
            )
        elif driver == "sqlserver":
            rows = await self.connection.select(
                """
                SELECT COUNT(*) AS view_count
                FROM sys.views
                WHERE is_ms_shipped = 0
                """,
            )
        else:
            rows = await self.connection.select(
                """
                SELECT (SELECT COUNT(*) FROM user_views) AS view_count,
                       (SELECT COUNT(*) FROM user_mviews) AS materialized_count
                FROM dual
                """,
            )
            return int(rows[0]["view_count"]), int(rows[0]["materialized_count"])
        return int(rows[0]["view_count"]), 0

    async def listTypes(self) -> list[str]:
        """
        List user-defined types that may be removed by ``db:wipe``.

        Returns
        -------
        list[str]
            Removable type names in catalog order.
        """
        if self.driver == "pgsql":
            rows = await self.connection.select(
                """
                SELECT n.nspname || '.' || t.typname AS name
                FROM pg_type t
                JOIN pg_namespace n ON n.oid = t.typnamespace
                LEFT JOIN pg_class c ON c.reltype = t.oid
                LEFT JOIN pg_depend d
                  ON d.classid = 'pg_type'::regclass
                 AND d.objid = t.oid
                 AND d.deptype IN ('e', 'i')
                WHERE LEFT(n.nspname, 3) <> 'pg_'
                  AND n.nspname <> 'information_schema'
                  AND (
                      t.typtype IN ('e', 'r', 'm')
                      OR (t.typtype = 'b' AND t.typcategory <> 'A' AND t.typisdefined)
                      OR (t.typtype = 'c' AND c.relkind = 'c')
                  )
                  AND d.objid IS NULL
                ORDER BY name
                """,
            )
        elif self.driver == "sqlserver":
            rows = await self.connection.select(
                """
                SELECT SCHEMA_NAME(schema_id) + '.' + name AS name
                FROM sys.types
                WHERE is_user_defined = 1
                ORDER BY name
                """,
            )
        elif self.driver == "oracle":
            rows = await self.connection.select(
                """
                SELECT type_name AS name
                FROM user_types
                ORDER BY type_name
                """,
            )
        else:
            return []
        return [str(row["name"]) for row in rows]

    async def listDomains(self) -> list[str]:
        """
        List PostgreSQL domains, which require ``DROP DOMAIN``.

        Returns
        -------
        list[str]
            Domain names in catalog order, or an empty list for other drivers.
        """
        if self.driver != "pgsql":
            return []
        rows = await self.connection.select(
            """
            SELECT n.nspname || '.' || t.typname AS name
            FROM pg_type t
            JOIN pg_namespace n ON n.oid = t.typnamespace
            WHERE t.typtype = 'd'
              AND LEFT(n.nspname, 3) <> 'pg_'
              AND n.nspname <> 'information_schema'
              AND NOT EXISTS (
                  SELECT 1
                  FROM pg_depend d
                  WHERE d.classid = 'pg_type'::regclass
                    AND d.objid = t.oid
                    AND d.deptype = 'e'
              )
            ORDER BY name
            """,
        )
        return [str(row["name"]) for row in rows]

    async def databaseSize(self) -> int | None:
        """
        Return database size in bytes when available.

        Returns
        -------
        int | None
            Database size, or ``None`` when unavailable.
        """
        if self.driver == "sqlite":
            pages = await self.connection.select("PRAGMA page_count")
            page_size = await self.connection.select("PRAGMA page_size")
            return int(pages[0]["page_count"]) * int(page_size[0]["page_size"])
        if self.driver == "pgsql":
            rows = await self.connection.select(
                "SELECT pg_database_size(current_database()) AS bytes",
            )
        elif self.driver == "mysql":
            rows = await self.connection.select(
                """
                SELECT COALESCE(SUM(data_length + index_length), 0) AS bytes
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                """,
            )
        elif self.driver == "sqlserver":
            rows = await self.connection.select(
                """
                SELECT SUM(size) * 8192 AS bytes
                FROM sys.database_files
                """,
            )
        else:
            rows = await self.connection.select(
                """
                SELECT COALESCE(SUM(bytes), 0) AS bytes
                FROM user_segments
                """,
            )
        return int(rows[0]["bytes"]) if rows and rows[0]["bytes"] is not None else None

    async def connectionCount(self) -> int | None:
        """
        Return server session count if the driver exposes it.

        Returns
        -------
        int | None
            Open server sessions, or ``None`` when unavailable.
        """
        if self.driver == "sqlite":
            return None
        try:
            if self.driver == "pgsql":
                rows = await self.connection.select(
                    """
                    SELECT COUNT(*) AS count
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                    """,
                )
            elif self.driver == "mysql":
                rows = await self.connection.select(
                    """
                    SELECT COUNT(*) AS count
                    FROM information_schema.processlist
                    WHERE db = DATABASE()
                    """,
                )
            elif self.driver == "sqlserver":
                rows = await self.connection.select(
                    """
                    SELECT COUNT(*) AS count
                    FROM sys.dm_exec_sessions
                    WHERE database_id = DB_ID()
                    """,
                )
            else:
                rows = await self.connection.select(
                    """
                    SELECT COUNT(*) AS count
                    FROM v$session
                    WHERE username = USER
                    """,
                )
        except (QueryException, SQLAlchemyError):
            # Server activity views often require extra privileges.
            return None
        return int(rows[0]["count"]) if rows else None

    async def rowCount(self, name: str) -> int:
        """
        Count rows in a table returned by the catalog.

        Parameters
        ----------
        name : str
            Catalog table name to count.

        Returns
        -------
        int
            Exact row count.
        """
        quoted = self.quoteIdentifier(name)
        # Quoting is dialect-aware, and callers use catalog-sourced names.
        rows = await self.connection.select(
            f"SELECT COUNT(*) AS count FROM {quoted}",  # noqa: S608
        )
        return int(rows[0]["count"])

    async def tableSize(self, name: str) -> int | None:
        """
        Return physical table size in bytes when exposed by the driver.

        Parameters
        ----------
        name : str
            Catalog table name to inspect.

        Returns
        -------
        int | None
            Physical size, or ``None`` when unavailable.
        """
        if self.driver == "sqlite":
            try:
                rows = await self.connection.select(
                    """
                    SELECT SUM(pgsize) AS bytes
                    FROM dbstat
                    WHERE name = :name
                    """,
                    {"name": name},
                )
            except (QueryException, SQLAlchemyError):
                # SQLite's optional dbstat virtual table may be unavailable.
                return None
        elif self.driver == "pgsql":
            rows = await self.connection.select(
                "SELECT pg_total_relation_size(to_regclass(:name)) AS bytes",
                {"name": self.quoteIdentifier(name)},
            )
        elif self.driver == "mysql":
            rows = await self.connection.select(
                """
                SELECT data_length + index_length AS bytes
                FROM information_schema.tables
                WHERE table_schema = DATABASE() AND table_name = :name
                """,
                {"name": name},
            )
        elif self.driver == "sqlserver":
            rows = await self.connection.select(
                """
                SELECT SUM(a.total_pages) * 8192 AS bytes
                FROM sys.tables t
                JOIN sys.indexes i ON t.object_id = i.object_id
                JOIN sys.partitions p
                  ON i.object_id = p.object_id AND i.index_id = p.index_id
                JOIN sys.allocation_units a
                  ON (a.type IN (1, 3) AND a.container_id = p.hobt_id)
                  OR (a.type = 2 AND a.container_id = p.partition_id)
                WHERE t.object_id = OBJECT_ID(:name)
                """,
                {"name": self.quoteIdentifier(name)},
            )
        else:
            rows = await self.connection.select(
                """
                SELECT SUM(bytes) AS bytes
                FROM user_segments
                WHERE segment_name = :name
                """,
                {"name": name},
            )
        return int(rows[0]["bytes"]) if rows and rows[0]["bytes"] is not None else None

    async def tableSizes(self, tables: list[str]) -> dict[str, int]:
        """
        Read physical sizes for all catalog tables in one query.

        Parameters
        ----------
        tables : list[str]
            Table names returned by :meth:`listTables`.

        Returns
        -------
        dict[str, int]
            Sizes in bytes keyed by table name. Missing sizes are omitted.
        """
        if not tables:
            return {}
        driver = self.driver
        if driver == "sqlite":
            query = """
                SELECT name, SUM(pgsize) AS bytes
                FROM dbstat
                GROUP BY name
                """
        elif driver == "pgsql":
            query = """
                SELECT n.nspname || '.' || c.relname AS name,
                       pg_total_relation_size(c.oid) AS bytes
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind IN ('r', 'p')
                  AND NOT c.relispartition
                  AND LEFT(n.nspname, 3) <> 'pg_'
                  AND n.nspname <> 'information_schema'
                """
        elif driver == "mysql":
            query = """
                SELECT table_name AS name, data_length + index_length AS bytes
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                  AND table_type = 'BASE TABLE'
                """
        elif driver == "sqlserver":
            query = """
                SELECT SCHEMA_NAME(t.schema_id) + '.' + t.name AS name,
                       SUM(a.total_pages) * 8192 AS bytes
                FROM sys.tables t
                JOIN sys.indexes i ON t.object_id = i.object_id
                JOIN sys.partitions p
                  ON i.object_id = p.object_id AND i.index_id = p.index_id
                JOIN sys.allocation_units a
                  ON (a.type IN (1, 3) AND a.container_id = p.hobt_id)
                  OR (a.type = 2 AND a.container_id = p.partition_id)
                WHERE t.is_ms_shipped = 0
                GROUP BY t.schema_id, t.name
                """
        else:
            query = """
                SELECT segment_name AS name, SUM(bytes) AS bytes
                FROM user_segments
                GROUP BY segment_name
                """
        try:
            rows = await self.connection.select(query)
        except (QueryException, SQLAlchemyError):
            if driver == "sqlite":
                # SQLite may be built without the dbstat virtual table.
                return {}
            raise
        selected = set(tables)
        return {
            name: int(row["bytes"])
            for row in rows
            if (name := str(row["name"])) in selected and row["bytes"] is not None
        }

    async def tableDetails(self, name: str) -> dict[str, Any]:
        """
        Describe a physical table, including columns, indexes and keys.

        Parameters
        ----------
        name : str
            Table name provided to ``db:table``.

        Returns
        -------
        dict[str, Any]
            Table metadata and statistics.

        Raises
        ------
        ValueError
            If the selected table is absent from the catalog.
        """
        resolved = await self._findTableName(name)
        if resolved is None:
            msg = f"Table '{name}' does not exist on connection '{self.name}'."
            raise ValueError(msg)
        name = resolved
        if self.driver in {"pgsql", "sqlserver"} and name.count(".") != 1:
            msg = (
                "Cannot inspect a schema-qualified object whose name "
                "contains a period."
            )
            raise ValueError(msg)
        if self.driver == "sqlite":
            columns, indexes, foreign_keys = await self._sqliteDetails(name)
        else:
            columns, indexes, foreign_keys = await self._serverDetails(name)
        return {
            "name": name,
            "rows": await self.rowCount(name),
            "size": await self.tableSize(name),
            "columns": columns,
            "indexes": indexes,
            "foreign_keys": foreign_keys,
        }

    async def _findTableName(self, name: str) -> str | None:
        """
        Find a requested table with a filtered catalog query.

        Parameters
        ----------
        name : str
            Qualified or unqualified table name requested by the user.

        Returns
        -------
        str | None
            Unambiguous catalog table name, if one exists.
        """
        driver = self.driver
        if driver == "sqlite":
            query = """
                SELECT name
                FROM sqlite_schema
                WHERE type = 'table'
                  AND name NOT GLOB 'sqlite_*' AND name = :name
                """
            bindings = {"name": name}
        elif driver == "pgsql":
            schema, separator, table = name.rpartition(".")
            query = """
                SELECT n.nspname || '.' || c.relname AS name
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind IN ('r', 'p')
                  AND NOT c.relispartition
                  AND LEFT(n.nspname, 3) <> 'pg_'
                  AND n.nspname <> 'information_schema'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM pg_depend d
                      WHERE d.classid = 'pg_class'::regclass
                        AND d.objid = c.oid
                        AND d.deptype = 'e'
                  )
                  AND c.relname = :table
                """
            bindings = {"table": table}
            if separator:
                query += """
                  AND n.nspname = :schema
                """
                bindings["schema"] = schema
        elif driver == "mysql":
            query = """
                SELECT table_name AS name
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                  AND table_type = 'BASE TABLE'
                  AND LOWER(table_name) = LOWER(:name)
                """
            bindings = {"name": name}
        elif driver == "sqlserver":
            schema, separator, table = name.rpartition(".")
            query = """
                SELECT SCHEMA_NAME(schema_id) + '.' + name AS name
                FROM sys.tables
                WHERE is_ms_shipped = 0
                  AND LOWER(name) = LOWER(:table)
                """
            bindings = {"table": table}
            if separator:
                query += """
                  AND LOWER(SCHEMA_NAME(schema_id)) = LOWER(:schema)
                """
                bindings["schema"] = schema
        else:
            query = """
                SELECT t.table_name AS name
                FROM user_tables t
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM user_mviews m
                    WHERE m.container_name = t.table_name
                )
                  AND UPPER(t.table_name) = UPPER(:name)
                """
            bindings = {"name": name}
        rows = await self.connection.select(query, bindings)
        return self._resolveTableName(name, [str(row["name"]) for row in rows])

    def _resolveTableName(self, name: str, tables: list[str]) -> str | None:
        """
        Match catalog names according to the driver's identifier rules.

        Parameters
        ----------
        name : str
            Requested table name.
        tables : list[str]
            Table names reported by the catalog.

        Returns
        -------
        str | None
            Unambiguous catalog table name, if one exists.
        """
        if name in tables:
            return name
        if self.driver in {"mysql", "oracle", "sqlserver"}:
            matches = [table for table in tables if table.casefold() == name.casefold()]
            if len(matches) == 1:
                return matches[0]
        if self.driver == "sqlserver" and "." not in name:
            matches = [
                table for table in tables
                if table.rpartition(".")[2].casefold() == name.casefold()
            ]
            if len(matches) == 1:
                return matches[0]
        if self.driver == "pgsql" and "." not in name:
            matches = [table for table in tables if table.endswith(f".{name}")]
            if len(matches) == 1:
                return matches[0]
        return None

    async def _sqliteDetails(
        self,
        name: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Read SQLite column, index and foreign-key metadata.

        Parameters
        ----------
        name : str
            Name of the table to inspect.

        Returns
        -------
        tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]
            Columns, indexes and foreign keys.
        """
        quoted = self.quoteIdentifier(name)
        raw_columns = await self.connection.select(f"PRAGMA table_xinfo({quoted})")
        columns = [
            {
                "name": row["name"],
                "type": row["type"] or "-",
                "nullable": not (row["notnull"] or row["pk"]),
                "default": row["dflt_value"],
                "primary": bool(row["pk"]),
            }
            for row in raw_columns
        ]
        index_rows = await self.connection.select(
            """
            SELECT il.name, il."unique" AS is_unique, il.origin,
                   ii.name AS column_name
            FROM pragma_index_list(:name) AS il
            LEFT JOIN pragma_index_info(il.name) AS ii
            ORDER BY il.seq, ii.seqno
            """,
            {"name": name},
        )
        indexes = []
        index_columns: list[str] = []
        last_index: str | None = None
        for row in index_rows:
            index_name = str(row["name"])
            if index_name != last_index:
                if indexes:
                    indexes[-1]["columns"] = ", ".join(index_columns)
                indexes.append({
                    "name": index_name,
                    "columns": "",
                    "unique": bool(row["is_unique"]),
                    "primary": row["origin"] == "pk",
                })
                index_columns = []
                last_index = index_name
            if row["column_name"] is not None:
                index_columns.append(str(row["column_name"]))
        if indexes:
            indexes[-1]["columns"] = ", ".join(index_columns)
        foreign_rows = await self.connection.select(
            f"PRAGMA foreign_key_list({quoted})",
        )
        foreign_keys = [
            {
                "name": str(row["id"]),
                "column": row["from"],
                "references": f"{row['table']}.{row['to']}",
                "on_delete": row["on_delete"],
            }
            for row in foreign_rows
        ]
        return columns, indexes, foreign_keys

    async def _serverDetails(
        self,
        name: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Read server column, index and foreign-key metadata.

        Parameters
        ----------
        name : str
            Catalog table name to inspect.

        Returns
        -------
        tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]
            Columns, indexes and foreign keys.
        """
        schema, _, table = name.rpartition(".")
        if self.driver == "pgsql":
            schema = schema or "public"
            raw_columns = await self.connection.select(
                """
                SELECT column_name AS name, data_type AS type,
                       c.is_nullable AS nullable,
                       c.column_default AS default_value,
                       CASE WHEN EXISTS (
                           SELECT 1
                           FROM information_schema.key_column_usage k
                           JOIN information_schema.table_constraints tc
                             ON tc.constraint_catalog = k.constraint_catalog
                            AND tc.constraint_schema = k.constraint_schema
                            AND tc.constraint_name = k.constraint_name
                           WHERE tc.constraint_type = 'PRIMARY KEY'
                             AND k.table_schema = c.table_schema
                             AND k.table_name = c.table_name
                             AND k.column_name = c.column_name
                       ) THEN 1 ELSE 0 END AS primary_key
                FROM information_schema.columns c
                WHERE c.table_schema = :schema AND c.table_name = :table
                ORDER BY c.ordinal_position
                """,
                {"schema": schema, "table": table},
            )
            raw_indexes = await self.connection.select(
                """
                SELECT ix.relname AS name,
                       array_to_string(
                           ARRAY(
                               SELECT pg_get_indexdef(i.indexrelid, k, true)
                               FROM generate_series(1, i.indnkeyatts) AS k
                           ), ', '
                       ) AS definition,
                       CASE WHEN i.indisunique THEN 0 ELSE 1 END AS non_unique,
                       i.indisprimary AS primary_key
                FROM pg_index i
                JOIN pg_class t ON t.oid = i.indrelid
                JOIN pg_class ix ON ix.oid = i.indexrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
                WHERE n.nspname = :schema AND t.relname = :table
                ORDER BY ix.relname
                """,
                {"schema": schema, "table": table},
            )
            raw_fks = await self.connection.select(
                """
                SELECT c.conname AS name, a.attname AS column_name,
                       rn.nspname || '.' || rt.relname AS ref_table,
                       ra.attname AS ref_column,
                       CASE c.confdeltype
                           WHEN 'a' THEN 'NO ACTION'
                           WHEN 'r' THEN 'RESTRICT'
                           WHEN 'c' THEN 'CASCADE'
                           WHEN 'n' THEN 'SET NULL'
                           WHEN 'd' THEN 'SET DEFAULT'
                       END AS on_delete
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
                JOIN pg_class rt ON rt.oid = c.confrelid
                JOIN pg_namespace rn ON rn.oid = rt.relnamespace
                JOIN LATERAL unnest(c.conkey, c.confkey)
                  AS keys(local_num, ref_num) ON true
                JOIN pg_attribute a
                  ON a.attrelid = t.oid AND a.attnum = keys.local_num
                JOIN pg_attribute ra
                  ON ra.attrelid = rt.oid AND ra.attnum = keys.ref_num
                WHERE c.contype = 'f' AND n.nspname = :schema
                  AND t.relname = :table
                ORDER BY c.conname, a.attnum
                """,
                {"schema": schema, "table": table},
            )
        elif self.driver == "mysql":
            table = name
            raw_columns = await self.connection.select(
                """
                SELECT column_name AS name, column_type AS type,
                       is_nullable AS nullable,
                       column_default AS default_value,
                       CASE WHEN column_key = 'PRI' THEN 1 ELSE 0 END AS primary_key
                FROM information_schema.columns
                WHERE table_schema = DATABASE() AND table_name = :table
                ORDER BY ordinal_position
                """,
                {"table": table},
            )
            raw_indexes = await self.connection.select(
                """
                SELECT index_name AS name,
                       GROUP_CONCAT(column_name ORDER BY seq_in_index) AS definition,
                       MIN(non_unique) AS non_unique
                FROM information_schema.statistics
                WHERE table_schema = DATABASE() AND table_name = :table
                GROUP BY index_name
                ORDER BY index_name
                """,
                {"table": table},
            )
            raw_fks = await self.connection.select(
                """
                SELECT k.constraint_name AS name,
                       k.column_name AS column_name,
                       k.referenced_table_name AS ref_table,
                       k.referenced_column_name AS ref_column,
                       r.delete_rule AS on_delete
                FROM information_schema.key_column_usage k
                LEFT JOIN information_schema.referential_constraints r
                  ON r.constraint_schema = k.constraint_schema
                 AND r.constraint_name = k.constraint_name
                 AND r.table_name = k.table_name
                WHERE k.table_schema = DATABASE() AND k.table_name = :table
                  AND k.referenced_table_name IS NOT NULL
                ORDER BY k.constraint_name, k.ordinal_position
                """,
                {"table": table},
            )
        elif self.driver == "sqlserver":
            raw_columns = await self.connection.select(
                """
                SELECT c.name, ty.name AS type, c.is_nullable AS nullable,
                       dc.definition AS default_value,
                       CASE WHEN ic.column_id IS NULL THEN 0 ELSE 1 END AS primary_key
                FROM sys.columns c
                JOIN sys.types ty ON ty.user_type_id = c.user_type_id
                LEFT JOIN sys.default_constraints dc
                  ON dc.object_id = c.default_object_id
                LEFT JOIN sys.indexes i
                  ON i.object_id = c.object_id AND i.is_primary_key = 1
                LEFT JOIN sys.index_columns ic
                  ON ic.object_id = c.object_id
                 AND ic.index_id = i.index_id
                 AND ic.column_id = c.column_id
                WHERE c.object_id = OBJECT_ID(:name)
                ORDER BY c.column_id
                """,
                {"name": self.quoteIdentifier(name)},
            )
            raw_indexes = await self.connection.select(
                """
                SELECT i.name,
                       STRING_AGG(c.name, ', ')
                           WITHIN GROUP (ORDER BY ic.key_ordinal) AS definition,
                       CASE WHEN i.is_unique = 1 THEN 0 ELSE 1 END AS non_unique,
                       i.is_primary_key AS primary_key
                FROM sys.indexes i
                LEFT JOIN sys.index_columns ic
                  ON ic.object_id = i.object_id
                 AND ic.index_id = i.index_id
                 AND ic.key_ordinal > 0
                LEFT JOIN sys.columns c
                  ON c.object_id = ic.object_id AND c.column_id = ic.column_id
                WHERE i.object_id = OBJECT_ID(:name) AND i.name IS NOT NULL
                GROUP BY i.name, i.is_unique, i.is_primary_key
                ORDER BY i.name
                """,
                {"name": self.quoteIdentifier(name)},
            )
            raw_fks = await self.connection.select(
                """
                SELECT fk.name, pc.name AS column_name, rt.name AS ref_table,
                       rc.name AS ref_column,
                       fk.delete_referential_action_desc AS on_delete
                FROM sys.foreign_keys fk
                JOIN sys.foreign_key_columns fkc
                  ON fkc.constraint_object_id = fk.object_id
                JOIN sys.columns pc
                  ON pc.object_id = fkc.parent_object_id
                 AND pc.column_id = fkc.parent_column_id
                JOIN sys.tables rt ON rt.object_id = fkc.referenced_object_id
                JOIN sys.columns rc
                  ON rc.object_id = fkc.referenced_object_id
                 AND rc.column_id = fkc.referenced_column_id
                WHERE fk.parent_object_id = OBJECT_ID(:name)
                ORDER BY fk.name
                """,
                {"name": self.quoteIdentifier(name)},
            )
        else:
            table = name
            raw_columns = await self.connection.select(
                """
                SELECT c.column_name AS name, c.data_type AS type, c.nullable,
                       c.data_default AS default_value,
                       CASE WHEN EXISTS (
                           SELECT 1
                           FROM user_constraints uc
                           JOIN user_cons_columns ucc
                             ON ucc.constraint_name = uc.constraint_name
                           WHERE uc.constraint_type = 'P'
                             AND uc.table_name = c.table_name
                             AND ucc.column_name = c.column_name
                       ) THEN 1 ELSE 0 END AS primary_key
                FROM user_tab_columns c
                WHERE c.table_name = :table
                ORDER BY c.column_id
                """,
                {"table": table},
            )
            raw_indexes = await self.connection.select(
                """
                SELECT i.index_name AS name,
                       LISTAGG(ic.column_name, ', ')
                           WITHIN GROUP (ORDER BY ic.column_position) AS definition,
                       CASE WHEN i.uniqueness = 'UNIQUE' THEN 0 ELSE 1 END
                           AS non_unique,
                       MAX(CASE WHEN pk.constraint_name IS NULL THEN 0 ELSE 1 END)
                           AS primary_key
                FROM user_indexes i
                LEFT JOIN user_ind_columns ic ON ic.index_name = i.index_name
                LEFT JOIN user_constraints pk
                  ON pk.index_name = i.index_name
                 AND pk.table_name = i.table_name
                 AND pk.constraint_type = 'P'
                WHERE i.table_name = :table
                GROUP BY i.index_name, i.uniqueness
                ORDER BY i.index_name
                """,
                {"table": table},
            )
            raw_fks = await self.connection.select(
                """
                SELECT child.constraint_name AS name,
                       cc.column_name AS column_name,
                       parent.owner || '.' || parent.table_name AS ref_table,
                       pc.column_name AS ref_column,
                       child.delete_rule AS on_delete
                FROM user_constraints child
                JOIN user_cons_columns cc
                  ON cc.constraint_name = child.constraint_name
                JOIN all_constraints parent
                  ON parent.owner = child.r_owner
                 AND parent.constraint_name = child.r_constraint_name
                JOIN all_cons_columns pc
                  ON pc.owner = parent.owner
                 AND pc.constraint_name = parent.constraint_name
                 AND pc.position = cc.position
                WHERE child.table_name = :table AND child.constraint_type = 'R'
                ORDER BY child.constraint_name, cc.position
                """,
                {"table": table},
            )
        columns = [
            {
                "name": row["name"],
                "type": row["type"],
                "nullable": row["nullable"] in ("YES", "Y", True, 1),
                "default": row["default_value"],
                "primary": bool(row["primary_key"]),
            }
            for row in raw_columns
        ]
        indexes = [
            {
                "name": row["name"],
                "columns": row.get("definition") or "-",
                "unique": (
                    not bool(row["non_unique"])
                    if "non_unique" in row
                    else str(row.get("definition", "")).startswith("CREATE UNIQUE")
                ),
                "primary": bool(row.get("primary_key")) or row["name"] == "PRIMARY",
            }
            for row in raw_indexes
        ]
        foreign_keys = [
            {
                "name": row["name"],
                "column": row.get("column_name") or "-",
                "references": (
                    f"{row['ref_table']}.{row['ref_column']}"
                    if row.get("ref_column") else row.get("definition")
                    or row.get("ref_table") or "-"
                ),
                "on_delete": row.get("on_delete") or "-",
            }
            for row in raw_fks
        ]
        return columns, indexes, foreign_keys

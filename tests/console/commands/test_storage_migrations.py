from tempfile import TemporaryDirectory
from threading import get_ident
from typing import TYPE_CHECKING
from orionis.auth.tokens.repository import AccessTokenRepository
from orionis.cache.stores.database import DatabaseCacheBackend
from orionis.console.commands.auth.migrate import AuthMigrateCommand
from orionis.console.commands.cache.migrate import CacheMigrateCommand
from orionis.console.commands.queue.migrate import QueueMigrateCommand
from orionis.console.commands.schedule.migrate import ScheduleMigrateCommand
from orionis.console.commands.session.migrate import SessionMigrateCommand
from orionis.console.contracts.store import IScheduleStore
from orionis.console.core.commands import CORE_COMMANDS
from orionis.console.core.loader import Loader
from orionis.console.tasks.store import ScheduleStore
from orionis.container.container import Container
from orionis.database.connection_manager import ConnectionManager
from orionis.database.contracts.connection_manager import IConnectionManager
from orionis.database.exceptions import QueryException
from orionis.foundation.contracts.application import IApplication
from orionis.orm.query.expressions import InsertPlan, SelectPlan
from orionis.orm.query_builder import QueryBuilder
from orionis.orm.resolver import ConnectionResolver
from orionis.orm.schema.table import TableDefinition
from orionis.queues.contracts.manager import IQueueManager
from orionis.queues.manager import QueueManager
from orionis.queues.schema import build_failed_jobs_table, build_jobs_table
from orionis.queues.serializer import JobSerializer
from orionis.test import TestCase
from tests.auth.test_tokens import _Identity
from tests.queues.console.test_commands import _Application as CommandApplication
from tests.queues.console.test_commands import _record

if TYPE_CHECKING:
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
    from orionis.console.base.command import BaseCommand

class _ObservedScheduleStore(ScheduleStore):
    """Record where the scheduler's native database store is constructed."""

    __slots__ = ("database_thread",)

    def database(self) -> SQLAlchemyJobStore:
        """
        Record the calling thread while constructing the real job store.

        Returns
        -------
        SQLAlchemyJobStore
            Configured native database job store.
        """
        self.database_thread = get_ident()
        return super().database()

class _Application(CommandApplication):
    """Expose isolated storage configuration and database services."""

    __slots__ = ("manager", "settings")

    def __init__(self, directory: str) -> None:
        """
        Configure two temporary SQL connections and a custom session table.

        Parameters
        ----------
        directory : str
            Temporary root containing test databases and application files.

        Returns
        -------
        None
            Prepare configuration without opening either database connection.
        """
        super().__init__(directory)
        self.settings = {
            "database": {
                "default": "default",
                "connections": {
                    name: {
                        "driver": "sqlite",
                        "database": str(self.basePath / (name + ".sqlite")),
                        "prefix": "app_",
                    }
                    for name in ("default", "storage")
                },
            },
            "session": {
                "driver": "memory",
                "connection": "storage",
                "table": "http_sessions",
            },
            "auth": {
                "tokens": {
                    "table": "api_tokens", "expiration": None, "secret_bytes": 40,
                },
            },
            "cache": {
                "default": "memory",
                "stores": {
                    "database": {
                        "driver": "database",
                        "connection": "storage",
                        "table": "cached_values",
                        "lock_table": "held_locks",
                    },
                },
            },
            "scheduler": {
                "store": "memory",
                "stores": {
                    "database": {
                        "driver": "database",
                        "connection": "storage",
                        "table": "cron_tasks",
                    },
                },
                "max_instances": 1,
                "coalesce": True,
                "misfire_grace_time": 30,
                "replace_existing": True,
                "jitter": 0,
            },
            "queue": {
                "default": "sync",
                "connections": {
                    "sync": {"driver": "sync"},
                    "database": {
                        "driver": "database",
                        "connection": "storage",
                        "table": "pending_jobs",
                    },
                },
                "failed": {"connection": "storage", "table": "failed_jobs"},
            },
        }
        self.manager = ConnectionManager(self)

    def config(self, key: str) -> object:
        """
        Resolve a dotted configuration path from the test settings.

        Parameters
        ----------
        key : str
            Dotted configuration key requested by a framework component.

        Returns
        -------
        object
            Configured value or None when the path is absent.
        """
        value = self.settings
        for part in key.split("."):
            if not isinstance(value, dict):
                return None
            value = value.get(part)
        return value

    async def make(self, contract: type) -> IConnectionManager:
        """
        Resolve the isolated database service for migration commands.

        Parameters
        ----------
        contract : type
            Service contract requested by a framework manager.

        Returns
        -------
        IConnectionManager
            Database manager backed only by the temporary test connections.

        Raises
        ------
        TypeError
            If a component requests an unexpected service.
        """
        if contract is not IConnectionManager:
            message = "Unexpected service requested during storage migration."
            raise TypeError(message)
        return self.manager

IApplication.register(_Application)

class TestStorageMigrations(TestCase):
    """Verify framework-owned schema commands against isolated SQL databases."""

    def setUp(self) -> None:
        """
        Prepare independent application settings and database paths.

        Returns
        -------
        None
            Register cleanup for the temporary application and SQL engines.
        """
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.app = _Application(self.temporary.name)
        self.addAsyncCleanup(self.app.manager.disconnect)
        previous_manager = ConnectionResolver._manager
        if previous_manager is None:
            self.addCleanup(ConnectionResolver.clear)
        else:
            self.addCleanup(ConnectionResolver.setManager, previous_manager)
        ConnectionResolver.setManager(self.app.manager)

    def _commands(self) -> tuple[tuple[BaseCommand, tuple[object, ...]], ...]:
        """
        Build the five commands with services bound to the temporary settings.

        Returns
        -------
        tuple[tuple[BaseCommand, tuple[object, ...]], ...]
            Real migration commands and their isolated service arguments.
        """
        shared = (self.app, self.app.manager)
        return (
            (_record(AuthMigrateCommand), shared),
            (_record(CacheMigrateCommand), shared),
            (_record(SessionMigrateCommand), shared),
            (_record(ScheduleMigrateCommand), (
                ScheduleStore(self.app, self.app.manager),
            )),
            (_record(QueueMigrateCommand), (QueueManager(self.app, JobSerializer()),)),
        )

    async def testQueueMigrateUsesConfiguredSqlConnectionAndInternalSchema(
        self,
    ) -> None:
        """
        Prepare queue and failure tables without initializing queue drivers.

        Returns
        -------
        None
            Verify SQL routing and both framework-owned queue definitions.
        """
        manager = QueueManager(self.app, JobSerializer())
        command = _record(QueueMigrateCommand)
        self.assertEqual(await command.handle(manager), 0)
        self.assertEqual(set(self.app.manager._cached_connections), {"storage"})
        connection = self.app.manager.connection("storage")
        for table, definition in (
            ("app_pending_jobs", build_jobs_table("pending_jobs")),
            ("app_failed_jobs", build_failed_jobs_table("failed_jobs")),
        ):
            columns = await connection.select(
                "SELECT name FROM pragma_table_info(:table)", {"table": table},
            )
            self.assertEqual(
                {column["name"] for column in columns}, set(definition.columns),
            )
        self.assertEqual(manager._drivers, {})
        self.assertIsNone(manager._failed)

    async def testAuthMigrateCreatesUsableTokenStorageAndPreservesTokens(self) -> None:
        """
        Create usable token storage and enforce digest uniqueness.

        Returns
        -------
        None
            Verify token issuance, lookup, persistence, and unique digest constraints.
        """
        command = _record(AuthMigrateCommand)
        self.assertEqual(await command.handle(self.app, self.app.manager), 0)
        repository = AccessTokenRepository(self.app, QueryBuilder(self.app.manager))
        issued = await repository.create(_Identity(123), "migration-check")
        self.assertIsNotNone(issued.access_token.id)
        self.assertEqual(await command.handle(self.app, self.app.manager), 0)
        restored = await repository.findByPlainText(issued.plain_text)
        self.assertIsNotNone(restored)
        self.assertEqual(str(restored.tokenable_id), "123")
        connection = self.app.manager.connection()
        definition = TableDefinition(name="api_tokens")
        rows = await connection.select(SelectPlan(table=definition))
        self.assertEqual(len(rows), 1)
        duplicate = {name: value for name, value in rows[0].items() if name != "id"}
        with self.assertRaises(QueryException):
            await connection.insert(InsertPlan(table=definition, values=[duplicate]))

    async def testCacheMigrateCreatesInternalTablesAndPreservesEntries(self) -> None:
        """
        Create cache entries and locks from the backend's internal definitions.

        Returns
        -------
        None
            Verify configured names, columns, prefix, and preserved cache values.
        """
        command = _record(CacheMigrateCommand)
        self.assertEqual(await command.handle(self.app, self.app.manager), 0)
        connection = self.app.manager.connection("storage")
        cases = {
            "app_cached_values": ["cache_key", "cache_value", "expiration"],
            "app_held_locks": ["cache_key", "owner", "expiration"],
        }
        for table, expected in cases.items():
            columns = await connection.select(f"PRAGMA table_info({table})")
            self.assertEqual([column["name"] for column in columns], expected)
        backend = DatabaseCacheBackend(connection, "cached_values", "held_locks")
        await backend.set("preserved", {"value": 42})
        self.assertEqual(await command.handle(self.app, self.app.manager), 0)
        self.assertEqual(await backend.get("preserved"), {"value": 42})

    async def testCacheMigrateRejectsMissingDatabaseStore(self) -> None:
        """
        Report missing database cache configuration instead of migrating a fallback.

        Returns
        -------
        None
            Verify a nonzero exit and an untouched default database engine.
        """
        self.app.settings["cache"]["stores"]["database"] = None
        command = _record(CacheMigrateCommand)
        self.assertEqual(await command.handle(self.app, self.app.manager), 1)
        self.assertEqual(command.messages[0][0], "error")
        self.assertIsNone(self.app.manager.connection()._engine)

    async def testScheduleMigrateUsesNativeSchemaAndPreservesJobs(self) -> None:
        """
        Create APScheduler's configured table and indexes outside the event loop.

        Returns
        -------
        None
            Verify native columns, indexed due times, thread isolation, and saved jobs.
        """
        store = _ObservedScheduleStore(self.app, self.app.manager)
        command = _record(ScheduleMigrateCommand)
        self.assertEqual(await command.handle(store), 0)
        self.assertNotEqual(store.database_thread, get_ident())
        connection = self.app.manager.connection("storage")
        columns = await connection.select("PRAGMA table_info(cron_tasks)")
        self.assertEqual(
            [column["name"] for column in columns],
            ["id", "next_run_time", "job_state"],
        )
        indexes = await connection.select("PRAGMA index_list(cron_tasks)")
        self.assertIn(
            "ix_cron_tasks_next_run_time", [index["name"] for index in indexes],
        )
        record = {"id": "preserved", "next_run_time": 1.5, "job_state": b"job-state"}
        await connection.execute(
            "INSERT INTO cron_tasks (id, next_run_time, job_state) "
            "VALUES (:id, :next_run_time, :job_state)",
            record,
        )
        self.assertEqual(
            await command.handle(ScheduleStore(self.app, self.app.manager)), 0,
        )
        self.assertEqual(await connection.select("SELECT * FROM cron_tasks"), [record])
        self.assertIsNone(self.app.manager.connection()._engine)

    async def testScheduleMigrateRejectsMissingDatabaseStore(self) -> None:
        """
        Report missing scheduler database configuration without creating storage.

        Returns
        -------
        None
            Verify a nonzero command exit and an untouched default SQL engine.
        """
        self.app.settings["scheduler"]["stores"]["database"] = None
        command = _record(ScheduleMigrateCommand)
        self.assertEqual(
            await command.handle(ScheduleStore(self.app, self.app.manager)), 1,
        )
        self.assertEqual(command.messages[0][0], "error")
        self.assertIsNone(self.app.manager.connection()._engine)

    async def testSessionMigrateUsesConfiguredTableAndPreservesData(self) -> None:
        """
        Create session storage on its selected connection without losing records.

        Returns
        -------
        None
            Verify internal columns, SQL prefix, connection routing, and repeatability.
        """
        command = _record(SessionMigrateCommand)
        self.assertEqual(await command.handle(self.app, self.app.manager), 0)
        connection = self.app.manager.connection("storage")
        columns = await connection.select("PRAGMA table_info(app_http_sessions)")
        self.assertEqual(
            [column["name"] for column in columns], ["id", "payload", "expires_at"],
        )
        definition = TableDefinition(name="http_sessions")
        record = {"id": "preserved", "payload": "{}", "expires_at": 1}
        await connection.insert(InsertPlan(table=definition, values=[record]))
        self.assertEqual(await command.handle(self.app, self.app.manager), 0)
        self.assertEqual(
            await connection.select(SelectPlan(table=definition)), [record],
        )
        self.assertEqual(await self.app.manager.connection().select(
            "SELECT name FROM sqlite_master WHERE type = 'table'",
        ), [])

    async def testSessionMigrateReportsMissingConnection(self) -> None:
        """
        Report an invalid SQL connection without a successful exit status.

        Returns
        -------
        None
            Verify the command exposes the configuration failure as an error.
        """
        self.app.settings["session"]["connection"] = "missing"
        command = _record(SessionMigrateCommand)
        self.assertEqual(await command.handle(self.app, self.app.manager), 1)
        self.assertEqual(command.messages[0][0], "error")

    async def testStorageCommandsNeverImportApplicationDatabaseFiles(self) -> None:
        """
        Ignore user migrations and schema modules when preparing internal storage.

        Returns
        -------
        None
            Verify database files remain unimported and no migration ledger is created.
        """
        traps = []
        for directory in ("migrations", "schemas"):
            module = self.app.basePath / "database" / directory / "m0000000001_trap.py"
            module.parent.mkdir(parents=True)
            module.write_text(
                "from pathlib import Path\n"
                "Path(__file__).with_suffix('.loaded').touch()\n"
                "raise RuntimeError('Application migration must not run')\n",
                encoding="utf-8",
            )
            traps.append(module.with_suffix(".loaded"))
        for command, arguments in self._commands():
            self.assertEqual(await command.handle(*arguments), 0)
        self.assertFalse(any(path.exists() for path in traps))
        tables = await self.app.manager.connection("storage").select(
            "SELECT name FROM sqlite_master WHERE type = 'table'",
        )
        self.assertEqual({row["name"] for row in tables}, {
            "app_cached_values", "app_held_locks", "app_http_sessions", "cron_tasks",
            "app_pending_jobs", "app_failed_jobs",
        })
        default_tables = await self.app.manager.connection().select(
            "SELECT name FROM sqlite_master WHERE type = 'table'",
        )
        self.assertEqual(default_tables, [{"name": "app_api_tokens"}])

    async def testStorageCommandsReportDatabaseFailures(self) -> None:
        """
        Report SQL opening failures without successful command output.

        Returns
        -------
        None
            Verify every command returns one when its configured database cannot open.
        """
        self.app.manager.addConnection("broken", {
            "driver": "sqlite",
            "database": str(self.app.basePath / "missing" / "broken.sqlite"),
        })
        self.app.manager.setDefaultName("broken")
        self.app.settings["session"]["connection"] = "broken"
        self.app.settings["cache"]["stores"]["database"]["connection"] = "broken"
        self.app.settings["scheduler"]["stores"]["database"]["connection"] = "broken"
        self.app.settings["queue"]["connections"]["database"]["connection"] = "broken"
        for command, arguments in self._commands():
            self.assertEqual(await command.handle(*arguments), 1)
            self.assertEqual(command.messages[0][0], "error")

    async def testStorageCommandsRejectUnenforcedUniqueConstraints(self) -> None:
        """
        Reject unsupported analytical storage before opening database engines.

        Returns
        -------
        None
            Verify all five commands reject a backend without key enforcement.
        """
        self.app.manager.addConnection("analytics", {
            "driver": "redshift", "database": "unused",
        })
        self.app.manager.setDefaultName("analytics")
        self.app.settings["session"]["connection"] = "analytics"
        self.app.settings["cache"]["stores"]["database"]["connection"] = "analytics"
        self.app.settings["scheduler"]["stores"]["database"]["connection"] = "analytics"
        queue_database = self.app.settings["queue"]["connections"]["database"]
        queue_database["connection"] = "analytics"
        for command, arguments in self._commands():
            self.assertEqual(await command.handle(*arguments), 1)
            self.assertEqual(command.messages[0][0], "error")
        self.assertIsNone(self.app.manager.connection("analytics")._engine)

    async def testCoreLoaderDiscoversStorageMigrationCommands(self) -> None:
        """
        Discover storage commands through the native core command loader.

        Returns
        -------
        None
            Verify canonical signatures are registered and loadable.
        """
        expected = {
            "auth:migrate", "cache:migrate", "queue:migrate",
            "schedule:migrate", "session:migrate",
        }
        self.assertTrue(expected <= {command.signature for command in CORE_COMMANDS})
        loader = Loader(self.app)
        for signature in expected:
            command = await loader.get(signature)
            self.assertIsNotNone(command)
            self.assertEqual(command.signature, signature)

    async def testStorageCommandsResolveDependenciesThroughContainer(self) -> None:
        """
        Resolve command dependencies through the native container in an isolated scope.

        Returns
        -------
        None
            Verify all five handlers execute with their registered service contracts.
        """
        container = Container()
        async with container.beginScope():
            container.instance(IApplication, self.app)
            container.instance(IConnectionManager, self.app.manager)
            container.instance(
                IScheduleStore, ScheduleStore(self.app, self.app.manager),
            )
            container.instance(IQueueManager, QueueManager(self.app, JobSerializer()))
            for command, _arguments in self._commands():
                self.assertEqual(await container.call(command, "handle"), 0)

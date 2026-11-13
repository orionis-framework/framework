# ruff: noqa: PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
import asyncio
import tempfile
from pathlib import Path
from types import ModuleType
from unittest.mock import patch
from sqlalchemy import event
from orionis.container.container import Container
from orionis.database.connection_manager import ConnectionManager
from orionis.database.seeders.events import SeederEvents
from orionis.database.seeders.runner import SeederRunner
from orionis.database.seeders.seeder import Seeder
from orionis.orm.query_builder import QueryBuilder
from orionis.orm.resolver import ConnectionResolver
from orionis.test import TestCase


class _StubApp:
    """Provide isolated database configuration to the runner."""

    __slots__ = ("_container", "_database", "basePath")

    def __init__(self, database: str) -> None:
        """Store the database path and create an isolated container.

        Parameters
        ----------
        database : str
            File path used by the default SQLite connection.

        Returns
        -------
        None
            No return value.
        """

        class _IsolatedContainer(Container):
            """Keep seeder test bindings separate from the application."""

        self.basePath = Path.cwd()
        self._database = database
        self._container = _IsolatedContainer()

    async def build(self, seeder_cls: type[Seeder]) -> Seeder:
        """Construct a seeder through the framework container.

        Parameters
        ----------
        seeder_cls : type of Seeder
            Seeder class to construct.

        Returns
        -------
        Seeder
            Seeder with registered dependencies injected.
        """
        return await self._container.build(seeder_cls)

    def provide(self, dependency: object) -> None:
        """Register an instance for constructor injection.

        Parameters
        ----------
        dependency : object
            Instance available to seeder constructors.

        Returns
        -------
        None
            No return value.
        """
        self._container.instance(None, dependency)

    def path(self, key: str) -> Path:
        """Return the seeder directory for discovery.

        Parameters
        ----------
        key : str
            Application path key.

        Returns
        -------
        Path
            Directory used by the runner.
        """
        if key != "database_seeders":
            raise KeyError(key)
        return self.basePath / "database" / "seeders"

    def config(self, key: str) -> dict:
        """Return two file-backed SQLite connections.

        Parameters
        ----------
        key : str
            Configuration key.

        Returns
        -------
        dict
            Database configuration.
        """
        if key != "database":
            raise KeyError(key)
        return {
            "default": "sqlite",
            "connections": {
                "sqlite": {
                    "driver": "sqlite",
                    "database": self._database,
                    "prefix": "",
                },
                "secondary": {
                    "driver": "sqlite",
                    "database": f"{self._database}.secondary",
                    "prefix": "",
                },
            },
        }


class _Alpha(Seeder):
    """Insert one application record."""

    calls = 0

    async def run(self) -> None:
        """Insert an alpha row.

        Returns
        -------
        None
            No return value.
        """
        type(self).calls += 1
        await ConnectionResolver.connection().execute(
            "INSERT INTO entries (label) VALUES (:label)",
            {"label": "alpha"},
        )


class _Beta(Seeder):
    """Insert a second application record."""

    async def run(self) -> None:
        """Insert a beta row.

        Returns
        -------
        None
            No return value.
        """
        await ConnectionResolver.connection().execute(
            "INSERT INTO entries (label) VALUES (:label)",
            {"label": "beta"},
        )


class _Flaky(Seeder):
    """Write data and fail until explicitly repaired by the test."""

    fail = True

    async def run(self) -> None:
        """Exercise transaction rollback and later retry.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        RuntimeError
            If the test keeps the seeder in its failing state.
        """
        await ConnectionResolver.connection().execute(
            "INSERT INTO entries (label) VALUES (:label)",
            {"label": "flaky"},
        )
        if type(self).fail:
            error_msg = "seeder failed"
            raise RuntimeError(error_msg)


class _Slow(Seeder):
    """Hold a transaction open while a second runner competes."""

    calls = 0
    entered: asyncio.Event
    release: asyncio.Event

    async def run(self) -> None:
        """Insert once after the contender attempts the SQLite write transaction.

        Returns
        -------
        None
            No return value.
        """
        type(self).calls += 1
        type(self).entered.set()
        await type(self).release.wait()
        await ConnectionResolver.connection().execute(
            "INSERT INTO entries (label) VALUES (:label)",
            {"label": "slow"},
        )


class _NestedTransaction(Seeder):
    """Use the public query builder transaction in a selected seeder."""

    manager: ConnectionManager

    async def run(self) -> None:
        """Write through an unqualified builder transaction.

        Returns
        -------
        None
            No return value.
        """
        db = QueryBuilder(type(self).manager)
        async with db.transaction():
            await db.table("entries").insert({"label": "nested"})


class _SeedLabel:
    """Value supplied by the test application container."""

    __slots__ = ("value",)

    def __init__(self, value: str) -> None:
        """Store the label to be inserted by an injected seeder.

        Parameters
        ----------
        value : str
            Label to insert.

        Returns
        -------
        None
            No return value.
        """
        self.value = value


class _Injected(Seeder):
    """Insert a record using a required constructor dependency."""

    __slots__ = ("_label",)

    constructor_connection = None

    def __init__(self, label: _SeedLabel) -> None:
        """Capture the injected label and selected connection.

        Parameters
        ----------
        label : _SeedLabel
            Value resolved by the application container.

        Returns
        -------
        None
            No return value.
        """
        self._label = label
        type(self).constructor_connection = ConnectionResolver.connection()

    async def run(self) -> None:
        """Insert the injected label through the scoped connection.

        Returns
        -------
        None
            No return value.
        """
        await ConnectionResolver.connection().execute(
            "INSERT INTO entries (label) VALUES (:label)",
            {"label": self._label.value},
        )


class TestSeederRunner(TestCase):
    """Exercise seeder tracking against a real file-backed SQLite store."""

    async def asyncSetUp(self) -> None:
        """Build isolated databases and reset class state.

        Returns
        -------
        None
            No return value.
        """
        self._workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self._workspace.cleanup)
        self._app = _StubApp(str(Path(self._workspace.name) / "seeders.sqlite"))
        self._manager = ConnectionManager(self._app)
        self.enterContext(patch.object(ConnectionResolver, "_manager", self._manager))
        self.addAsyncCleanup(self._manager.disconnect)
        self._runner = SeederRunner(self._app, self._manager)
        self.enterContext(patch.object(_Alpha, "calls", 0))
        self.enterContext(patch.object(_Flaky, "fail", new=True))
        self.enterContext(patch.object(_Slow, "calls", 0))
        self.enterContext(patch.object(_Injected, "constructor_connection", None))
        self.enterContext(
            patch.object(_NestedTransaction, "manager", self._manager, create=True),
        )
        for name in ("sqlite", "secondary"):
            await self._manager.connection(name).statement(
                "CREATE TABLE entries (id INTEGER PRIMARY KEY, label VARCHAR(50))",
            )

    def useSeeders(self, seeders: dict[str, type[Seeder]]) -> None:
        """Replace filesystem discovery with a fixed mapping.

        Parameters
        ----------
        seeders : dict
            Classes keyed by persisted names.
        """
        self._runner._SeederRunner__discovered_cache = dict(
            sorted(
                seeders.items(),
            ),
        )

    async def entries(self, connection: str = "sqlite") -> list[str]:
        """Read inserted application rows from a chosen connection.

        Parameters
        ----------
        connection : str
            Configured connection name.

        Returns
        -------
        list of str
            Inserted labels in order.
        """
        rows = await self._manager.connection(connection).select(
            "SELECT label FROM entries ORDER BY id",
        )
        return [row["label"] for row in rows]

    async def tracking(self, connection: str = "sqlite") -> list[dict]:
        """Read the persisted seeder history.

        Parameters
        ----------
        connection : str
            Configured connection name.

        Returns
        -------
        list of dict
            Recorded seeders.
        """
        return await self._manager.connection(connection).select(
            "SELECT seeder, batch, seeded_at FROM seeders ORDER BY id",
        )

    async def testPendingSeederIsRecordedAndNeverRepeated(self) -> None:
        """Run pending data once and persist a completion timestamp.

        Returns
        -------
        None
            No return value.
        """
        self.useSeeders({"s01_alpha": _Alpha})
        self.assertEqual(await self._runner.seed(), ["s01_alpha"])
        self.assertEqual(await self.entries(), ["alpha"])
        self.assertEqual(await self._runner.seed(), [])
        self.assertEqual(_Alpha.calls, 1)
        rows = await self.tracking()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["seeder"], "s01_alpha")
        self.assertEqual(rows[0]["batch"], 1)
        self.assertGreater(rows[0]["seeded_at"], 0)

    async def testNewSeederRunsInNextBatchAndFilenameOrder(self) -> None:
        """Run a newly added seeder without repeating previous work.

        Returns
        -------
        None
            No return value.
        """
        self.useSeeders({"s01_alpha": _Alpha})
        await self._runner.seed()
        self.useSeeders({"s03_beta": _Beta, "s01_alpha": _Alpha})
        self.assertEqual(await self._runner.seed(), ["s03_beta"])
        self.assertEqual(await self.entries(), ["alpha", "beta"])
        rows = await self.tracking()
        self.assertEqual([row["batch"] for row in rows], [1, 2])

    async def testFailureRollsBackDataAndTrackingThenCanRetry(self) -> None:
        """Leave no claim or data after failure and allow a later retry.

        Returns
        -------
        None
            No return value.
        """
        self.useSeeders({"s02_flaky": _Flaky})
        events: list[str] = []
        callbacks = SeederEvents(
            on_start=lambda name: events.append(f"start:{name}"),
            on_error=lambda name, _: events.append(f"error:{name}"),
        )
        with self.assertRaisesRegex(RuntimeError, "seeder failed"):
            await self._runner.seed(events=callbacks)
        self.assertEqual(await self.entries(), [])
        self.assertEqual(await self.tracking(), [])
        self.assertEqual(events, ["start:s02_flaky", "error:s02_flaky"])
        self.enterContext(patch.object(_Flaky, "fail", new=False))
        self.assertEqual(await self._runner.seed(), ["s02_flaky"])
        self.assertEqual(await self.entries(), ["flaky"])
        self.assertEqual(len(await self.tracking()), 1)

    async def testConnectionSelectionIncludesNestedBuilderTransaction(self) -> None:
        """Bind ORM queries and nested transactions to the selected database.

        Returns
        -------
        None
            No return value.
        """
        self.useSeeders({"s01_nested": _NestedTransaction})
        self.assertEqual(
            await self._runner.seed(connection="secondary"),
            ["s01_nested"],
        )
        self.assertEqual(await self.entries("secondary"), ["nested"])
        self.assertEqual(await self.entries(), [])
        self.assertEqual(len(await self.tracking("secondary")), 1)

    async def testConstructorInjectionUsesSelectedTransactionScope(self) -> None:
        """Build seeders through DI while the selected connection is active.

        Returns
        -------
        None
            No return value.
        """
        self._app.provide(_SeedLabel("injected"))
        self.useSeeders({"s01_injected": _Injected})

        self.assertEqual(
            await self._runner.seed(connection="secondary"),
            ["s01_injected"],
        )
        self.assertIs(
            _Injected.constructor_connection,
            self._manager.connection("secondary"),
        )
        self.assertEqual(await self.entries("secondary"), ["injected"])
        self.assertEqual(await self.entries(), [])
        self.assertEqual(len(await self.tracking("secondary")), 1)

    async def testTwoRunnersExecuteSameSeederOnlyOnce(self) -> None:
        """Let the unique claim serialize concurrent runners.

        Returns
        -------
        None
            No return value.
        """
        entered, release, attempted = asyncio.Event(), asyncio.Event(), asyncio.Event()
        self.enterContext(patch.object(_Slow, "entered", entered, create=True))
        self.enterContext(patch.object(_Slow, "release", release, create=True))
        # Create the tracking table before holding a claim transaction open.
        self.useSeeders({})
        self.assertEqual(await self._runner.seed(), [])
        self.useSeeders({"s01_slow": _Slow})
        other_manager = ConnectionManager(self._app)
        self.addAsyncCleanup(other_manager.disconnect)
        competing = SeederRunner(self._app, other_manager)
        competing._SeederRunner__discovered_cache = {"s01_slow": _Slow}
        self.assertEqual(
            await other_manager.connection().select("SELECT 1 AS ready"),
            [{"ready": 1}],
        )
        engine = other_manager.connection()._getEngine().sync_engine

        def observe_claim(
            _connection: object,
            _cursor: object,
            statement: str,
            _parameters: object,
            _context: object,
            _executemany: object,
        ) -> None:
            """Observe the competing write transaction without replacing it.

            Parameters
            ----------
            _connection, _cursor, _parameters, _context, _executemany : object
                SQLAlchemy event arguments unused by this observer.
            statement : str
                SQL about to execute on the competing connection.
            """
            if statement == "BEGIN IMMEDIATE":
                attempted.set()

        event.listen(engine, "before_cursor_execute", observe_claim)
        self.addCleanup(event.remove, engine, "before_cursor_execute", observe_claim)
        async with asyncio.TaskGroup() as group:
            first = group.create_task(self._runner.seed())
            try:
                await asyncio.wait_for(entered.wait(), 5)
                second = group.create_task(competing.seed())
                await asyncio.wait_for(attempted.wait(), 5)
                self.assertFalse(first.done())
                self.assertFalse(second.done())
            finally:
                release.set()
        results = [first.result(), second.result()]
        self.assertCountEqual(results, [["s01_slow"], []])
        self.assertEqual(_Slow.calls, 1)
        self.assertEqual(await self.entries(), ["slow"])
        self.assertEqual(len(await self.tracking()), 1)

    async def testDiscoverySortsFilenameStems(self) -> None:
        """Sort modules regardless of filesystem enumeration order.

        Returns
        -------
        None
            No return value.
        """
        later = type(
            "Later",
            (Seeder,),
            {"__module__": "demo.s02_later", "run": _Beta.run},
        )
        earlier = type(
            "Earlier",
            (Seeder,),
            {"__module__": "demo.s01_earlier", "run": _Beta.run},
        )
        modules = {
            "demo.s02_later": ModuleType("demo.s02_later"),
            "demo.s01_earlier": ModuleType("demo.s01_earlier"),
        }
        modules["demo.s02_later"].Later = later
        modules["demo.s01_earlier"].Earlier = earlier
        self._app.basePath = Path(self._workspace.name)
        (self._app.path("database_seeders")).mkdir(parents=True)
        with (
            patch(
                "orionis.database.migrations.discovery.ModuleInspector.discoverModules",
                return_value=set(modules),
            ),
            patch.dict("sys.modules", modules),
        ):
            self.assertEqual(
                await self._runner.seed(),
                ["s01_earlier", "s02_later"],
            )

# ruff: noqa: PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect database ownership, cleanup and public runtime annotations."""

import asyncio
import inspect
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, Lock
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import TYPE_CHECKING, get_type_hints
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from orionis.database.connection import Connection, _TransactionState
from orionis.database.connection_manager import ConnectionManager
from orionis.database.contracts.connection import IConnection
from orionis.database.contracts.connection_manager import IConnectionManager
from orionis.database.contracts.transaction import ITransaction
from orionis.database.exceptions import QueryException, TransactionException
from orionis.database.threaded.connection import ThreadedConnection
from orionis.database.threaded.engine import ThreadedEngine
from orionis.database.threaded.result import ThreadedResult
from orionis.database.threaded.transaction import ThreadedTransaction
from orionis.database.threaded.worker import ThreadedWorker, _wait_for_completion
from orionis.database.transaction import Transaction
from orionis.failure.runtime import operation
from tests.support.failure_runtime import IsolatedFailureTestCase, activate_runtime

if TYPE_CHECKING:
    from collections.abc import Callable


class TestDatabaseConnectionRegressions(IsolatedFailureTestCase):
    """Exercise database cleanup through real adapters and controlled failures."""

    async def testFailedImplicitRollbackCannotReachPoolResetLogs(self) -> None:
        """Discard failed checkouts while preserving and sanitizing both errors."""
        directory = self.enterContext(TemporaryDirectory())
        marker = "controlled-private-driver-payload"
        for driver in ("sqlite", "redshift"):
            with self.subTest(driver=driver):
                path = Path(directory) / f"{driver}.sqlite"
                connection = Connection(
                    "controlled",
                    {"driver": driver, "database": str(path)},
                )
                if driver == "redshift":
                    connection._engine = ThreadedEngine(
                        create_engine(
                            "sqlite:///" + path.as_posix(),
                            connect_args={"check_same_thread": False},
                        ),
                    )
                self.addAsyncCleanup(connection.disconnect)
                await connection.select("SELECT 1 AS value")
                native = connection._engine.sync_engine
                original = native.dialect.do_rollback
                body_error = ValueError("controlled transaction body failure")
                app, runtime, handler = activate_runtime()
                try:

                    def fail_rollback(
                        raw: object,
                        callback: Callable[[object], object] = original,
                    ) -> None:
                        """Complete driver rollback and then report its failure.

                        Parameters
                        ----------
                        raw : object
                            DBAPI connection supplied by the current dialect.
                        callback : collections.abc.Callable[[object], object]
                            Original rollback operation captured for this driver.

                        Returns
                        -------
                        None
                            No return value.
                        """
                        callback(raw)
                        raise SQLAlchemyError(marker)

                    with (
                        operation(app),
                        patch.object(native.dialect, "do_rollback", fail_rollback),
                        self.assertNoLogs("sqlalchemy.pool", level="ERROR"),
                    ):
                        with self.assertRaises(ValueError) as caught:
                            async with connection._acquire():
                                raise body_error
                        await runtime.drain()
                    self.assertIs(caught.exception, body_error)
                    self.assertEqual(len(handler.reports), 1)
                    observed = handler.reports[0]
                    self.assertIsInstance(observed, QueryException)
                    self.assertNotIn(marker, str(observed))
                    self.assertIsNone(observed.__cause__)
                    self.assertIsNone(observed.__context__)
                    self.assertEqual(native.pool.checkedout(), 0)
                    self.assertEqual(
                        await connection.select("SELECT 1 AS value"),
                        [{"value": 1}],
                    )
                finally:
                    await runtime.shutdown()
                    await connection.disconnect()

    def testDefaultConnectionPreservesItsConfiguredName(self) -> None:
        """Prefer an exact default key and retain the legacy lowercase fallback."""
        for requested, registered in (("Reporting", "Reporting"), ("SQLITE", "sqlite")):
            with self.subTest(requested=requested, registered=registered):
                configuration = {
                    "default": requested,
                    "connections": {
                        registered: {"driver": "sqlite", "database": ":memory:"},
                    },
                }
                manager = ConnectionManager(
                    SimpleNamespace(config=Mock(return_value=configuration)),
                )
                self.assertEqual(manager.getDefaultName(), registered)
                self.assertIs(manager.connection(), manager.connection(registered))
                self.assertIs(manager.configFor(), manager.configFor(registered))

    async def testConcurrentResolutionPublishesOneNamedConnection(self) -> None:
        """Build one real connection when two threads resolve an uncached name."""
        configuration = {
            "default": "local",
            "connections": {"local": {"driver": "sqlite", "database": ":memory:"}},
        }
        manager = ConnectionManager(
            SimpleNamespace(config=lambda _section: configuration),
        )
        barrier = Barrier(2)
        reads_lock = Lock()
        reads = 0

        class ObservedCache(dict[str, IConnection]):
            """Synchronize the initial cache misses before either publication."""

            def get(
                self,
                name: str,
                default: IConnection | None = None,
            ) -> IConnection | None:
                """Return the observed entry after synchronizing the first two reads."""
                nonlocal reads
                value = super().get(name, default)
                with reads_lock:
                    reads += 1
                    synchronize = reads <= barrier.parties
                if synchronize:
                    barrier.wait(timeout=5)
                return value

        manager._cached_connections = ObservedCache()

        with (
            patch(
                "orionis.database.connection.Connection",
                wraps=Connection,
            ) as construct,
            ThreadPoolExecutor(max_workers=2) as executor,
        ):
            connections = await asyncio.gather(
                *(
                    asyncio.wrap_future(executor.submit(manager.connection))
                    for _ in range(2)
                ),
            )
        self.assertIs(connections[0], connections[1])
        self.assertEqual(construct.call_count, 1)

    async def testDisconnectAllSettlesEveryCachedConnectionAfterFailure(self) -> None:
        """Finish every registered disconnect and preserve the first failure."""
        configuration = {
            "default": "first",
            "connections": {
                name: {"driver": "sqlite", "database": ":memory:"}
                for name in ("first", "second", "third")
            },
        }
        manager = ConnectionManager(
            SimpleNamespace(config=lambda _section: configuration),
        )
        instances = [manager.connection(name) for name in configuration["connections"]]
        first = RuntimeError("first controlled disconnect failure")
        later = RuntimeError("later controlled disconnect failure")
        visited = []
        app, runtime, handler = activate_runtime()
        self.addAsyncCleanup(runtime.shutdown)

        async def disconnect(connection: Connection) -> None:
            """Record real cached connections and fail at selected boundaries."""
            name = connection.getName()
            visited.append(name)
            if name == "first":
                raise first
            if name == "third":
                raise later

        with patch.object(Connection, "disconnect", disconnect), operation(app):
            with self.assertRaises(RuntimeError) as caught:
                await manager.disconnect()
            await runtime.drain()
        self.assertIs(caught.exception, first)
        self.assertEqual(visited, ["first", "second", "third"])
        self.assertEqual(handler.reports, [later])
        for instance in instances:
            self.assertIsNot(manager.connection(instance.getName()), instance)

    async def testTransactionRollbackCannotReplaceTheBodyFailure(self) -> None:
        """Preserve the body's exception while reporting a failed rollback once."""
        body_error = ValueError("controlled transaction body failure")
        rollback_error = RuntimeError("controlled rollback failure")
        owner = asyncio.current_task()

        async def rollback() -> None:
            """Reject cleanup transferred out of the public transaction's owner."""
            self.assertIs(asyncio.current_task(), owner)
            raise rollback_error

        connection = SimpleNamespace(
            begin=AsyncMock(),
            commit=AsyncMock(),
            rollback=AsyncMock(side_effect=rollback),
        )
        app, runtime, handler = activate_runtime()
        self.addAsyncCleanup(runtime.shutdown)
        with operation(app):
            with self.assertRaises(ValueError) as caught:
                async with Transaction(connection):
                    raise body_error
            await runtime.drain()
        self.assertIs(caught.exception, body_error)
        self.assertEqual(handler.reports, [rollback_error])
        connection.commit.assert_not_awaited()

    async def testConcurrentWorkerCloseWaitsForOwnedWork(self) -> None:
        """Keep all close callers waiting until the worker releases its thread."""
        worker = ThreadedWorker()
        entered, release = Event(), Event()

        def blocked() -> str:
            """Retain the worker until its owner explicitly releases the barrier."""
            entered.set()
            if not release.wait(5):
                message = "The test did not release its database worker."
                raise TimeoutError(message)
            return "completed"

        work = asyncio.create_task(worker.run(blocked))
        closers = []
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait, 2))
            closers.append(asyncio.create_task(worker.close()))
            await asyncio.sleep(0)
            closers.append(asyncio.create_task(worker.close()))
            done, _ = await asyncio.wait(closers, timeout=0.02)
            self.assertFalse(done)
        finally:
            release.set()
            await asyncio.gather(work, *closers, return_exceptions=True)
            await worker.close()
        self.assertEqual(work.result(), "completed")

    async def testWorkerCloseCannotOvertakeCancelledResultCleanup(self) -> None:
        """Keep a late resource owned until cancellation cleanup has run."""
        worker = ThreadedWorker()
        entered, release = Event(), Event()
        resource = object()
        disposed = []

        def acquire() -> object:
            """Produce a controlled resource after cancellation can be requested."""
            entered.set()
            if not release.wait(5):
                message = "The test did not release its database acquisition."
                raise TimeoutError(message)
            return resource

        pending = asyncio.create_task(worker.run(acquire, on_cancel=disposed.append))
        closing = None
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait, 2))
            pending.cancel()
            closing = asyncio.create_task(worker.close())
            await asyncio.sleep(0)
        finally:
            release.set()
            await asyncio.gather(
                pending,
                *(task for task in (closing,) if task is not None),
                return_exceptions=True,
            )
            await worker.close()
        self.assertTrue(pending.cancelled())
        self.assertEqual(disposed, [resource])

    async def testConcurrentCheckoutCloseWaitsForTheSameRelease(self) -> None:
        """Join an already-started checkout release from every close caller."""
        entered, release = Event(), Event()

        def release_checkout() -> None:
            """Hold the native checkout release behind the fixture barrier."""
            entered.set()
            if not release.wait(5):
                message = "The test did not release its native checkout."
                raise TimeoutError(message)

        connection = ThreadedConnection(
            SimpleNamespace(close=release_checkout),
            ThreadedWorker(),
        )
        closers = [asyncio.create_task(connection.close())]
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait, 2))
            closers.append(asyncio.create_task(connection.close()))
            done, _ = await asyncio.wait(closers, timeout=0.02)
            self.assertFalse(done)
        finally:
            release.set()
            await asyncio.gather(*closers, return_exceptions=True)
            await connection.close()

    async def testCursorCleanupCannotReplaceMaterializationFailure(self) -> None:
        """Preserve failed materialization and observe cursor cleanup separately."""
        body_error = ValueError("controlled materialization failure")
        close_error = RuntimeError("controlled cursor close failure")
        result = SimpleNamespace(
            rowcount=1,
            is_insert=False,
            returns_rows=True,
            freeze=Mock(side_effect=body_error),
            close=Mock(side_effect=close_error),
        )
        app, runtime, handler = activate_runtime()
        self.addAsyncCleanup(runtime.shutdown)
        with operation(app):
            with self.assertRaises(ValueError) as caught:
                ThreadedResult(result)
            await runtime.drain()
        self.assertIs(caught.exception, body_error)
        self.assertEqual(handler.reports, [close_error])

    async def testLateDriverFailureIsRedactedBeforeCentralReporting(self) -> None:
        """Keep SQL and bindings out of late cancellation diagnostics."""
        marker = "controlled-private-database-binding"
        failure = OperationalError(
            "SELECT :value",
            {"value": marker},
            RuntimeError(marker),
        )
        app, runtime, handler = activate_runtime()
        self.addAsyncCleanup(runtime.shutdown)
        future = asyncio.get_running_loop().create_future()
        with operation(app):
            pending = asyncio.create_task(_wait_for_completion(future))
            await asyncio.sleep(0)
            pending.cancel()
            future.set_exception(failure)
            await asyncio.gather(pending, return_exceptions=True)
            await runtime.drain()
        self.assertTrue(pending.cancelled())
        self.assertEqual(len(handler.reports), 1)
        observed = handler.reports[0]
        self.assertIsInstance(observed, QueryException)
        self.assertNotIn(marker, str(observed))
        self.assertIn("OperationalError", str(observed))
        self.assertIsNone(observed.__cause__)

    async def testImplicitCleanupCannotReplaceTheOperationFailure(self) -> None:
        """Preserve the body while sanitizing both rollback and close failures."""
        marker = "controlled-private-cleanup-binding"
        body_error = ValueError("controlled query processing failure")
        transaction = SimpleNamespace(
            __aenter__=AsyncMock(),
            __aexit__=AsyncMock(
                side_effect=OperationalError(
                    "ROLLBACK :value",
                    {"value": marker},
                    RuntimeError(marker),
                ),
            ),
        )
        raw = SimpleNamespace(
            begin=Mock(return_value=transaction),
            invalidate=AsyncMock(),
            close=AsyncMock(
                side_effect=OperationalError(
                    "CLOSE :value",
                    {"value": marker},
                    RuntimeError(marker),
                ),
            ),
        )
        connection = Connection("controlled", {"driver": "sqlite"})
        connection._engine = SimpleNamespace(connect=AsyncMock(return_value=raw))
        app, runtime, handler = activate_runtime()
        self.addAsyncCleanup(runtime.shutdown)
        with operation(app):
            with self.assertRaises(ValueError) as caught:
                async with connection._acquire():
                    raise body_error
            await runtime.drain()
        self.assertIs(caught.exception, body_error)
        self.assertEqual(len(handler.reports), 2)
        for observed in handler.reports:
            self.assertIsInstance(observed, QueryException)
            self.assertNotIn(marker, str(observed))

    async def testManualControlPreservesItsFailureWhenCloseAlsoFails(self) -> None:
        """Keep the sanitized control failure ahead of a secondary release error."""
        for action in ("begin", "commit", "rollback"):
            with self.subTest(action=action):
                first = IntegrityError("CONTROL", {}, RuntimeError("control"))
                later = OperationalError("CLOSE", {}, RuntimeError("close"))
                transaction = SimpleNamespace(
                    commit=AsyncMock(side_effect=first),
                    rollback=AsyncMock(side_effect=first),
                )
                raw = SimpleNamespace(
                    begin=AsyncMock(side_effect=first),
                    close=AsyncMock(side_effect=later),
                )
                connection = Connection("controlled", {"driver": "sqlite"})
                connection._engine = SimpleNamespace(
                    connect=AsyncMock(return_value=raw),
                )
                if action != "begin":
                    connection._tx_state.set(_TransactionState(raw, transaction))
                app, runtime, handler = activate_runtime()
                try:
                    with operation(app):
                        with self.assertRaises(TransactionException) as caught:
                            await getattr(connection, action)()
                        await runtime.drain()
                    self.assertIn("IntegrityError", str(caught.exception))
                    self.assertFalse(connection.inTransaction())
                    self.assertEqual(len(handler.reports), 1)
                    self.assertIsInstance(handler.reports[0], QueryException)
                    self.assertIn("OperationalError", str(handler.reports[0]))
                finally:
                    await runtime.shutdown()

    async def testCleanupDoesNotInheritAnUnrelatedCallerException(self) -> None:
        """Propagate a new release failure when called inside another except block."""
        app, runtime, handler = activate_runtime()
        self.addAsyncCleanup(runtime.shutdown)
        for action in ("cursor", "implicit", "commit", "rollback", "engine"):
            with self.subTest(action=action), operation(app):
                failure = OperationalError("CLOSE", {}, RuntimeError("close"))
                transaction = SimpleNamespace(
                    __aenter__=AsyncMock(),
                    __aexit__=AsyncMock(),
                    commit=AsyncMock(),
                    rollback=AsyncMock(),
                )
                raw = SimpleNamespace(
                    begin=Mock(return_value=transaction),
                    close=AsyncMock(side_effect=failure),
                )
                connection = Connection("controlled", {"driver": "sqlite"})
                connection._engine = SimpleNamespace(
                    connect=AsyncMock(return_value=raw),
                )
                if action in {"commit", "rollback"}:
                    connection._tx_state.set(_TransactionState(raw, transaction))
                expected = OperationalError if action == "cursor" else QueryException
                try:
                    message = "An unrelated failure already handled by the caller"
                    raise ValueError(message)
                except ValueError:
                    with self.assertRaises(expected):
                        if action == "cursor":
                            ThreadedResult(
                                SimpleNamespace(
                                    rowcount=0,
                                    is_insert=False,
                                    returns_rows=False,
                                    close=Mock(side_effect=failure),
                                ),
                            )
                        elif action == "implicit":
                            async with connection._acquire():
                                pass
                        elif action == "engine":
                            engine = ThreadedEngine(SimpleNamespace())
                            raw.begin = AsyncMock(return_value=transaction)
                            with patch.object(
                                ThreadedEngine,
                                "connect",
                                AsyncMock(return_value=raw),
                            ):
                                async with engine.begin():
                                    pass
                        else:
                            await getattr(connection, action)()
                await runtime.drain()
        self.assertEqual(handler.reports, [])

    def testPublicDatabaseAnnotationsResolveAtRuntime(self) -> None:
        """Resolve concrete, contract and threaded bridge method annotations."""
        with self.subTest(function="_wait_for_completion"):
            self.assertIn("return", get_type_hints(_wait_for_completion))
        for klass in (
            Connection,
            ConnectionManager,
            Transaction,
            _TransactionState,
            IConnection,
            IConnectionManager,
            ITransaction,
            ThreadedConnection,
            ThreadedEngine,
            ThreadedResult,
            ThreadedTransaction,
            ThreadedWorker,
        ):
            for name, descriptor in vars(klass).items():
                method = (
                    descriptor.__func__
                    if isinstance(descriptor, (classmethod, staticmethod))
                    else descriptor
                )
                if inspect.isfunction(method):
                    with self.subTest(klass=klass.__name__, method=name):
                        self.assertIn("return", get_type_hints(method))

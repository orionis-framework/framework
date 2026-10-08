import asyncio
import json
import os
import sys
from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from uuid import uuid4
from orionis import Application
from orionis.database.contracts.connection_manager import IConnectionManager
from orionis.logging.contracts.logger import ILogger
from orionis.queues.contracts.manager import IQueueManager
from orionis.queues.contracts.serializer import IJobSerializer
from orionis.queues.serializer import JobSerializer
from orionis.support.facades.queue import Queue
from orionis.test import TestCase
from tests.queues.test_worker import ScopedService, State

if TYPE_CHECKING:
    from orionis.queues.contracts.driver import IQueueDriver
    from orionis.queues.job import BaseJob

_JOB_PACKAGE = "queue_probe_jobs"
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

class TransactionRollback(RuntimeError):
    """Trigger rollback of an application-owned test transaction."""

    __slots__ = ()

def verify_equal(actual: object, expected: object, message: str) -> None:
    """Verify a probe result without relying on interpreter assert settings.

    Parameters
    ----------
    actual : object
        Observed runtime result.
    expected : object
        Required behavior.
    message : str
        Failure description for subprocess output.
    """
    if actual != expected:
        error = f"{message}: expected {expected!r}, received {actual!r}."
        raise AssertionError(error)

def create_application(directory: str, driver: str) -> Application:
    """Configure an actual application with isolated durable queue storage.

    Parameters
    ----------
    directory : str
        Temporary application root and SQLite database directory.
    driver : str
        Connection used for public dispatch and command consumption.

    Returns
    -------
    Application
        Created application awaiting its real async provider boot.
    """
    base_path = Path(directory)
    (base_path / "app/console/commands").mkdir(parents=True)
    jobs_path = base_path / _JOB_PACKAGE
    jobs_path.mkdir()
    (jobs_path / "probe.py").write_text(
        "from tests.queues.test_worker import FailJob as _FailJob\n"
        "from tests.queues.test_worker import RecordJob as _RecordJob\n"
        "\n"
        "class RecordJob(_RecordJob):\n"
        '    """Record execution for a path-discovered application job."""\n'
        "    __slots__ = ()\n"
        "\n"
        "class FailJob(_FailJob):\n"
        '    """Exercise retries for a path-discovered application job."""\n'
        "    __slots__ = ()\n",
        encoding="utf-8",
    )
    sys.path.insert(0, str(base_path))
    app = Application(base_path=base_path)
    app.withConfigPaths(app_jobs=jobs_path)
    app.withRouting(console=[])
    app.withConfigDatabase(
        default="sqlite",
        connections={"sqlite": {
            "driver": "sqlite", "database": str(base_path / "queue.sqlite"),
            "journal_mode": "WAL", "busy_timeout": 30000,
        }},
    )
    app.withConfigQueue(
        default=driver,
        connections={
            "database": {"driver": "database", "retry_after": 2.0},
            "redis": {
                "driver": "redis", "retry_after": 2.0,
                "endpoint": os.environ.get(
                    "ORIONIS_QUEUE_REDIS_HOST", "127.0.0.1",
                ),
                "port": int(os.environ.get("ORIONIS_QUEUE_REDIS_PORT", "6379")),
                "db": int(os.environ.get("ORIONIS_QUEUE_REDIS_DB", "0")),
                "password": os.environ.get("ORIONIS_QUEUE_REDIS_PASSWORD"),
                "prefix": f"orionis:e2e:{uuid4().hex}",
            },
            "sync": {"driver": "sync", "retry_after": 2.0},
        },
        worker={"timeout": 0.5, "backoff": (0.01, 0.02), "sleep": 0.01},
    )
    app.create()
    verify_equal(app.path("app_jobs"), jobs_path.resolve(), "Custom jobs path")
    return app

def create_job(value: int, *, fail: bool = False) -> BaseJob:
    """Create a job declared in the temporary application's resolved directory.

    Parameters
    ----------
    value : int
        Persistent value observed during execution.
    fail : bool, optional
        Select the job that raises an application exception.

    Returns
    -------
    BaseJob
        Concrete application job discovered through its configured path.
    """
    module = import_module(_JOB_PACKAGE + ".probe")
    job_type = module.FailJob if fail else module.RecordJob
    return job_type(value)

async def call_command(app: Application, *arguments: str) -> None:
    """Invoke Reactor through the application's actual CLI lifecycle.

    Parameters
    ----------
    app : Application
        Current bootstrapped application.
    *arguments : str
        Signature and command-line arguments.
    """
    result = await app.handleCommand(["reactor", *arguments])
    verify_equal(result, 0, f"Reactor command {' '.join(arguments)}")

async def verify_transactions(app: Application, manager: IQueueManager) -> None:
    """Verify inline pending dispatch joins cold and warm SQLite transactions.

    Parameters
    ----------
    app : Application
        Actual application providing database services.
    manager : IQueueManager
        Queue manager whose database connection shares task-owned transactions.
    """
    databases = await app.make(IConnectionManager)
    connection = databases.connection()
    driver = await manager.connection("database")
    try:
        async with connection.transaction():
            await (
                Queue.dispatch(create_job(201))
                .onConnection("database").onQueue("transactions")
            )
            message = "Roll back the cold queue schema and its dispatch."
            raise TransactionRollback(message)
    except TransactionRollback:
        verify_equal(await driver.size("transactions"), 0, "Cold dispatch rollback")
    async with connection.transaction():
        await (
            Queue.dispatch(create_job(202))
            .onConnection("database").onQueue("transactions")
        )
    verify_equal(await driver.size("transactions"), 1, "Committed dispatch")
    await call_command(
        app, "queue:work", "database", "--queue=transactions", "--stop-when-empty",
    )
    verify_equal(await driver.size("transactions"), 0, "Committed job acknowledgement")
    try:
        async with connection.transaction():
            await (
                Queue.dispatch(create_job(203))
                .onConnection("database").onQueue("transactions")
            )
            message = "Roll back a dispatch after durable schema bootstrap."
            raise TransactionRollback(message)
    except TransactionRollback:
        verify_equal(await driver.size("transactions"), 0, "Warm dispatch rollback")

async def verify_success(
    app: Application, driver_name: str, driver: IQueueDriver, state: State,
) -> None:
    """Verify facade chaining, prioritized consumption, and real scoped DI.

    Parameters
    ----------
    app : Application
        Bootstrapped application exposing Reactor commands.
    driver_name : str
        Durable connection selected by public dispatch.
    driver : IQueueDriver
        Real persistent backend.
    state : State
        Shared application observation service.
    """
    await (
        Queue.dispatch(create_job(1)).onConnection(driver_name).onQueue("high")
    )
    await Queue.dispatch(create_job(2))
    delayed = (
        Queue.dispatch(create_job(3))
        .onConnection(driver_name).onQueue("emails").delay(seconds=0.03)
    )
    verify_equal(await driver.size("emails"), 0, "Pending dispatch performs no push")
    await delayed
    verify_equal(
        await driver.reserve(("emails",), 2.0), None, "Delayed job not ready early",
    )
    await asyncio.sleep(0.04)
    state.events.clear()
    await call_command(
        app, "queue:work", driver_name, "--queue=high,default,emails",
        "--concurrency=3", "--stop-when-empty",
    )
    verify_equal(
        sorted(event[0] for event in state.events), [1, 2, 3],
        "Deserialized jobs receive application dependencies",
    )
    verify_equal(
        {event[1] for event in state.events}, {"high", "default", "emails"},
        "Logical queue selections preserved",
    )
    verify_equal(
        len({id(event[3]) for event in state.events}), 3,
        "Every job receives a distinct scoped service",
    )
    verify_equal([event[2] for event in state.events], [1, 1, 1], "Initial attempts")
    for queue in ("high", "default", "emails"):
        verify_equal(await driver.size(queue), 0, f"Successful {queue} acknowledgement")

async def verify_failures(
    app: Application, manager: IQueueManager, driver_name: str,
    driver: IQueueDriver, state: State,
) -> None:
    """Verify persistent retries and failure administration through Reactor.

    Parameters
    ----------
    app : Application
        Bootstrapped application providing the actual CLI runtime.
    manager : IQueueManager
        Queue service shared by facade dispatch and commands.
    driver_name : str
        Durable connection used for failing work.
    driver : IQueueDriver
        Persistent backend whose attempt state can be inspected.
    state : State
        Application service observing injected contexts and scopes.
    """
    repository = await manager.failed()
    original_job_id = await Queue.dispatch(create_job(101, fail=True))
    state.events.clear()
    await call_command(app, "queue:work", driver_name, "--max-jobs=3")
    verify_equal(
        [event[2] for event in state.events], [1, 2, 3], "Retry attempt budget",
    )
    failures = await repository.all()
    verify_equal(len(failures), 1, "One terminal failure event")
    failed = failures[0]
    failed_id = failed.id
    verify_equal(failed.job_id, original_job_id, "Failure retains dispatch identity")
    verify_equal(failed.attempts, 3, "Terminal failure retains attempts")
    verify_equal(
        failed.exception_message, "Application job failure", "Original exception",
    )
    verify_equal(await driver.size("default"), 0, "Failed job removed from queue")
    await call_command(app, "queue:failed")
    await call_command(app, "queue:retry", failed_id)
    verify_equal(await repository.find(failed_id), None, "Retried failure removed")
    reserved = await driver.reserve(("default",), 2.0)
    verify_equal(reserved.id, original_job_id, "Retry preserves dispatch identity")
    verify_equal(reserved.attempts, 1, "Retry resets backend attempts")
    await call_command(app, "queue:clear", driver_name)
    verify_equal(await driver.size("default"), 0, "Clear removes active reservations")
    await Queue.dispatch(create_job(102, fail=True))
    await call_command(app, "queue:work", driver_name, "--max-jobs=3")
    forgotten = (await repository.all())[0]
    await call_command(app, "queue:forget", forgotten.id)
    verify_equal(await repository.all(), (), "Forget removes only failure records")
    result = await app.handleCommand(["reactor", "queue:forget", "missing"])
    verify_equal(result, 1, "Missing failure returns a failure exit code")

async def run_probe(driver_name: str = "database") -> dict[str, object]:
    """Execute public queue workflows in an isolated real application process.

    Parameters
    ----------
    driver_name : str, optional
        Database by default or explicit Redis for opt-in server verification.

    Returns
    -------
    dict[str, object]
        Verified lifecycle capabilities and backend identity.
    """
    with TemporaryDirectory() as directory:
        app = create_application(directory, driver_name)
        state = State()
        app.instance(State, state)
        app.scoped(ScopedService, ScopedService)
        try:
            await call_command(app, "queue:failed")
            manager = await app.make(IQueueManager)
            source = JobSerializer()
            job = create_job(77)
            source.register(type(job))
            identity, payload = source.encode(job)
            worker_codec = await app.make(IJobSerializer)
            verify_equal(
                worker_codec.decode(identity, payload).value, 77,
                "Worker discovers jobs before their first dispatch",
            )
            driver = await manager.connection(driver_name)
            await verify_transactions(app, manager)
            await verify_success(app, driver_name, driver, state)
            await verify_failures(app, manager, driver_name, driver, state)
        finally:
            manager = await app.make(IQueueManager)
            await manager.close()
            databases = await app.make(IConnectionManager)
            await databases.disconnect()
            logger = await app.make(ILogger)
            await asyncio.to_thread(logger.close)
    return {
        "driver": driver_name, "success_jobs": 3, "scoped_services": 3,
        "job_discovery": "app_jobs",
        "failure_attempts": 6, "transactions": "cold/warm rollback and commit",
        "cli": "work/failed/retry/forget/clear",
    }

async def main() -> None:
    """Run a bounded probe and emit its verified result as JSON."""
    driver_name = sys.argv[1] if len(sys.argv) > 1 else "database"
    async with asyncio.timeout(30):
        result = await run_probe(driver_name)
    sys.stdout.write("ORIONIS_QUEUE_E2E=" + json.dumps(result) + "\n")

class TestQueueApplicationIntegration(TestCase):
    """Verify eager providers and public workflows in a real application."""

    __slots__ = ()

    async def testRealApplicationDispatchWorkerFailureAndTransactions(self) -> None:
        """Exercise persisted dispatch, scoped DI, retries, CLI, and transactions."""
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-B", "-X", "utf8", "-m",
            "tests.queues.test_integration",
            cwd=_REPOSITORY_ROOT,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            output, errors = await asyncio.wait_for(process.communicate(), timeout=45)
        except TimeoutError:
            process.kill()
            await process.wait()
            raise
        self.assertEqual(process.returncode, 0, (output + errors).decode("utf-8"))
        result_line = next(
            (line for line in output.decode("utf-8").splitlines()
             if line.startswith("ORIONIS_QUEUE_E2E=")),
        )
        result = json.loads(result_line.partition("=")[2])
        self.assertEqual(result["driver"], "database")
        self.assertEqual(result["job_discovery"], "app_jobs")
        self.assertEqual(result["success_jobs"], 3)
        self.assertEqual(result["scoped_services"], 3)
        self.assertEqual(result["failure_attempts"], 6)
        self.assertEqual(result["cli"], "work/failed/retry/forget/clear")

if __name__ == "__main__":
    asyncio.run(main())

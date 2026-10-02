import argparse
import ast
import asyncio
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from orionis.console.commands.make.job import MakeJob
from orionis.console.commands.queue.clear import QueueClearCommand
from orionis.console.commands.queue.failed import QueueFailedCommand
from orionis.console.commands.queue.forget import QueueForgetCommand
from orionis.console.commands.queue.retry import QueueRetryCommand
from orionis.console.commands.queue.work import QueueWorkCommand
from orionis.console.core.commands import CORE_COMMANDS
from orionis.console.core.loader import Loader
from orionis.queues.entities.failed_job import FailedJob
from orionis.queues.exceptions import QueueConfigurationError
from orionis.test import TestCase

if TYPE_CHECKING:
    from orionis.console.base.command import BaseCommand


class _RecordedOutput:
    """Record console messages while retaining real command behavior."""

    __slots__ = ()

    def info(self, message: str, *, timestamp: bool = True) -> None:
        """Store an informational command message.

        Parameters
        ----------
        message : str
            Message emitted by the command.
        timestamp : bool, optional
            Whether a timestamp was requested.
        """
        self.messages.append(("info", message, timestamp))

    def success(self, message: str, *, timestamp: bool = True) -> None:
        """Store a successful command message.

        Parameters
        ----------
        message : str
            Message emitted by the command.
        timestamp : bool, optional
            Whether a timestamp was requested.
        """
        self.messages.append(("success", message, timestamp))

    def error(self, message: str, *, timestamp: bool = True) -> None:
        """Store an error command message.

        Parameters
        ----------
        message : str
            Message emitted by the command.
        timestamp : bool, optional
            Whether a timestamp was requested.
        """
        self.messages.append(("error", message, timestamp))


def _record(command_type: type[BaseCommand]) -> BaseCommand:
    """Create a command with explicit output records.

    Parameters
    ----------
    command_type : type[BaseCommand]
        Concrete Reactor command to instantiate.

    Returns
    -------
    BaseCommand
        Real command with console output replaced by records.
    """
    recorded = type(
        "Recorded" + command_type.__name__,
        (_RecordedOutput, command_type),
        {"__slots__": ("messages",)},
    )()
    recorded.messages = []
    return recorded


class _Worker:
    """Record worker execution without creating backend resources."""

    __slots__ = ("options", "stopped")

    def __init__(self) -> None:
        """Initialize empty execution and shutdown records."""
        self.options: dict[str, object] = {}
        self.stopped = False

    async def run(
        self, *, stop_when_empty: bool = False, max_jobs: int | None = None,
    ) -> int:
        """Record worker stopping options and return a processed attempt count.

        Parameters
        ----------
        stop_when_empty : bool, optional
            Whether an empty queue should end consumption.
        max_jobs : int | None, optional
            Maximum reservations requested by the command.

        Returns
        -------
        int
            Fixed processed attempt count for output assertions.
        """
        self.options = {"stop_when_empty": stop_when_empty, "max_jobs": max_jobs}
        return 4

    def stop(self) -> None:
        """Record a graceful shutdown request."""
        self.stopped = True


class _Repository:
    """Provide explicit failure listing and deletion behavior."""

    __slots__ = ("failures", "forgotten")

    def __init__(self) -> None:
        """Initialize empty persistent failure records."""
        self.failures: tuple[FailedJob, ...] = ()
        self.forgotten: list[str] = []

    async def all(self) -> tuple[FailedJob, ...]:
        """Return the configured failed jobs.

        Returns
        -------
        tuple[FailedJob, ...]
            Immutable failure records for command output.
        """
        return self.failures

    async def forget(self, failed_id: str) -> bool:
        """Delete a present failure and record the requested identifier.

        Parameters
        ----------
        failed_id : str
            Failure record selected by the command.

        Returns
        -------
        bool
            Whether the requested record exists.
        """
        self.forgotten.append(failed_id)
        return any(failure.id == failed_id for failure in self.failures)


class _Driver:
    """Record clearing of one logical queue."""

    __slots__ = ("cleared",)

    def __init__(self) -> None:
        """Initialize cleared queue records."""
        self.cleared: list[str] = []

    async def clear(self, queue: str) -> int:
        """Record the queue and return its removed job count.

        Parameters
        ----------
        queue : str
            Logical channel to clear.

        Returns
        -------
        int
            Removed job count used in command output.
        """
        self.cleared.append(queue)
        return 2


class _Manager:
    """Provide queue administration services with controllable errors."""

    __slots__ = (
        "driver", "error", "repository", "retried", "selected", "worker_object",
    )

    def __init__(self) -> None:
        """Prepare independent command service doubles."""
        self.driver = _Driver()
        self.repository = _Repository()
        self.worker_object = _Worker()
        self.error: QueueConfigurationError | None = None
        self.retried: list[str] = []
        self.selected: dict[str, object] = {}

    async def connection(self, name: str | None = None) -> _Driver:
        """Resolve a selected backend or raise the configured error.

        Parameters
        ----------
        name : str | None, optional
            Selected connection name.

        Returns
        -------
        _Driver
            Explicit queue driver double.
        """
        if self.error is not None:
            raise self.error
        self.selected = {"connection": name}
        return self.driver

    async def worker(self, **options: object) -> _Worker:
        """Record worker selection and return the configured runtime.

        Parameters
        ----------
        **options : object
            Connection, queue priority, and concurrency selections.

        Returns
        -------
        _Worker
            Explicit worker double.
        """
        if self.error is not None:
            raise self.error
        self.selected = options
        return self.worker_object

    async def failed(self) -> _Repository:
        """Resolve the explicit failed-job repository.

        Returns
        -------
        _Repository
            Failure storage double.
        """
        if self.error is not None:
            raise self.error
        return self.repository

    async def retryFailed(self, failed_id: str) -> str:
        """Record retry selection and return a fresh dispatch identifier.

        Parameters
        ----------
        failed_id : str
            Failure identifier selected by the command.

        Returns
        -------
        str
            Fresh job identifier used in success output.
        """
        if self.error is not None:
            raise self.error
        self.retried.append(failed_id)
        return "fresh-job"


class _Application:
    """Supply real temporary directories for command discovery and generation."""

    __slots__ = ("basePath",)
    compiled = False

    def __init__(self, directory: str) -> None:
        """Store the application root.

        Parameters
        ----------
        directory : str
            Temporary application directory.
        """
        self.basePath = Path(directory)
        self.path("app_console_commands").mkdir(parents=True)

    def path(self, key: str) -> Path:
        """Resolve the requested application package path.

        Parameters
        ----------
        key : str
            Directory key used by generators and Loader.

        Returns
        -------
        Path
            Temporary command or job directory.
        """
        relative = "app/jobs" if key == "app_jobs" else "app/console/commands"
        return self.basePath / relative

    def routingPaths(self, _key: str) -> list[Path]:
        """Provide no custom console route modules.

        Parameters
        ----------
        _key : str
            Console route selector.

        Returns
        -------
        list[Path]
            Empty routing module list.
        """
        return []


def _failure() -> FailedJob:
    """Build a real immutable failure record for command assertions.

    Returns
    -------
    FailedJob
        Stored job routing and original exception details.
    """
    return FailedJob(
        id="failed-id", job_id="job-id", connection="database", queue="emails",
        payload=b"payload", exception_type="ValueError", exception_message="broken",
        traceback="original traceback", failed_at=1.0, attempts=3,
    )


class TestQueueCommands(TestCase):
    """Verify real parser definitions and queue administration behavior."""

    __slots__ = ()

    async def testCoreLoaderDiscoversEveryQueueCommand(self) -> None:
        """Discover canonical command classes through the real core Loader."""
        expected = {
            "make:job", "queue:work", "queue:failed", "queue:retry",
            "queue:forget", "queue:clear",
        }
        self.assertTrue(expected <= {command.signature for command in CORE_COMMANDS})
        with TemporaryDirectory() as directory:
            loader = Loader(_Application(directory))
            for signature in expected:
                command = await loader.get(signature)
                self.assertIsNotNone(command)
                self.assertEqual(command.signature, signature)

    def testWorkArgumentsPreservePriorityAndFlags(self) -> None:
        """Parse the documented worker invocation with Reactor Argument."""
        parser = argparse.ArgumentParser()
        for argument in QueueWorkCommand.arguments:
            argument.addToParser(parser)
        parsed = vars(parser.parse_args([
            "redis", "--queue=high,default", "--concurrency=50",
            "--stop-when-empty", "--max-jobs=5",
        ]))
        self.assertEqual(parsed, {
            "connection": "redis", "queue": "high,default", "concurrency": 50,
            "stop_when_empty": True, "max_jobs": 5,
        })

    async def testWorkRunsWithSelectedOptions(self) -> None:
        """Forward priority, concurrency, and stopping options to the worker."""
        manager = _Manager()
        command = _record(QueueWorkCommand)
        command.setArguments({
            "connection": "redis", "queue": "high, default", "concurrency": 50,
            "stop_when_empty": True, "max_jobs": 5,
        })
        self.assertEqual(await command.handle(manager), 0)
        self.assertEqual(manager.selected, {
            "connection": "redis", "queues": ("high", "default"), "concurrency": 50,
        })
        self.assertEqual(manager.worker_object.options, {
            "stop_when_empty": True, "max_jobs": 5,
        })
        self.assertIn("4 attempt(s)", command.messages[0][1])

    async def testFailureListingAndEmptyOutput(self) -> None:
        """Display stored original failures and the empty repository state."""
        manager = _Manager()
        command = _record(QueueFailedCommand)
        self.assertEqual(await command.handle(manager), 0)
        self.assertEqual(command.messages[0][1], "No failed jobs.")
        manager.repository.failures = (_failure(),)
        command.messages.clear()
        self.assertEqual(await command.handle(manager), 0)
        message = command.messages[0][1]
        self.assertIn("failed-id", message)
        self.assertIn("job=job-id", message)
        self.assertIn("database/emails", message)
        self.assertIn("ValueError: broken", message)

    async def testRetryForgetAndClearUseCanonicalServices(self) -> None:
        """Retry failures, delete records, and clear only the selected channel."""
        manager = _Manager()
        retry = _record(QueueRetryCommand)
        retry.setArguments({"id": "failed-id"})
        self.assertEqual(await retry.handle(manager), 0)
        self.assertEqual(manager.retried, ["failed-id"])
        self.assertIn("fresh-job", retry.messages[0][1])
        forget = _record(QueueForgetCommand)
        forget.setArguments({"id": "missing"})
        self.assertEqual(await forget.handle(manager), 1)
        manager.repository.failures = (_failure(),)
        forget.setArguments({"id": "failed-id"})
        self.assertEqual(await forget.handle(manager), 0)
        clear = _record(QueueClearCommand)
        clear.setArguments({"connection": "database", "queue": "emails"})
        self.assertEqual(await clear.handle(manager), 0)
        self.assertEqual(manager.selected, {"connection": "database"})
        self.assertEqual(manager.driver.cleared, ["emails"])
        self.assertIn("2 job(s)", clear.messages[0][1])

    async def testInvalidBackendProducesFailureExitCode(self) -> None:
        """Report queue service errors without successful command exit codes."""
        manager = _Manager()
        manager.error = QueueConfigurationError("Unknown connection 'missing'.")
        command_types = (
            QueueWorkCommand, QueueFailedCommand, QueueRetryCommand,
            QueueForgetCommand, QueueClearCommand,
        )
        for command_type in command_types:
            with self.subTest(command=command_type.signature):
                command = _record(command_type)
                command.setArguments({"id": "missing", "connection": "missing"})
                self.assertEqual(await command.handle(manager), 1)
                self.assertEqual(command.messages[0][0], "error")

    async def testMakeJobCreatesPersistentStateAndRuntimeDependencies(self) -> None:
        """Generate an importable annotated job without service constructor state."""
        with TemporaryDirectory() as directory:
            app = _Application(directory)
            command = _record(MakeJob)
            command.setArguments({"name": "emails/send_welcome"})
            await command.handle(app)
            generated = app.path("app_jobs") / "emails/send_welcome_job.py"
            self.assertTrue(generated.is_file())
            source = generated.read_text(encoding="utf-8")
            tree = ast.parse(source)
            job = next(node for node in tree.body if isinstance(node, ast.ClassDef))
            methods = {
                node.name: node for node in job.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            self.assertEqual(job.name, "SendWelcomeJob")
            self.assertEqual(
                [arg.arg for arg in methods["__init__"].args.args],
                ["self", "record_id"],
            )
            self.assertEqual(
                [arg.arg for arg in methods["handle"].args.args], ["self", "logger"],
            )
            self.assertNotIn("from __future__", source)
            self.assertNotIn("NotImplementedError", source)

    async def testSignalsStopWorkerAndRestorePreviousHandlers(self) -> None:
        """Request graceful shutdown and restore interpreter signal handlers."""
        script = '''
import asyncio
import signal
from tests.queues.console.test_commands import _Worker
from orionis.console.commands.queue._signals import WorkerSignals

async def probe():
    """Verify graceful signal delivery on the main event loop."""
    worker = _Worker()
    original = {
        signum: signal.getsignal(signum)
        for signum in (signal.SIGINT, signal.SIGTERM)
    }
    with WorkerSignals(worker):
        signal.raise_signal(signal.SIGTERM)
        await asyncio.sleep(0)
        assert worker.stopped
    for signum, handler in original.items():
        assert signal.getsignal(signum) is handler

asyncio.run(probe())
'''
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-X", "utf8", "-c", script,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        output, errors = await process.communicate()
        self.assertEqual(process.returncode, 0, (output + errors).decode("utf-8"))

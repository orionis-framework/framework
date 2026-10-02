import asyncio
import inspect
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4
from orionis.database.contracts.connection_manager import IConnectionManager
from orionis.foundation.config.queue import Queue as QueueConfig, Redis as RedisConfig
from orionis.foundation.contracts.application import IApplication  # noqa: TC001
from orionis.introspection.modules.inspector import ModuleInspector
from orionis.queues.contracts.manager import IQueueManager
from orionis.queues.contracts.serializer import IJobSerializer  # noqa: TC001
from orionis.queues.drivers.database import DatabaseQueueDriver
from orionis.queues.drivers.redis import RedisQueueDriver
from orionis.queues.drivers.sync import SyncQueueDriver
from orionis.queues.entities.envelope import JobEnvelope
from orionis.queues.exceptions import QueueConfigurationError, QueueRetryError
from orionis.queues.failed.repository import DatabaseFailedJobRepository
from orionis.queues.functions import current_time, validate_name, validate_seconds
from orionis.queues.job import BaseJob
from orionis.queues.pending import PendingDispatch
from orionis.queues.worker import Worker, WorkerOptions

if TYPE_CHECKING:
    from orionis.queues.contracts.driver import IQueueDriver
    from orionis.queues.contracts.failed_repository import IFailedJobRepository

def _discover_jobs(base_path: Path, jobs_path: Path) -> tuple[type[BaseJob], ...]:
    """
    Import modules from the application jobs directory and collect jobs.

    Parameters
    ----------
    base_path : Path
        Application root used to resolve Python module names.
    jobs_path : Path
        Jobs directory resolved from the application's ``app_jobs`` path.

    Returns
    -------
    tuple[type[BaseJob], ...]
        Concrete job classes defined in the discovered application modules.

    Raises
    ------
    QueueConfigurationError
        If a discovered module cannot be imported.
    """
    modules = {
        name.removesuffix(".__init__")
        for name in ModuleInspector.discoverModules(base_path, jobs_path)
    }
    discovered: set[type[BaseJob]] = set()
    for name in sorted(modules):
        try:
            module = import_module(name)
        except ImportError as exception:
            message = f"Application queue job module '{name}' cannot be imported."
            raise QueueConfigurationError(message) from exception
        for candidate in vars(module).values():
            if (
                inspect.isclass(candidate)
                and candidate is not BaseJob
                and issubclass(candidate, BaseJob)
                and not inspect.isabstract(candidate)
                and candidate.__module__ == module.__name__
            ):
                discovered.add(candidate)
    return tuple(discovered)


class QueueManager(IQueueManager):
    """Resolve lazy connections and expose the canonical deferred dispatch API."""

    __slots__ = (
        "_app",
        "_config",
        "_driver_lock",
        "_drivers",
        "_failed",
        "_failed_lock",
        "_serializer",
    )

    def __init__(self, app: IApplication, serializer: IJobSerializer) -> None:
        """
        Validate and serialize queue settings without opening backend clients.

        Parameters
        ----------
        app : IApplication
            Existing application container.
        serializer : IJobSerializer
            Singleton registered-job serializer.

        Returns
        -------
        None
            Retain the normalized wire settings for lazy backend resolution.

        Raises
        ------
        TypeError
            If queue settings have invalid types or unsupported fields.
        ValueError
            If queue settings or their storage relationships are invalid.
        """
        self._app = app
        self._serializer = serializer
        configuration = app.config("queue")
        self._config = QueueConfig(**configuration).toDict()
        self._drivers: dict[str, IQueueDriver] = {}
        self._driver_lock = asyncio.Lock()
        self._failed: IFailedJobRepository | None = None
        self._failed_lock = asyncio.Lock()

    async def boot(self) -> None:
        """
        Register jobs from the application's configured jobs path.

        Returns
        -------
        None
            Register discovered job classes with the shared serializer.

        Raises
        ------
        QueueConfigurationError
            If the jobs path is invalid or a discovered module cannot be imported.
        """
        jobs_path = self._app.path("app_jobs")
        if not isinstance(jobs_path, Path):
            message = "The application 'app_jobs' path must resolve to a Path."
            raise QueueConfigurationError(message)
        jobs = await asyncio.to_thread(_discover_jobs, self._app.basePath, jobs_path)
        for job_type in jobs:
            self._serializer.register(job_type)

    def dispatch(self, job: BaseJob) -> PendingDispatch:
        """
        Create one awaitable dispatch without serializing or persisting data.

        Parameters
        ----------
        job : BaseJob
            Application job containing persistent constructor state.

        Returns
        -------
        PendingDispatch
            Fluent operation submitted only when awaited.
        """
        if not isinstance(job, BaseJob):
            message = "Queue.dispatch() requires a BaseJob instance."
            raise QueueConfigurationError(message)
        return PendingDispatch(self._submit, job)

    def _connectionName(self, name: str | None) -> str:
        """
        Validate selection against the configured named backends.

        Parameters
        ----------
        name : str | None
            Explicit selection or central default.

        Returns
        -------
        str
            Existing configured connection name.
        """
        selected = self._config["default"] if name is None else name
        validate_name(selected, "Connection")
        if selected not in self._config["connections"]:
            message = f"Queue connection '{selected}' is not configured."
            raise QueueConfigurationError(message)
        return selected

    async def _submit(
        self,
        job: BaseJob,
        connection: str | None,
        queue: str | None,
        delay: float,
    ) -> str:
        """
        Serialize validated job options and submit to the selected backend.

        Parameters
        ----------
        job : BaseJob
            Job containing only declared serializable state.
        connection : str | None
            Explicit backend selection.
        queue : str | None
            Explicit channel selection.
        delay : float
            Delay in seconds before availability.

        Returns
        -------
        str
            Dispatch identifier.
        """
        selected = self._connectionName(connection)
        options = self._config["connections"][selected]
        channel = options["queue"] if queue is None else queue
        validate_name(channel, "Queue")
        self._serializer.register(type(job))
        identity, payload = self._serializer.encode(job)
        defaults = self._config["worker"]
        timeout = defaults["timeout"] if job.timeout is None else job.timeout
        timeout = validate_seconds(timeout, "Job timeout", positive=True)
        if timeout >= options["retry_after"]:
            message = "Job timeout must be shorter than connection retry_after."
            raise QueueConfigurationError(message)
        envelope = JobEnvelope(
            id=str(uuid4()), job=identity, payload=payload,
            connection=selected, queue=channel,
            max_tries=defaults["tries"] if job.tries is None else job.tries,
            timeout=timeout,
            backoff=defaults["backoff"] if job.backoff is None else job.backoff,
            retry_until=job.retryUntil(),
        )
        driver = await self.connection(selected)
        return await driver.push(envelope, delay)

    async def connection(self, name: str | None = None) -> IQueueDriver:
        """
        Resolve one shared lazy driver for the selected named connection.

        Parameters
        ----------
        name : str | None, optional
            Explicit connection or central default.

        Returns
        -------
        IQueueDriver
            Backend shared by its logical channels.
        """
        selected = self._connectionName(name)
        cached = self._drivers.get(selected)
        if cached is not None:
            return cached
        async with self._driver_lock:
            cached = self._drivers.get(selected)
            if cached is None:
                cached = await self._createDriver(selected)
                self._drivers[selected] = cached
            return cached

    async def _createDriver(self, name: str) -> IQueueDriver:
        """
        Construct a configured driver through framework database services.

        Parameters
        ----------
        name : str
            Validated configured connection name.

        Returns
        -------
        IQueueDriver
            Driver whose real I/O starts with its first operation.
        """
        options = self._config["connections"][name]
        if options["driver"] == "sync":
            return SyncQueueDriver(self._app, self._serializer, name, self.failed,
                                   retry_after=options["retry_after"])
        if options["driver"] == "redis":
            return RedisQueueDriver(RedisConfig(**options))
        manager = await self._app.make(IConnectionManager)
        return DatabaseQueueDriver(manager.connection(options["connection"]),
                                   options["table"])

    async def worker(
        self,
        connection: str | None = None,
        queues: tuple[str, ...] | None = None,
        concurrency: int | None = None,
    ) -> Worker:
        """
        Create an independent persistent worker using validated defaults.

        Parameters
        ----------
        connection : str | None, optional
            Explicit backend or central default.
        queues : tuple[str, ...] | None, optional
            Channels ordered by priority.
        concurrency : int | None, optional
            Simultaneous job executions or configured default.

        Returns
        -------
        Worker
            Consumer runtime sharing the existing application container.
        """
        selected = self._connectionName(connection)
        options = self._config["connections"][selected]
        if options["driver"] == "sync":
            message = (
                "The sync connection executes during dispatch; "
                "use a durable worker."
            )
            raise QueueConfigurationError(message)
        channels = (options["queue"],) if queues is None else queues
        for channel in channels:
            validate_name(channel, "Queue")
        driver = await self.connection(selected)
        settings = WorkerOptions(
            selected, queues=channels,
            concurrency=(self._config["worker"]["concurrency"]
                         if concurrency is None else concurrency),
            retry_after=options["retry_after"],
            sleep=self._config["worker"]["sleep"],
        )
        return Worker(self._app, driver, self._serializer, settings, self.failed)

    async def failed(self) -> IFailedJobRepository:
        """
        Resolve durable failed-job storage only when first requested.

        Returns
        -------
        IFailedJobRepository
            Repository shared by all queue connections.
        """
        if self._failed is not None:
            return self._failed
        async with self._failed_lock:
            if self._failed is None:
                manager = await self._app.make(IConnectionManager)
                options = self._config["failed"]
                self._failed = DatabaseFailedJobRepository(
                    manager.connection(options["connection"]), options["table"],
                )
            return self._failed

    async def retryFailed(self, failed_id: str) -> str:
        """
        Requeue preserved job data with attempts reset by a fresh push.

        Parameters
        ----------
        failed_id : str
            Failure record identifier.

        Returns
        -------
        str
            Restored job identifier.
        """
        repository = await self.failed()
        failed = await repository.find(failed_id)
        if failed is None:
            message = f"Failed queue job '{failed_id}' does not exist."
            raise QueueRetryError(message)
        envelope = self._serializer.decodeEnvelope(failed.payload)
        if (envelope.retry_until is not None
                and current_time() >= envelope.retry_until):
            message = "The failed job retry deadline has expired."
            raise QueueRetryError(message)
        driver = await self.connection(envelope.connection)
        dispatched = await driver.push(envelope)
        await repository.forget(failed_id)
        return dispatched

    async def close(self) -> None:
        """
        Release queue-owned resources without closing shared database services.

        Returns
        -------
        None
            Close cached drivers and any initialized failed-job repository,
            then clear their cached references.
        """
        for driver in self._drivers.values():
            await driver.close()
        self._drivers.clear()
        if self._failed is not None:
            await self._failed.close()
            self._failed = None

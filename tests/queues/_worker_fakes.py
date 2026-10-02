import asyncio
import traceback
from typing import TYPE_CHECKING, Self
from dataclasses import dataclass
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5
from orionis.container.container import Container
from orionis.foundation.contracts.application import IApplication
from orionis.foundation.core_paths import CORE_APP_PATHS
from orionis.queues.context import JobContext  # noqa: TC001
from orionis.queues.contracts.driver import IQueueDriver
from orionis.queues.contracts.failed_repository import IFailedJobRepository
from orionis.queues.entities.envelope import JobEnvelope
from orionis.queues.entities.failed_job import FailedJob
from orionis.queues.entities.reserved_job import ReservedJob
from orionis.queues.exceptions import QueueStorageError
from orionis.queues.functions import current_time
from orionis.queues.job import BaseJob
from orionis.queues.serializer import JobSerializer  # noqa: TC001

if TYPE_CHECKING:
    from collections.abc import Callable


class FakeApp(Container):
    """Expose queue configuration while retaining the real DI container."""

    __slots__ = ("_paths", "basePath", "hooks", "isBooted", "settings")

    def __new__(
        cls,
        settings: dict | None = None,
        *,
        base_path: Path | None = None,
        jobs_path: Path | None = None,
    ) -> Self:
        """Allocate an isolated container for each contractual test.

        Parameters
        ----------
        settings : dict | None, optional
            Settings consumed during initialization.
        base_path : Path | None, optional
            Application root consumed during initialization.
        jobs_path : Path | None, optional
            Jobs path consumed during initialization.

        Returns
        -------
        FakeApp
            Fresh test container instance.
        """
        del settings, base_path, jobs_path
        return object.__new__(cls)

    def __init__(
        self,
        settings: dict | None = None,
        *,
        base_path: Path | None = None,
        jobs_path: Path | None = None,
    ) -> None:
        """Initialize isolated configuration and real service bindings.

        Parameters
        ----------
        settings : dict | None, optional
            Explicit queue settings.
        base_path : Path | None, optional
            Application root, defaulting to a missing isolated test directory.
        jobs_path : Path | None, optional
            Override the default jobs path from ``CORE_APP_PATHS``.

        Returns
        -------
        None
            Initialize configuration, resolved paths, and service bindings.
        """
        super().__init__()
        self.settings = {} if settings is None else settings
        self.basePath = (
            Path(__file__).resolve().parent / "missing_application"
            if base_path is None else base_path
        )
        self._paths = {
            "app_jobs": self.basePath / CORE_APP_PATHS["app_jobs"]
            if jobs_path is None else jobs_path,
        }
        self.isBooted = True
        self.hooks: dict[object, set[Callable]] = {}

    def path(self, key: str) -> Path | None:
        """Return one centrally configured application path.

        Parameters
        ----------
        key : str
            Application path key.

        Returns
        -------
        Path | None
            Configured path, or None when the key is absent.
        """
        return self._paths.get(key)

    def on(self, event: object, *callbacks: Callable) -> Self:
        """Record lifecycle hooks using the application's callback contract.

        Parameters
        ----------
        event : object
            Framework lifecycle event.
        *callbacks : Callable
            Callbacks registered for this event.

        Returns
        -------
        Self
            Application stub supporting fluent registration.
        """
        self.hooks.setdefault(event, set()).update(callbacks)
        return self

    def config(self, key: str) -> dict:
        """Return this test application's queue settings.

        Parameters
        ----------
        key : str
            Configuration key required by the manager.

        Returns
        -------
        dict
            Canonical queue configuration.
        """
        del key
        return self.settings

    async def make(self, key: type | str, *args: object, **kwargs: object):
        """Resolve the application contract or delegate to real DI.

        Parameters
        ----------
        key : type | str
            Requested contract.
        *args : object
            Constructor arguments.
        **kwargs : object
            Constructor keyword arguments.

        Returns
        -------
        object
            Application or resolved service.
        """
        if key is IApplication:
            return self
        return await super().make(key, *args, **kwargs)


class State:
    """Collect DI identities, attempt counts and concurrency observations."""

    __slots__ = ("active", "entered", "events", "gate", "maximum")

    def __init__(self) -> None:
        """Initialize isolated execution observations."""
        self.events: list[tuple[int, str, int, object]] = []
        self.active = self.maximum = 0
        self.entered = asyncio.Event()
        self.gate = asyncio.Event()


class ScopedService:
    """Represent a dependency that must be isolated between jobs."""

    __slots__ = ()


class SlowApp(FakeApp):
    """Suspend scoped-service resolution to exercise timeout coverage of DI."""

    __slots__ = ()

    async def make(self, key: type | str, *args: object, **kwargs: object):
        """Delay scoped dependency construction before invoking real resolution.

        Parameters
        ----------
        key : type | str
            Requested service contract.
        *args : object
            Constructor arguments.
        **kwargs : object
            Constructor keyword arguments.

        Returns
        -------
        object
            Service resolved by the real container.
        """
        if key is ScopedService:
            await asyncio.sleep(0.1)
        return await super().make(key, *args, **kwargs)


class RecordJob(BaseJob):
    """Record an injected scope, context and value."""

    __slots__ = ("value",)
    value: int

    def __init__(self, value: int) -> None:
        """Store persistent job state.

        Parameters
        ----------
        value : int
            Value recorded during execution.
        """
        self.value = value

    async def handle(self, context: JobContext, service: ScopedService,
                     state: State) -> None:
        """Record context and dependency identity across concurrent jobs.

        Parameters
        ----------
        context : JobContext
            Current reservation.
        service : ScopedService
            Isolated scoped dependency.
        state : State
            Shared observation collector.
        """
        state.events.append((self.value, context.queue, context.attempts, service))
        state.active += 1
        state.maximum = max(state.maximum, state.active)
        try:
            await asyncio.sleep(0.001)
        finally:
            state.active -= 1


class FailJob(RecordJob):
    """Raise an original application exception on each attempt."""

    __slots__ = ()

    async def handle(self, context: JobContext, service: ScopedService,
                     state: State) -> None:
        """Record the attempt and raise an application failure.

        Parameters
        ----------
        context : JobContext
            Current reservation.
        service : ScopedService
            Isolated scoped dependency.
        state : State
            Shared observation collector.
        """
        await super().handle(context, service, state)
        message = "Application job failure"
        raise ValueError(message)


class ReleaseJob(RecordJob):
    """Release the first attempt explicitly and complete the next."""

    __slots__ = ()

    async def handle(self, context: JobContext, service: ScopedService,
                     state: State) -> None:
        """Record execution and release an unready job.

        Parameters
        ----------
        context : JobContext
            Current reservation.
        service : ScopedService
            Isolated scoped dependency.
        state : State
            Shared observation collector.
        """
        await super().handle(context, service, state)
        if context.attempts == 1:
            await context.release()


class GateJob(RecordJob):
    """Wait for the test to release an in-flight job."""

    __slots__ = ()

    async def handle(self, context: JobContext, service: ScopedService,
                     state: State) -> None:
        """Signal job entry and wait before completing.

        Parameters
        ----------
        context : JobContext
            Current reservation.
        service : ScopedService
            Isolated scoped dependency.
        state : State
            Shared observation collector.
        """
        state.entered.set()
        await state.gate.wait()
        await super().handle(context, service, state)


@dataclass(slots=True)
class Entry:
    """Retain mutable reservation state in the contractual fake backend."""

    envelope: JobEnvelope
    attempts: int = 0
    available: float = 0.0
    reserved_until: float = 0.0
    token: str = ""


class MemoryDriver(IQueueDriver):
    """Implement atomic task-local transitions for lifecycle tests."""

    __slots__ = ("broken", "closed", "entries", "releases", "serializer")

    def __init__(self, serializer: JobSerializer) -> None:
        """Initialize isolated test storage.

        Parameters
        ----------
        serializer : JobSerializer
            Shared job wire codec.
        """
        self.serializer = serializer
        self.entries: dict[str, Entry] = {}
        self.releases: list[float] = []
        self.closed = self.broken = False

    async def push(self, envelope: JobEnvelope, delay: float = 0.0) -> str:
        """Persist an immutable envelope for a future reservation.

        Parameters
        ----------
        envelope : JobEnvelope
            Encoded job metadata.
        delay : float, optional
            Availability delay.

        Returns
        -------
        str
            Dispatch identifier.
        """
        self.entries[envelope.id] = Entry(envelope,
                                         available=current_time() + delay)
        return envelope.id

    async def reserve(self, queues: tuple[str, ...],
                      retry_after: float) -> ReservedJob | None:
        """Claim one ready job in priority order.

        Parameters
        ----------
        queues : tuple[str, ...]
            Priority-ordered channels.
        retry_after : float
            Lease duration.

        Returns
        -------
        ReservedJob | None
            Newly fenced reservation.
        """
        now = current_time()
        for queue in queues:
            for entry in self.entries.values():
                if (entry.envelope.queue == queue and entry.available <= now
                        and entry.reserved_until <= now):
                    entry.attempts += 1
                    entry.token = uuid4().hex
                    entry.reserved_until = now + retry_after
                    return ReservedJob(
                        id=entry.envelope.id, queue=queue, token=entry.token,
                        payload=self.serializer.encodeEnvelope(entry.envelope),
                        attempts=entry.attempts,
                        reserved_until=entry.reserved_until,
                    )
        return None

    async def release(self, reserved: ReservedJob, delay: float = 0.0) -> bool:
        """Release an owned claim or emulate a storage failure.

        Parameters
        ----------
        reserved : ReservedJob
            Current reservation.
        delay : float, optional
            New availability delay.

        Returns
        -------
        bool
            Whether the claim was still owned.
        """
        if self.broken:
            message = "Storage transition failure"
            raise QueueStorageError(message)
        entry = self.entries.get(reserved.id)
        if entry is None or entry.token != reserved.token:
            return False
        entry.reserved_until = 0
        entry.available = current_time() + delay
        self.releases.append(delay)
        return True

    async def delete(self, reserved: ReservedJob) -> bool:
        """Delete only the fenced claim belonging to this execution.

        Parameters
        ----------
        reserved : ReservedJob
            Current reservation.

        Returns
        -------
        bool
            Whether deletion succeeded.
        """
        entry = self.entries.get(reserved.id)
        if entry is None or entry.token != reserved.token:
            return False
        del self.entries[reserved.id]
        return True

    async def size(self, queue: str) -> int:
        """Count all jobs on one logical channel.

        Parameters
        ----------
        queue : str
            Selected channel.

        Returns
        -------
        int
            Number of stored jobs.
        """
        return sum(entry.envelope.queue == queue for entry in self.entries.values())

    async def clear(self, queue: str) -> int:
        """Remove all jobs on a selected channel.

        Parameters
        ----------
        queue : str
            Selected channel.

        Returns
        -------
        int
            Number of removed jobs.
        """
        identifiers = [key for key, entry in self.entries.items()
                       if entry.envelope.queue == queue]
        for key in identifiers:
            del self.entries[key]
        return len(identifiers)

    async def close(self) -> None:
        """Record closure of resources owned by this fake."""
        self.closed = True


class FailedRepository(IFailedJobRepository):
    """Preserve original exceptions without an external database."""

    __slots__ = ("broken", "closed", "items")

    def __init__(self) -> None:
        """Initialize isolated failed-job records."""
        self.items: dict[str, FailedJob] = {}
        self.closed = self.broken = False

    async def record(self, reserved: ReservedJob, connection: str,
                     exception: Exception) -> FailedJob:
        """Preserve a terminal error and its retryable envelope.

        Parameters
        ----------
        reserved : ReservedJob
            Failed reservation.
        connection : str
            Backend name.
        exception : Exception
            Original application error.

        Returns
        -------
        FailedJob
            Stored failure data.
        """
        if self.broken:
            message = "Failure repository unavailable"
            raise QueueStorageError(message)
        failure = FailedJob(
            id=str(uuid5(NAMESPACE_URL, reserved.id + ":" + reserved.token)),
            job_id=reserved.id, connection=connection,
            queue=reserved.queue, payload=reserved.payload,
            exception_type=type(exception).__qualname__,
            exception_message=str(exception),
            traceback="".join(traceback.format_exception(exception)),
            failed_at=current_time(), attempts=reserved.attempts,
        )
        self.items[failure.id] = failure
        return failure

    async def all(self) -> tuple[FailedJob, ...]:
        """Return all recorded failures.

        Returns
        -------
        tuple[FailedJob, ...]
            Current failure records.
        """
        return tuple(self.items.values())

    async def find(self, failed_id: str) -> FailedJob | None:
        """Find one preserved failure.

        Parameters
        ----------
        failed_id : str
            Failure identifier.

        Returns
        -------
        FailedJob | None
            Matching record.
        """
        return self.items.get(failed_id)

    async def forget(self, failed_id: str) -> bool:
        """Remove a preserved failure.

        Parameters
        ----------
        failed_id : str
            Failure identifier.

        Returns
        -------
        bool
            Whether a record existed.
        """
        return self.items.pop(failed_id, None) is not None

    async def close(self) -> None:
        """Record repository resource cleanup."""
        self.closed = True


def envelope(serializer: JobSerializer, job: BaseJob, *, tries: int = 3,
             timeout: float = 0.5,
             options: dict | None = None) -> JobEnvelope:
    """Build real immutable wire metadata for a contractual test job.

    Parameters
    ----------
    serializer : JobSerializer
        Registered wire codec.
    job : BaseJob
        Job whose state must be persisted.
    tries : int, optional
        Maximum reservation budget.
    timeout : float, optional
        Cooperative execution timeout.
    options : dict | None, optional
        Explicit backoff and absolute retry deadline.

    Returns
    -------
    JobEnvelope
        Valid dispatch metadata.
    """
    identity, payload = serializer.encode(job)
    settings = {} if options is None else options
    return JobEnvelope(id=str(uuid4()), job=identity, payload=payload,
                       connection="database", queue="default", max_tries=tries,
                       timeout=timeout, backoff=settings.get("backoff", (0.0,)),
                       retry_until=settings.get("retry_until"))

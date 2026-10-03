import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING
from dataclasses import dataclass
from orionis.queues.context import JobContext
from orionis.queues.contracts.worker import IWorker
from orionis.queues.exceptions import (
    QueueConfigurationError, QueuePayloadError, QueueRetryError,
)
from orionis.queues.functions import current_time, validate_name, validate_seconds

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication
    from orionis.queues.contracts.driver import IQueueDriver
    from orionis.queues.contracts.failed_repository import IFailedJobRepository
    from orionis.queues.contracts.serializer import IJobSerializer
    from orionis.queues.entities.envelope import JobEnvelope
    from orionis.queues.entities.reserved_job import ReservedJob

_LOGGER = logging.getLogger(__name__)
type FailedResolver = Callable[[], Awaitable[IFailedJobRepository]]

@dataclass(frozen=True, slots=True)
class WorkerOptions:
    """Retain stable validated settings for an independent worker runtime."""

    connection: str
    queues: tuple[str, ...] = ("default",)
    concurrency: int = 1
    retry_after: float = 90.0
    sleep: float = 1.0

    def __post_init__(self) -> None:
        """
        Validate worker concurrency, routing names and polling durations.

        Returns
        -------
        None
            Leave valid settings unchanged.

        Raises
        ------
        QueueConfigurationError
            If concurrency, queue selection, routing names or durations are invalid.
        """
        if (isinstance(self.concurrency, bool)
                or not isinstance(self.concurrency, int)
                or self.concurrency < 1 or not isinstance(self.queues, tuple)
                or not self.queues):
            message = "Worker concurrency and queues are invalid."
            raise QueueConfigurationError(message)
        validate_name(self.connection, "Connection")
        for queue in self.queues:
            validate_name(queue, "Queue")
        validate_seconds(self.retry_after, "Worker retry_after", positive=True)
        validate_seconds(self.sleep, "Worker sleep")


class Worker(IWorker):
    """Consume leased jobs through isolated Orionis dependency scopes."""

    __slots__ = (
        "_app",
        "_concurrency",
        "_connection",
        "_driver",
        "_failed",
        "_failed_resolver",
        "_processed",
        "_queues",
        "_retry_after",
        "_running",
        "_serializer",
        "_sleep",
        "_started",
        "_stop",
    )

    def __init__(
        self, app: IApplication, driver: IQueueDriver,
        serializer: IJobSerializer, options: WorkerOptions,
        failed: IFailedJobRepository | FailedResolver | None = None,
    ) -> None:
        """
        Initialize worker settings without opening backend connections.

        Parameters
        ----------
        app : IApplication
            Application container used to create an isolated scope per job.
        driver : IQueueDriver
            Backend used to reserve, release and acknowledge jobs.
        serializer : IJobSerializer
            Serializer used to restore envelopes and registered jobs.
        options : WorkerOptions
            Validated connection, queues, concurrency, lease and poll settings.
        failed : IFailedJobRepository | FailedResolver | None, optional
            Failure repository or async resolver invoked on terminal failure.
            If ``None``, terminal failures cannot be recorded.

        Returns
        -------
        None
            Store dependencies and initialize counters and stop state.
        """
        self._app = app
        self._driver = driver
        self._serializer = serializer
        self._connection = options.connection
        self._queues = options.queues
        self._concurrency = options.concurrency
        self._retry_after = options.retry_after
        self._sleep = options.sleep
        self._failed = None if callable(failed) else failed
        self._failed_resolver = failed if callable(failed) else None
        self._stop = asyncio.Event()
        self._running = False
        self._started = 0
        self._processed = 0

    def stop(self) -> None:
        """
        Request a graceful stop without waiting for active jobs.

        Returns
        -------
        None
            Set the stop event; active consumers complete their current work.
        """
        self._stop.set()

    async def run(
        self,
        *,
        stop_when_empty: bool = False,
        max_jobs: int | None = None,
    ) -> int:
        """
        Consume jobs concurrently until a stopping condition is reached.

        Parameters
        ----------
        stop_when_empty : bool, optional
            Stop each consumer when no job is ready, even if delayed jobs remain.
        max_jobs : int | None, optional
            Limit reservations across all consumers; ``None`` means no limit.

        Returns
        -------
        int
            Number of processed reservations, including retried or failed jobs.

        Raises
        ------
        QueueConfigurationError
            If already running or a supplied job limit is not a positive integer.
        asyncio.CancelledError
            If cancelled, after in-flight consumers finish.
        Exception
            If a consumer fails, after the remaining consumers finish.
        """
        if self._running or (max_jobs is not None and (
                isinstance(max_jobs, bool) or not isinstance(max_jobs, int)
                or max_jobs < 1)):
            message = "The worker is already running or max_jobs is invalid."
            raise QueueConfigurationError(message)
        self._running = True
        self._started = self._processed = 0
        self._stop.clear()
        consumers = tuple(asyncio.create_task(self._consume(
            stop_when_empty=stop_when_empty, max_jobs=max_jobs,
        )) for _ in range(self._concurrency))
        group = asyncio.gather(*consumers)
        try:
            await asyncio.shield(group)
        except BaseException:
            # Drain current executions after a stop or runtime interruption.
            self.stop()
            await asyncio.gather(*consumers, return_exceptions=True)
            raise
        finally:
            self._running = False
        return self._processed

    async def _consume(
        self,
        *,
        stop_when_empty: bool,
        max_jobs: int | None,
    ) -> None:
        """
        Consume reservations within the shared job budget.

        Parameters
        ----------
        stop_when_empty : bool
            End this consumer when the backend has no ready job.
        max_jobs : int | None
            Shared reservation limit, or ``None`` to run without a job limit.

        Returns
        -------
        None
            Process reserved jobs and update the shared counters.

        Raises
        ------
        Exception
            If reservation or execution raises an unhandled error.
        """
        while not self._stop.is_set():
            if max_jobs is not None and self._started >= max_jobs:
                return
            self._started += 1
            reserved = await self._driver.reserve(self._queues, self._retry_after)
            if reserved is None:
                self._started -= 1
                if stop_when_empty:
                    return
                try:
                    await asyncio.wait_for(self._stop.wait(), self._sleep)
                except TimeoutError:
                    continue
                return
            await self.execute(reserved)
            self._processed += 1

    def _validateReservation(
        self,
        reserved: ReservedJob,
        envelope: JobEnvelope,
    ) -> None:
        """
        Validate reservation routing, timeout and retry eligibility.

        Parameters
        ----------
        reserved : ReservedJob
            Backend reservation containing routing metadata and attempt count.
        envelope : JobEnvelope
            Decoded dispatch metadata and retry policy to match and enforce.

        Returns
        -------
        None
            Accept a reservation that matches its envelope and retry limits.

        Raises
        ------
        QueuePayloadError
            If routing metadata differs or the attempt count is invalid.
        QueueConfigurationError
            If the timeout is missing or not shorter than worker ``retry_after``.
        QueueRetryError
            If attempts exceed ``max_tries`` or the retry deadline has expired.
        """
        if (reserved.id != envelope.id or reserved.queue != envelope.queue
                or envelope.connection != self._connection
                or isinstance(reserved.attempts, bool)
                or not isinstance(reserved.attempts, int)
                or reserved.attempts < 1):
            message = "The reserved job does not match its envelope routing."
            raise QueuePayloadError(message)
        if envelope.timeout is None or envelope.timeout >= self._retry_after:
            message = "Job timeout must be finite and shorter than retry_after."
            raise QueueConfigurationError(message)
        if reserved.attempts > envelope.max_tries:
            message = "The job exhausted its attempts before this reservation."
            raise QueueRetryError(message)
        if (envelope.retry_until is not None
                and current_time() >= envelope.retry_until):
            message = "The job retry deadline expired before execution."
            raise QueueRetryError(message)

    async def execute(
        self,
        reserved: ReservedJob,
        *,
        raise_errors: bool = False,
    ) -> None:
        """
        Execute a reserved job with isolated DI and lease-aware completion.

        Parameters
        ----------
        reserved : ReservedJob
            Backend reservation containing the payload, attempt count and lease.
        raise_errors : bool, optional
            Propagate execution errors and bypass automatic retries when true.

        Returns
        -------
        None
            Attempt acknowledgement, retry release or terminal failure recording.
            Skip expired reservations without executing their jobs.

        Raises
        ------
        asyncio.CancelledError
            If cancelled, after attempting to release unfinished work.
        Exception
            If execution or completion fails and ``raise_errors`` is true.
        """
        if current_time() >= reserved.reserved_until:
            _LOGGER.warning("Skipping expired queue reservation %s", reserved.id)
            return
        envelope = None
        context = JobContext(self._driver, reserved, self._connection, self._fail)
        try:
            envelope = self._serializer.decodeEnvelope(reserved.payload)
            self._validateReservation(reserved, envelope)
            remaining = reserved.reserved_until - current_time()
            if remaining <= 0:
                return
            execution_timeout = min(envelope.timeout, remaining * 0.95)
            async with (
                asyncio.timeout(execution_timeout),
                self._app.beginScope(),
            ):
                self._app.instance(JobContext, context)
                job = self._serializer.decode(envelope.job, envelope.payload)
                await self._app.call(job, "handle")
            await self._finish(context, raise_errors=raise_errors)
        except asyncio.CancelledError:
            if not context.finished:
                await self._releaseCancelled(reserved)
            raise
        except Exception as exception:
            # Persist or release each failed execution independently.
            _LOGGER.exception("Queue job %s failed on attempt %s", reserved.id,
                              reserved.attempts)
            if not context.finished:
                try:
                    await self._handleFailure(reserved, envelope, exception,
                                              raise_errors=raise_errors)
                except Exception:
                    # Retain an unacknowledged lease for crash recovery.
                    _LOGGER.exception("Cannot complete failed queue job %s",
                                      reserved.id)
            if raise_errors:
                raise

    async def _releaseCancelled(self, reserved: ReservedJob) -> None:
        """
        Release a cancelled reservation without replacing its cancellation.

        Parameters
        ----------
        reserved : ReservedJob
            Reservation whose execution was interrupted before completion.

        Returns
        -------
        None
            Attempt lease release and log backend errors without re-raising them.
        """
        try:
            await self._driver.release(reserved)
        except Exception:
            # Preserve cancellation while leaving an unacknowledged lease.
            _LOGGER.exception("Cannot release cancelled queue job %s", reserved.id)

    async def _finish(self, context: JobContext, *, raise_errors: bool) -> None:
        """
        Acknowledge unfinished work or propagate an immediate job failure.

        Parameters
        ----------
        context : JobContext
            Lifecycle state containing the reservation's explicit transitions.
        raise_errors : bool
            Raise a recorded failure when immediate execution requires propagation.

        Returns
        -------
        None
            Delete unfinished work or preserve an existing lifecycle transition.

        Raises
        ------
        Exception
            If deletion fails or a recorded failure must be propagated.
        """
        if not context.finished:
            await context.delete()
        elif raise_errors and context.failure is not None:
            raise context.failure

    async def _handleFailure(
        self,
        reserved: ReservedJob,
        envelope: JobEnvelope | None,
        exception: Exception,
        *,
        raise_errors: bool,
    ) -> None:
        """
        Choose a retry release or terminal failure from the job's retry policy.

        Parameters
        ----------
        reserved : ReservedJob
            Current reservation used to release or record the failed attempt.
        envelope : JobEnvelope | None
            Decoded retry policy, or ``None`` if the envelope is unavailable.
        exception : Exception
            Original error used to determine retry eligibility and record failure.
        raise_errors : bool
            Disable retries so immediate execution records a terminal failure.

        Returns
        -------
        None
            Attempt a delayed retry release or terminal failure recording.

        Raises
        ------
        QueueConfigurationError
            If a terminal failure has no available failed-job repository.
        Exception
            If the backend or failure repository cannot complete the transition.
        """
        delay = 0.0
        if envelope is not None and envelope.backoff:
            index = min(reserved.attempts - 1, len(envelope.backoff) - 1)
            delay = envelope.backoff[index]
        retry = (not raise_errors and envelope is not None
                 and reserved.attempts < envelope.max_tries
                 and not isinstance(exception, (QueuePayloadError,
                                                QueueConfigurationError,
                                                QueueRetryError)))
        if retry and envelope.retry_until is not None:
            retry = current_time() + delay < envelope.retry_until
        if retry:
            if not await self._driver.release(reserved, delay):
                _LOGGER.warning("Queue job %s lost its retry lease", reserved.id)
        else:
            await self._fail(reserved, exception)

    async def _fail(self, reserved: ReservedJob, exception: Exception) -> bool:
        """
        Record a terminal failure before deleting the owned reservation.

        Parameters
        ----------
        reserved : ReservedJob
            Reservation whose lease must still be valid before recording failure.
        exception : Exception
            Original job exception stored in the failure repository.

        Returns
        -------
        bool
            ``True`` if deletion succeeds; ``False`` if the lease is expired or lost.

        Raises
        ------
        QueueConfigurationError
            If no failed-job repository can be resolved.
        Exception
            If repository resolution, failure recording or job deletion fails.
        """
        if current_time() >= reserved.reserved_until:
            return False
        repository = self._failed
        if repository is None and self._failed_resolver is not None:
            repository = self._failed = await self._failed_resolver()
        if repository is None:
            message = "Terminal failures require a failed-job repository."
            raise QueueConfigurationError(message)
        await repository.record(reserved, self._connection, exception)
        return await self._driver.delete(reserved)

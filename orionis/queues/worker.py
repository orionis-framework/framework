# ruff: noqa: BLE001, TC001
# Keep worker annotations resolvable and observe secondary recovery failures.
"""Provide queues operations through ``WorkerOptions``, ``Worker``."""

import asyncio
import logging
from contextlib import suppress
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from orionis.failure.runtime import capture, capture_result, operation
from orionis.foundation.contracts.application import IApplication
from orionis.queues.context import JobContext
from orionis.queues.contracts.driver import IQueueDriver
from orionis.queues.contracts.failed_repository import IFailedJobRepository
from orionis.queues.contracts.serializer import IJobSerializer
from orionis.queues.contracts.worker import IWorker
from orionis.queues.entities.envelope import JobEnvelope
from orionis.queues.entities.reserved_job import ReservedJob
from orionis.queues.exceptions import (
    QueueConfigurationError,
    QueuePayloadError,
    QueueRetryError,
)
from orionis.queues.functions import current_time, validate_name, validate_seconds
from orionis.support.concurrency import complete_on_cancel

_LOGGER = logging.getLogger(__name__)
"""Logger used by ``worker``."""
type FailedResolver = Callable[[], Awaitable[IFailedJobRepository]]
"""Type alias for ``Callable[[], Awaitable[IFailedJobRepository]]``."""


@dataclass(frozen=True, slots=True)
class WorkerOptions:
    """Retain stable validated settings for an independent worker runtime."""

    connection: str
    """Configured connection used to store or dispatch the operation."""
    queues: tuple[str, ...] = ("default",)
    """Queue names selected for worker polling."""
    concurrency: int = 1
    """Concurrency value used by ``WorkerOptions``."""
    retry_after: float = 90.0
    """Retry after value used by ``WorkerOptions``."""
    sleep: float = 1.0
    """Sleep value used by ``WorkerOptions``."""

    def __post_init__(self) -> None:
        """
        Validate concurrency, queue routing, and worker polling settings.

        Returns
        -------
        None
            Keep the frozen worker settings unchanged after successful validation.

        Raises
        ------
        orionis.queues.exceptions.QueueConfigurationError
            If concurrency, queue selection, routing names, or durations are invalid.
        """
        if (
            isinstance(self.concurrency, bool)
            or not isinstance(self.concurrency, int)
            or self.concurrency < 1
            or not isinstance(self.queues, tuple)
            or not self.queues
        ):
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
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self,
        app: IApplication,
        driver: IQueueDriver,
        serializer: IJobSerializer,
        options: WorkerOptions,
        failed: IFailedJobRepository | FailedResolver | None = None,
    ) -> None:
        """
        Initialize a worker without opening queue-backend connections.

        Parameters
        ----------
        app : orionis.IApplication
            Application used to create an isolated dependency scope per job.
        driver : orionis.queues.contracts.driver.IQueueDriver
            Backend used to reserve, release, and acknowledge jobs.
        serializer : orionis.queues.contracts.serializer.IJobSerializer
            Serializer restoring dispatch envelopes and registered job instances.
        options : orionis.queues.worker.WorkerOptions
            Validated connection, queues, concurrency, lease, and polling settings.
        failed : IFailedJobRepository | FailedResolver | None, optional
            Repository or asynchronous resolver, resolved lazily and cached.
            ``None`` makes terminal failure storage unavailable.

        Returns
        -------
        None
            Retain dependencies and initialize polling, counters, and stop state.
        """
        self._app = app
        """Application container used to create an isolated scope per job."""
        self._driver = driver
        """Backend used to reserve, release and acknowledge jobs."""
        self._serializer = serializer
        """Serializer used to restore envelopes and registered jobs."""
        self._connection = options.connection
        """Configured connection used to store or dispatch the operation."""
        self._queues = options.queues
        """Queue names selected for worker polling."""
        self._concurrency = options.concurrency
        """Concurrency obtained from ``options.concurrency``."""
        self._retry_after = options.retry_after
        """Retry after obtained from ``options.retry_after``."""
        self._sleep = options.sleep
        """Sleep obtained from ``options.sleep``."""
        self._failed = None if callable(failed) else failed
        """
        Failure repository or async resolver invoked on terminal failure. If
        ``None``, terminal failures cannot be recorded.
        """
        self._failed_resolver = failed if callable(failed) else None
        """Resolver supplying the configured failed-job storage backend."""
        self._stop = asyncio.Event()
        """Stop produced by ``asyncio.Event``."""
        self._running = False
        """Running flag used by ``Worker``."""
        self._started = 0
        """Started value used by ``Worker``."""
        self._processed = 0
        """Processed value used by ``Worker``."""

    def stop(self) -> None:
        """
        Signal consumers to stop after their in-flight reservations finish.

        Returns
        -------
        None
            Set the shared stop event without waiting for active consumers.
        """
        self._stop.set()

    async def run(
        self,
        *,
        stop_when_empty: bool = False,
        max_jobs: int | None = None,
    ) -> int:
        """
        Run concurrent consumers under shared stop and reservation limits.

        Parameters
        ----------
        stop_when_empty : bool, optional
            Stop each consumer after an empty poll, even if delayed jobs remain.
        max_jobs : int | None, optional
            Shared reservation cap, or ``None`` for no job-count limit.

        Returns
        -------
        int
            Number of processed reservations, including retries, handled failures,
            and skipped expired leases.

        Raises
        ------
        orionis.queues.exceptions.QueueConfigurationError
            If already running or a supplied limit is not a positive, non-boolean
            integer.
        asyncio.CancelledError
            If cancelled, after requesting a stop and draining active consumers.
        Exception
            If a consumer fails, after requesting a stop and joining its peers.
        """
        if self._running or (
            max_jobs is not None
            and (
                isinstance(max_jobs, bool)
                or not isinstance(max_jobs, int)
                or max_jobs < 1
            )
        ):
            message = "The worker is already running or max_jobs is invalid."
            raise QueueConfigurationError(message)
        self._running = True
        self._started = self._processed = 0
        self._stop.clear()
        consumers = tuple(
            asyncio.create_task(
                self._consume(
                    stop_when_empty=stop_when_empty,
                    max_jobs=max_jobs,
                ),
            )
            for _ in range(self._concurrency)
        )
        group = asyncio.gather(*consumers)
        try:
            await complete_on_cancel(group, on_cancel=self.stop)
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
        Run one consumer in an isolated queue-failure observation context.

        Parameters
        ----------
        stop_when_empty : bool
            End this consumer after an empty reservation attempt.
        max_jobs : int or None
            Shared reservation cap across consumers, or ``None`` for no cap.

        Returns
        -------
        None
            Finish this consumer when its stopping condition or budget is reached.

        Raises
        ------
        Exception
            If polling or execution fails; observe the consumer failure before
            propagating it.
        """
        with operation(self._app, flow="queue", operation="consume", isolated=True):
            try:
                await self._consumeJobs(
                    stop_when_empty=stop_when_empty,
                    max_jobs=max_jobs,
                )
            except Exception as error:
                await capture(
                    error,
                    app=self._app,
                    flow="queue",
                    phase="consumer",
                )
                raise

    async def _consumeJobs(
        self,
        *,
        stop_when_empty: bool,
        max_jobs: int | None,
    ) -> None:
        """
        Reserve and execute jobs within the worker's shared reservation budget.

        Parameters
        ----------
        stop_when_empty : bool
            Return when the backend has no ready job instead of polling again.
        max_jobs : int | None
            Shared reservation limit across consumers, or ``None`` for no cap.

        Returns
        -------
        None
            Update shared counters and return on stop, an exhausted budget, or
            empty polling when requested.

        Raises
        ------
        Exception
            If reservation or execution raises outside its own recovery policy.
        """
        while not self._stop.is_set():
            if max_jobs is not None and self._started >= max_jobs:
                return
            self._started += 1
            try:
                reserved = await self._driver.reserve(self._queues, self._retry_after)
            except Exception as error:
                # Observe each consumer before gather can discard sibling errors.
                await capture(
                    error,
                    app=self._app,
                    flow="queue",
                    phase="reserve",
                    metadata={"connection": self._connection},
                )
                raise
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
        Validate reservation routing, timeout compatibility, and retry eligibility.

        Parameters
        ----------
        reserved : orionis.queues.entities.reserved_job.ReservedJob
            Reservation identifier, queue, and current attempt count.
        envelope : orionis.queues.JobEnvelope
            Decoded routing, execution timeout, and retry policy.

        Returns
        -------
        None
            Accept matching routing, a valid attempt, and an eligible retry policy.

        Raises
        ------
        orionis.queues.exceptions.QueuePayloadError
            If identifiers or routing differ, or the attempt count is invalid.
        orionis.queues.exceptions.QueueConfigurationError
            If the timeout is missing or not strictly below worker ``retry_after``.
        orionis.queues.exceptions.QueueRetryError
            If attempts exceed ``max_tries`` or ``retry_until`` has been reached.
        """
        if (
            reserved.id != envelope.id
            or reserved.queue != envelope.queue
            or envelope.connection != self._connection
            or isinstance(reserved.attempts, bool)
            or not isinstance(reserved.attempts, int)
            or reserved.attempts < 1
        ):
            message = "The reserved job does not match its envelope routing."
            raise QueuePayloadError(message)
        if envelope.timeout is None or envelope.timeout >= self._retry_after:
            message = "Job timeout must be finite and shorter than retry_after."
            raise QueueConfigurationError(message)
        if reserved.attempts > envelope.max_tries:
            message = "The job exhausted its attempts before this reservation."
            raise QueueRetryError(message)
        if envelope.retry_until is not None and current_time() >= envelope.retry_until:
            message = "The job retry deadline expired before execution."
            raise QueueRetryError(message)

    async def execute(
        self,
        reserved: ReservedJob,
        *,
        raise_errors: bool = False,
    ) -> None:
        """
        Execute one leased job in an isolated scope and apply its lifecycle outcome.

        Limit handler execution to its configured timeout or 95% of the remaining
        lease, whichever is shorter.

        Parameters
        ----------
        reserved : orionis.queues.entities.reserved_job.ReservedJob
            Backend reservation containing the payload, attempt count, and lease.
        raise_errors : bool, optional
            Propagate the original execution or completion error and disable retries.

        Returns
        -------
        None
            Attempt acknowledgement, retry release, or terminal storage; skip
            expired reservations without invoking their jobs.

        Raises
        ------
        asyncio.CancelledError
            If execution or failure observation is cancelled, after draining the
            release of unfinished work, including repeated cancellation.
        Exception
            If ``raise_errors`` requests error propagation, or reporting an expired
            reservation itself fails.
        """
        if current_time() >= reserved.reserved_until:
            try:
                _LOGGER.warning("Skipping expired queue reservation %s", reserved.id)
            except Exception as error:
                await capture(
                    error,
                    app=self._app,
                    flow="queue",
                    phase="report",
                    correlation_id=reserved.id,
                )
                raise
            return
        with operation(
            self._app,
            flow="queue",
            operation="execute",
            correlation_id=reserved.id,
            isolated=True,
        ):
            envelope = None
            context = JobContext(self._driver, reserved, self._connection, self._fail)
            try:
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
                except Exception as exception:
                    # Reporting cannot bypass the owner's cancellation cleanup.
                    await self._observe(
                        exception,
                        reserved,
                        "execution",
                        "Queue job %s failed on attempt %s",
                        reserved.id,
                        reserved.attempts,
                    )
                    if not context.finished:
                        try:
                            await self._handleFailure(
                                reserved,
                                envelope,
                                exception,
                                raise_errors=raise_errors,
                            )
                        except Exception as recovery_error:
                            # Retain an unacknowledged lease for crash recovery.
                            await self._observe(
                                recovery_error,
                                reserved,
                                "recovery",
                                "Cannot complete failed queue job %s",
                                reserved.id,
                            )
                    if raise_errors:
                        raise
            except asyncio.CancelledError:
                if not context.finished:
                    await complete_on_cancel(self._releaseCancelled(reserved))
                raise

    async def _releaseCancelled(self, reserved: ReservedJob) -> None:
        """
        Attempt reservation release while preserving the original cancellation.

        Parameters
        ----------
        reserved : orionis.queues.entities.reserved_job.ReservedJob
            Unfinished reservation to release after cancellation.

        Returns
        -------
        None
            Attempt lease release and observe ordinary backend errors without
            re-raising them.
        """
        try:
            await self._driver.release(reserved)
        except Exception as error:
            # Preserve cancellation while leaving an unacknowledged lease.
            await self._observe(
                error,
                reserved,
                "release",
                "Cannot release cancelled queue job %s",
                reserved.id,
            )

    async def _observe(
        self,
        error: Exception,
        reserved: ReservedJob,
        phase: str,
        message: str,
        *args: object,
    ) -> None:
        """
        Observe a job failure without letting fallback logging replace it.

        Parameters
        ----------
        error : Exception
            Job or recovery exception sent through shared failure observation.
        reserved : orionis.queues.entities.reserved_job.ReservedJob
            Reservation supplying the job identifier and attempt metadata.
        phase : str
            Queue operation phase associated with the failure.
        message : str
            Fallback log template used when no capture receipt is returned.
        *args : object
            Positional values interpolated into the fallback log message.

        Returns
        -------
        None
            Await observation and, if no receipt is returned, attempt fallback
            logging while suppressing its ordinary exceptions.
        """
        receipt = await capture(
            error,
            app=self._app,
            flow="queue",
            phase=phase,
            correlation_id=reserved.id,
            metadata={"connection": self._connection, "attempt": reserved.attempts},
        )
        if receipt is None:
            # Inactive standalone workers retain the original recovery policy.
            with suppress(Exception):
                _LOGGER.error(
                    message,
                    *args,
                    exc_info=(type(error), error, error.__traceback__),
                )

    async def _finish(self, context: JobContext, *, raise_errors: bool) -> None:
        """
        Acknowledge unfinished work or propagate an explicitly recorded job failure.

        Parameters
        ----------
        context : orionis.queues.JobContext
            Job state tracking release, deletion, and explicit failure.
        raise_errors : bool
            Re-raise a recorded failure after an explicit lifecycle transition.

        Returns
        -------
        None
            Attempt to delete unfinished work, or preserve an existing transition.

        Raises
        ------
        Exception
            If deletion fails or a recorded job failure must be propagated.
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
        Select a delayed retry or terminal handling from the envelope's policy.

        Reject retries for payload, configuration, or retry-policy errors.
        Reuse the last configured backoff entry for later attempts.

        Parameters
        ----------
        reserved : orionis.queues.entities.reserved_job.ReservedJob
            Current reservation whose lease controls release and terminal deletion.
        envelope : orionis.queues.JobEnvelope | None
            Retry limits and backoff schedule; ``None`` selects terminal handling.
        exception : Exception
            Original error used to reject non-retryable failures and populate storage.
        raise_errors : bool
            Force terminal handling for immediate execution instead of retrying.

        Returns
        -------
        None
            Attempt a backoff-delayed release or a terminal failure transition.

        Raises
        ------
        orionis.queues.exceptions.QueueConfigurationError
            If terminal handling requires an unavailable failed-job repository.
        Exception
            If a backend transition, failure recording, or lease-loss warning fails.
        """
        delay = 0.0
        if envelope is not None and envelope.backoff:
            index = min(reserved.attempts - 1, len(envelope.backoff) - 1)
            delay = envelope.backoff[index]
        retry = (
            not raise_errors
            and envelope is not None
            and reserved.attempts < envelope.max_tries
            and not isinstance(
                exception,
                (QueuePayloadError, QueueConfigurationError, QueueRetryError),
            )
        )
        if retry and envelope.retry_until is not None:
            retry = current_time() + delay < envelope.retry_until
        if retry:
            if not await self._driver.release(reserved, delay):
                _LOGGER.warning("Queue job %s lost its retry lease", reserved.id)
        else:
            await self._fail(reserved, exception)

    async def _fail(self, reserved: ReservedJob, exception: Exception) -> bool:
        """
        Record a terminal job failure before deleting its leased reservation.

        Parameters
        ----------
        reserved : orionis.queues.entities.reserved_job.ReservedJob
            Reservation whose lease must remain valid before terminal recording.
        exception : Exception
            Job or recovery exception to record in failed-job storage.

        Returns
        -------
        bool
            ``True`` if deletion succeeds; ``False`` if the lease expired or was lost.
            A failure may already be recorded when deletion returns false.

        Raises
        ------
        orionis.queues.exceptions.QueueConfigurationError
            If terminal storage is required and no repository can be resolved.
        Exception
            If observation, repository resolution, recording, or deletion fails.
        """
        await capture(
            exception,
            app=self._app,
            flow="queue",
            phase="terminal",
            correlation_id=reserved.id,
            metadata={"attempt": reserved.attempts},
        )
        if current_time() >= reserved.reserved_until:
            return False
        repository = self._failed
        if repository is None and self._failed_resolver is not None:
            repository = self._failed = await self._failed_resolver()
        if repository is None:
            message = "Terminal failures require a failed-job repository."
            raise QueueConfigurationError(message)
        await repository.record(reserved, self._connection, exception)
        acknowledged = await self._driver.delete(reserved)
        await capture_result(
            "failed",
            app=self._app,
            flow="queue",
            phase="terminal",
            correlation_id=reserved.id,
            metadata={"attempt": reserved.attempts, "acknowledged": acknowledged},
        )
        return acknowledged

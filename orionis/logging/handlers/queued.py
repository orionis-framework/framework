# ruff: noqa: BLE001, SLF001, TC003
# Drain after arbitrary sink failures; retain reporting metadata and runtime types.
"""Queue log records and observe sink delivery or cleanup failures."""

import logging
import sys
from collections.abc import Callable
from copy import copy
from logging.handlers import QueueListener
from queue import Queue
from typing import Self
from orionis.failure import runtime as failure_runtime


class LoggingDeliveryError(Exception):
    """Signal a synchronous or background log-delivery failure."""


def observe_sink_error(
    record: logging.LogRecord,
    *,
    app: object,
    original: Callable[[logging.LogRecord], None],
) -> None:
    """
    Observe an active sink exception before invoking its original callback.

    Parameters
    ----------
    record : ``logging.LogRecord``
        Record passed to the sink's original error callback.
    app : object
        Application context supplied to failure observation.
    original : collections.abc.Callable
        Original error callback receiving the record after observation.

    Returns
    -------
    None
        This function does not return a value.

    Raises
    ------
    LoggingDeliveryError
        If a sink error occurs while reporting another application failure.
    """
    error = sys.exc_info()[1]
    if error is not None:
        if failure_runtime.is_reporting():
            message = "The logging sink failed while reporting an application error."
            raise LoggingDeliveryError(message) from error
        failure_runtime.capture_nowait(error, app=app, flow="logging", phase="delivery")
    original(record)


def _raise_sink_error(_record: logging.LogRecord) -> None:
    """
    Raise a delivery error for the active sink exception.

    Parameters
    ----------
    _record : ``logging.LogRecord``
        Failed record, accepted for ``handleError`` compatibility.

    Returns
    -------
    None
        Never return normally.

    Raises
    ------
    LoggingDeliveryError
        Always, with the active sink exception as its cause when present.
    """
    error_msg = "The background logging sink could not emit a record."
    raise LoggingDeliveryError(error_msg) from sys.exc_info()[1]


class _Listener(QueueListener):
    """Drain queued records while retaining and observing delivery failures."""

    error: Exception | None = None
    """First error retained while background work continues to drain."""
    app: object | None = None
    """Application owning the sink and its failure policy."""
    runtime: failure_runtime.FailureRuntime | None = None
    """Prepared coordinator retained for deliveries outside a request context."""

    def handle(self: Self, record: logging.LogRecord) -> None:
        """
        Deliver a record under its originating failure-reporting context.

        Parameters
        ----------
        record : ``logging.LogRecord``
            Queued record carrying optional reporter identity metadata.

        Returns
        -------
        None
            This method does not return a value.
        """
        reporter = getattr(record, "_orionis_failure_reporting", None)
        if reporter is not None:
            with failure_runtime.reporting_from(reporter):
                self._deliver(record)
        else:
            self._deliver(record)

    def _deliver(self: Self, record: logging.LogRecord) -> None:
        """
        Deliver a queued record and retain the listener's first sink failure.

        Continue draining after delivery exceptions and offer each failure to
        the owner's runtime.

        Parameters
        ----------
        record : ``logging.LogRecord``
            Queued record to pass to the configured handlers.

        Returns
        -------
        None
            This method does not return a value.
        """
        try:
            super().handle(record)
        except Exception as error:
            if self.error is None:
                self.error = error
            # The sink thread has no request context. Its owner is retained at
            # construction; reporting is activated only after app startup.
            if isinstance(error, LoggingDeliveryError) and error.__cause__ is not None:
                error = error.__cause__
            failure_runtime.capture_nowait(
                error,
                app=self.app,
                runtime=self.runtime,
                flow="logging",
                phase="delivery",
            )

    def enqueueSentinel(self: Self) -> None:
        """
        Enqueue the shutdown sentinel, waiting for queue capacity.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.queue.put(self._sentinel)

    # Preserve the logging.handlers.QueueListener protocol name.
    enqueue_sentinel = enqueueSentinel


class BoundedQueueHandler(logging.Handler):
    """
    Deliver records to an owned sink through a bounded background queue.

    Notes
    -----
    Reject full queues with ``queue.Full`` at every severity. Drain accepted
    records on close and surface background delivery failures to the caller.
    """

    def __init__(
        self: Self,
        target: logging.Handler,
        capacity: int,
        *,
        app: object | None = None,
    ) -> None:
        """
        Start a bounded background listener for an owned logging sink.

        Parameters
        ----------
        target : ``logging.Handler``
            Target sink, closed by this handler after accepted records drain.
        capacity : int
            Positive maximum number of pending records, excluding active delivery.
        app : object | None, optional
            Application supplied to sink-failure observation, or ``None``.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ValueError
            If ``capacity`` is not a positive integer or is a boolean.
        """
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
            error_msg = "Logging queue capacity must be a positive integer."
            raise ValueError(error_msg)
        super().__init__(target.level)
        self._target = target
        """Owned sink, closed after the queue drains."""
        target.handleError = _raise_sink_error
        self._queue: Queue = Queue(maxsize=capacity)
        """Name of the queue receiving or storing the job."""
        self._listener = _Listener(self._queue, target)
        """Listener produced by ``_Listener``."""
        self._listener.app = app
        self._listener.runtime = failure_runtime.get_runtime(app)
        self._stopped = False
        """Stopped flag used by ``BoundedQueueHandler``."""
        self._listener.start()

    def emit(self: Self, record: logging.LogRecord) -> None:
        """
        Enqueue a record snapshot without waiting for queue capacity.

        Parameters
        ----------
        record : ``logging.LogRecord``
            Source record, copied with its formatted message and reporter identity.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        LoggingDeliveryError
            If the handler is closed or background delivery has already failed.
        queue.Full
            If the pending-record queue has reached its configured capacity.
        """
        if self._stopped:
            error_msg = "Logging queue is closed."
            raise LoggingDeliveryError(error_msg)
        if self._listener.error is not None:
            error_msg = "The background logging sink failed."
            raise LoggingDeliveryError(error_msg) from self._listener.error
        snapshot = copy(record)
        snapshot.msg = record.getMessage()
        snapshot.args = None
        snapshot._orionis_failure_reporting = failure_runtime.reporting_runtime()
        self._queue.put_nowait(snapshot)

    def flush(self: Self) -> None:
        """
        Wait for queued work, then flush the owned sink and surface failures.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        LoggingDeliveryError
            If the sink cannot flush or a background delivery has failed.
        """
        self._queue.join()
        try:
            self._target.flush()
        except Exception as error:
            self._observeFailure(error, phase="flush")
            error_msg = "The background logging sink could not flush."
            raise LoggingDeliveryError(error_msg) from error
        if self._listener.error is not None:
            error_msg = "The background logging sink failed."
            raise LoggingDeliveryError(error_msg) from self._listener.error

    def close(self: Self) -> None:
        """
        Stop admission, drain queued records, and close the owned sink.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        LoggingDeliveryError
            If shutdown, flushing, or sink closure fails, chained from the first
            failure encountered during shutdown.
        """
        self.acquire()
        try:
            if self._stopped:
                return
            self._stopped = True
        finally:
            self.release()
        failure = None
        try:
            self._listener.stop()
            self.flush()
        except Exception as error:
            failure = error
            if not isinstance(error, LoggingDeliveryError):
                self._observeFailure(error, phase="cleanup")
        finally:
            try:
                self._target.close()
            except Exception as error:
                self._observeFailure(error, phase="cleanup")
                failure = failure or error
            finally:
                self._listener.error = None
                super().close()
        if failure is not None:
            error_msg = "The background logging sink failed during shutdown."
            raise LoggingDeliveryError(error_msg) from failure

    def _observeFailure(self, error: BaseException, *, phase: str) -> None:
        """
        Observe a sink failure without replacing the retained shutdown error.

        Parameters
        ----------
        error : BaseException
            Flush or cleanup error offered to the listener's failure runtime.
        phase : str
            Logging operation associated with the failure.

        Returns
        -------
        None
            This method does not return a value.
        """
        failure_runtime.capture_nowait(
            error,
            app=self._listener.app,
            runtime=self._listener.runtime,
            flow="logging",
            phase=phase,
        )

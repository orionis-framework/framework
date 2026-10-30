import logging
import sys
from copy import copy
from logging.handlers import QueueListener
from queue import Queue
from typing import Self

class LoggingDeliveryError(Exception):
    """Report a background handler failure instead of silently losing records."""

def _raise_sink_error(_record: logging.LogRecord) -> None:
    """
    Surface errors swallowed by standard FileHandler.emit implementations.

    Parameters
    ----------
    _record : logging.LogRecord
        Log record associated with the simulated sink failure.

    Returns
    -------
    None
        Never return normally; raise the sink delivery failure.
    """
    error_msg = "The background logging sink could not emit a record."
    raise LoggingDeliveryError(error_msg) from sys.exc_info()[1]

class _Listener(QueueListener):
    """Drain a bounded queue even after a sink reports a failure."""

    error: Exception | None = None

    def handle(self: Self, record: logging.LogRecord) -> None:
        """
        Deliver a record, retaining the first sink failure for the owner.

        Parameters
        ----------
        record : logging.LogRecord
            Log record to deliver to the sink.

        Returns
        -------
        None
            Complete the operation without returning a value.
        """
        try:
            super().handle(record)
        except Exception as error:  # noqa: BLE001
            if self.error is None:
                self.error = error

    def enqueue_sentinel(self: Self) -> None:
        """
        Wait for space during shutdown so a full queue still drains.

        Returns
        -------
        None
            Complete the operation without returning a value.
        """
        self.queue.put(self._sentinel)

class BoundedQueueHandler(logging.Handler):
    """
    Move file emission and rotation to a bounded background queue.

    Full queues raise queue.Full for every severity, including critical records.
    Callers can apply their own fallback; no record is silently dropped.
    Close drains accepted records and surfaces background delivery errors.
    """

    def __init__(self: Self, target: logging.Handler, capacity: int) -> None:
        """
        Start one listener for the supplied sink and bounded queue.

        Parameters
        ----------
        target : logging.Handler
            Owned sink, closed after the queue drains.
        capacity : int
            Positive number of pending records allowed.

        Returns
        -------
        None
            Complete the operation without returning a value.
        """
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
            error_msg = "Logging queue capacity must be a positive integer."
            raise ValueError(error_msg)
        super().__init__(target.level)
        self._target = target
        target.handleError = _raise_sink_error
        self._queue: Queue = Queue(maxsize=capacity)
        self._listener = _Listener(self._queue, target)
        self._stopped = False
        self._listener.start()

    def emit(self: Self, record: logging.LogRecord) -> None:
        """
        Enqueue an owned record snapshot or explicitly reject it.

        Parameters
        ----------
        record : logging.LogRecord
            Log record to deliver to the sink.

        Returns
        -------
        None
            Complete the operation without returning a value.
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
        self._queue.put_nowait(snapshot)

    def flush(self: Self) -> None:
        """
        Wait for accepted records and flush the target sink.

        Returns
        -------
        None
            Complete the operation without returning a value.
        """
        self._queue.join()
        try:
            self._target.flush()
        except Exception as error:
            error_msg = "The background logging sink could not flush."
            raise LoggingDeliveryError(error_msg) from error
        if self._listener.error is not None:
            error_msg = "The background logging sink failed."
            raise LoggingDeliveryError(error_msg) from self._listener.error

    def close(self: Self) -> None:
        """
        Stop admission, drain accepted records and close the owned sink.

        Returns
        -------
        None
            Complete the operation without returning a value.
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
        except Exception as error:  # noqa: BLE001
            failure = error
        finally:
            try:
                self._target.close()
            except Exception as error:  # noqa: BLE001
                failure = failure or error
            finally:
                self._listener.error = None
                super().close()
        if failure is not None:
            error_msg = "The background logging sink failed during shutdown."
            raise LoggingDeliveryError(error_msg) from failure

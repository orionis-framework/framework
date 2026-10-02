class QueueError(RuntimeError):
    """Represent a failure in the queue runtime."""

    __slots__ = ()

class QueueConfigurationError(QueueError):
    """Represent invalid connection, worker, or job settings."""

    __slots__ = ()

class QueuePayloadError(QueueError):
    """Represent malformed or unsupported persistent job data."""

    __slots__ = ()

class UnknownJobError(QueuePayloadError):
    """Reject a job identity absent from the trusted registry."""

    __slots__ = ()

class QueueStorageError(QueueError):
    """Represent an invalid response or transition from queue storage."""

    __slots__ = ()

class QueueLeaseError(QueueError):
    """Represent an expired or superseded job reservation."""

    __slots__ = ()

class QueueDispatchError(QueueError):
    """Represent an invalid pending dispatch operation."""

    __slots__ = ()

class QueueRetryError(QueueError):
    """Represent exhausted attempts or an expired retry deadline."""

    __slots__ = ()

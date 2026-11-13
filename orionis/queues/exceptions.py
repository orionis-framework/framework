"""Provide queues operations.

Includes ``QueueError``, ``QueueConfigurationError``, ``QueuePayloadError``,
``UnknownJobError``.
"""


class QueueError(RuntimeError):
    """Represent a failure in the queue runtime."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""


class QueueConfigurationError(QueueError):
    """Represent invalid connection, worker, or job settings."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""


class QueuePayloadError(QueueError):
    """Represent malformed or unsupported persistent job data."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""


class UnknownJobError(QueuePayloadError):
    """Reject a job identity absent from the trusted registry."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""


class QueueStorageError(QueueError):
    """Represent an invalid response or transition from queue storage."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""


class QueueLeaseError(QueueError):
    """Represent an expired or superseded job reservation."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""


class QueueDispatchError(QueueError):
    """Represent an invalid pending dispatch operation."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""


class QueueRetryError(QueueError):
    """Represent exhausted attempts or an expired retry deadline."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

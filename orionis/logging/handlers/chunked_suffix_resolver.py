"""Resolve log suffixes for configured time chunks."""

from __future__ import annotations
from datetime import UTC, datetime, timedelta
from threading import Lock
from orionis.logging.handlers._local import ApplicationTimeResolver


class ChunkedSuffixResolver(ApplicationTimeResolver):
    """
    Name size-rotated log chunks with a local timestamp and counter.

    The counter keeps chunks distinct when multiple rotations share a timestamp.
    """

    __slots__ = ("_counter", "_lock")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self) -> None:
        """
        Initialize the chunk counter and its lock.

        Returns
        -------
        None
            Set up the counter so the first generated suffix uses value one.
        """
        self._counter = 0
        """Counter value used by ``ChunkedSuffixResolver``."""
        self._lock = Lock()
        """Lock protecting concurrent access to shared state."""
        super().__init__()

    def getSuffix(self, dt: datetime | None = None) -> str:
        """
        Build the suffix for a size-rotated chunk in the resolver's timezone.

        Parameters
        ----------
        dt : datetime.datetime or None, optional
            Aware instant, naive local wall time, or None for the current time.

        Returns
        -------
        str
            A local ``YYYYMMDD_HHMMSS`` timestamp and a unique counter.
        """
        # Use current time if no datetime is provided
        dt = self._local(dt)
        with self._lock:
            self._counter += 1
            # Suffix includes timestamp and a zero-padded counter
            return f"{dt.strftime('%Y%m%d_%H%M%S')}_{self._counter:04d}"

    def getNextRotationTime(self, current_time: datetime) -> datetime:
        """
        Find the fallback rotation boundary.

        Parameters
        ----------
        current_time : datetime.datetime
            Reference instant, interpreted locally when it has no timezone.

        Returns
        -------
        datetime.datetime
            Instant one elapsed hour later, expressed in the resolver's timezone.
        """
        # For size-based rotation, return current time plus one hour
        local = self._local(current_time)
        return (local.astimezone(UTC) + timedelta(hours=1)).astimezone(local.tzinfo)

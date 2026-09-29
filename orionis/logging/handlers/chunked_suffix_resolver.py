from __future__ import annotations
from datetime import datetime, timedelta
from threading import Lock
from orionis.logging.contracts.suffix_resolver import SuffixResolver
from orionis.support.facades.datetime import DateTime

class ChunkedSuffixResolver(SuffixResolver):

    __slots__ = ("_counter", "_lock", "tz")

    def __init__(self) -> None:
        """
        Initialize the ChunkedSuffixResolver.

        Sets up the counter, thread lock, and timezone for suffix generation.

        Returns
        -------
        None
            This method does not return a value.
        """
        self._counter = 0
        self._lock = Lock()
        self.tz = DateTime.getZoneInfo()

    def getSuffix(self, dt: datetime | None = None) -> str:
        """
        Generate a unique suffix for the log file.

        Parameters
        ----------
        dt : datetime or None, optional
            The datetime to use for the suffix. If None, uses current time.

        Returns
        -------
        str
            The generated suffix in the format 'YYYYMMDD_HHMMSS_counter'.
        """
        # Use current time if no datetime is provided
        if dt is None:
            dt = datetime.now(tz=self.tz)
        with self._lock:
            self._counter += 1
            # Suffix includes timestamp and a zero-padded counter
            return f"{dt.strftime('%Y%m%d_%H%M%S')}_{self._counter:04d}"

    def getNextRotationTime(self, current_time: datetime) -> datetime:
        """
        Compute the next rotation time for the log file.

        Parameters
        ----------
        current_time : datetime
            The current datetime.

        Returns
        -------
        datetime
            The next rotation time. For size-based rotation, this is
            current_time plus one hour.
        """
        # For size-based rotation, return current time plus one hour
        return current_time + timedelta(hours=1)

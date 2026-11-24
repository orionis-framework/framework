"""Resolve log suffixes for hourly rotation windows."""

from __future__ import annotations
from datetime import UTC, datetime, timedelta
from orionis.logging.handlers._local import ApplicationTimeResolver


class HourlySuffixResolver(ApplicationTimeResolver):
    """
    Group log files by local hour and distinguish repeated hours.

    The second occurrence of an hour includes its UTC offset in the filename.
    """

    __slots__ = ()
    """Declare the instance attribute slots reserved by this class."""

    def getSuffix(self, dt: datetime | None = None) -> str:
        """
        Build the hourly suffix in the resolver's timezone.

        Parameters
        ----------
        dt : datetime.datetime or None, optional
            Aware instant, naive local wall time, or None for the current time.

        Returns
        -------
        str
            The local hour as ``YYYY-MM-DD_HH``, with an offset on a repeated hour.
        """
        # Use current local datetime if dt is not provided
        dt = self._local(dt)
        return dt.strftime("%Y-%m-%d_%H_%z" if dt.fold else "%Y-%m-%d_%H")

    def getNextRotationTime(self, current_time: datetime) -> datetime:
        """
        Find the next hourly rotation boundary.

        Parameters
        ----------
        current_time : datetime.datetime
            Reference instant, interpreted locally when it has no timezone.

        Returns
        -------
        datetime.datetime
            First instant at which the local hour or its fold changes.
        """
        local_time = self._local(current_time)
        start = local_time.astimezone(UTC).replace(microsecond=0)
        label = (local_time.date(), local_time.hour, local_time.fold)
        # Search elapsed seconds so half-hour transitions and repeated hours
        # rotate at the instant when the filename actually changes.
        low, high = 0, 3600
        while high - low > 1:
            middle = (low + high) // 2
            probe = (start + timedelta(seconds=middle)).astimezone(local_time.tzinfo)
            if (probe.date(), probe.hour, probe.fold) == label:
                low = middle
            else:
                high = middle
        return (start + timedelta(seconds=high)).astimezone(local_time.tzinfo)

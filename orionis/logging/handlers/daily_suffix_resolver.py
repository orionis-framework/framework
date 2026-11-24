"""Resolve log suffixes for daily rotation windows."""

from __future__ import annotations
from datetime import datetime, time, timedelta
from orionis.logging.handlers._local import ApplicationTimeResolver


class DailySuffixResolver(ApplicationTimeResolver):
    """
    Group log files by local calendar day.

    The daily boundary defaults to midnight in the resolver's timezone.
    """

    __slots__ = ("at_time",)
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self, at_time: time | None = None) -> None:
        """
        Configure the daily rotation boundary.

        Parameters
        ----------
        at_time : datetime.time or None, optional
            Local rotation time, defaulting to midnight.

        Returns
        -------
        None
            Store the local time used for each daily boundary.
        """
        self.at_time = at_time or time(0, 0, 0)
        """The time of day when log rotation should occur. Defaults to midnight."""
        super().__init__()

    def getSuffix(self, dt: datetime | None = None) -> str:
        """
        Build the suffix for a day in the resolver's timezone.

        Parameters
        ----------
        dt : datetime.datetime or None, optional
            Aware instant, naive local wall time, or None for the current time.

        Returns
        -------
        str
            The local date as ``YYYY-MM-DD``.
        """
        # Use current local datetime if none is provided
        dt = self._local(dt)
        return dt.strftime("%Y-%m-%d")

    def getNextRotationTime(self, current_time: datetime) -> datetime:
        """
        Find the next daily rotation boundary.

        Parameters
        ----------
        current_time : datetime.datetime
            Reference instant, interpreted locally when it has no timezone.

        Returns
        -------
        datetime.datetime
            First future local date at the configured time.
        """
        local_time = self._local(current_time)
        next_rotation = datetime.combine(
            local_time.date(),
            self.at_time,
            tzinfo=local_time.tzinfo,
        )
        # If the calculated rotation time is not in the future, move to next day
        while not self._upcoming(next_rotation, local_time):
            next_rotation += timedelta(days=1)
        return next_rotation

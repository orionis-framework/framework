"""Resolve log suffixes for weekly rotation windows."""

from __future__ import annotations
from datetime import datetime, time, timedelta
from orionis.logging.handlers._local import ApplicationTimeResolver


class WeeklySuffixResolver(ApplicationTimeResolver):
    """
    Group log files by local ISO week.

    The weekly boundary falls on Monday at the configured local time.
    """

    __slots__ = ("at_time",)
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self, at_time: time | None = None) -> None:
        """
        Configure the weekly rotation boundary.

        Parameters
        ----------
        at_time : datetime.time or None, optional
            Local rotation time, defaulting to midnight.

        Returns
        -------
        None
            Store the local rotation time for each Monday.
        """
        self.at_time = at_time or time(0, 0, 0)
        """The time of day when rotation should occur. Defaults to midnight."""
        super().__init__()

    def getSuffix(self, dt: datetime | None = None) -> str:
        """
        Build the suffix for a week in the resolver's timezone.

        Parameters
        ----------
        dt : datetime.datetime or None, optional
            Aware instant, naive local wall time, or None for the current time.

        Returns
        -------
        str
            The ISO week year and number as ``YYYY-weekWW``.
        """
        # Use current local datetime if none is provided
        dt = self._local(dt)
        year, week, _ = dt.isocalendar()
        return f"{year}-week{week:02d}"

    def getNextRotationTime(self, current_time: datetime) -> datetime:
        """
        Find the next weekly rotation boundary.

        Parameters
        ----------
        current_time : datetime.datetime
            Reference instant, interpreted locally when it has no timezone.

        Returns
        -------
        datetime.datetime
            First future Monday at the configured local time.
        """
        local_time = self._local(current_time)
        monday = local_time.date() - timedelta(days=local_time.weekday())
        next_rotation = datetime.combine(monday, self.at_time, tzinfo=local_time.tzinfo)
        while not self._upcoming(next_rotation, local_time):
            next_rotation += timedelta(days=7)
        return next_rotation

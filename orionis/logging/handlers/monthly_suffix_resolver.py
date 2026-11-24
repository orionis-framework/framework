"""Resolve log suffixes for monthly rotation windows."""

from __future__ import annotations
from datetime import datetime, time
from orionis.logging.handlers._local import ApplicationTimeResolver

_DECEMBER = 12
"""Identify the final month before the calendar year advances."""


class MonthlySuffixResolver(ApplicationTimeResolver):
    """
    Group log files by local calendar month.

    The monthly boundary falls on the first day at the configured local time.
    """

    __slots__ = ("at_time",)
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self, at_time: time | None = None) -> None:
        """
        Configure the monthly rotation boundary.

        Parameters
        ----------
        at_time : datetime.time or None, optional
            Local rotation time, defaulting to midnight.

        Returns
        -------
        None
            Store the local rotation time for the first day of each month.
        """
        self.at_time = at_time or time(0, 0, 0)
        """The time of day when rotation should occur. Defaults to midnight."""
        super().__init__()

    def getSuffix(self, dt: datetime | None = None) -> str:
        """
        Build the suffix for a month in the resolver's timezone.

        Parameters
        ----------
        dt : datetime.datetime or None, optional
            Aware instant, naive local wall time, or None for the current time.

        Returns
        -------
        str
            The local year and month as ``YYYY-MM``.
        """
        # Use current local datetime if none is provided
        dt = self._local(dt)
        return dt.strftime("%Y-%m")

    def getNextRotationTime(self, current_time: datetime) -> datetime:
        """
        Find the next monthly rotation boundary.

        Parameters
        ----------
        current_time : datetime.datetime
            Reference instant, interpreted locally when it has no timezone.

        Returns
        -------
        datetime.datetime
            First future start of a month at the configured local time.
        """
        local_time = self._local(current_time)
        next_rotation = datetime.combine(
            local_time.date().replace(day=1),
            self.at_time,
            tzinfo=local_time.tzinfo,
        )
        while not self._upcoming(next_rotation, local_time):
            next_rotation = (
                next_rotation.replace(year=next_rotation.year + 1, month=1)
                if next_rotation.month == _DECEMBER
                else next_rotation.replace(month=next_rotation.month + 1)
            )
        return next_rotation

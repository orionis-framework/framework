"""Resolve log suffixes for monthly rotation windows."""

from __future__ import annotations
from datetime import datetime, time
from orionis.logging.contracts.suffix_resolver import SuffixResolver
from orionis.support.facades.datetime import DateTime

_DECEMBER = 12
"""Identify the final month before the calendar year advances."""


class MonthlySuffixResolver(SuffixResolver):
    """Resolve log suffixes for monthly rotation windows."""

    __slots__ = ("at_time", "tz")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self, at_time: time | None = None) -> None:
        """
        Initialize the resolver with an optional rotation time.

        Parameters
        ----------
        at_time : datetime.time or None, optional
            The time of day when rotation should occur. Defaults to midnight.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.at_time = at_time or time(0, 0, 0)
        """The time of day when rotation should occur. Defaults to midnight."""
        self.tz = DateTime.getZoneInfo()
        """Tz produced by ``DateTime.getZoneInfo``."""

    def getSuffix(self, dt: datetime | None = None) -> str:
        """
        Return the suffix string for the given datetime.

        Parameters
        ----------
        dt : datetime.datetime or None, optional
            The datetime to generate the suffix for. If None, uses current
            local datetime.

        Returns
        -------
        str
            The suffix in the format 'YYYY-MM'.
        """
        # Use current local datetime if none is provided
        if dt is None:
            dt = datetime.now(tz=self.tz)
        return dt.strftime("%Y-%m")

    def getNextRotationTime(self, current_time: datetime) -> datetime:
        """
        Compute the next rotation datetime after the current time.

        Parameters
        ----------
        current_time : datetime.datetime
            The current instant. Naive values use the resolver timezone.

        Returns
        -------
        datetime.datetime
            The datetime when the next rotation should occur.
        """
        local_time = (
            current_time.replace(tzinfo=self.tz)
            if current_time.tzinfo is None
            else current_time.astimezone(self.tz)
        )
        next_rotation = datetime.combine(
            local_time.date().replace(day=1),
            self.at_time,
            tzinfo=self.tz,
        )
        if next_rotation <= local_time:
            next_rotation = (
                next_rotation.replace(year=local_time.year + 1, month=1)
                if local_time.month == _DECEMBER
                else next_rotation.replace(month=local_time.month + 1)
            )
        return next_rotation

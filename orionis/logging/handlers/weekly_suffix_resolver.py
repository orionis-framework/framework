"""Resolve log suffixes for weekly rotation windows."""

from __future__ import annotations
from datetime import datetime, time, timedelta
from orionis.logging.contracts.suffix_resolver import SuffixResolver
from orionis.support.facades.datetime import DateTime


class WeeklySuffixResolver(SuffixResolver):
    """Resolve log suffixes for weekly rotation windows."""

    __slots__ = ("at_time", "tz")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self, at_time: time | None = None) -> None:
        """
        Initialize WeeklySuffixResolver.

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
        Generate a weekly suffix based on the provided datetime.

        Parameters
        ----------
        dt : datetime.datetime or None, optional
            The datetime to use for suffix generation. If None, uses current
            local datetime.

        Returns
        -------
        str
            The generated suffix in the format 'YYYY-weekWW'.
        """
        # Use current local datetime if none is provided
        if dt is None:
            dt = datetime.now(tz=self.tz)
        year, week, _ = dt.isocalendar()
        return f"{year}-week{week:02d}"

    def getNextRotationTime(self, current_time: datetime) -> datetime:
        """
        Calculate the next rotation datetime based on the current time.

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
        monday = local_time.date() - timedelta(days=local_time.weekday())
        next_rotation = datetime.combine(monday, self.at_time, tzinfo=self.tz)
        if next_rotation <= local_time:
            next_rotation += timedelta(days=7)
        return next_rotation

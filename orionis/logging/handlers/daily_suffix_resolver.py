from __future__ import annotations
from datetime import datetime, time, timedelta
from orionis.logging.contracts.suffix_resolver import SuffixResolver
from orionis.support.facades.datetime import DateTime

class DailySuffixResolver(SuffixResolver):

    __slots__ = ("at_time", "tz")

    def __init__(self, at_time: time | None = None) -> None:
        """
        Initialize the DailySuffixResolver with an optional rotation time.

        Parameters
        ----------
        at_time : time or None, optional
            The time of day when log rotation should occur. Defaults to midnight.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.at_time = at_time or time(0, 0, 0)
        self.tz = DateTime.getZoneInfo()

    def getSuffix(self, dt: datetime | None = None) -> str:
        """
        Generate a date-based suffix for log files.

        Parameters
        ----------
        dt : datetime or None, optional
            The datetime to use for generating the suffix. If None, uses current
            local datetime.

        Returns
        -------
        str
            The date suffix in the format 'YYYY-MM-DD'.
        """
        # Use current local datetime if none is provided
        if dt is None:
            dt = datetime.now(tz=self.tz)
        return dt.strftime("%Y-%m-%d")

    def getNextRotationTime(self, current_time: datetime) -> datetime:
        """
        Calculate the next log rotation datetime.

        Parameters
        ----------
        current_time : datetime
            The current datetime.

        Returns
        -------
        datetime
            The datetime when the next log rotation should occur.
        """
        # Combine current date with rotation time
        next_rotation = datetime.combine(
            current_time.date(),
            self.at_time,
            tzinfo=self.tz,
        )
        # If the calculated rotation time is not in the future, move to next day
        if next_rotation <= current_time:
            next_rotation += timedelta(days=1)
        return next_rotation

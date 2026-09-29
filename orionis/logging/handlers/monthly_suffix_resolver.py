from __future__ import annotations
from datetime import datetime, time
from orionis.logging.contracts.suffix_resolver import SuffixResolver
from orionis.support.facades.datetime import DateTime

class MonthlySuffixResolver(SuffixResolver):

    # ruff: noqa: PLR2004

    __slots__ = ("at_time", "tz")

    def __init__(self, at_time: time | None = None) -> None:
        """Initialize the resolver with an optional rotation time.

        Parameters
        ----------
        at_time : time or None, optional
            The time of day when rotation should occur. Defaults to midnight.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.at_time = at_time or time(0, 0, 0)
        self.tz = DateTime.getZoneInfo()

    def getSuffix(self, dt: datetime | None = None) -> str:
        """Return the suffix string for the given datetime.

        Parameters
        ----------
        dt : datetime or None, optional
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
        """Compute the next rotation datetime after the current time.

        Parameters
        ----------
        current_time : datetime
            The current datetime.

        Returns
        -------
        datetime
            The datetime when the next rotation should occur.
        """
        # Determine the first day of the next month
        if current_time.month == 12:
            next_month = datetime(current_time.year + 1, 1, 1, tzinfo=self.tz)
        else:
            next_month = datetime(
                current_time.year, current_time.month + 1, 1, tzinfo=self.tz,
            )
        # Combine with the rotation time
        return datetime.combine(
            next_month.date(),
            self.at_time,
            tzinfo=self.tz,
        )

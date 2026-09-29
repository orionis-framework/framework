from __future__ import annotations
from datetime import datetime, timedelta
from orionis.logging.contracts.suffix_resolver import SuffixResolver
from orionis.support.facades.datetime import DateTime

class HourlySuffixResolver(SuffixResolver):

    __slots__ = ("tz",)

    def __init__(self) -> None:
        """
        Initialize the HourlySuffixResolver.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.tz = DateTime.getZoneInfo()

    def getSuffix(self, dt: datetime | None = None) -> str:
        """
        Generate a suffix string for the given datetime in hourly format.

        Parameters
        ----------
        dt : datetime or None, optional
            The datetime object to generate the suffix for. If None, uses the
            current local datetime.

        Returns
        -------
        str
            The formatted suffix string in the form 'YYYY-MM-DD_HH'.
        """
        # Use current local datetime if dt is not provided
        if dt is None:
            dt = datetime.now(tz=self.tz)
        return dt.strftime("%Y-%m-%d_%H")

    def getNextRotationTime(self, current_time: datetime) -> datetime:
        """
        Calculate the next rotation time rounded to the next hour.

        Parameters
        ----------
        current_time : datetime
            The current datetime to base the next rotation time on.

        Returns
        -------
        datetime
            The datetime object representing the next rotation time at the
            start of the next hour.
        """
        # Round down to the start of the current hour, then add one hour
        return (
            current_time.replace(minute=0, second=0, microsecond=0, tzinfo=self.tz)
            + timedelta(hours=1)
        )

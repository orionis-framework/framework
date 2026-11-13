"""Resolve log suffixes for hourly rotation windows."""

from __future__ import annotations
from datetime import datetime, timedelta
from orionis.logging.contracts.suffix_resolver import SuffixResolver
from orionis.support.facades.datetime import DateTime


class HourlySuffixResolver(SuffixResolver):
    """Resolve log suffixes for hourly rotation windows."""

    __slots__ = ("tz",)
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self) -> None:
        """
        Initialize the HourlySuffixResolver.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.tz = DateTime.getZoneInfo()
        """Tz produced by ``DateTime.getZoneInfo``."""

    def getSuffix(self, dt: datetime | None = None) -> str:
        """
        Generate a suffix string for the given datetime in hourly format.

        Parameters
        ----------
        dt : datetime.datetime or None, optional
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
        current_time : datetime.datetime
            The current instant. Naive values use the resolver timezone.

        Returns
        -------
        datetime.datetime
            The datetime object representing the next rotation time at the
            start of the next hour.
        """
        local_time = (
            current_time.replace(tzinfo=self.tz)
            if current_time.tzinfo is None
            else current_time.astimezone(self.tz)
        )
        return local_time.replace(minute=0, second=0, microsecond=0) + timedelta(
            hours=1,
        )

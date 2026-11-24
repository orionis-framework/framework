"""
Interpret local times for the built-in log rotation strategies.

The resolvers share conversion rules for both record and calendar timestamps.
"""

from __future__ import annotations
from datetime import UTC, datetime, tzinfo
from orionis.logging.contracts.suffix_resolver import SuffixResolver
from orionis.support.facades.datetime import DateTime


class ApplicationTimeResolver(SuffixResolver):
    """
    Resolve log timestamps in the active application timezone.

    Set ``tz`` to pin a resolver to a particular zone.
    """

    __slots__ = ("_zone",)

    def __init__(self) -> None:
        """
        Initialize the resolver with the application's default timezone.

        Returns
        -------
        None
            Configure the resolver to read the application zone on each conversion.
        """
        self._zone: tzinfo | None = None
        """Store the rotation zone override, or None to use the application zone."""

    @property
    def tz(self) -> tzinfo:
        """
        Return the active rotation zone.

        Returns
        -------
        datetime.tzinfo
            Explicit override when set, otherwise the current application zone.
        """
        return self._zone if self._zone is not None else DateTime.getZoneInfo()

    @tz.setter
    def tz(self, value: tzinfo | None) -> None:
        """
        Set the timezone override for this resolver.

        Parameters
        ----------
        value : datetime.tzinfo or None
            Rotation zone, or None to resume following application settings.

        Returns
        -------
        None
            Apply the selected timezone policy to subsequent conversions.
        """
        self._zone = value

    def _local(self, value: datetime | None) -> datetime:
        """
        Express a timestamp in the resolver's timezone.

        Parameters
        ----------
        value : datetime.datetime or None
            Aware instant, naive local wall time, or None for the current time.

        Returns
        -------
        datetime.datetime
            Timezone-aware local datetime.
        """
        zone = self.tz
        if value is None:
            return datetime.now(zone)
        if value.tzinfo is None:
            return value.replace(tzinfo=zone)
        return value.astimezone(zone)

    @staticmethod
    def _upcoming(candidate: datetime, current: datetime) -> bool:
        """
        Check whether a proposed boundary exists and falls after the current time.

        Parameters
        ----------
        candidate : datetime.datetime
            Proposed timezone-aware local boundary.
        current : datetime.datetime
            Timezone-aware reference instant.

        Returns
        -------
        bool
            True when the candidate's wall time exists and its instant is later.
        """
        instant = candidate.astimezone(UTC)
        return (
            instant > current.astimezone(UTC)
            and instant.astimezone(candidate.tzinfo) == candidate
        )

# ruff: noqa: TC003
# Resolve datetime annotations when inspecting the public resolver contract.
"""Define how rotating log files derive their time-based suffixes."""

from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime


class SuffixResolver(ABC):
    """Define how rotating log files derive their time-based suffixes."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @abstractmethod
    def getSuffix(self, dt: datetime | None = None) -> str:
        """
        Return the suffix based on the rotation type.

        Parameters
        ----------
        dt : datetime.datetime or None, optional
            The datetime for which to obtain the suffix. If None, uses current time.

        Returns
        -------
        str
            The resolved suffix string.
        """

    @abstractmethod
    def getNextRotationTime(self, current_time: datetime) -> datetime:
        """
        Compute the next rotation time.

        Parameters
        ----------
        current_time : datetime.datetime
            The current datetime to base the next rotation calculation.

        Returns
        -------
        datetime.datetime
            The next rotation datetime.
        """

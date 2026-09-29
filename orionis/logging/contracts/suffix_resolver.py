from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

class SuffixResolver(ABC):

    __slots__ = ()

    @abstractmethod
    def getSuffix(self, dt: datetime | None = None) -> str:
        """
        Return the suffix based on the rotation type.

        Parameters
        ----------
        dt : datetime or None, optional
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
        current_time : datetime
            The current datetime to base the next rotation calculation.

        Returns
        -------
        datetime
            The next rotation datetime.
        """

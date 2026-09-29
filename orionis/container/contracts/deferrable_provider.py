from __future__ import annotations
from abc import ABC, abstractmethod

class IDeferrableProvider(ABC):

    @classmethod
    @abstractmethod
    def provides(cls) -> list[type | str]:
        """
        Return the services provided by this provider.

        Returns
        -------
        list[type | str]
            A list of service types or string identifiers that this provider offers.

        Raises
        ------
        NotImplementedError
            When subclasses do not implement this method.
        """

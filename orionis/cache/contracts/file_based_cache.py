from __future__ import annotations
from abc import ABC, abstractmethod

class IFileBasedCache(ABC):

    @abstractmethod
    def get(self) -> dict | None:
        """
        Retrieve cached data if valid.

        Returns
        -------
        dict or None
            The cached data if valid, otherwise None.
        """

    @abstractmethod
    def save(self, data: dict) -> tuple[int, str]:
        """
        Save data to the cache file with metadata.

        Parameters
        ----------
        data : dict
            The data to be cached.

        Returns
        -------
        tuple[int, str]
            A tuple containing the cache version and the sources hash.
        """

    @abstractmethod
    def clear(self) -> bool:
        """
        Remove the cache file if it exists.

        Returns
        -------
        bool
            True if the cache file was removed, False if it did not exist.
        """

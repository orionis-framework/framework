from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.localization.types import TranslationMap

class ITranslationRepository(ABC):
    """
    Define the contract for the in-memory translation cache.

    The repository guarantees that each locale is read from disk at
    most once, keeping every subsequent lookup fully in memory with
    O(1) access.

    Notes
    -----
    Implementations are not required to be thread-safe nor to copy the
    cached mapping before returning it.
    """

    __slots__ = ()

    @abstractmethod
    def get(self, locale: str) -> TranslationMap:
        """
        Return the translation map for *locale*, loading it on demand.

        Parameters
        ----------
        locale : str
            Locale code whose translations are requested.

        Returns
        -------
        TranslationMap
            Cached translation map for the locale. The mapping is the
            cached instance, not a copy.
        """

    @abstractmethod
    def has(self, locale: str) -> bool:
        """
        Determine whether *locale* is already cached in memory.

        Parameters
        ----------
        locale : str
            Locale code to check.

        Returns
        -------
        bool
            True when the locale is present in the cache.
        """

    @abstractmethod
    def forget(self, locale: str) -> bool:
        """
        Discard the cached translations for *locale*.

        Parameters
        ----------
        locale : str
            Locale code whose cache entry must be removed.

        Returns
        -------
        bool
            True when an entry was removed, False otherwise.
        """

    @abstractmethod
    def flush(self) -> None:
        """
        Discard every cached translation map.

        Returns
        -------
        None
        """

    @abstractmethod
    def loadedLocales(self) -> tuple[str, ...]:
        """
        Return the locales currently held in the cache.

        Returns
        -------
        tuple[str, ...]
            Locale codes present in the in-memory cache.
        """

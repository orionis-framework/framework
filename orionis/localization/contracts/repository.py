# ruff: noqa: TC001
# Resolve the public mapping annotation during runtime introspection.
"""Define the contract for the in-memory translation cache."""

from __future__ import annotations
from abc import ABC, abstractmethod
from orionis.localization.types import TranslationMap


class ITranslationRepository(ABC):
    """
    Define the contract for the in-memory translation cache.

    A repository loads locale maps on demand and retains them according
    to its cache policy. Invalidation, expiration, or capacity limits may
    require a locale to be loaded again.

    Notes
    -----
    Implementations are not required to be thread-safe nor to copy the
    cached mapping before returning it.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

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
        orionis.localization.types.TranslationMap
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
            No return value.
        """

    @abstractmethod
    def loadedLocales(self) -> tuple[str, ...]:
        """
        Return the locales currently held in the cache.

        Returns
        -------
        tuple[str, ``...``]
            Locale codes present in the in-memory cache.
        """

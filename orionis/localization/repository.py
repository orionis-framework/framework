from __future__ import annotations
from typing import TYPE_CHECKING
from orionis.localization.contracts.repository import ITranslationRepository

if TYPE_CHECKING:
    from orionis.localization.contracts.loader import ITranslationLoader
    from orionis.localization.types import LocaleCache, TranslationMap

class TranslationRepository(ITranslationRepository):
    """
    In-memory cache of translation maps keyed by locale.

    Each locale is loaded from disk exactly once; every subsequent
    lookup resolves from the internal dictionary with O(1) access. The
    cache is fully transparent to consumers.

    Notes
    -----
    The repository uses no lock. Two tasks missing the cache for the
    same locale may both call the loader; the last assignment wins and
    both callers receive a valid map. :meth:`get` returns the cached
    mapping itself, not a copy, so mutating it mutates the cache for
    every consumer.
    """

    __slots__ = ("_cache", "_loader")

    def __init__(self, loader: ITranslationLoader) -> None:
        """
        Initialize the repository with its translation loader.

        Parameters
        ----------
        loader : ITranslationLoader
            Loader used to read translation sources on cache misses.

        Returns
        -------
        None
        """
        self._loader = loader
        self._cache: LocaleCache = {}

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

        Raises
        ------
        TranslationSyntaxException
            If a translation file contains invalid JSON.
        """
        # Serve from memory when the locale was already loaded.
        cached = self._cache.get(locale)
        if cached is not None:
            return cached

        # Load once from disk and keep the map for every future lookup.
        loaded = self._loader.load(locale)
        self._cache[locale] = loaded
        return loaded

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
        return locale in self._cache

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
        return self._cache.pop(locale, None) is not None

    def flush(self) -> None:
        """
        Discard every cached translation map.

        Returns
        -------
        None
        """
        self._cache.clear()

    def loadedLocales(self) -> tuple[str, ...]:
        """
        Return the locales currently held in the cache.

        Returns
        -------
        tuple[str, ...]
            Locale codes present in the in-memory cache.
        """
        return tuple(self._cache)

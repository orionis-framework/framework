# ruff: noqa: TC001
# Resolve loader and mapping annotations during runtime injection and inspection.
"""Cache translation maps in memory by locale."""

from __future__ import annotations
import math
from collections import OrderedDict
from threading import RLock
from time import monotonic
from typing import Self
from orionis.localization.contracts.loader import ITranslationLoader
from orionis.localization.contracts.repository import ITranslationRepository
from orionis.localization.types import TranslationMap


class TranslationRepository(ITranslationRepository):
    """
    In-memory cache of translation maps keyed by locale.

    Recently used locales are retained within a configurable capacity.
    Missing locales expire so newly created translation files can be found.

    Notes
    -----
    A reentrant lock protects cache and loader access across threads.
    :meth:`orionis.localization.TranslationRepository.get` returns the cached mapping
    itself, not a copy.
    """

    __slots__ = ("_cache", "_expires", "_limit", "_loader", "_lock", "_negative_ttl")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self: Self,
        loader: ITranslationLoader,
        *,
        max_locales: int = 256,
        negative_ttl: float = 30,
    ) -> None:
        """
        Initialize the repository with its translation loader.

        Parameters
        ----------
        loader : orionis.localization.contracts.ITranslationLoader
            Loader used to read translation sources on cache misses.
        max_locales : int
            Maximum retained locales, including empty results.
        negative_ttl : float
            Seconds to retain an empty result before retrying the loader.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        ValueError
            If the capacity is not a positive integer or the negative-cache
            lifetime is nonfinite or negative.
        TypeError
            If the negative-cache lifetime is not numeric.
        """
        self._loader = loader
        """Loader used to read translation sources on cache misses."""
        if (
            isinstance(max_locales, bool)
            or not isinstance(max_locales, int)
            or max_locales < 1
        ):
            error_msg = "max_locales must be a positive integer."
            raise ValueError(error_msg)
        if not math.isfinite(negative_ttl) or negative_ttl < 0:
            error_msg = "negative_ttl must be finite and nonnegative."
            raise ValueError(error_msg)
        self._cache: OrderedDict[str, TranslationMap] = OrderedDict()
        """Cache policy or cached state used by this component."""
        self._expires: dict[str, float] = {}
        """Expiration deadline for the cached or protected value."""
        self._limit = max_locales
        """Maximum retained locales, including empty results."""
        self._negative_ttl = negative_ttl
        """Seconds to retain an empty result before retrying the loader."""
        self._lock = RLock()
        """Lock protecting concurrent access to shared state."""

    def get(self: Self, locale: str) -> TranslationMap:
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

        Raises
        ------
        orionis.localization.TranslationSyntaxException
            If a translation file contains invalid JSON.
        """
        with self._lock:
            if self.has(locale):
                self._cache.move_to_end(locale)
                return self._cache[locale]
            loaded = self._loader.load(locale)
            if len(self._cache) >= self._limit:
                oldest, _value = self._cache.popitem(last=False)
                self._expires.pop(oldest, None)
            self._cache[locale] = loaded
            if not loaded:
                self._expires[locale] = monotonic() + self._negative_ttl
            return loaded

    def has(self: Self, locale: str) -> bool:
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
        with self._lock:
            deadline = self._expires.get(locale)
            if deadline is not None and monotonic() >= deadline:
                self.forget(locale)
            return locale in self._cache

    def forget(self: Self, locale: str) -> bool:
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
        with self._lock:
            self._expires.pop(locale, None)
            return self._cache.pop(locale, None) is not None

    def flush(self: Self) -> None:
        """
        Discard every cached translation map.

        Returns
        -------
        None
            No return value.
        """
        with self._lock:
            self._cache.clear()
            self._expires.clear()

    def loadedLocales(self: Self) -> tuple[str, ...]:
        """
        Return the locales currently held in the cache.

        Returns
        -------
        tuple[str, ``...``]
            Unexpired locale codes, ordered from least to most recently used.
        """
        with self._lock:
            return tuple(locale for locale in tuple(self._cache) if self.has(locale))

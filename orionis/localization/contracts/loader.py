# ruff: noqa: TC001
# Resolve the public mapping annotation during runtime introspection.
"""Define the contract for translation file loaders."""

from __future__ import annotations
from abc import ABC, abstractmethod
from orionis.localization.types import TranslationMap


class ITranslationLoader(ABC):
    """
    Define the contract for translation file loaders.

    A loader reads translation sources from disk and produces a flat
    translation map per locale. It knows nothing about caching, locale
    resolution, or template engines: its single responsibility is
    loading translations.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @abstractmethod
    def load(self, locale: str) -> TranslationMap:
        """
        Load every translation available for *locale*.

        Merges the grouped files located under ``{path}/{locale}/*.json``
        (flattened with dot notation, e.g. ``validation.required``) with
        the root JSON file ``{path}/{locale}.json`` whose keys are the
        literal source texts. Root JSON entries take precedence over
        grouped entries on key collision.

        Parameters
        ----------
        locale : str
            Locale code whose translation sources must be read.

        Returns
        -------
        orionis.localization.types.TranslationMap
            Flat mapping of translation key to translated text. An
            empty mapping is returned when no source exists.

        Raises
        ------
        orionis.localization.InvalidLocaleException
            If the locale code is malformed or contains path components.
        orionis.localization.TranslationException
            If a source resolves outside the configured language directory.
        orionis.localization.TranslationSyntaxException
            If a translation file is not UTF-8 encoded, contains
            invalid JSON, or its root element is not an object.
        """

    @abstractmethod
    def availableLocales(self) -> tuple[str, ...]:
        """
        Discover every locale with at least one translation source.

        Returns
        -------
        tuple[str, ``...``]
            Sorted locale codes discovered from root JSON files and
            grouped directories inside the language path.
        """

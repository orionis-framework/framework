from __future__ import annotations
from typing import Any
from orionis.support.facades.lang import Lang

# ruff: noqa: ANN401

def _global_trans() -> Any:
    """
    Build the ``trans`` (and ``__``) template global.

    Returns
    -------
    Any
        Callable that translates a key for a given or the active locale.
    """
    def trans(key: str, locale: str | None = None, **replace: Any) -> str:
        """
        Translate a key for the active or an explicit locale.

        Parameters
        ----------
        key : str
            Translation key, literal text or dot-notated grouped key.
        locale : str | None, optional
            Locale to translate into, or ``None`` for the active locale.
        **replace : Any
            Placeholder values substituted into the resolved line.

        Returns
        -------
        str
            Translated line, or the key itself when missing.
        """
        return Lang.get(key, locale, **replace)

    return trans

def _global_choice() -> Any:
    """
    Build the ``choice`` template global.

    Returns
    -------
    Any
        Callable that translates a pluralized key based on a quantity.
    """
    def choice(
        key: str,
        count: int,
        locale: str | None = None,
        **replace: Any,
    ) -> str:
        """
        Translate a pluralized key based on a quantity.

        Parameters
        ----------
        key : str
            Translation key containing the pluralized segments.
        count : int
            Quantity used to select the proper segment.
        locale : str | None, optional
            Locale to translate into, or ``None`` for the active locale.
        **replace : Any
            Placeholder values substituted into the selected segment.

        Returns
        -------
        str
            Pluralized and interpolated translation line.
        """
        return Lang.choice(key, count, locale, **replace)

    return choice

def _global_locale() -> Any:
    """
    Build the ``locale`` template global.

    Returns
    -------
    Any
        Callable that returns the active application locale.
    """
    def locale() -> str:
        """
        Return the active application locale.

        Returns
        -------
        str
            Locale code currently in use.
        """
        return Lang.getLocale()

    return locale

def _global_locales() -> Any:
    """
    Build the ``locales`` template global.

    Returns
    -------
    Any
        Callable that returns every locale with a translation source.
    """
    def locales() -> tuple[str, ...]:
        """
        Return every locale with at least one translation source.

        Returns
        -------
        tuple[str, ...]
            Sorted locale codes discovered in the language path.
        """
        return Lang.availableLocales()

    return locales

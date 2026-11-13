"""Group the localization components and public imports."""

from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.localization.exceptions import (
        InvalidLocaleException,
        TranslationException,
        TranslationFileNotFoundException,
        TranslationSyntaxException,
    )
    from orionis.localization.loader import TranslationLoader
    from orionis.localization.manager import LocalizationManager
    from orionis.localization.repository import TranslationRepository
    from orionis.localization.translator import Translator

__all__ = [
    "InvalidLocaleException",
    "LocalizationManager",
    "TranslationException",
    "TranslationFileNotFoundException",
    "TranslationLoader",
    "TranslationRepository",
    "TranslationSyntaxException",
    "Translator",
]

_EXCEPTION_MODULE = "orionis.localization.exceptions"
"""Module defining the public localization exception types."""

_EXPORTS = {
    "InvalidLocaleException": (_EXCEPTION_MODULE, "InvalidLocaleException"),
    "LocalizationManager": ("orionis.localization.manager", "LocalizationManager"),
    "TranslationException": (_EXCEPTION_MODULE, "TranslationException"),
    "TranslationFileNotFoundException": (
        _EXCEPTION_MODULE,
        "TranslationFileNotFoundException",
    ),
    "TranslationLoader": ("orionis.localization.loader", "TranslationLoader"),
    "TranslationRepository": (
        "orionis.localization.repository",
        "TranslationRepository",
    ),
    "TranslationSyntaxException": (_EXCEPTION_MODULE, "TranslationSyntaxException"),
    "Translator": ("orionis.localization.translator", "Translator"),
}
"""Public export names mapped to their defining modules and attributes."""


def __getattr__(name: str) -> object:
    """
    Resolve and cache a public package export.

    Parameters
    ----------
    name : str
        Public attribute requested from this package.

    Returns
    -------
    object
        Exported object from its defining module.

    Raises
    ------
    AttributeError
        If the requested attribute is not exported.
    """
    return _resolve_export(globals(), _EXPORTS, name)


def __dir__() -> list[str]:
    """
    List loaded attributes and declared public exports.

    Returns
    -------
    list[str]
        Sorted attribute names available on this package.
    """
    return sorted(globals().keys() | _EXPORTS.keys())

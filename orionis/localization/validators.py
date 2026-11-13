"""Validate locale codes shared by translators and filesystem loaders."""

import re

from orionis.localization.exceptions import InvalidLocaleException

_LOCALE_PATTERN = re.compile(r"[A-Za-z0-9]+(?:[_-][A-Za-z0-9]+)*")
"""Accept alphanumeric locale segments separated by hyphens or underscores."""


def validate_locale(locale: str) -> str:
    """Validate a locale code and return its original spelling.

    Parameters
    ----------
    locale : str
        Locale code to validate without normalizing its case or separators.

    Returns
    -------
    str
        The unchanged, validated locale code.

    Raises
    ------
    orionis.localization.InvalidLocaleException
        If the locale is empty, malformed, or unsafe for path use.
    """
    if not isinstance(locale, str) or _LOCALE_PATTERN.fullmatch(locale) is None:
        error_msg = f"Invalid locale code: {locale!r}"
        raise InvalidLocaleException(error_msg)
    return locale

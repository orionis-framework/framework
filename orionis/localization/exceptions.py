from __future__ import annotations

class TranslationException(Exception):
    """Base exception for all localization-related errors."""

class InvalidLocaleException(TranslationException):
    """Raised when a locale code is empty, malformed, or unsafe."""

class TranslationFileNotFoundException(TranslationException):
    """Raised when a translation file cannot be found on disk."""

class TranslationSyntaxException(TranslationException):
    """Raised when a translation file contains invalid JSON or structure."""

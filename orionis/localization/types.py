from __future__ import annotations
from collections.abc import Callable

# Callable is imported at runtime so the aliases below stay introspectable.

# Flat mapping of translation key to translated text for a single locale.
type TranslationMap = dict[str, str]

# In-memory cache mapping each locale code to its translation map.
type LocaleCache = dict[str, TranslationMap]

# Handler invoked when a translation key is missing; receives the key and
# the locale, and may return a replacement line or ``None``.
type MissingKeyHandler = Callable[[str, str], str | None]

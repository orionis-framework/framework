# orionis.localization

> API reference derived from the current implementation.

## Table of contents

- Requirements
- Functional overview
- Module structure
- API reference
- Usage examples
- Design characteristics
- Performance and concurrency
- Compatibility notes
- Verification and limitations

## Requirements

Python 3.14 or newer, as declared by pyproject.toml.

## Functional overview

The orionis.localization initializer exports 8 public symbols. This reference uses __all__, export routes, and current source files as evidence.

## Module structure

| Path | Responsibility |
| --- | --- |
| ../__init__.py | Defines package exports. |
| orionis.localization/ | Implementations and subpackages for those exports. |

## API reference

| Symbol | Verified import | Source | Declaration | Observed behavior |
| --- | --- | --- | --- | --- |
| InvalidLocaleException | from orionis.localization import InvalidLocaleException | [exceptions.py](../exceptions.py) | InvalidLocaleException | Raised when a locale code is empty, malformed, or unsafe. |
| LocalizationManager | from orionis.localization import LocalizationManager | [manager.py](../manager.py) | LocalizationManager | Wire the localization component from the application configuration. The manager reads the ``app.locale``, ``app.fallback_locale``, and ``app.language_path`` settings, builds the loader, the repository, and the translator, and caches the resulting translator so a single shared instance serves the whole application. |
| LocalizationManager.translator | from orionis.localization import LocalizationManager | [manager.py](../manager.py) | def translator(self) -> ITranslator | Return the shared translator instance, building it on demand. Returns ------- ITranslator Translator configured from the application settings. Raises ------ InvalidLocaleException If the configured locale or fallback locale is malformed. |
| TranslationException | from orionis.localization import TranslationException | [exceptions.py](../exceptions.py) | TranslationException | Base exception for all localization-related errors. |
| TranslationFileNotFoundException | from orionis.localization import TranslationFileNotFoundException | [exceptions.py](../exceptions.py) | TranslationFileNotFoundException | Raised when a translation file cannot be found on disk. |
| TranslationLoader | from orionis.localization import TranslationLoader | [loader.py](../loader.py) | TranslationLoader | Load translation sources from the configured language path. The loader reads root JSON files (``{path}/{locale}.json``) whose keys are the literal source texts, and grouped JSON files (``{path}/{locale}/{group}.json``) flattened with dot notation such as ``validation.required``. Decoding is performed with ``msgspec`` for maximum throughput. The loader holds no cache: that concern belongs to the repository. Notes ----- Translation files are read as raw bytes and decoded as UTF-8 JSON. A source stored in any other encoding raises :class:`TranslationSyntaxException`, like any other unusable payload. |
| TranslationLoader.load | from orionis.localization import TranslationLoader | [loader.py](../loader.py) | def load(self, locale: str) -> TranslationMap | Load every translation available for *locale*. Grouped files are merged first and root JSON entries are merged last so literal-text keys take precedence on collision. Parameters ---------- locale : str Locale code whose translation sources must be read. Returns ------- TranslationMap Flat mapping of translation key to translated text. An empty mapping is returned when no source exists. Raises ------ TranslationSyntaxException If a translation file is not UTF-8 encoded, contains invalid JSON, or its root element is not an object. |
| TranslationLoader.availableLocales | from orionis.localization import TranslationLoader | [loader.py](../loader.py) | def availableLocales(self) -> tuple[str, ...] | Discover every locale with at least one translation source. Returns ------- tuple[str, ...] Sorted locale codes discovered from root JSON files and grouped directories inside the language path. |
| TranslationRepository | from orionis.localization import TranslationRepository | [repository.py](../repository.py) | TranslationRepository | In-memory cache of translation maps keyed by locale. Each locale is loaded from disk exactly once; every subsequent lookup resolves from the internal dictionary with O(1) access. The cache is fully transparent to consumers. Notes ----- The repository uses no lock. Two tasks missing the cache for the same locale may both call the loader; the last assignment wins and both callers receive a valid map. :meth:`get` returns the cached mapping itself, not a copy, so mutating it mutates the cache for every consumer. |
| TranslationRepository.get | from orionis.localization import TranslationRepository | [repository.py](../repository.py) | def get(self, locale: str) -> TranslationMap | Return the translation map for *locale*, loading it on demand. Parameters ---------- locale : str Locale code whose translations are requested. Returns ------- TranslationMap Cached translation map for the locale. The mapping is the cached instance, not a copy. Raises ------ TranslationSyntaxException If a translation file contains invalid JSON. |
| TranslationRepository.has | from orionis.localization import TranslationRepository | [repository.py](../repository.py) | def has(self, locale: str) -> bool | Determine whether *locale* is already cached in memory. Parameters ---------- locale : str Locale code to check. Returns ------- bool True when the locale is present in the cache. |
| TranslationRepository.forget | from orionis.localization import TranslationRepository | [repository.py](../repository.py) | def forget(self, locale: str) -> bool | Discard the cached translations for *locale*. Parameters ---------- locale : str Locale code whose cache entry must be removed. Returns ------- bool True when an entry was removed, False otherwise. |
| TranslationRepository.flush | from orionis.localization import TranslationRepository | [repository.py](../repository.py) | def flush(self) -> None | Discard every cached translation map. Returns ------- None |
| TranslationRepository.loadedLocales | from orionis.localization import TranslationRepository | [repository.py](../repository.py) | def loadedLocales(self) -> tuple[str, ...] | Return the locales currently held in the cache. Returns ------- tuple[str, ...] Locale codes present in the in-memory cache. |
| TranslationSyntaxException | from orionis.localization import TranslationSyntaxException | [exceptions.py](../exceptions.py) | TranslationSyntaxException | Raised when a translation file contains invalid JSON or structure. |
| Translator | from orionis.localization import Translator | [translator.py](../translator.py) | Translator | Resolve translation lines for the active locale. The translator performs O(1) lookups against the in-memory repository, falls back to the configured fallback locale, applies style ``:name`` parameter replacement, and selects pluralized segments through :meth:`choice`. Notes ----- The provider binds a single instance for the whole process and the class uses no lock, so :meth:`setLocale`, :meth:`missing`, :meth:`reload`, :meth:`forget` and :meth:`flush` are global side effects visible to every concurrent task. Pass an explicit ``locale`` to :meth:`get`, :meth:`has` or :meth:`choice` to select a language for a single call instead. |
| Translator.get | from orionis.localization import Translator | [translator.py](../translator.py) | def get(self, key: str, locale: str / None, **replace) -> str | Retrieve the translation line registered under *key*. The lookup order is the requested locale first, then the fallback locale, and finally the key itself when no translation exists. Placeholders in the ``:name`` form are substituted with the values provided in *replace*. Parameters ---------- key : str Translation key, either a literal source text or a dot-notated grouped key such as ``validation.required``. locale : str / None, optional Locale to translate into, or ``None`` for the active locale. **replace : object Placeholder values substituted into the resolved line. Returns ------- str Translated line, or the key itself when missing. Raises ------ InvalidLocaleException If an explicit locale is malformed. |
| Translator.has | from orionis.localization import Translator | [translator.py](../translator.py) | def has(self, key: str, locale: str / None, *, fallback: bool) -> bool | Determine whether a translation exists for *key*. Parameters ---------- key : str Translation key to check. locale : str / None, optional Locale to inspect, or ``None`` for the active locale. fallback : bool, optional Whether the fallback locale is also inspected. Returns ------- bool True when a translation line is registered for the key. Raises ------ InvalidLocaleException If an explicit locale is malformed. |
| Translator.choice | from orionis.localization import Translator | [translator.py](../translator.py) | def choice(self, key: str, count: int, locale: str / None, **replace) -> str | Retrieve a pluralized translation line based on *count*. Segments are separated by ``/`` and may declare explicit conditions such as ``{0}``, ``{1}`` or ranges ``[2,*]``. When no explicit condition matches, the first segment is used for a count of one and the second segment otherwise. The ``:count`` placeholder is always available in the selected segment. Parameters ---------- key : str Translation key containing the pluralized segments. count : int Quantity used to select the proper segment. The value is used as received: explicit conditions compare it against their numeric bounds and the positional rule tests ``count == 1``. No coercion or validation is applied, so a non-numeric quantity propagates the comparison ``TypeError`` raised by Python. locale : str / None, optional Locale to translate into, or ``None`` for the active locale. **replace : object Placeholder values substituted into the selected segment. Returns ------- str Pluralized and interpolated translation line. Raises ------ InvalidLocaleException If an explicit locale is malformed. |
| Translator.setLocale | from orionis.localization import Translator | [translator.py](../translator.py) | def setLocale(self, locale: str) -> None | Change the active locale at runtime. Parameters ---------- locale : str Locale code to activate. Returns ------- None Raises ------ InvalidLocaleException If the locale is malformed. |
| Translator.getLocale | from orionis.localization import Translator | [translator.py](../translator.py) | def getLocale(self) -> str | Return the active locale. Returns ------- str Locale code currently in use. |
| Translator.availableLocales | from orionis.localization import Translator | [translator.py](../translator.py) | def availableLocales(self) -> tuple[str, ...] | Return every locale with at least one translation source. Returns ------- tuple[str, ...] Sorted locale codes discovered in the language path. |
| Translator.reload | from orionis.localization import Translator | [translator.py](../translator.py) | def reload(self, locale: str / None) -> None | Discard cached translations so they are re-read from disk. Parameters ---------- locale : str / None, optional Locale to reload, or ``None`` to reload every locale. Returns ------- None Raises ------ InvalidLocaleException If an explicit locale is malformed. |
| Translator.forget | from orionis.localization import Translator | [translator.py](../translator.py) | def forget(self, locale: str) -> bool | Discard the cached translations for a single locale. Parameters ---------- locale : str Locale code whose cache entry must be removed. Returns ------- bool True when an entry was removed, False otherwise. Raises ------ InvalidLocaleException If the locale is malformed. |
| Translator.flush | from orionis.localization import Translator | [translator.py](../translator.py) | def flush(self) -> None | Discard every cached translation map. Returns ------- None |
| Translator.missing | from orionis.localization import Translator | [translator.py](../translator.py) | def missing(self, handler: MissingKeyHandler / None) -> None | Register a handler invoked when a translation key is missing. The handler receives the key and the locale, and may return a replacement line. When it returns ``None`` the key itself is used as the translation. Parameters ---------- handler : MissingKeyHandler / None Callable invoked on missing keys, or ``None`` to remove the current handler. Returns ------- None |

## Usage examples

    from orionis.localization import InvalidLocaleException

The import path matches the API table. Import status: executed successfully under Python 3.14.3.

## Design characteristics

The package uses an explicit public surface. Private names are excluded; declarations link to their concrete owner.

## Performance and concurrency

No uniform guarantee is declared at package level. Inspect each linked file for I/O, coroutines, caches, locks, and shared state.

## Compatibility notes

Declared minimum: Python 3.14. Validation used Python 3.14.3. Dependency bounds are in pyproject.toml.

## Verification and limitations

Python files were analysed and exports verified. Failures from dependencies, callbacks, I/O, or configuration may propagate and are not presented as exhaustive.

# orionis.localization

> `orionis.localization` loads JSON language resources, caches flattened translations, applies fallback and replacements, and selects plural forms.

## Overview

The localization pipeline has four small layers: `TranslationLoader` reads resources, `TranslationRepository` caches each locale, `Translator` performs lookup and plural selection, and `LocalizationManager` wires them from application configuration. `LocalizationProvider` exposes the shared translator through the container and the `Lang` facade.

Translation resources may be root files such as `resources/lang/es.json`, where keys are literal source strings, or grouped files such as `resources/lang/es/validation.json`, flattened to keys like `validation.required`.

## Requirements

- Python 3.14 or newer.
- UTF-8 JSON translation files whose root value is an object.
- A valid language path for file-backed translations.
- A booted Orionis application when using `orionis.support.facades.Lang`.

## Quick start

```python
from pathlib import Path
from orionis.localization import TranslationLoader, TranslationRepository, Translator

loader = TranslationLoader(Path("resources/lang"))
repository = TranslationRepository(loader)
translator = Translator(locale="en", fallback="en", loader=loader, repository=repository)
assert translator.get("Welcome") == "Welcome"
assert translator.get("Welcome", locale="es") == "Bienvenido"
assert translator.availableLocales() == ("en", "es")
print(translator.getLocale())
```

Validation: **Executed successfully** from the repository root on CPython 3.14.6.

## Core concepts

### Sources and keys

`{locale}.json` is suited to literal source-text keys. `{locale}/{group}.json` is recursively flattened under the group name. Grouped files load in sorted order, then the root locale file is merged last and wins on a key collision. Non-string leaf values are converted with `str()`.

### Lookup and fallback

`get(key, locale=None, **replace)` checks the explicit or active locale, then the configured fallback when different. If neither contains the key, a registered missing-key handler may return a line; otherwise the key itself is returned. `has(..., fallback=False)` can restrict existence checks to the requested locale.

### Replacement

Placeholders use `:name`. The translator also replaces `:Name` with a capitalized value and `:NAME` with an uppercased value. Longer placeholder names are processed first, preventing a short name from consuming a longer prefix.

### Plural selection

`choice(key, count, ...)` splits a line on `|`. It supports exact selectors such as `{0}` or `{1}`, inclusive ranges such as `[2,10]`, and `*` as an open bound. Without a matching explicit selector, one segment means always use it; otherwise count `1` selects the first and every other count selects the second. `:count` is injected automatically.

## Module structure

| Path | Responsibility |
|---|---|
| `loader.py` | Discover, decode, merge, and flatten JSON resources. |
| `repository.py` | Lazy, per-locale in-memory cache. |
| `translator.py` | Lookup, fallback, interpolation, pluralization, locale and cache controls. |
| `manager.py` | Build and retain a translator from application configuration. |
| `provider.py` | Register manager/translator services and pin `Lang`. |
| `types.py` | Translation map/cache and missing-handler aliases. |
| `exceptions.py` | Localization error hierarchy. |
| `contracts/` | Loader, repository, translator, and manager interfaces. |

## Public API

The package exports `TranslationLoader`, `TranslationRepository`, `Translator`, `LocalizationManager`, `TranslationException`, `InvalidLocaleException`, `TranslationFileNotFoundException`, and `TranslationSyntaxException`.

### `TranslationLoader(path)`

`load(locale)` returns a flat `dict[str, str]`; an unknown locale yields an empty dictionary. `availableLocales()` returns a sorted tuple gathered from root `.json` files and directories containing `.json` group files. The loader deliberately holds no cache.

### `TranslationRepository(loader)`

`get(locale)` loads once and returns the cached map. `has(locale)`, `forget(locale)`, `flush()`, and `loadedLocales()` inspect or invalidate that process-local cache. Loaded-locale order follows insertion order.

### `Translator`

- `get`, `has`, and `choice` perform per-call translation operations.
- `setLocale` and `getLocale` control the shared active locale.
- `availableLocales` delegates discovery to the loader.
- `reload(locale=None)`, `forget(locale)`, and `flush()` invalidate repository entries.
- `missing(handler)` installs or removes a process-wide missing-key callback on that translator.

### `LocalizationManager(app)`

`translator()` lazily creates one translator using `app.locale`, `app.fallback_locale`, and `app.language_path`. Relative resource paths are resolved against `app.basePath`.

## Common workflows

### Translate application text

Use `Lang.get("Welcome")` in booted application code. Prefer stable dotted keys for validation and domain messages; literal keys are convenient for UI copy already present in root resources. Pass replacement values as keyword arguments.

### Select a request-specific locale

Pass `locale=` to `get`, `has`, or `choice`. Avoid calling `setLocale()` per request because the provider shares one translator process-wide and concurrent requests would observe the mutation.

### Update translations during development

Call `Lang.reload("es")` after a file change, or `Lang.reload()` / `Lang.flush()` to discard every cached locale. The next lookup reloads it lazily. Production workers have independent caches and must each be invalidated or restarted.

### Report missing keys

Register `missing(lambda key, locale: ...)` for telemetry or a controlled substitute. Keep the handler fast and non-recursive. Returning `None` preserves the default behavior of echoing the key.

## Examples

### Apply fallback and replacements

```python
from orionis.localization import TranslationRepository, Translator


class MemoryLoader:
    data = {
        "en": {"greeting": "Hello :name"},
        "es": {},
    }

    def load(self, locale: str) -> dict[str, str]:
        return dict(self.data.get(locale, {}))

    def availableLocales(self) -> tuple[str, ...]:
        return tuple(sorted(self.data))


loader = MemoryLoader()
repository = TranslationRepository(loader)
translator = Translator(locale="es", fallback="en", loader=loader, repository=repository)
assert translator.get("greeting", name="Ada") == "Hello Ada"
assert translator.has("greeting")
assert not translator.has("greeting", fallback=False)
print(translator.get("missing.key"))
```

Validation: **Executed successfully** on CPython 3.14.6.

### Select plural forms

```python
from orionis.localization import TranslationRepository, Translator


class MemoryLoader:
    def load(self, locale: str) -> dict[str, str]:
        return {"apples": "{0} No apples|{1} One apple|[2,*] :count apples"}

    def availableLocales(self) -> tuple[str, ...]:
        return ("en",)


loader = MemoryLoader()
translator = Translator(
    locale="en",
    fallback="en",
    loader=loader,
    repository=TranslationRepository(loader),
)
assert translator.choice("apples", 0) == "No apples"
assert translator.choice("apples", 1) == "One apple"
assert translator.choice("apples", 7) == "7 apples"
print(translator.choice("apples", 2))
```

Validation: **Executed successfully** on CPython 3.14.6.

### Handle missing keys

```python
from orionis.localization import TranslationRepository, Translator


class EmptyLoader:
    def load(self, locale: str) -> dict[str, str]:
        return {}

    def availableLocales(self) -> tuple[str, ...]:
        return ()


loader = EmptyLoader()
translator = Translator(
    locale="en",
    fallback="en",
    loader=loader,
    repository=TranslationRepository(loader),
)
translator.missing(lambda key, locale: f"[{locale}] {key}")
assert translator.get("unknown") == "[en] unknown"
translator.missing(None)
assert translator.get("unknown") == "unknown"
print("missing handler removed")
```

Validation: **Executed successfully** on CPython 3.14.6.

### Inspect and invalidate the repository cache

```python
from pathlib import Path
from orionis.localization import TranslationLoader, TranslationRepository

repository = TranslationRepository(TranslationLoader(Path("resources/lang")))
assert repository.loadedLocales() == ()
assert repository.get("en")["Welcome"] == "Welcome"
assert repository.loadedLocales() == ("en",)
assert repository.forget("en")
assert repository.loadedLocales() == ()
print("cache cleared")
```

Validation: **Executed successfully** from the repository root on CPython 3.14.6.

### Use the application facade

```python
from orionis.support.facades import Lang

title = Lang.get("Welcome")
message = Lang.choice("cart.items", 3, user="Ada")
available = Lang.availableLocales()
```

Validation: **Import-only** on CPython 3.14.6; calls require a booted application and pinned facade.

## Configuration

Localization uses fields in `config/app.py`:

| Setting | Environment | Default | Meaning |
|---|---|---|---|
| `app.locale` | `APP_LOCALE` | `en` | Shared active locale. |
| `app.fallback_locale` | `APP_FALLBACK_LOCALE` | `en` | Secondary locale for missing keys. |
| `app.language_path` | `APP_LANGUAGE_PATH` | `resources/lang/` | Absolute path or path relative to application root. |

Locale codes must contain alphanumeric groups separated only by `-` or `_`, for example `en`, `es-CO`, or `pt_BR`. They are preserved exactly; case and separator normalization are the application's responsibility.

## Integration with Orionis

`LocalizationProvider` binds `ILocalizationManager` to `LocalizationManager` as a singleton. During boot it materializes the translator, binds `ITranslator`, and pins the `Lang` facade. Templates receive localization helpers/globals, and framework default responses use translations for user-facing pages.

Direct construction is useful for libraries and tests. Application code should inject `ITranslator` or use `Lang`, which both reference the same configured singleton.

## Errors and edge cases

- Malformed or path-like locale codes raise `InvalidLocaleException` before filesystem access.
- Invalid UTF-8, malformed JSON, or a non-object JSON root raises `TranslationSyntaxException`.
- A file removed between discovery and reading raises `TranslationFileNotFoundException`.
- Missing directories/locales are not exceptional: discovery returns `()` and loading returns `{}`.
- Missing keys echo the key unless a handler returns a string.
- Replacement is literal string substitution, not message-format parsing; unused placeholders remain unchanged.
- Explicit plural bounds are numeric and inclusive. Malformed conditions do not match; nonnumeric counts can propagate comparison `TypeError`.
- Root files override grouped keys on collision. Multiple grouped files are merged deterministically by filename.
- `reload()` invalidates cached maps; it does not proactively read or validate changed files.

## Performance and concurrency

JSON decoding uses `msgspec`; nested dictionaries are flattened once when a locale is first requested. Subsequent key lookup is O(1) in the repository map. Filesystem discovery and loading are synchronous, so warm required locales during bootstrap if first-request latency matters.

The provider shares one mutable translator without a lock. Concurrent reads are appropriate after caches are warm, but `setLocale`, `missing`, `reload`, `forget`, and `flush` are global mutations and can race with reads. Prefer explicit `locale=` for request-scoped selection and coordinate cache invalidation operationally.

## Compatibility

Orionis declares Python 3.14+ and uses UTF-8 JSON. Translation syntax is Orionis-specific rather than ICU MessageFormat. Locale identifiers are safe opaque codes, not automatically validated against CLDR or operating-system locales. Resource lookup works consistently on Windows and POSIX through `pathlib`.

## Verification notes

Validation used CPython 3.14.6. Exports, contracts, loader precedence/flattening, repository cache, translator fallback/replacements/plural rules, manager, provider, facade, application settings, template integration, and all `tests/localization` were inspected. All **148** localization test methods passed through the Orionis runner. Four direct programs executed successfully; the facade example was import-validated only.

# Persistence, reloads, and Env reference

## Public API

### `Env.get(key, default=None)` and `env(key, default=None)`

Validate the uppercase key and return its parsed process value, or the exact default when absent. `env()` is a thin one-call delegate to `Env.get`.

### `Env.set(key, value, type_hint=None, *, only_os=False)`

Serializes the value, optionally with an explicit typed prefix. By default it updates `.env`, the file cache, and `os.environ`; `only_os=True` updates only the current process. Success returns `True`. Without a hint, supported values include `None`, strings, scalars, and literal containers; other objects are converted with `str`. An explicit hint requires a value accepted by the type validator.

### `Env.unset(key, *, only_os=False)`

Removes the entry from file/cache and process, or from the process only. Missing valid keys are treated as successfully absent and return `True`; `python-dotenv` may emit an informational message for a missing file entry.

### `Env.all()` and `Env.reload()`

`all()` returns a new dictionary containing parsed file-backed cache values. `reload()` reads and interpolates the file once, validates values for process publication, and uses that snapshot to update the process and rebuild its cache. A reload failure is wrapped by `DotEnv` as `RuntimeError` and propagates, including invalid UTF-8. The facade returns `False` only for `OSError` or `ValueError` escaping initialization or the delegated call.

### Advanced components

`EnvironmentCaster`, `EnvironmentValueType`, `DotEnv`, and `SecureKeyGenerator` live in their respective subpackages. They are useful for framework integration and tests, but only `Env` and `env` are exported by `orionis.environment`.

## Integration with Orionis

Framework configuration dataclasses call `Env.get` in their default factories, so environment parsing happens before providers consume normalized config. Application key validation also uses `SecureKeyGenerator` and persists a generated `APP_KEY` through `Env.set` when absent.

Console, HTTP, database, cache, queue, session, mail, logging, view, MCP, and testing configuration all depend on this module. It has no service provider because its singleton facade is usable during early bootstrap.

## Errors and edge cases

- Public lookup and mutation keys must start with an uppercase letter and contain only uppercase letters, digits, and underscores; invalid keys raise `TypeError` or `ValueError`. File loading retains dotenv's naming rules.
- Unknown explicit type hints passed to `Env.set` raise `RuntimeError`; incompatible values raise `TypeError` or `ValueError`.
- Empty unprefixed stored strings parse as `None`; explicit `str:` and `base64:` produce an empty string. Empty numeric payloads are invalid.
- Typed booleans reject unknown spellings. Invalid numeric, Boolean, container, and Base64 payloads produce conversion errors that omit the supplied value from their messages and normal formatted tracebacks.
- `base64:` uses strict validation; malformed payloads fail instead of returning undecoded text.
- Serialized null bytes are rejected before `set` changes the file, cache, or process. File loading validates process entries before publishing them; a failed validation preserves the previous cache and process values.
- On Windows, `KEY=VALUE` must fit within 32,767 UTF-16 code units, including `=`. This platform limit is checked before persistent writes or publication of a reloaded snapshot; it is not imposed on other platforms.
- `only_os=True` does not update the file cache, so `get()` can see the value while `all()` does not.
- Values returned by `all()` are newly collected, but nested mutable values are newly parsed rather than shared cache objects.
- The module stores secrets as plain `.env` text; Base64 is encoding, not encryption.

## Performance and concurrency

`DotEnv` coordinates its process, file, and cache operations with one class-level `threading.Lock`. File access is synchronous, so async callers should avoid frequent persistent writes on an event-loop hot path. This lock protects callers using the same service in one process; it does not coordinate external file writers or make arbitrary direct `os.environ` changes transactional.

File entries are cached for `all()`, typed primitive parsing has a fast path, key validation uses an LRU of 512 names, and type-hint normalization uses an LRU of 64 entries. `get()` still reads `os.environ` so process-only updates remain visible immediately.

## Compatibility

Orionis declares Python 3.14+ and `python-dotenv` 1.2.3+. Persisted path strings use POSIX separators across platforms; collection syntax is Python-literal based rather than JSON.

## Module structure

| Path | Responsibility |
|---|---|
| `facade.py`, `functions.py` | Public `Env` class methods and `env()` helper. |
| `core/dot_env.py` | File lifecycle, process synchronization, cache, parsing, and locking. |
| `dynamic/caster.py` | Typed serialization and deserialization. |
| `enums/value_type.py` | Supported `EnvironmentValueType` values. |
| `validators/` | Variable-name and type-hint validation with bounded caches. |
| `key/key_generator.py` | Random Laravel-compatible AES application keys. |
| `contracts/` | Abstract environment and caster interfaces. |

## Evidence and next steps

[dot_env.py](../../core/dot_env.py) · [key_name.py](../../validators/key_name.py) · [key_generator.py](../../key/key_generator.py)

[Return to the module index](README.md).

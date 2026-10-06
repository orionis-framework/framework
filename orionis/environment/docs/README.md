# orionis.environment

> `orionis.environment` loads `.env` values, exposes typed process configuration, persists controlled updates, and generates application encryption keys.

## Overview

The package-level API is `Env` plus the `env()` lookup helper. Both delegate to a process-wide `DotEnv` singleton. On first use, it resolves `.env` from the working directory, creates it if absent, loads it into `os.environ` with file values taking precedence, and caches the file entries for `all()`.

Values may use explicit prefixes such as `int:`, `bool:`, `list:`, `path:`, or `base64:`. Unprefixed values still recognize nulls, booleans, and safe Python literals. `EnvironmentCaster` owns the typed serialization/parsing rules.

## Requirements

- Python 3.14 or newer.
- `python-dotenv>=1.2.3,<2.0`, installed by Orionis.
- Read/write access to the selected `.env` file for persistent `set`, `unset`, and `reload` workflows.
- Uppercase variable names matching `[A-Z][A-Z0-9_]*`.

## Quick start

```python
from orionis.environment import Env, env

Env.set("ORIONIS_DOC_SAMPLE", 7, "int", only_os=True)
assert Env.get("ORIONIS_DOC_SAMPLE") == 7
assert env("MISSING_DOC_KEY", "fallback") == "fallback"
Env.unset("ORIONIS_DOC_SAMPLE", only_os=True)
print("7 fallback")
```

Validation: **Executed successfully** on CPython 3.14.6. `only_os=True` kept the repository `.env` unchanged.

## Core concepts

### Process environment and file cache

`get()` reads `os.environ`, the current process source of truth. Persistent writes update both the file/cache and process environment. `all()` returns only cached entries originating from the selected `.env`; it is not a dump of every operating-system variable.

### Typed values

Supported hints are `str`, `int`, `float`, `bool`, `list`, `dict`, `tuple`, `set`, `path`, and `base64`. Typed storage has the form `<hint>:<payload>`. Container payloads use safe literal parsing; paths normalize to POSIX form; Base64 parses to UTF-8 text when possible and otherwise bytes.

### Singleton path

`DotEnv` uses a singleton metaclass. The path supplied to the first construction in a process determines the backing file for later facade calls. Normal applications rely on the default working-directory `.env`; tests that need another path should isolate the singleton in a fresh process or reset it with the test utilities.

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

## Public API

### `Env.get(key, default=None)` and `env(key, default=None)`

Validate the uppercase key and return its parsed process value, or the exact default when absent. `env()` is a thin one-call delegate to `Env.get`.

### `Env.set(key, value, type_hint=None, *, only_os=False)`

Serializes the value, optionally with an explicit typed prefix. By default it updates `.env`, the file cache, and `os.environ`; `only_os=True` updates only the current process. Success returns `True`.

### `Env.unset(key, *, only_os=False)`

Removes the entry from file/cache and process, or from the process only. Missing valid keys are treated as successfully absent and return `True`; `python-dotenv` may emit an informational message for a missing file entry.

### `Env.all()` and `Env.reload()`

`all()` returns a new dictionary containing parsed file-backed cache values. `reload()` loads the file again with override enabled and rebuilds that cache. A reload failure is wrapped by `DotEnv` as `RuntimeError` and propagates.

### Advanced components

`EnvironmentCaster`, `EnvironmentValueType`, `DotEnv`, and `SecureKeyGenerator` live in their respective subpackages. They are useful for framework integration and tests, but only `Env` and `env` are exported by `orionis.environment`.

## Common workflows

### Read configuration defaults

Call `env("NAME", fallback)` inside configuration factories. Returned values may already be booleans, numbers, collections, paths, or decoded Base64 content, so do not assume every value is a string.

### Persist a typed value

Use `Env.set("WORKERS", 4, "int")`; the file stores `int:4` and later reads return integer `4`. Use `EnvironmentValueType.INT` instead of a string when enum-based code is clearer.

### Apply an external file edit

Call `Env.reload()` after changing the selected `.env` outside the process. It overrides matching process values and refreshes `all()`. A key removed from the file is removed from the cache, but `python-dotenv` does not automatically delete an already-existing process variable.

## Examples

### Serialize and parse a typed dictionary

```python
from orionis.environment.dynamic.caster import EnvironmentCaster

stored = EnvironmentCaster({"workers": 4}).to("dict")
assert stored == "dict:{'workers': 4}"
assert EnvironmentCaster.parseTyped(stored) == {"workers": 4}
print(stored)
```

Validation: **Executed successfully** on CPython 3.14.6.

### Work with an isolated `.env`

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.environment.core.dot_env import DotEnv

with TemporaryDirectory() as directory:
    path = Path(directory) / ".env"
    values = DotEnv(str(path))
    values.set("FEATURES", ["mail", "queue"], "list")
    assert values.get("FEATURES") == ["mail", "queue"]
    assert values.all() == {"FEATURES": ["mail", "queue"]}
    values.unset("FEATURES")

print("temporary .env ok")
```

Validation: **Executed successfully** on CPython 3.14.6 in a temporary directory.

### Generate an AES application key

```python
import base64
from orionis.environment.key.key_generator import SecureKeyGenerator

key = SecureKeyGenerator.generate("AES-256-GCM")
raw = base64.b64decode(key.removeprefix("base64:"), validate=True)
assert len(raw) == 32
print("key bytes:", len(raw))
```

Validation: **Executed successfully** on CPython 3.14.6; the decoded key had 32 bytes.

## Configuration

The subsystem itself selects `.env` at `Path.cwd() / ".env"` unless the first direct `DotEnv(path)` construction supplies another path. There is no separate Orionis config file for this module.

File values support plain dotenv syntax and these typed prefixes:

| Prefix | Parsed value |
|---|---|
| `str:` | String with leading value whitespace removed. |
| `int:`, `float:` | Python number. |
| `bool:` | `true/1/yes/on/enabled` or `false/0/no/off/disabled`. |
| `list:`, `dict:`, `tuple:`, `set:` | Matching Python literal container. |
| `path:` | Normalized POSIX path string. |
| `base64:` | Decoded UTF-8 string or raw bytes. |

Unprefixed `none`, `null`, `nan`, and `nil` map to `None`; unprefixed safe literals are parsed with `ast.literal_eval`.

## Integration with Orionis

Framework configuration dataclasses call `Env.get` in their default factories, so environment parsing happens before providers consume normalized config. Application key validation also uses `SecureKeyGenerator` and persists a generated `APP_KEY` through `Env.set` when absent.

Console, HTTP, database, cache, queue, session, mail, logging, view, MCP, and testing configuration all depend on this module. It has no service provider because its singleton facade is usable during early bootstrap.

## Errors and edge cases

- Keys must be uppercase and may contain only uppercase letters, digits, and underscores; invalid keys raise `TypeError` or `ValueError`.
- Unknown explicit type hints passed to `Env.set` raise `RuntimeError`; incompatible values raise `TypeError` or `ValueError`.
- Empty stored strings parse as `None`, which differs from explicit `str:` behavior.
- `base64:` uses strict validation; malformed payloads fail instead of returning undecoded text.
- `only_os=True` does not update the file cache, so `get()` can see the value while `all()` does not.
- Values returned by `all()` are newly collected, but nested mutable values are newly parsed rather than shared cache objects.
- The module stores secrets as plain `.env` text; Base64 is encoding, not encryption.

## Performance and concurrency

All `DotEnv` operations use one class-level `threading.Lock`, protecting process/file/cache consistency but serializing reads and writes across threads. Async callers should avoid frequent persistent writes on an event-loop hot path because file access is synchronous.

File entries are cached for `all()`, typed primitive parsing has a fast path, key validation uses an LRU of 512 names, and type-hint normalization uses an LRU of 64 entries. `get()` still reads `os.environ` so process-only updates remain visible immediately.

## Compatibility

Orionis declares Python 3.14+ and `python-dotenv` 1.2.3+. Validation used CPython 3.14.6 on Windows. Persisted path strings use POSIX separators across platforms; collection syntax is Python-literal based rather than JSON.

## Verification notes

Validation used CPython 3.14.6. Exports, facade/helper, singleton/file behavior, caster, enums, validators, key generator, bootstrap integrations, and `tests/environment` were inspected. All 210 environment tests passed through the Orionis runner. Four standalone examples executed successfully without changing the repository `.env`.

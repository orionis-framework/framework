# Orionis Environment (`orionis.environment`)

> Thread-safe `.env` file management with typed value casting, key
> validation, and secure application-key generation for the Orionis
> Framework.
>
> 🇪🇸 Versión en español: [README.es.md](README.es.md)

`orionis.environment` is the framework's single source of truth for
reading and writing environment variables. It combines a `.env` file
manager (`DotEnv`), a simple static facade (`Env`) and a helper function
(`env()`), a typed value caster (`EnvironmentCaster`) that lets values keep
their Python type across the string-only `.env` format, and a secure key
generator used to produce the application's encryption key (`APP_KEY`,
consumed by [`orionis.encrypter`](../../encrypter)).

---

## Table of contents

1. [Requirements](#requirements)
2. [What problem it solves](#what-problem-it-solves)
3. [API reference](#api-reference)
   - [`Env`](#env)
   - [`env()`](#env-1)
   - [`IEnv`](#ienv)
   - [`DotEnv`](#dotenv)
   - [`EnvironmentCaster`](#environmentcaster)
   - [`IEnvironmentCaster`](#ienvironmentcaster)
   - [`EnvironmentValueType`](#environmentvaluetype)
   - [`ValidateKeyName`](#validatekeyname)
   - [`ValidateTypes`](#validatetypes)
   - [`SecureKeyGenerator`](#securekeygenerator)
4. [Usage examples](#usage-examples)
5. [Design notes](#design-notes)
6. [Performance and concurrency considerations](#performance-and-concurrency-considerations)
7. [Compatibility notes](#compatibility-notes)

---

## Requirements

No installation steps beyond the framework itself are required:

```bash
pip install orionis
```

- **Python:** 3.14 or newer.
- **Third-party dependency** (already declared by the framework):
  [`python-dotenv`](https://pypi.org/project/python-dotenv/) `~=1.2`
  (`dotenv_values`, `load_dotenv`, `set_key`, `unset_key`).
- A `.env` file is created automatically (empty, if it does not already
  exist) in the current working directory the first time `DotEnv` is used,
  unless an explicit path is provided.

## What problem it solves

Environment files (`.env`) only store plain strings, but application code
usually wants `int`, `float`, `bool`, `list`, `dict`, `tuple`, `set`,
filesystem paths, or base64-encoded secrets. Reading and writing these
values consistently, validating variable names, and keeping the in-process
`os.environ` state, an in-memory cache, and the `.env` file itself all in
sync — safely across threads — is exactly what this module centralises:

- `Env` / `env()` give the rest of the framework (and application code) a
  simple, static way to read and write configuration without touching
  `os.environ` or `python-dotenv` directly.
- `DotEnv` is the actual engine behind `Env`: a thread-safe, per-process
  singleton that owns the resolved `.env` file path, keeps `os.environ` and
  an in-memory cache synchronized, and validates every key it touches.
- `EnvironmentCaster` implements a small `"<type>:<value>"` convention
  (e.g. `int:42`, `list:[1, 2, 3]`, `path:/abs/path`, `base64:aGVsbG8=`) so
  a value written with a type hint comes back out with the same Python
  type, instead of always being a plain string.
- `SecureKeyGenerator` produces cryptographically random, Laravel-style
  `base64:<...>` keys sized correctly for a given AES cipher — used to
  auto-generate `APP_KEY` the first time an application boots without one.

## API reference

### `Env`

```python
from orionis.environment import Env
# or
from orionis.environment.facade import Env
```

Static facade implementing `IEnv`. Every method is a `@classmethod` that
delegates to the shared `DotEnv()` singleton — there is no need (and no
supported way) to instantiate `Env`.

| Method | Signature | Description |
| --- | --- | --- |
| `get` | `Env.get(key: str, default: object \| None = None) -> object` | Returns the parsed value of `key`, or `default` if not set. |
| `set` | `Env.set(key: str, value: str \| float \| bool \| list \| dict \| tuple \| set, type_hint: str \| EnvironmentValueType \| None = None, *, only_os: bool = False) -> bool` | Writes/updates `key` in the `.env` file (unless `only_os=True`) and in `os.environ`. Returns `True` on success. |
| `unset` | `Env.unset(key: str, *, only_os: bool = False) -> bool` | Removes `key` from the `.env` file (unless `only_os=True`) and from `os.environ`. Returns `True`. |
| `all` | `Env.all() -> dict[str, Any]` | Returns every variable currently in the `.env`-backed in-memory cache, parsed to native Python types. |
| `reload` | `Env.reload() -> bool` | Reloads variables from disk into `os.environ` and rebuilds the internal cache. Returns `True` on success, `False` on `OSError`/`ValueError`. |

**Raises:** `get`/`set`/`unset` propagate `TypeError`/`ValueError` from key
validation (see [`ValidateKeyName`](#validatekeyname)) when `key` is not a
valid environment variable name.

---

### `env()`

```python
from orionis.environment import env
# or
from orionis.environment.functions import env
```

```python
def env(key: str, default: object | None = None) -> object
```

Convenience function equivalent to `Env.get(key, default)` — a
Laravel-style global helper for reading configuration values.

| Parameter | Type | Description |
| --- | --- | --- |
| `key` | `str` | Name of the environment variable to retrieve. |
| `default` | `object \| None`, optional | Value returned when `key` is not set. |

**Returns:** the parsed value, or `default`.

**Raises:** same as `Env.get`.

---

### `IEnv`

```python
from orionis.environment.contracts.env import IEnv
```

Abstract base class (`abc.ABC`) defining the contract implemented by
`Env`: abstract classmethods `get`, `set`, `unset`, `all`, and `reload`
with the exact same signatures described above.

---

### `DotEnv`

```python
from orionis.environment.core.dot_env import DotEnv
```

Thread-safe, per-process **singleton** (enforced via the `Singleton`
metaclass from `orionis.support.patterns.singleton`) that manages a
resolved `.env` file. `Env`'s methods are thin wrappers around this class.

#### `DotEnv(path=None)`

Constructor (only meaningful on the **first** call — subsequent calls to
`DotEnv(...)` return the same singleton instance regardless of arguments
passed).

| Parameter | Type | Description |
| --- | --- | --- |
| `path` | `str \| None`, optional | Path to the `.env` file. Defaults to `.env` in the current working directory. |

**Behaviour:** resolves the path, creates the file if missing, loads it
into `os.environ` via `load_dotenv(..., override=True)`, and builds an
in-memory cache (`dotenv_values(...)`) used by `all()`.

**Raises:** `OSError` if the file cannot be created/accessed; `RuntimeError`
for any other unexpected initialization failure.

#### `dotenv.get(key, default=None)`

Same contract as `Env.get`. Internally, `get` reads from `os.environ`
directly (the single source of truth after `load_dotenv(override=True)`
and subsequent `set`/`unset` calls) rather than from the in-memory cache,
and parses the raw string via the same logic as `EnvironmentCaster` (type
prefixes, booleans, null tokens, and `ast.literal_eval` as a fallback).

**Raises:** `TypeError`/`ValueError` from `ValidateKeyName` for invalid
key names.

#### `dotenv.set(key, value, type_hint=None, *, only_os=False)`

Same contract as `Env.set`. Validates the key, serializes `value` (via
`EnvironmentCaster` when `type_hint` is given, or simple `str`/`repr`
conversion otherwise), writes it to the `.env` file with `set_key` and
updates the in-memory cache (unless `only_os=True`), and always updates
`os.environ`.

**Raises:** `TypeError`/`ValueError` from key/type validation.

#### `dotenv.unset(key, *, only_os=False)`

Same contract as `Env.unset`. Removes the key from the `.env` file (via
`unset_key`) and the in-memory cache (unless `only_os=True`), and always
removes it from `os.environ`. Returns `True` even if the key did not
exist.

**Raises:** `TypeError`/`ValueError` from key validation.

#### `dotenv.all()`

Same contract as `Env.all`. Returns a dict built by parsing every entry
currently in the **in-memory cache** (populated at construction time and
refreshed by `reload()`, plus any keys added via `set(..., only_os=False)`).

#### `dotenv.reload()`

Same contract as `Env.reload`, but raises instead of swallowing errors:
re-runs `load_dotenv(..., override=True)` and rebuilds the in-memory
cache from disk.

**Raises:** `RuntimeError` wrapping any exception encountered while
reloading.

---

### `EnvironmentCaster`

```python
from orionis.environment.dynamic.caster import EnvironmentCaster
```

Implements `IEnvironmentCaster`. Converts between typed Python values and
the `"<type_hint>:<value>"` string convention used for `.env` storage.
Uses `__slots__ = ("_EnvironmentCaster__type_hint", "_EnvironmentCaster__value_raw")`
— no dynamic attributes are allowed on instances.

#### `EnvironmentCaster.supportedTypes()`

```python
@staticmethod
def supportedTypes() -> frozenset[str]
```

Returns the set of valid type-hint strings:
`{"base64", "path", "str", "int", "float", "bool", "list", "dict", "tuple", "set"}`.

#### `EnvironmentCaster.parseTyped(value_str)`

```python
@staticmethod
def parseTyped(value_str: str) -> object
```

Fast path for parsing an already-typed string like `"int:42"` without
constructing a full `EnvironmentCaster` instance for primitive types
(`int`, `float`, `bool`, `str`); falls back to a full instance
(`EnvironmentCaster(value_str).get()`) for complex types (`list`, `dict`,
`tuple`, `set`, `path`, `base64`).

| Parameter | Type | Description |
| --- | --- | --- |
| `value_str` | `str` | A string formatted as `"<type_hint>:<value>"`, e.g. `"int:42"`. |

**Returns:** the parsed Python value.

**Raises:** `ValueError` if the value cannot be converted to the
indicated type; `TypeError` if the value is incompatible with it.

#### `EnvironmentCaster(raw)`

Constructor.

| Parameter | Type | Description |
| --- | --- | --- |
| `raw` | `str \| object` | If a string containing a colon whose prefix is a valid type hint, the prefix becomes the type hint and the remainder becomes the raw value. Otherwise the entire input is treated as the raw value with no type hint. |

#### `caster.get()`

```python
def get(self) -> object
```

Returns the value processed according to the detected type hint (`str`,
`int`, `float`, `bool`, `list`, `dict`, `tuple`, `set`, `path`, or
`base64`), or the raw value unchanged if no type hint was detected.

**Raises:** `ValueError` or `TypeError` if conversion fails (the specific
type depends on the failure; both are re-raised with a descriptive
message).

#### `caster.to(type_hint)`

```python
def to(self, type_hint: str | EnvironmentValueType) -> str
```

Converts the internal value to the given `type_hint` and returns the
`"<type_hint>:<value>"` string representation suitable for writing to a
`.env` file.

| Parameter | Type | Description |
| --- | --- | --- |
| `type_hint` | `str \| EnvironmentValueType` | The target type. Must be one of `EnvironmentCaster.supportedTypes()`. |

**Returns:** `str`, e.g. `"int:42"`, `"list:[1, 2, 3]"`,
`"path:/home/user/app"`, `"base64:aGVsbG8="`.

**Raises:** `ValueError` if `type_hint` is invalid or the conversion
fails.

---

### `IEnvironmentCaster`

```python
from orionis.environment.contracts.caster import IEnvironmentCaster
```

Abstract base class (`abc.ABC`) defining the `get()`/`to(type_hint)`
contract implemented by `EnvironmentCaster`.

---

### `EnvironmentValueType`

```python
from orionis.environment.enums import EnvironmentValueType
```

`Enum` listing the ten supported type-hint identifiers: `BASE64 = "base64"`,
`PATH = "path"`, `STR = "str"`, `INT = "int"`, `FLOAT = "float"`,
`BOOL = "bool"`, `LIST = "list"`, `DICT = "dict"`, `TUPLE = "tuple"`,
`SET = "set"`.

---

### `ValidateKeyName`

```python
from orionis.environment.validators import ValidateKeyName
```

A callable (backed by an `functools.lru_cache`-decorated function,
`maxsize=512`) that validates an environment variable name.

```python
ValidateKeyName(key: str) -> str
```

| Parameter | Type | Description |
| --- | --- | --- |
| `key` | `str` | The name to validate. Must match `^[A-Z][A-Z0-9_]*$` (starts with an uppercase letter, then uppercase letters, digits, or underscores). |

**Returns:** `key` unchanged, if valid.

**Raises:** `TypeError` if `key` is not a `str`; `ValueError` if it does
not match the required pattern.

---

### `ValidateTypes`

```python
from orionis.environment.validators import ValidateTypes
```

A callable **instance** (singleton-like module-level object) used to
determine/validate the serialization type of a value.

```python
ValidateTypes(*, value: str | int | float | bool | list | dict | tuple | set,
              type_hint: str | EnvironmentValueType | None = None) -> str
```

| Parameter | Type | Description |
| --- | --- | --- |
| `value` | `str \| int \| float \| bool \| list \| dict \| tuple \| set` | The value whose type is being validated/determined. |
| `type_hint` | `str \| EnvironmentValueType \| None`, optional | Explicit type hint; if omitted, the type is inferred from `value` via `type(value).__name__.lower()`. |

**Returns:** the canonical type-hint string (e.g. `"int"`, `"list"`).

**Raises:** `TypeError` if `value`'s type is unsupported, or if
`type_hint` is provided but is neither a `str` nor an
`EnvironmentValueType`; `RuntimeError` if `type_hint` (as a string) does
not match any known `EnvironmentValueType` member name.

---

### `SecureKeyGenerator`

```python
from orionis.environment.key.key_generator import SecureKeyGenerator
```

Utility class for generating cryptographically secure, Laravel-style
application keys sized for a given AES cipher.

#### `SecureKeyGenerator.generate(cipher=Cipher.AES_256_CBC)`

```python
@staticmethod
def generate(cipher: str | Cipher = Cipher.AES_256_CBC) -> str
```

| Parameter | Type | Description |
| --- | --- | --- |
| `cipher` | `str \| Cipher`, optional | The cipher to size the key for. One of `AES_128_CBC`, `AES_256_CBC`, `AES_128_GCM`, `AES_256_GCM` (from `orionis.foundation.config.app.enums.ciphers.Cipher`). Defaults to `Cipher.AES_256_CBC`. |

**Returns:** `str` — a key formatted as `"base64:<base64-encoded-random-bytes>"`,
using `os.urandom(16)` for 128-bit ciphers or `os.urandom(32)` for
256-bit ciphers.

**Raises:** `ValueError` if `cipher` is not one of the supported values.

> This is the mechanism the framework uses to auto-populate `APP_KEY` when
> it is missing at boot time (see [orionis.encrypter](../../encrypter)),
> and the `"base64:..."` format it produces is exactly what
> `EnvironmentCaster`/`DotEnv.get()` decode back into raw `bytes` when read
> through `Env.get("APP_KEY")`.

## Usage examples

### 1. Basic read/write with the `Env` facade

```python
from orionis.environment import Env

Env.set("APP_NAME", "Orionis Demo")
print(Env.get("APP_NAME"))              # "Orionis Demo"
print(Env.get("MISSING_VAR", "fallback"))  # "fallback"

Env.unset("APP_NAME")
print(Env.get("APP_NAME"))              # None
```

### 2. Using the `env()` shorthand

```python
from orionis.environment import env

debug_mode = env("APP_DEBUG", False)
if debug_mode:
    print("Running in debug mode")
```

### 3. Storing and reading typed values

```python
from orionis.environment import Env

Env.set("MAX_RETRIES", 5, type_hint="int")
Env.set("ALLOWED_HOSTS", ["api.example.com", "web.example.com"], type_hint="list")
Env.set("STORAGE_PATH", "storage/app", type_hint="path")

retries = Env.get("MAX_RETRIES")           # 5 (int)
hosts = Env.get("ALLOWED_HOSTS")           # ["api.example.com", "web.example.com"]
storage_path = Env.get("STORAGE_PATH")     # absolute POSIX path string
```

### 4. Using `EnvironmentCaster` directly for a one-off conversion

```python
from orionis.environment.dynamic.caster import EnvironmentCaster

encoded = EnvironmentCaster("super-secret").to("base64")
print(encoded)  # "base64:c3VwZXItc2VjcmV0"

decoded = EnvironmentCaster(encoded).get()
print(decoded)  # "super-secret"

# Fast path for already-typed strings:
value = EnvironmentCaster.parseTyped("int:42")  # 42
```

### 5. Generating a secure application key

```python
from orionis.environment.key.key_generator import SecureKeyGenerator
from orionis.environment import Env

new_key = SecureKeyGenerator.generate("AES-256-GCM")
Env.set("APP_KEY", new_key)  # stored verbatim, e.g. "base64:...="
```

### 6. Reloading after an external edit to `.env`

```python
from orionis.environment import Env

# Some external process (or a text editor) modified the .env file on disk.
reloaded = Env.reload()
if reloaded:
    print("Environment variables refreshed:", Env.all())
```

## Design notes

The following notes describe **existing** design decisions for
informational purposes only — they are not suggestions for change.

- **Singleton `DotEnv` via metaclass.** `DotEnv` uses
  `orionis.support.patterns.singleton.Singleton` as its metaclass, so
  `DotEnv()` (with or without a `path` argument) always returns the same
  process-wide instance after the first construction — subsequent
  arguments are ignored because `__init__` only runs once.
- **`os.environ` as the single source of truth for `get`.** `DotEnv.get`
  reads from `os.environ`, not from the in-memory cache, so it always
  reflects the latest state including values set with `only_os=True` or
  changed by other means during the process's lifetime. `DotEnv.all()`,
  on the other hand, reads from the **in-memory cache**, which is only
  updated by `set(..., only_os=False)` (the default) and rebuilt entirely
  by `reload()` — variables set with `only_os=True` will **not** appear in
  `Env.all()` even though `Env.get()` can read them.
  `Env.reload()` only catches `OSError`/`ValueError` from the underlying
  `DotEnv.reload()`; because `DotEnv.reload()` itself wraps unexpected
  failures as `RuntimeError`, such a `RuntimeError` is **not** caught by
  `Env.reload()` and will propagate to the caller.
- **Explicit per-instance `threading.Lock`.** All `DotEnv` operations
  (`get`, `set`, `unset`, `all`, `reload`, and `__init__`) acquire the same
  `_lock`, serializing every call across threads — simplicity and
  correctness are prioritized over concurrent throughput for `.env`
  access, which is not expected to be a hot path.
- **`lru_cache` on validators.** Both `ValidateKeyName`
  (`maxsize=512`) and the internal `_normalize_type_hint` used by
  `ValidateTypes` (`maxsize=64`) are memoized, since the set of
  environment variable names and type hints used by a given application
  is small and finite, so repeated validation collapses to an O(1) dict
  lookup after the first call.
- **`if`/`elif` dispatch instead of dict-of-callables.** Both
  `EnvironmentCaster.get()` and `EnvironmentCaster.to()` dispatch on the
  type hint using an explicit `if`/`elif` chain rather than a dispatch
  table, avoiding bound-method allocation on every call.
- **Name-mangled slots.** `EnvironmentCaster` explicitly lists the
  mangled attribute names in `__slots__`
  (`"_EnvironmentCaster__type_hint"`, `"_EnvironmentCaster__value_raw"`),
  combining private, double-underscore attributes with `__slots__` memory
  savings.
- **`"<type>:<value>"` is a plain string convention, not a schema.** Any
  string containing a colon whose prefix matches a known type hint (e.g.
  `"int:"`, `"path:"`) is interpreted as typed; there is no escaping
  mechanism for colons that happen to appear at the start of an otherwise
  untyped string value.

## Performance and concurrency considerations

These are informative notes about existing behaviour, not tuning advice:

- Every `DotEnv` operation (`get`, `set`, `unset`, `all`, `reload`) takes
  the **same single lock**, so concurrent calls from multiple threads are
  fully serialized — there is no read/write distinction or per-key
  locking. Under heavy concurrent access, calls will queue up rather than
  run in parallel.
- `set` and `unset` (unless `only_os=True`) write to the `.env` file on
  disk via `python-dotenv`'s `set_key`/`unset_key`, which involves file
  I/O on every call — this is synchronous, blocking I/O with no async
  variant provided by this module.
- `get` avoids disk I/O by reading from `os.environ` (populated once at
  `DotEnv()` construction/`reload()` and kept in sync by `set`/`unset`),
  so repeated `Env.get(...)` calls are cheap relative to `set`/`unset`.
- `ValidateKeyName` and the type-hint normalization used by `ValidateTypes`
  are `lru_cache`-memoized, so validating the same key/type-hint
  repeatedly (e.g. inside a hot configuration-reading path) is O(1) after
  the first call — but the caches are process-wide and unbounded by key
  content beyond their `maxsize` (512 and 64 respectively), so an
  application generating a very large number of distinct dynamic keys
  could evict earlier entries.
- `DotEnv` is a metaclass-based singleton with no async variant; calling
  any of its methods from within `async def` code executes synchronously
  on the calling thread/event loop (there is no `run_in_executor`
  offloading inside this module) — see
  [orionis.aio](../../aio) if async-safe offloading of blocking calls is
  needed for a specific workload.

## Compatibility notes

- **Minimum Python version:** 3.14.
- **Dependencies:**
  - `python-dotenv ~= 1.2` — provides `dotenv_values`, `load_dotenv`,
    `set_key`, `unset_key`.
  - Standard library: `os`, `ast`, `threading`, `pathlib`, `re`,
    `functools`, `base64`, `enum`, `abc`, `typing`.
  - `SecureKeyGenerator` imports `orionis.foundation.config.app.enums.ciphers.Cipher`
    (a framework-internal enum), coupling key generation to the
    framework's supported cipher list.
- **Framework integration:** `config/app.py` reads `APP_KEY` / `APP_CIPHER`
  through `Env.get(...)`, and `orionis.encrypter.Encrypter` consumes the
  resulting `bytes` value; other configuration files across the framework
  (database, cache, mail, queue, etc.) follow the same `Env.get(...)`
  pattern for reading environment-driven settings.

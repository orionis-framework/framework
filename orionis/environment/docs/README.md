# Environment (`orionis.environment`)

> Reads and writes `.env` variables, keeping `os.environ`, an in-memory cache and the file on disk in sync, with an explicit `"<type>:<value>"` convention so values survive the string-only format of `.env`.

🇪🇸 Versión en español: [README.es.md](README.es.md)

## Table of contents

- [Functional description](#functional-description)
  - [Where it fits](#where-it-fits)
  - [Read and write pipeline](#read-and-write-pipeline)
  - [File map](#file-map)
  - [Typed value convention](#typed-value-convention)
  - [Design decisions](#design-decisions)
- [API reference](#api-reference)
  - [`Env`](#env)
  - [`env()`](#env-1)
  - [`IEnv`](#ienv)
  - [`DotEnv`](#dotenv)
  - [`EnvironmentCaster`](#environmentcaster)
  - [`IEnvironmentCaster`](#ienvironmentcaster)
  - [`EnvironmentValueType`](#environmentvaluetype)
  - [`ValidateKeyName()`](#validatekeyname)
  - [`ValidateTypes()`](#validatetypes)
  - [`SecureKeyGenerator`](#securekeygenerator)
- [Usage examples](#usage-examples)
  - [Reading and writing values](#reading-and-writing-values)
  - [Storing typed values](#storing-typed-values)
  - [Handling validation and casting errors](#handling-validation-and-casting-errors)
  - [Using the caster on its own](#using-the-caster-on-its-own)
  - [Generating an application key](#generating-an-application-key)
  - [Reading configuration from an entity](#reading-configuration-from-an-entity)
  - [Reloading after an external edit](#reloading-after-an-external-edit)
- [Performance and concurrency considerations](#performance-and-concurrency-considerations)
- [Compatibility notes](#compatibility-notes)

## Functional description

A `.env` file can only hold text. Application code, however, needs `int`,
`float`, `bool`, `list`, `dict`, `tuple`, `set`, filesystem paths and
base64-encoded secrets. This module centralises that translation, validates
every variable name it touches, and keeps three storages consistent: the
`.env` file, the process environment (`os.environ`) and an in-memory cache.

### Where it fits

- Every configuration entity under `orionis/foundation/config/**` declares
  its defaults with `default_factory=lambda: Env.get("VAR", default)`, and
  the application-level files in `config/*.py` do the same. That makes this
  module the entry point for all framework configuration.
- `orionis.foundation.config.app.entities.app.App.__post_init__` calls
  `SecureKeyGenerator.generate()` and `Env.set("APP_KEY", ...)` when no key
  is configured, so the key consumed by `orionis.encrypter` is produced
  here.
- The module has **no service provider and no facade registered in the
  container**: `Env` is a plain class with classmethods, imported directly.
  It only depends on `orionis.support.patterns.singleton` (for the `DotEnv`
  metaclass) and, for `SecureKeyGenerator`, on the `Cipher` enum of
  `orionis.foundation.config.app.enums.ciphers`.

### Read and write pipeline

```text
Env.get(key)      -> DotEnv.get      -> ValidateKeyName -> os.environ -> __parseValue -> value
env(key)          -> Env.get
Env.set(k, v, t)  -> DotEnv.set      -> ValidateKeyName -> ValidateTypes -> EnvironmentCaster.to()
                                     -> set_key(.env)  + cache + os.environ
Env.all()         -> DotEnv.all      -> in-memory cache -> __parseValue per entry
Env.reload()      -> DotEnv.reload   -> load_dotenv(override=True) + cache rebuild
```

Two facts follow from that diagram and are visible in the source:

- `get()` reads **`os.environ`**, so a variable exported by the operating
  system (or set by another library) is visible through `Env.get`.
- `all()` reads the **in-memory cache**, which is filled at construction
  time and on `reload()` from the `.env` file and updated by `set()` /
  `unset()` when `only_os=False`. A variable that only lives in
  `os.environ` is therefore returned by `get()` but is *not* listed by
  `all()`.

### File map

| Path | Contents |
| --- | --- |
| `__init__.py` | Public exports: `Env`, `env`. |
| `facade.py` | `Env`, the static facade implementing `IEnv`. |
| `functions.py` | `env()`, module-level shorthand for `Env.get`. |
| `core/dot_env.py` | `DotEnv`, the singleton engine that owns the file. |
| `dynamic/caster.py` | `EnvironmentCaster`, the `"<type>:<value>"` codec. |
| `enums/value_type.py` | `EnvironmentValueType`, the ten supported types. |
| `validators/key_name.py` | `ValidateKeyName`, the `^[A-Z][A-Z0-9_]*$` guard. |
| `validators/types.py` | `ValidateTypes`, value/type-hint validation. |
| `key/key_generator.py` | `SecureKeyGenerator`, `base64:` application keys. |
| `contracts/env.py` | `IEnv` abstract contract. |
| `contracts/caster.py` | `IEnvironmentCaster` abstract contract. |

### Typed value convention

A value written with a type hint is stored as `"<type>:<value>"` and decoded
back on read. The prefix match performed by `DotEnv.__parseValue` is
**case-sensitive and not stripped** (`value_str.split(":", 1)`), so
`INT:5` is *not* treated as a typed value and comes back as the plain
string `'INT:5'`.

| Type hint | Stored form | Value returned by `get()` |
| --- | --- | --- |
| `str` | `str:hello` | `'hello'` (leading whitespace removed) |
| `int` | `int:42` | `42` |
| `float` | `float:3.5` | `3.5` |
| `bool` | `bool:true` | `True` |
| `list` | `list:[1, 2, 3]` | `[1, 2, 3]` |
| `dict` | `dict:{'a': 1}` | `{'a': 1}` |
| `tuple` | `tuple:(1, 2)` | `(1, 2)` |
| `set` | `set:{1, 2}` | `{1, 2}` |
| `path` | `path:/abs/posix/path` | `str` with `/` separators |
| `base64` | `base64:aGVsbG8=` | `'hello'` (`bytes` if not valid UTF-8) |

Reads are prefix-driven, not hint-driven: any value already stored with a
recognised prefix is decoded even if it was written without a type hint.
That is why `APP_KEY`, stored by the framework as `base64:<...>`, is
returned by `Env.get("APP_KEY")` as decoded `bytes`, not as the literal
string.

Values without a prefix are still parsed: `none`/`null`/`nan`/`nil`
(case-insensitive) and the empty string become `None`, `true`/`false`
become booleans, and anything else is passed through `ast.literal_eval`,
falling back to the original string when that fails.

### Design decisions

- **Singleton (`DotEnv`)** — one resolved `.env` path per process, so the
  cache and the file never diverge between call sites. The instance is
  created by the *first* call; later calls ignore their arguments.
- **Static facade (`Env`)** — classmethods only, no state, so configuration
  entities can call it inside a `default_factory` without dependency
  injection.
- **`__slots__` everywhere** — no class in the module gives its instances a
  `__dict__`: `EnvironmentCaster` declares its two slots (written with the
  already-mangled names), `DotEnv` declares `("__cache", "__resolved_path")`,
  and the stateless `Env` and `SecureKeyGenerator` declare `__slots__ = ()`,
  matching the `__slots__ = ()` of their contracts.
- **`lru_cache` on both validators** — key names (512 entries) and type
  hints (64 entries) come from a small, finite set, so validation becomes a
  dictionary lookup after the first call.
- **Contracts are `abc.ABC` with `__slots__ = ()`** — `IEnv` and
  `IEnvironmentCaster` add no per-instance storage to their implementations.
- **`threading.Lock` (not `RLock`) inside `DotEnv`** — every public method
  takes the class-level lock once and never calls another locked method
  while holding it.

## API reference

### `Env`

```python
from orionis.environment import Env
```

Static facade defined in `orionis/environment/facade.py`, implementing
`IEnv`. Every method is a `@classmethod` that delegates to the shared
`DotEnv()` singleton; the class holds no state and declares
`__slots__ = ()`, so instantiating it adds nothing.

```python
@classmethod
def get(cls, key: str, default: object | None = None) -> object: ...

@classmethod
def set(
    cls,
    key: str,
    value: str | float | bool | list | dict | tuple | set,
    type_hint: str | EnvironmentValueType | None = None,
    *,
    only_os: bool = False,
) -> bool: ...

@classmethod
def unset(cls, key: str, *, only_os: bool = False) -> bool: ...

@classmethod
def all(cls) -> dict[str, Any]: ...

@classmethod
def reload(cls) -> bool: ...
```

| Method | Returns | Notes |
| --- | --- | --- |
| `get` | parsed value, or `default` | `default` is returned **as-is**, it is never parsed. |
| `set` | `True` | Side effects: writes `.env` (unless `only_os=True`), updates the cache and `os.environ`. |
| `unset` | `True` | Returns `True` even when the key did not exist. |
| `all` | `dict[str, Any]` | Snapshot of the in-memory cache, parsed. |
| `reload` | `bool` | `False` when building the shared `DotEnv` raises `OSError` or `ValueError`. |

**Raises**

- `TypeError` — `key` is not a string, `value` is not one of the supported
  types, or `type_hint` is neither a string nor an `EnvironmentValueType`.
- `ValueError` — `key` does not match `^[A-Z][A-Z0-9_]*$`, or a value
  cannot be serialised/parsed for the requested type.
- `RuntimeError` — `type_hint` is a string that does not name a member of
  `EnvironmentValueType`. Also on `reload()`: it only catches `OSError` and
  `ValueError`, but `DotEnv.reload()` wraps every failure in `RuntimeError`,
  so a failed reload propagates instead of returning `False`.

### `env()`

```python
from orionis.environment import env
```

```python
def env(key: str, default: object | None = None) -> object: ...
```

Module-level shorthand defined in `orionis/environment/functions.py`. It
calls `Env.get(key, default)` and has exactly the same behaviour, return
value and exceptions.

### `IEnv`

```python
from orionis.environment.contracts.env import IEnv
```

`abc.ABC` with `__slots__ = ()` declaring five abstract classmethods:
`get`, `set`, `unset`, `all` and `reload`, with the same signatures listed
for `Env`.

### `DotEnv`

```python
from orionis.environment.core.dot_env import DotEnv
```

Engine that owns the `.env` file. It uses the `Singleton` metaclass from
`orionis.support.patterns.singleton`, so there is exactly one instance per
process, and it guards every public method with a class-level
`threading.Lock`. Its whole instance state is declared in
`__slots__ = ("__cache", "__resolved_path")`.

#### `DotEnv.__init__()`

```python
def __init__(self, path: str | None = None) -> None: ...
```

| Parameter | Type | Description |
| --- | --- | --- |
| `path` | `str \| None` | Path to the `.env` file. Defaults to `Path.cwd() / ".env"`; a provided path is resolved with `expanduser().resolve()`. |

Side effects: creates the file with `touch()` when it does not exist, loads
it into `os.environ` with `load_dotenv(..., override=True)`, and builds the
in-memory cache with `dotenv_values(...)`.

**Raises**

- `OSError` — the file cannot be created or accessed.
- `RuntimeError` — any other failure during initialisation.

> **Note:** because the class is a singleton, only the first construction in
> the process applies. In a standard Orionis application that first
> construction already happened while the framework was being imported
> (`orionis/foundation/core_config.py` builds `App()` at module level, which
> writes `APP_KEY` through `Env.set`), so passing a custom `path` from
> application code has no effect and the default `.env` of the current
> working directory is the one in use.

#### `DotEnv.set()`

```python
def set(
    self,
    key: str,
    value: str | float | bool | list | dict | tuple | set,
    type_hint: str | EnvironmentValueType | None = None,
    *,
    only_os: bool = False,
) -> bool: ...
```

Validates the key, resolves the type with `ValidateTypes` when `type_hint`
is given, serialises the value, writes it with `set_key` (unless
`only_os=True`), updates the cache and always sets `os.environ[key]`.
Returns `True`.

**Raises** `TypeError` / `ValueError` from key and type validation, and
`RuntimeError` from `ValidateTypes` for an unknown type-hint name.

#### `DotEnv.get()`

```python
def get(self, key: str, default: object | None = None) -> object: ...
```

Validates the key, reads `os.environ.get(key)` and parses it with
`__parseValue`. Returns `default` unchanged when the key is absent.

**Raises** `TypeError` / `ValueError` from key validation, plus any
`ValueError` / `TypeError` raised while decoding a typed value.

#### `DotEnv.unset()`

```python
def unset(self, key: str, *, only_os: bool = False) -> bool: ...
```

Validates the key, removes it from the file with `unset_key` and from the
cache (unless `only_os=True`), and pops it from `os.environ`. Returns
`True` even when the key was missing; in that case `python-dotenv` prints
its own warning to stdout.

#### `DotEnv.all()`

```python
def all(self) -> dict: ...
```

Returns a new dictionary built from the in-memory cache, with every value
passed through `__parseValue`. A key present in the file without `=` is
stored as `None` and returned as `None`.

#### `DotEnv.reload()`

```python
def reload(self) -> bool: ...
```

Runs `load_dotenv(..., override=True)` again and rebuilds the cache from
disk. Returns `True`.

**Raises** `RuntimeError` wrapping any exception raised during the reload
(for example a `.env` file that is not valid UTF-8).

#### Private helpers

Not part of the public API, but they define the observable behaviour
described above:

- `__serializeValue(value, type_hint=None)` — `None` becomes `"null"`; with
  a type hint it delegates to `EnvironmentCaster(value).to(type_hint)`;
  otherwise strings are stripped, booleans become `"true"`/`"false"`,
  numbers use `str()`, and `list`/`dict`/`tuple`/`set` use `repr()`.
- `__parseValue(value)` — implements the null tokens, the boolean strings,
  the `"<type>:"` prefix dispatch to `EnvironmentCaster.parseTyped` and the
  `ast.literal_eval` fallback.

### `EnvironmentCaster`

```python
from orionis.environment.dynamic.caster import EnvironmentCaster
```

Codec for the `"<type>:<value>"` convention, implementing
`IEnvironmentCaster`. Exposes `OPTIONS`, a `ClassVar[frozenset[str]]` built
from `EnvironmentValueType`, and declares `__slots__`, so instances have no
`__dict__`.

#### `EnvironmentCaster.supportedTypes()`

```python
@staticmethod
def supportedTypes() -> frozenset[str]: ...
```

Returns `EnvironmentCaster.OPTIONS` itself (same object):
`{'base64', 'bool', 'dict', 'float', 'int', 'list', 'path', 'set', 'str', 'tuple'}`.

#### `EnvironmentCaster.parseTyped()`

```python
@staticmethod
def parseTyped(value_str: str) -> object: ...
```

Fast path used by `DotEnv.__parseValue`. `int`, `float`, `bool` and `str`
are resolved inline without allocating an instance; the remaining types
delegate to `EnvironmentCaster(value_str).get()`.

**Raises**

- `ValueError` — `value_str` contains no `":"` (`substring not found`, from
  `str.index`), or the value does not fit the announced type.
- `TypeError` — the value is incompatible with the announced type.

#### `EnvironmentCaster.__init__()`

```python
def __init__(self, raw: str | object) -> None: ...
```

For a string input, the part before the first `":"` is taken as the type
hint **only if** it is one of `OPTIONS` after `strip().lower()`; otherwise
the whole string is kept as the value. Non-string inputs are stored as the
value with no type hint. Leading whitespace is removed from the value.

#### `EnvironmentCaster.get()`

```python
def get(self) -> object: ...
```

Decodes the stored value according to the current type hint. With no hint,
returns the raw value untouched (leading whitespace already removed).

Behaviour worth knowing:

- `path` only normalises separators; it does **not** make the path
  absolute, and it returns a `str`, not a `Path`.
- `base64` returns `str` when the decoded bytes are valid UTF-8, otherwise
  `bytes`.
- `list`, `dict`, `tuple` and `set` use `ast.literal_eval` and require the
  literal to be of the announced type.

**Raises** `TypeError` when the underlying failure is a `TypeError` (for
example `list:{1}`), `ValueError` in every other case. Both messages are
prefixed with `Error processing value '<raw>' with type hint '<hint>':`.

#### `EnvironmentCaster.to()`

```python
def to(self, type_hint: str | EnvironmentValueType) -> str: ...
```

Serialises the stored value and returns `"<type_hint>:<value>"`. Accepts
the enum member or its string value.

**Side effect:** it assigns `type_hint` to the instance, so a later `get()`
on the same instance decodes with that hint instead of the original one.

Behaviour worth knowing:

- `path` produces an **absolute** POSIX path: a relative value is joined to
  `Path.cwd()` and then `expanduser()` is applied.
- `base64` keeps the value unchanged when it already is valid Base64, and
  encodes it otherwise; only `str` and `bytes` are accepted.
- `int`, `float` and `bool` accept string input (`"42"`, `"on"`, `"yes"`,
  `"disabled"`, ...); `list`, `dict`, `tuple` and `set` require the value to
  already be of that exact type.

**Raises** `ValueError` for an invalid type hint and for every conversion
failure — including the ones raised internally as `TypeError`, which this
method wraps. Messages are prefixed with
`Error converting value '<raw>' to type '<hint>':`.

### `IEnvironmentCaster`

```python
from orionis.environment.contracts.caster import IEnvironmentCaster
```

`abc.ABC` with `__slots__ = ()` declaring two abstract methods, `get()` and
`to(type_hint)`.

### `EnvironmentValueType`

```python
from orionis.environment.enums import EnvironmentValueType
```

`enum.Enum` (not `StrEnum`) with ten members whose values are the accepted
type hints: `BASE64`, `PATH`, `STR`, `INT`, `FLOAT`, `BOOL`, `LIST`,
`DICT`, `TUPLE`, `SET`. Because it is a plain `Enum`, a member is not equal
to its string; use `.value` when a string is required. `Env.set`,
`EnvironmentCaster.to` and `ValidateTypes` accept both forms.

### `ValidateKeyName()`

```python
from orionis.environment.validators import ValidateKeyName
```

```python
def ValidateKeyName(key: str) -> str: ...
```

Module-level alias of `_validate_key_name`, decorated with
`functools.lru_cache(maxsize=512)`. Returns the key unchanged when it
matches `^[A-Z][A-Z0-9_]*$` (checked with `fullmatch`).

**Raises**

- `TypeError` — `key` is not a `str`.
- `ValueError` — the name does not match the pattern.

### `ValidateTypes()`

```python
from orionis.environment.validators import ValidateTypes
```

```python
def ValidateTypes(
    *,
    value: str | float | bool | list | dict | tuple | set,
    type_hint: str | EnvironmentValueType | None = None,
) -> str: ...
```

Module-level instance of the private `__ValidateTypes` class; both
parameters are keyword-only. Returns the canonical type name: the
normalised `type_hint` when one is given (the lookup is by enum **name**,
so `"INT"`, `"int"` and `EnvironmentValueType.INT` are equivalent), or
`type(value).__name__.lower()` otherwise.

**Raises**

- `TypeError` — `value` is not one of `str`, `int`, `float`, `bool`,
  `list`, `dict`, `tuple`, `set`; or `type_hint` is neither `str` nor
  `EnvironmentValueType`.
- `RuntimeError` — `type_hint` is a string that is not a member name of
  `EnvironmentValueType`.

### `SecureKeyGenerator`

```python
from orionis.environment.key.key_generator import SecureKeyGenerator
```

```python
KEY_SIZES: ClassVar[dict[Cipher, int]]

@staticmethod
def generate(cipher: str | Cipher = Cipher.AES_256_CBC) -> str: ...
```

Produces a `"base64:<...>"` key from `os.urandom`, sized for the requested
cipher: 16 bytes for `AES-128-CBC` and `AES-128-GCM`, 32 bytes for
`AES-256-CBC` and `AES-256-GCM`. The `cipher` argument accepts a `Cipher`
member or its string value.

**Raises** `ValueError` when the cipher is not one of the four supported
values (the message lists the valid options).

Consumer inside the framework: `App.__post_init__`
(`orionis/foundation/config/app/entities/app.py`) calls `generate()` and
stores the result with `Env.set("APP_KEY", ...)` when no key is configured.

## Usage examples

Every example below was executed as-is; the output shown is the real one.

### Reading and writing values

```python
from orionis.environment import Env, env

# Write a value into the .env file and the process environment.
Env.set("APP_NAME", "Orionis")

# Env.get() and the env() shorthand read the very same value.
print(Env.get("APP_NAME"))
print(env("APP_NAME"))

# A missing key falls back to the provided default.
print(Env.get("APP_TIMEOUT", 30))

# Remove it again: gone from the file and from os.environ.
print(Env.unset("APP_NAME"))
print(Env.get("APP_NAME"))
```

```text
Orionis
Orionis
30
True
None
```

### Storing typed values

```python
from orionis.environment import Env
from orionis.environment.enums import EnvironmentValueType

# The type hint is stored in the file as a "<type>:<value>" prefix.
Env.set("QUEUE_RETRIES", 5, "int")
Env.set("ALLOWED_HOSTS", ["localhost", "127.0.0.1"], "list")
Env.set("FEATURE_FLAGS", {"beta": True}, EnvironmentValueType.DICT)
Env.set("MAIL_ENABLED", True, "bool")

for key in ("QUEUE_RETRIES", "ALLOWED_HOSTS", "FEATURE_FLAGS", "MAIL_ENABLED"):
    value = Env.get(key)
    print(f"{key}: {value!r} ({type(value).__name__})")

# Any value already stored with a known prefix is decoded on read,
# even when it was written without a type hint.
Env.set("SIGNING_SECRET", "base64:aGVsbG8=")
print("SIGNING_SECRET:", repr(Env.get("SIGNING_SECRET")))
```

```text
QUEUE_RETRIES: 5 (int)
ALLOWED_HOSTS: ['localhost', '127.0.0.1'] (list)
FEATURE_FLAGS: {'beta': True} (dict)
MAIL_ENABLED: True (bool)
SIGNING_SECRET: 'hello'
```

### Handling validation and casting errors

```python
from orionis.environment import Env
from orionis.environment.dynamic.caster import EnvironmentCaster

# Key names must match ^[A-Z][A-Z0-9_]*$.
try:
    Env.get("app_name")
except ValueError as exc:
    print("ValueError:", exc)

# A non-string key is rejected before the pattern check.
try:
    Env.set(42, "value")
except TypeError as exc:
    print("TypeError:", exc)

# Parsing failures keep the concrete exception type.
try:
    EnvironmentCaster("int:not-a-number").get()
except ValueError as exc:
    print("ValueError:", exc)

# Serialising a value whose type does not match the hint fails too.
try:
    EnvironmentCaster([1, 2]).to("dict")
except ValueError as exc:
    print("ValueError:", exc)
```

```text
ValueError: Invalid environment variable name 'app_name'. It must start with an uppercase letter, contain only uppercase letters, numbers, or underscores. Example: 'MY_ENV_VAR'.
TypeError: Environment variable name must be a string, got int.
ValueError: Error processing value 'not-a-number' with type hint 'int': Cannot convert 'not-a-number' to int: invalid literal for int() with base 10: 'not-a-number'
ValueError: Error converting value '[1, 2]' to type 'dict': Value must be a dict to convert to dict, got list instead.
```

### Using the caster on its own

```python
from orionis.environment.dynamic.caster import EnvironmentCaster

# Serialise a Python value into its .env representation...
encoded = EnvironmentCaster([1, 2, 3]).to("list")
print(encoded)

# ...and read it back into a real Python object.
print(EnvironmentCaster(encoded).get())

# Fast path for primitives: no instance is allocated.
print(EnvironmentCaster.parseTyped("bool:on"))
print(EnvironmentCaster.parseTyped("float: 3.5"))

# Without a recognised prefix the raw string is returned untouched.
print(EnvironmentCaster("mailto:someone@example.com").get())

print(sorted(EnvironmentCaster.supportedTypes()))
```

```text
list:[1, 2, 3]
[1, 2, 3]
True
3.5
mailto:someone@example.com
['base64', 'bool', 'dict', 'float', 'int', 'list', 'path', 'set', 'str', 'tuple']
```

### Generating an application key

```python
import base64

from orionis.environment.key.key_generator import SecureKeyGenerator
from orionis.foundation.config.app.enums.ciphers import Cipher

# Each cipher gets a key of the exact size it needs.
for cipher in (Cipher.AES_128_CBC, Cipher.AES_256_GCM):
    key = SecureKeyGenerator.generate(cipher)
    raw = base64.b64decode(key.split(":", 1)[1])
    print(f"{cipher.value}: prefix={key[:7]!r} bytes={len(raw)}")

# The cipher may also be given as its string value.
print(SecureKeyGenerator.generate("AES-256-CBC").startswith("base64:"))

# Anything outside the catalogue is rejected.
try:
    SecureKeyGenerator.generate("AES-512-CBC")
except ValueError as exc:
    print("ValueError:", exc)
```

```text
AES-128-CBC: prefix='base64:' bytes=16
AES-256-GCM: prefix='base64:' bytes=32
True
ValueError: Cipher 'AES-512-CBC' is not supported. Options: AES-128-CBC, AES-256-CBC, AES-128-GCM, AES-256-GCM
```

### Reading configuration from an entity

```python
from dataclasses import dataclass, field

from orionis.environment import Env

# This is how every entity under orionis/foundation/config reads its
# defaults: a default_factory that calls Env.get() at construction time.
@dataclass(frozen=True, kw_only=True)
class CacheSection:
    default: str = field(default_factory=lambda: Env.get("CACHE_STORE", "file"))
    ttl: int = field(default_factory=lambda: Env.get("CACHE_TTL", 3600))

# No variable set yet: the declared defaults win.
print(CacheSection())

# Once the variable exists, the same declaration picks it up.
Env.set("CACHE_STORE", "redis")
Env.set("CACHE_TTL", 60, "int")
print(CacheSection())
```

```text
CacheSection(default='file', ttl=3600)
CacheSection(default='redis', ttl=60)
```

### Reloading after an external edit

```python
from pathlib import Path

from orionis.environment import Env

# Simulate an external process appending a variable to the .env file.
with Path(".env").open("a", encoding="utf-8") as handle:
    handle.write("\nEXTERNALLY_ADDED=42\n")

# The process environment has not changed yet.
print(Env.get("EXTERNALLY_ADDED"))

# reload() re-reads the file into os.environ and rebuilds the cache.
print(Env.reload())
print(Env.get("EXTERNALLY_ADDED"))

# all() lists what the .env file holds, parsed to native types.
# APP_KEY is there because the App config entity generated one on boot.
print(sorted(Env.all()))
```

```text
None
True
42
['APP_KEY', 'EXTERNALLY_ADDED']
```

## Performance and concurrency considerations

- **Reads avoid disk I/O.** `get()` only touches `os.environ`; the file is
  read at construction time and on `reload()`.
- **Thread safety inside the process.** `DotEnv` guards `__init__`, `set`,
  `get`, `unset`, `all` and `reload` with a class-level `threading.Lock`.
  Concurrent `set()` calls from several threads complete without errors and
  every value is stored (verified with twelve threads writing distinct
  keys). The lock is a plain `Lock`, not an `RLock`: no public method calls
  another one while holding it, so no reentrancy is required.
- **Writes are not atomic and are not locked across processes.** `set()` /
  `unset()` delegate to `python-dotenv`'s `set_key` / `unset_key`, which
  rewrite the file. Two processes writing the same `.env` concurrently are
  not coordinated by this module.
- **No async API.** The module contains no `async def`; every call is
  synchronous and blocking. `set`, `unset` and `reload` perform file I/O,
  so calling them from inside an event loop blocks it.
- **Validators are cached.** `ValidateKeyName` (512 entries) and the type
  hint normaliser (64 entries) use `functools.lru_cache`, so repeated
  validation is a dictionary lookup.
- **`parseTyped` avoids allocations** for `int`, `float`, `bool` and `str`;
  only the container/path/base64 hints build an `EnvironmentCaster`
  instance.
- **`all()` copies.** It builds a new dictionary and re-parses every entry
  on each call, so it is not meant for hot paths.
- **Module-level constants.** `_NULL_VALUES` and `_ENV_TYPE_PREFIXES` are
  `frozenset`s computed once at import time; membership checks are O(1).

## Compatibility notes

- **Python:** the framework declares `requires-python = ">=3.14"`
  (`pyproject.toml`). The module itself uses `from __future__ import
  annotations` in every file, `X | Y` unions and `ClassVar`.
- **Third-party dependency:** `python-dotenv~=1.2`, already a base
  dependency of `orionis`, so `pip install orionis` is enough. The module
  uses `dotenv_values`, `load_dotenv`, `set_key` and `unset_key` without
  overriding their defaults, which means UTF-8 encoding,
  `quote_mode="always"` (values are written single-quoted) and
  `interpolate=True` (a `${OTHER_VAR}` reference is expanded when the file
  is loaded).
- **`SecureKeyGenerator` imports the framework:** it depends on
  `orionis.foundation.config.app.enums.ciphers.Cipher`, unlike the rest of
  the module, which only depends on `orionis.support.patterns.singleton`.
- **No provider, no container facade.** Nothing in this module is
  registered in the service container, so it works in plain scripts,
  console commands and tests without booting the application.
- **Windows:** `path` values are always normalised to POSIX separators, and
  a relative path passed to `to("path")` is anchored to the current working
  directory, so the stored value includes the drive letter of that
  directory.

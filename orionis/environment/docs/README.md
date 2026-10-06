# orionis.environment

> Read, persist and decode environment values through a shared `.env` service.

Spanish version: [README.es.md](README.es.md). Agent entry point:
[SKILL.md](SKILL.md).

## Table of contents

- [Functional overview](#functional-overview)
- [Module structure](#module-structure)
- [API reference](#api-reference)
- [Env](#env)
- [Environment lookup helper](#environment-lookup-helper)
- [DotEnv](#dotenv)
- [EnvironmentCaster](#environmentcaster)
- [EnvironmentValueType](#environmentvaluetype)
- [ValidateKeyName](#validatekeyname)
- [ValidateTypes](#validatetypes)
- [SecureKeyGenerator](#securekeygenerator)
- [IEnv](#ienv)
- [IEnvironmentCaster](#ienvironmentcaster)
- [Usage examples](#usage-examples)
- [Design characteristics](#design-characteristics)
- [Performance and concurrency](#performance-and-concurrency)
- [Compatibility notes](#compatibility-notes)
- [Verification and limitations](#verification-and-limitations)

## Functional overview

The module exposes synchronous reads and writes through `Env` and `env()`.
`DotEnv` owns one selected file and a cached file snapshot; reads consult
`os.environ`, not that snapshot. `EnvironmentCaster` implements explicit typed
values, while the validators check names and hints and `SecureKeyGenerator`
produces random Base64 keys. See [facade.py](../facade.py),
[core/dot_env.py](../core/dot_env.py) and [dynamic/caster.py](../dynamic/caster.py).

The concrete integration is configuration defaults, for example
`App.name`, `App.debug` and `App.key` in
[orionis/foundation/config/app/entities/app.py](../../foundation/config/app/entities/app.py).
`App.__validateKey` generates and persists `APP_KEY` only when `key is None`.
`Env` derives from `IEnv`, not the container's `Facade`; its classmethods do not
require application boot, dependency injection or `pin()`.

### Initialization and import effects

The inspected [orionis/__init__.py](../../__init__.py) resolves its exports
lazily, and [core_config.py](../../foundation/core_config.py) constructs defaults
inside `get_core_config_mapping()`, not at module import. Importing this module,
its caster and its key generator was verified not to create `.env` or initialize
`DotEnv`. The first `Env` operation or explicit `DotEnv(...)` construction does
initialize the service, even `set(..., only_os=True)` or `get()` on a missing key.

Select a custom file with `DotEnv(path)` **before the first operation that creates
the singleton**. Later constructor arguments are ignored. Building configuration
defaults can initialize it earlier and may generate `APP_KEY`; distinguish that
construction from a simple import. Evidence: [DotEnv.__init__](../core/dot_env.py),
[Singleton.__call__](../../support/patterns/singleton/meta.py) and
[App.__validateKey](../../foundation/config/app/entities/app.py).

### Process, cache and file views

| Operation | Process environment | Cached file snapshot | File |
| --- | --- | --- | --- |
| First construction | Load file values with `override=True`. | Read `dotenv_values`. | Touch if missing; do not create parent directories. |
| `get(key, default)` | Read and parse this view. | Not read. | Not read after initialization. |
| `all()` | Not read directly; earlier interpolation may have used it. | Parse into a new dictionary. | Not read after initialization. |
| `set(key, value)` | Assign serialized string last. | Update after the file write. | Rewrite via `set_key`. |
| `set(..., only_os=True)` | Assign serialized string. | Unchanged. | Unchanged after initialization. |
| `unset(key)` | Remove last. | Remove after `unset_key`. | Rewrite via `unset_key`. |
| `unset(..., only_os=True)` | Remove only here. | Unchanged. | Unchanged after initialization. |
| `reload()` | Overwrite keys supplied by the file. | Replace with a new file snapshot. | Read twice through the dependency. |

The table follows [DotEnv](../core/dot_env.py). `reload()` does **not** remove
process keys absent from the new file. A bare declaration such as `DOC_BARE`
appears as `None` in `all()` but is not assigned to `os.environ`; a previous
process value can therefore remain. There is no rollback across the three
views if a later step fails. Dependency behavior was inspected in
`dotenv.main.DotEnv.set_as_environment_variables`, `dotenv_values` and `rewrite`
from installed `python-dotenv` 1.2.4.

## Module structure

All 17 Python files were inspected. Paths below are relative to
`orionis/environment`; none of its non-Python resources participates in runtime.

| Files | Responsibility and public symbols |
| --- | --- |
| [__init__.py](../__init__.py) | Reexport exactly `Env` and `env` through `__all__`. |
| [facade.py](../facade.py) | `Env`, five delegating classmethods. |
| [functions.py](../functions.py) | `env`, one delegating function. |
| [core/dot_env.py](../core/dot_env.py) | `DotEnv`, file selection, locking, cache and process I/O. |
| [dynamic/caster.py](../dynamic/caster.py) | `EnvironmentCaster`, conversion and `OPTIONS`. |
| [enums/value_type.py](../enums/value_type.py) | `EnvironmentValueType`, ten members. |
| [enums/__init__.py](../enums/__init__.py) | Reexport `EnvironmentValueType`. |
| [validators/key_name.py](../validators/key_name.py) | `ValidateKeyName`, alias of a cached function. |
| [validators/types.py](../validators/types.py) | `ValidateTypes`, a callable instance. |
| [validators/__init__.py](../validators/__init__.py) | Reexport both validators. |
| [key/key_generator.py](../key/key_generator.py) | `SecureKeyGenerator`, `KEY_SIZES` and `generate`. |
| [contracts/env.py](../contracts/env.py) | `IEnv`, five abstract classmethods. |
| [contracts/caster.py](../contracts/caster.py) | `IEnvironmentCaster`, two abstract methods. |
| [contracts/__init__.py](../contracts/__init__.py), [core/__init__.py](../core/__init__.py), [dynamic/__init__.py](../dynamic/__init__.py), [key/__init__.py](../key/__init__.py) | Empty initializers; import their symbols from concrete files. |

Imported standard-library and dependency names are implementation dependencies,
not additional intended public exports. Private parser helpers, `_lock`, storage
slots, `_NULL_VALUES`, `_ENV_TYPE_PREFIXES`, `_pattern`, `_normalize_type_hint`,
`_ALLOWED_TYPE_HINT_VALUES` and `__ValidateTypes` are excluded as independent API;
their observable effects are documented through the public operations below.

## API reference

Declarations in this section reproduce source headers, decorators and defaults.
Method bodies are intentionally omitted: these are **reference fragments**, not
standalone scripts. Imports identify actual public paths. Literal declarations
retain the source annotations, including `Any`, `str | object` and the absence
of an explicit `int` or `None` in some value unions.

### Env

Import `Env` from `orionis.environment` or `orionis.environment.facade`.
Source: [orionis/environment/facade.py](../facade.py), symbol `Env`.

```python
class Env(IEnv):
```

No explicit constructor is declared. `Env()` is permitted but provides no
independent environment state; the methods always obtain the shared `DotEnv()`.

#### Env.get

```python
@classmethod
def get(
        cls,
        key: str,
        default: object | None = None,
) -> object:
```

`key` must satisfy `ValidateKeyName`. `default` is any object, defaults to `None`,
and is returned unchanged only when the process key is absent. An existing empty
or null-like value returns `None`, not `default`. Results, parsing exceptions,
initialization effects and locking are those of [DotEnv.get](#dotenvget).

#### Env.set

```python
@classmethod
def set(
        cls,
        key: str,
        value: str | float | bool | list | dict | tuple | set,
        type_hint: str | EnvironmentValueType | None = None,
        *,
        only_os: bool = False,
) -> bool:
```

`key` is validated; `value` is serialized; `type_hint` optionally specifies an
enum member or supported textual hint. `only_os` is keyword-only and skips file
and cache updates, not first-time initialization. Returns `True` after normal
completion. See [DotEnv.set](#dotenvset) for supported runtime values,
`TypeError`, `ValueError`, `RuntimeError` and propagated I/O failures.

#### Env.unset

```python
@classmethod
def unset(
        cls,
        key: str,
        *,
        only_os: bool = False,
) -> bool:
```

Remove the validated `key`; keyword-only `only_os=False` controls persistence.
Returns `True` even for an absent key. Exceptions and effects are those of
[DotEnv.unset](#dotenvunset), not a boolean report of dependency failure.

#### Env.all

```python
@classmethod
def all(
        cls,
) -> dict[str, Any]:
```

Return the parsed cached-file dictionary, not all process variables. No
parameters besides `cls`; initialization and decoding can raise. See
[DotEnv.all](#dotenvall) for new-object and malformed-entry behavior.

#### Env.reload

```python
@classmethod
def reload(cls) -> bool:
```

Refresh the same singleton. Returns `False` if the delegated construction or
call raises `OSError` or `ValueError`; otherwise returns the delegated result.
Actual `DotEnv.reload` wraps its failures in `RuntimeError`, which propagates
through this method. It is **not** a reset or a file-switch operation. Source:
`Env.reload` in [facade.py](../facade.py); regression:
[TestEnvReload.testKeepsTheSingletonAlive](../../../tests/environment/test_facade.py).

### Environment lookup helper

Import `env` from `orionis.environment` or `orionis.environment.functions`.
Source: [orionis/environment/functions.py](../functions.py), symbol `env`.

```python
def env(key: str, default: object | None = None) -> object:
```

Call `Env.get(key, default)` exactly once and return its object unchanged. The
same name validation, missing-key fallback, decoding and initialization apply;
no additional state, conversion or exception handling is introduced. Verified
delegation cases: [test_functions.py](../../../tests/environment/test_functions.py).

### DotEnv

Import from `orionis.environment.core.dot_env`. Source:
[orionis/environment/core/dot_env.py](../core/dot_env.py), symbol `DotEnv`.

```python
class DotEnv(metaclass=Singleton):
```

`Singleton` creates one instance **per class**; later construction reuses it
without evaluating new constructor arguments. Its sync construction lock is
distinct from `DotEnv._lock`. There is no public close, reset or file-path
setter. No file handle is retained; dependency functions scope their handles.

#### DotEnv.__init__

```python
def __init__(
        self,
        path: str | None = None,
) -> None:
```

`path=None` or `path=""` selects `Path.cwd() / ".env"`. A truthy supplied path
uses `Path(path).expanduser().resolve()`. This is an explicit path selection,
not an upward `.env` search. Missing files are touched; missing parent
directories are not created. Under `_lock`, load with `override=True` then
cache `dict(dotenv_values(path))`; file strings are not Orionis-decoded yet.

Initialization rethrows `OSError` as a chained `OSError` with path context;
other caught exceptions become chained `RuntimeError`. The singleton is
published only after successful construction. File contents, process variables
or touched files are not rolled back on failure. Evidence:
[DotEnv.__init__](../core/dot_env.py), [Singleton.__call__](../../support/patterns/singleton/meta.py)
and [TestDotEnvInitialisation](../../../tests/environment/core/test_dot_env.py).

The metaclass also supplies the following **inherited** factory. This declaration
belongs to `Singleton.__acall__`, not to a function defined in this module:

```python
async def __acall__(
        cls,
        *args: object,
        **kwargs: object,
) -> object:
```

Explicitly awaiting `DotEnv.__acall__()` obtains the same instance. It uses the
same `threading.Lock` and performs synchronous construction without an `await`
inside its body; it does not make environment I/O nonblocking. Evidence:
[Singleton.__acall__](../../support/patterns/singleton/meta.py).

#### DotEnv.set

```python
def set(
        self,
        key: str,
        value: str | float | bool | list | dict | tuple | set,
        type_hint: str | EnvironmentValueType | None = None,
        *,
        only_os: bool = False,
) -> bool:
```

Hold `_lock`; validate `key`; serialize `value`; when `only_os` is false, call
`set_key` and then update the cache; assign `os.environ[key]` last. Return
`True`, ignoring the dependency's returned tuple.

| Input path | Implemented behavior |
| --- | --- |
| `type_hint is None` | Skip `ValidateTypes`; `None` becomes `"null"`, strings use `strip()`, booleans use lowercase text, numeric values use `str()`, containers use `repr()`, other objects use `str()`. |
| Explicit hint | `ValidateTypes` checks the runtime value catalogue and normalizes the hint, then `EnvironmentCaster(value).to(hint)` performs conversion. |
| Hint spelling | Names are case-insensitive through enum name lookup, but whitespace is not stripped: `"INT"` works; `" INT "` raises `RuntimeError`. |
| Container payload | Representation uses Python literals, not JSON or recursive type enforcement. Nonliteral nested values may serialize and later fail to decode. |

Runtime integers are accepted. Unhinted `None` and objects outside the annotated
union are also accepted by the fallback; hinted `None`, `bytes`, `Path` and
`frozenset` are rejected by `ValidateTypes`. This is an annotation and docstring
scope discrepancy, not an expanded type declaration. Evidence:
[DotEnv.__serializeValue](../core/dot_env.py) and
[TestDotEnvSet](../../../tests/environment/core/test_dot_env.py).

`TypeError` comes from invalid key types, unsupported hinted values or hint
types. `ValueError` comes from invalid names or failed serialization;
unknown textual hints raise `RuntimeError`. Filesystem `OSError`, process
assignment errors and exceptions from custom `str()`/`repr()` are not translated
by `set`. Serialization does not promise a reversible round trip: strings
such as `"42"` are decoded as numbers unless explicitly stored as `str`.

#### DotEnv.get

```python
def get(
        self,
        key: str,
        default: object | None = None,
) -> object:
```

Under `_lock`, validate `key`, fetch `os.environ.get(key)` and parse it.
Absent keys return `default` by identity. An existing empty string yields
`None`; whitespace-only text is not the same as an empty string.

Parsing order in `DotEnv.__parseValue` is significant:

1. `None` stays `None`; existing native bool/numeric/container values stay as-is
     in internal calls, although `os.environ` provides strings.
2. `""` becomes `None`; stripped, case-insensitive `none`, `null`, `nan` and
     `nil` become `None`; `true` and `false` become booleans.
3. An exact unstripped lowercase prefix from `EnvironmentValueType` delegates
     to `EnvironmentCaster.parseTyped`.
4. Otherwise use `ast.literal_eval`; `ValueError` or `SyntaxError` falls back
     to the original string, preserving its whitespace.

Thus `"INT:5"`, `" int:5"` and URLs remain text, while `"int:5"` returns `5`.
Untyped `"yes"` remains text; `"bool:yes"` is `True`. The fast boolean parser
returns `False` for `"bool:maybe"`. Invalid `"int:abc"` raises `ValueError`;
`"list:{1}"` raises `TypeError`; dict/tuple/set shape failures are wrapped as
`ValueError` by their individual parsers. Key validation raises `TypeError` or
`ValueError`. Other standard-library parsing/resource failures can propagate;
this list is not exhaustive. Source: [DotEnv.__parseValue](../core/dot_env.py),
[EnvironmentCaster.parseTyped and get](../dynamic/caster.py).

#### DotEnv.unset

```python
def unset(
        self,
        key: str,
        *,
        only_os: bool = False,
) -> bool:
```

Validate `key` under `_lock`; unless `only_os=True`, call `unset_key` and remove
the cache entry; then `os.environ.pop(key, None)`. Returns `True` even for an
absent key or a dependency result indicating no removal. Invalid key types and
names raise `TypeError` and `ValueError`; filesystem errors propagate. In the
inspected dependency, an absent key emits a `dotenv.main` logger warning, not
a guaranteed stdout message. A process-only removal leaves `all()` unchanged;
`reload()` can restore the file value.

#### DotEnv.all

```python
def all(self) -> dict:
```

Under `_lock`, build a new dictionary by parsing each cached raw value. This
does not reread disk, validate file-loaded key names or enumerate process-only
keys. Mutable literal values are reparsed into new containers; mutations to a
returned dictionary do not update the cached strings. Bare and empty file
entries yield `None`. One malformed typed entry can fail the whole call with
the same decoding exceptions as `get`; no partial dictionary is returned.
The private cache is annotated `dict[str, str]`, although `dotenv_values` can
put `None` there for bare keys; the runtime behavior takes precedence here.
Source: [DotEnv.all](../core/dot_env.py).

#### DotEnv.reload

```python
def reload(self) -> bool:
```

Hold `_lock`; run `load_dotenv(path, override=True)` then replace the cache with
`dict(dotenv_values(path))`. Returns `True` without checking the dependency's
load result, even for an empty or missing file. It neither switches files nor
clears process-only or externally deleted keys. Every caught `Exception` is
wrapped in chained `RuntimeError`; invalid UTF-8 produces a
`UnicodeDecodeError` cause. Two file reads do not form a transactional snapshot
against external writers. Source: [DotEnv.reload](../core/dot_env.py).

### EnvironmentCaster

Import from `orionis.environment.dynamic.caster`. Source:
[orionis/environment/dynamic/caster.py](../dynamic/caster.py).

```python
class EnvironmentCaster(IEnvironmentCaster):
```

#### OPTIONS and supportedTypes

```python
OPTIONS: ClassVar[frozenset[str]] = frozenset(e.value for e in EnvironmentValueType)
```

```python
@staticmethod
def supportedTypes() -> frozenset[str]:
```

`OPTIONS` holds the ten enum values computed at class definition.
`supportedTypes()` returns `EnvironmentCaster.OPTIONS` itself, not a copy or
`cls.OPTIONS`. The object is a `frozenset`; the class attribute is not frozen
against reassignment. The method has no parameters and performs no I/O.
Its Returns docstring says `set[str]`, while the signature and implementation
return `frozenset[str]`.

#### EnvironmentCaster.__init__

```python
def __init__(
        self,
        raw: str | object,
) -> None:
```

For a string `raw`, store `raw.lstrip()`. If its first colon separates a prefix
whose `strip().lower()` is in `OPTIONS`, retain the normalized hint and the
payload with leading whitespace removed. An exactly empty payload is stored
as `None`; an unknown prefix keeps the whole untyped string. Nonstrings are
retained by reference without a hint. The constructor does not eagerly parse,
copy containers or validate the eventual conversion.

The constructor docstring describes the part before a colon as a type hint
without stating the supported-prefix guard; the implementation applies that
guard. Source: `EnvironmentCaster.__init__` in [caster.py](../dynamic/caster.py).

#### EnvironmentCaster.parseTyped

```python
@staticmethod
def parseTyped(value_str: str) -> object:
```

`value_str` must be a string containing a colon. Strip and lowercase its prefix;
remove leading payload whitespace. `int`, `float`, `bool` and `str` are parsed
inline without constructing a caster; other prefixes use a new caster's
`get()`. Unknown prefixes therefore return untyped text, not an unsupported-hint
exception. A missing colon raises the `ValueError` from `str.index`; invalid
nonstring inputs can raise `AttributeError` or `TypeError` before conversion.

| Prefix | Fast-path result |
| --- | --- |
| `int` | `int(raw.strip())`; conversion `ValueError` is contextualized. |
| `float` | `float(raw.strip())`; conversion `ValueError` is contextualized. |
| `bool` | `True` only for `true`, `1`, `yes`, `on`, `enabled`; **all other text**, including empty text, is `False`. |
| `str` | Payload after `lstrip()`, including `""`; trailing whitespace is retained. |

`DotEnv` performs a stricter exact-prefix check before calling this method.
Direct `parseTyped(" INT :5")` works even though `Env.get` leaves that stored
text unparsed. Evidence: [DotEnv.__parseValue](../core/dot_env.py) and
[TestEnvironmentCasterParseTyped](../../../tests/environment/dynamic/test_caster.py).

#### EnvironmentCaster.get

```python
def get(  # noqa: PLR0911, PLR0912, C901
        self,
) -> object:
```

No arguments besides `self`. Decode the retained raw value with the current
hint, or return it unchanged when no hint exists. No file or process mutation.
The following table describes the full parser, not the primitive fast path:

| Hint | Result and restrictions |
| --- | --- |
| `str` | `raw.lstrip()`; `"str:"` fails because the constructor stored `None`. |
| `int`, `float` | Strip text then call the builtin numeric conversion. |
| `bool` | Strip and lowercase; accept true/1/yes/on/enabled or false/0/no/off/disabled; other spellings raise `ValueError`. |
| `list` | `ast.literal_eval`, require `isinstance(result, list)`; wrong shape is `TypeError`. |
| `dict`, `tuple`, `set` | Evaluate a Python literal and require the matching container; parser shape/syntax failures become `ValueError`. Empty set spelling `set()` is accepted by the builtin literal parser. |
| `path` | `Path` to POSIX text, replacing backslashes for strings; do not resolve, expand `~` or make relative paths absolute. |
| `base64` | Decode with `validate=True`; return UTF-8 text if decodable, otherwise raw `bytes`. |

`get()` preserves caught `TypeError` as chained `TypeError`, preserves caught
`ValueError` as chained `ValueError`, and wraps other caught exceptions in
`ValueError`. Its contextual message starts with `Error processing value`.
Individual helpers may already have changed a concrete exception type before
this wrapper. Source: `EnvironmentCaster.get` and its `__parse*` helpers in
[caster.py](../dynamic/caster.py).

#### EnvironmentCaster.to

```python
def to(  # noqa: PLR0911, PLR0912, C901
        self,
        type_hint: str | EnvironmentValueType,
) -> str:
```

Accept an enum member or an **exact lowercase** value in `OPTIONS`; unlike
`ValidateTypes`, do not normalize textual case or whitespace. Return a typed
string; every caught conversion or validation exception becomes chained
`ValueError`, including internal `TypeError`. The message starts with
`Error converting value`; displayed option-set order is not stable.

| Hint | Accepted input and serialization |
| --- | --- |
| `str` | Require `str`; preserve retained payload after constructor processing. |
| `int` | Use integers directly, otherwise builtin `int` conversion; `True` enters the integer branch and produces `"int:True"`, which is not numerically decodable. |
| `float` | Use floats directly, otherwise builtin `float` conversion. |
| `bool` | Booleans directly; accepted textual boolean vocabulary; other objects through `bool(value)`. |
| `list`, `dict`, `tuple`, `set` | Require `isinstance` of the corresponding container, allowing subclasses; use `repr`, not element coercion or JSON. |
| `path` | Require `str` or `Path`; strip and normalize slashes, join relative input to `Path.cwd()`, then call `expanduser().as_posix()`. Do not call `resolve()` or create anything. |
| `base64` | Require `str` or UTF-8-decodable `bytes`; preserve an already valid Base64 candidate, otherwise Base64-encode it. Non-UTF-8 raw bytes are rejected before encoding. |

Relative `~/file` is joined to the working directory **before** `expanduser`,
so it does not expand to the user's home. `a/../file` retains the `..` component.
Base64-like plaintext can be treated as encoded input; this is not an
unconditional arbitrary-binary encoder. Evidence: `__toPath`, `__toBase64` and
`__toInt` in [caster.py](../dynamic/caster.py).

State matters: after validating the hint, `to()` assigns it to the instance but
does **not** replace the original raw value with the serialized output. The hint
can remain changed after a conversion failure. A subsequent `get()` interprets
the original raw value using that new hint and may fail. To decode the emitted
string, build another caster or use `parseTyped`. Nonstrings retained by
reference can reflect subsequent caller mutations.

### EnvironmentValueType

Import from `orionis.environment.enums` or
`orionis.environment.enums.value_type`. Source:
[orionis/environment/enums/value_type.py](../enums/value_type.py).

```python
class EnvironmentValueType(Enum):
```

Literal member assignments, in source order:

```python
BASE64 = "base64"
PATH = "path"
STR = "str"
INT = "int"
FLOAT = "float"
BOOL = "bool"
LIST = "list"
DICT = "dict"
TUPLE = "tuple"
SET = "set"
```

This is `enum.Enum`, not `StrEnum`; members have standard `.name` and `.value`
and are not equal to their strings. Enum-generated value lookup
`EnvironmentValueType("int")` is case-sensitive and raises `ValueError` for
unknown values; name lookup `EnvironmentValueType["INT"]` raises `KeyError`
for unknown names. No explicit constructor is declared. Tests:
[test_value_type.py](../../../tests/environment/enums/test_value_type.py).

### ValidateKeyName

Import from `orionis.environment.validators` or
`orionis.environment.validators.key_name`. Source:
[orionis/environment/validators/key_name.py](../validators/key_name.py).
The public name is an alias, not a separately defined `def ValidateKeyName`:

```python
@functools.lru_cache(maxsize=512)
def _validate_key_name(key: str) -> str:
```

```python
ValidateKeyName = _validate_key_name
```

`ValidateKeyName(key)` requires `str` and a full match of
`^[A-Z][A-Z0-9_]*$`. ASCII uppercase first letter; subsequent ASCII uppercase
letters, digits and underscores only. No stripping or case conversion. Return
the validated string; empty text, initial `_` or digit, non-ASCII letters,
lowercase and final newline raise `ValueError`. Nonstring keys raise
`TypeError`; unhashable keys can fail in the cache wrapper before the body.

The alias exposes inherited cache-wrapper methods `cache_info()`,
`cache_parameters()` and `cache_clear()`; these come from `functools.lru_cache`,
not hand-written module methods. Successful results retain key references in a
process-local LRU of 512; exceptions are not cached. Tests:
[test_key_name.py](../../../tests/environment/validators/test_key_name.py).

### ValidateTypes

Import from `orionis.environment.validators` or
`orionis.environment.validators.types`. Source:
[orionis/environment/validators/types.py](../validators/types.py).
This public callable is an instance, not a function declaration:

```python
ValidateTypes = __ValidateTypes()
```

Its literal call implementation header is:

```python
def __call__(
        self,
        *,
        value: str | float | bool | list | dict | tuple | set,
        type_hint: str | EnvironmentValueType | None = None,
) -> str:
```

Call `ValidateTypes(value=..., type_hint=...)` with keyword-only arguments.
Validate `value` using `isinstance` against str/int/float/bool/list/dict/tuple/set;
unsupported values, including `None`, `bytes` and `Path`, raise `TypeError`.
Validate hints even if falsy: neither string nor enum is `TypeError`; an unknown,
empty or whitespace-padded textual member name is `RuntimeError`.

A provided hint is looked up with `EnvironmentValueType[type_hint.upper()]` and
returned as its lowercase `.value`; enum members return their `.value`. Without
a hint return `type(value).__name__.lower()`; subclasses can therefore produce
names outside the enum catalogue. This does **not** validate compatibility
between the hint and the value: `ValidateTypes(value=42, type_hint="str")`
returns `"str"`, while `EnvironmentCaster(42).to("str")` fails.

The private `_normalize_type_hint` has an LRU of 64 keyed by the original hint
argument, including its case and enum identity. Value validation runs on each
call; the public object itself has no `cache_info()` or `cache_clear()` API.
Tests: [test_types.py](../../../tests/environment/validators/test_types.py).

### SecureKeyGenerator

Import from `orionis.environment.key.key_generator`. Source:
[orionis/environment/key/key_generator.py](../key/key_generator.py).
The related `Cipher` is from
[orionis.foundation.config.app.enums.ciphers](../../foundation/config/app/enums/ciphers.py),
not an environment enum.

```python
class SecureKeyGenerator:
```

```python
KEY_SIZES: ClassVar[dict[Cipher, int]] = {
        Cipher.AES_128_CBC: 16,
        Cipher.AES_256_CBC: 32,
        Cipher.AES_128_GCM: 16,
        Cipher.AES_256_GCM: 32,
}
```

```python
@staticmethod
def generate(cipher: str | Cipher = Cipher.AES_256_CBC) -> str:
```

Accept a `Cipher` member or its exact case-sensitive value (`AES-128-CBC`,
`AES-256-CBC`, `AES-128-GCM`, `AES-256-GCM`). Default `Cipher.AES_256_CBC`
draws 32 bytes. Look up the size in `KEY_SIZES`, call `os.urandom`, Base64-encode
the bytes, then return a `base64:`-prefixed string. No persistence, environment
mutation, encryption, instance state or cached random key is involved.

Invalid textual ciphers and unsupported hashable objects raise explicit
`ValueError`; an unhashable object can raise `TypeError` in dictionary lookup.
Random-source and standard-library encoding errors are not translated.
`KEY_SIZES` is a mutable class dictionary consulted on every call; no copying,
freezing or synchronization of modifications is implemented. Tests:
[test_key_generator.py](../../../tests/environment/key/test_key_generator.py).

### IEnv

Import from `orionis.environment.contracts.env`. Source:
[orionis/environment/contracts/env.py](../contracts/env.py).

```python
class IEnv(ABC):
```

```python
@classmethod
@abstractmethod
def get(
        cls,
        key: str,
        default: object | None = None,
) -> object:
```

```python
@classmethod
@abstractmethod
def set(
        cls,
        key: str,
        value: str | float | bool | list | dict | tuple | set,
        type_hint: str | EnvironmentValueType | None = None,
        *,
        only_os: bool = False,
) -> bool:
```

```python
@classmethod
@abstractmethod
def unset(
        cls,
        key: str,
        *,
        only_os: bool = False,
) -> bool:
```

```python
@classmethod
@abstractmethod
def all(
        cls,
) -> dict[str, Any]:
```

```python
@classmethod
@abstractmethod
def reload(cls) -> bool:
```

ABC with `__slots__ = ()`, no explicit constructor and no implementation besides
docstring-only abstract bodies. Direct or incomplete instantiation raises the
ABC machinery's `TypeError`. Parameters and declared results mirror `Env`;
reading, serialization, mutation and exceptions belong to the concrete
implementation, not an executing body in this contract. The set/unset docstrings
allow `False` while the concrete methods return `True` on normal completion.
Tests: [test_env.py](../../../tests/environment/contracts/test_env.py).

### IEnvironmentCaster

Import from `orionis.environment.contracts.caster`. Source:
[orionis/environment/contracts/caster.py](../contracts/caster.py).

```python
class IEnvironmentCaster(ABC):
```

```python
@abstractmethod
def get(
        self,
) -> object:
```

```python
@abstractmethod
def to(
        self,
        type_hint: str | EnvironmentValueType,
) -> str:
```

ABC with `__slots__ = ()` and no explicit constructor. Its two abstract bodies
only contain docstrings; ABC `TypeError` prevents direct or incomplete
instantiation. The `get` result and `to` parameter, result and documented
`ValueError`/`TypeError` contracts are implemented by `EnvironmentCaster`;
the concrete `to` wrapper converts internal `TypeError` into `ValueError`.
Tests: [test_caster.py](../../../tests/environment/contracts/test_caster.py).

## Usage examples

Each block is an independent **fresh-process script** for an installed local
framework on Python 3.14+. Temporary directories, working directories and
process variables are restored. Do not concatenate the scripts in one process:
restoring the working directory does not change an already selected singleton
file, and its temporary file no longer exists after cleanup. The scripts do not
boot an application, contact services or need private credentials.

### Reading and persisting values

Write one value, observe all three views, hide only the process value and reload.
Assertions verify the difference between an absent key and a null-like value.

```python
import os
import tempfile
from pathlib import Path

previous_cwd = Path.cwd()
previous_environment = dict(os.environ)
with tempfile.TemporaryDirectory() as temporary:
    try:
        os.chdir(temporary)
        from orionis.environment import Env, env

        assert Env.set("DOC_VALUE", "Orionis") is True
        assert env("DOC_VALUE") == "Orionis"
        assert Env.all()["DOC_VALUE"] == "Orionis"
        assert "DOC_VALUE=" in Path(".env").read_text(encoding="utf-8")
        assert Env.unset("DOC_VALUE", only_os=True) is True
        fallback = ["int:5"]
        assert Env.get("DOC_VALUE", fallback) is fallback
        assert Env.all()["DOC_VALUE"] == "Orionis"
        assert Env.reload() is True
        assert Env.get("DOC_VALUE") == "Orionis"
        os.environ["DOC_EMPTY"] = ""
        assert Env.get("DOC_EMPTY", "fallback") is None
        assert Env.unset("DOC_VALUE") is True
        assert "DOC_VALUE" not in Env.all()
    finally:
        os.environ.clear()
        os.environ.update(previous_environment)
        os.chdir(previous_cwd)
```

### Storing typed values

Exercise every hint through process-only writes. The initial service still
creates its temporary `.env`; none of these values is added to the cached file.

```python
import os
import tempfile
from pathlib import Path

previous_cwd = Path.cwd()
previous_environment = dict(os.environ)
with tempfile.TemporaryDirectory() as temporary:
    try:
        os.chdir(temporary)
        from orionis.environment import Env
        from orionis.environment.enums import EnvironmentValueType

        values = (
            ("DOC_TEXT", "42", "str", "42"),
            ("DOC_NUMBER", 42, "int", 42),
            ("DOC_RATIO", 2.5, "float", 2.5),
            ("DOC_FLAG", True, "bool", True),
            ("DOC_LIST", [1, 2], "list", [1, 2]),
            ("DOC_DICT", {"active": True}, "dict", {"active": True}),
            ("DOC_TUPLE", (1, 2), "tuple", (1, 2)),
            ("DOC_SET", {1, 2}, "set", {1, 2}),
            ("DOC_PATH", "logs", "path", (Path.cwd() / "logs").as_posix()),
            ("DOC_BASE64", "hi!", "base64", "hi!"),
        )
        for key, value, hint, expected in values:
            assert Env.set(key, value, hint, only_os=True) is True
            assert Env.get(key) == expected
            assert key not in Env.all()
        Env.set("DOC_ENUM", [3], EnvironmentValueType.LIST, only_os=True)
        assert Env.get("DOC_ENUM") == [3]
        Env.set("DOC_UNTYPED", "42", only_os=True)
        assert Env.get("DOC_UNTYPED") == 42
        os.environ["DOC_CASE"] = "INT:5"
        assert Env.get("DOC_CASE") == "INT:5"
    finally:
        os.environ.clear()
        os.environ.update(previous_environment)
        os.chdir(previous_cwd)
```

### Handling real validation errors

Verify the public callable validators and three distinct exception categories.
No assertion relies on the unstable ordering of an option set in an error.

```python
import os
import tempfile
from pathlib import Path

previous_cwd = Path.cwd()
previous_environment = dict(os.environ)
with tempfile.TemporaryDirectory() as temporary:
    try:
        os.chdir(temporary)
        from orionis.environment import Env
        from orionis.environment.validators import ValidateKeyName, ValidateTypes

        assert ValidateKeyName("DOC_VALID") == "DOC_VALID"
        assert ValidateKeyName.cache_parameters()["maxsize"] == 512
        assert ValidateTypes(value=42, type_hint="INT") == "int"
        failures = []
        try:
            Env.get("lower_case")
        except ValueError:
            failures.append("name")
        try:
            Env.set("DOC_BYTES", b"payload", "base64", only_os=True)
        except TypeError:
            failures.append("value")
        try:
            Env.set("DOC_HINT", "value", "decimal", only_os=True)
        except RuntimeError:
            failures.append("hint")
        os.environ["DOC_BROKEN"] = "int:abc"
        try:
            Env.get("DOC_BROKEN")
        except ValueError:
            failures.append("decode")
        assert failures == ["name", "value", "hint", "decode"]
        assert "DOC_BYTES" not in os.environ
    finally:
        os.environ.clear()
        os.environ.update(previous_environment)
        os.chdir(previous_cwd)
```

### Using the caster directly

Contrast fast and full parsing, round-trip via a new instance, binary decoding,
relative paths and the retained raw value after `to()`.

```python
import os
import tempfile
from pathlib import Path

previous_cwd = Path.cwd()
with tempfile.TemporaryDirectory() as temporary:
    try:
        os.chdir(temporary)
        from orionis.environment.dynamic.caster import EnvironmentCaster

        payload = {"ports": [8000, 8001]}
        encoded = EnvironmentCaster(payload).to("dict")
        assert EnvironmentCaster(encoded).get() == payload
        assert EnvironmentCaster.supportedTypes() is EnvironmentCaster.OPTIONS
        assert EnvironmentCaster("  INT :5").get() == 5
        assert EnvironmentCaster.parseTyped("bool:maybe") is False
        try:
            EnvironmentCaster("bool:maybe").get()
        except ValueError:
            pass
        else:
            raise AssertionError("The full boolean parser must reject maybe")
        assert EnvironmentCaster.parseTyped("str:") == ""
        assert EnvironmentCaster("base64:/w==").get() == b"\xff"
        assert EnvironmentCaster("path:logs\\app").get() == "logs/app"
        stored_path = EnvironmentCaster("logs/app").to("path")
        assert stored_path == "path:" + (Path.cwd() / "logs/app").as_posix()
        caster = EnvironmentCaster("hi!")
        assert caster.to("base64") == "base64:aGkh"
        try:
            caster.get()
        except ValueError:
            pass
        else:
            raise AssertionError("The retained plaintext is not Base64")
    finally:
        os.chdir(previous_cwd)
```

### Generating keys

Generate temporary random material without printing or persisting it. Validate
each cipher's decoded length and reject an actual unsupported cipher.

```python
import base64
import os
import tempfile
from pathlib import Path

previous_cwd = Path.cwd()
with tempfile.TemporaryDirectory() as temporary:
    try:
        os.chdir(temporary)
        from orionis.environment.key.key_generator import SecureKeyGenerator
        from orionis.foundation.config.app.enums.ciphers import Cipher

        for cipher, expected_size in SecureKeyGenerator.KEY_SIZES.items():
            generated = SecureKeyGenerator.generate(cipher)
            assert generated.startswith("base64:")
            raw = base64.b64decode(generated[7:], validate=True)
            assert len(raw) == expected_size
        generated = SecureKeyGenerator.generate(Cipher.AES_256_CBC.value)
        assert len(base64.b64decode(generated[7:], validate=True)) == 32
        try:
            SecureKeyGenerator.generate("AES-512-CBC")
        except ValueError:
            pass
        else:
            raise AssertionError("Unsupported cipher must fail")
        assert not Path(".env").exists()
    finally:
        os.chdir(previous_cwd)
```

### Integrating with App configuration

Construct the **real** `App` entity. Environment-backed fields are read at entity
construction; changing the process environment does not update an existing
frozen entity. Explicit valid key bytes prevent unrelated key generation.

```python
import os
import tempfile
from pathlib import Path

previous_cwd = Path.cwd()
previous_environment = dict(os.environ)
with tempfile.TemporaryDirectory() as temporary:
    try:
        os.chdir(temporary)
        from orionis.environment import Env
        from orionis.foundation.config.app.entities.app import App
        from orionis.foundation.config.app.enums.ciphers import Cipher

        for key in (
            "APP_NAME", "APP_ENV", "APP_DEBUG", "APP_TIMEZONE", "APP_LOCALE",
            "APP_FALLBACK_LOCALE", "APP_LANGUAGE_PATH", "APP_MAINTENANCE",
        ):
            os.environ.pop(key, None)
        Env.set("APP_NAME", "Environment example", "str", only_os=True)
        Env.set("APP_DEBUG", False, "bool", only_os=True)
        settings = App(cipher=Cipher.AES_256_CBC, key=b"x" * 32)
        assert settings.name == "Environment example"
        assert settings.debug is False
        assert settings.key == b"x" * 32
        Env.set("APP_NAME", "Second snapshot", "str", only_os=True)
        newer = App(cipher=Cipher.AES_256_CBC, key=b"x" * 32)
        assert newer.name == "Second snapshot"
        assert settings.name == "Environment example"
    finally:
        os.environ.clear()
        os.environ.update(previous_environment)
        os.chdir(previous_cwd)
```

### Custom file, reload and recovery

Combine custom first construction, interpolation, process-only overrides,
removed file keys, the inherited factory and recovery from invalid UTF-8. The
`RuntimeError` is an expected observed failure, not silently converted to `False`.

```python
import asyncio
import os
import tempfile
from pathlib import Path

previous_cwd = Path.cwd()
previous_environment = dict(os.environ)
with tempfile.TemporaryDirectory() as temporary:
    try:
        os.chdir(temporary)
        os.environ.pop("PYTHON_DOTENV_DISABLED", None)
        from orionis.environment import Env
        from orionis.environment.core.dot_env import DotEnv

        selected = Path("settings.env")
        selected.write_text(
            "DOC_ROOT=site\nDOC_URL=${DOC_ROOT}/api\nDOC_RETRIES=int:2\n"
            "DOC_LEGACY=retained\nDOC_BARE\n",
            encoding="utf-8",
        )
        manager = DotEnv(str(selected))
        assert DotEnv("ignored.env") is manager
        assert not Path("ignored.env").exists()
        assert not Path(".env").exists()
        assert Env.get("DOC_URL") == "site/api"
        assert Env.all()["DOC_BARE"] is None
        Env.set("DOC_RETRIES", 9, "int", only_os=True)
        assert Env.get("DOC_RETRIES") == 9
        assert Env.all()["DOC_RETRIES"] == 2
        selected.write_text("DOC_RETRIES=int:3\nDOC_BARE\n", encoding="utf-8")
        assert Env.reload() is True
        assert Env.get("DOC_RETRIES") == 3
        assert "DOC_LEGACY" not in Env.all()
        assert Env.get("DOC_LEGACY") == "retained"
        assert asyncio.run(DotEnv.__acall__()) is manager
        selected.write_bytes(b"DOC_BROKEN=\xff\xfe\n")
        try:
            Env.reload()
        except RuntimeError as failure:
            assert isinstance(failure.__cause__, UnicodeDecodeError)
        else:
            raise AssertionError("Invalid UTF-8 must fail the reload")
        selected.write_text("DOC_RETRIES=int:4\n", encoding="utf-8")
        assert Env.reload() is True
        assert Env.get("DOC_RETRIES") == 4
        assert Env.unset("DOC_LEGACY", only_os=True) is True
    finally:
        os.environ.clear()
        os.environ.update(previous_environment)
        os.chdir(previous_cwd)
```

## Design characteristics

- `Env` classmethods plus `env()` delegation -> no per-call container resolution;
    both use the same `DotEnv`. Source: [facade.py](../facade.py),
    [functions.py](../functions.py).
- `Singleton` metaclass -> per-class construction state, later arguments ignored;
    `reload` mutates the existing instance. Source:
    [singleton/meta.py](../../support/patterns/singleton/meta.py).
- `DotEnv.__slots__`, `EnvironmentCaster.__slots__` and empty slots on `Env`,
    `SecureKeyGenerator` and both ABCs -> these concrete instances have no instance
    dictionary. This is not a claim about the enum or the private callable class.
- Retained raw references and mutable caster hint -> a caster is reusable state,
    not an immutable codec result. Source: [caster.py](../dynamic/caster.py).
- Python literal parsing and explicit prefixes -> no JSON schema, recursively
    enforced element types or guarantee that arbitrary `repr()` is decodable.
    Source: `DotEnv.__parseValue` and caster `__parse*`/`__to*` helpers.
- Mutable `SecureKeyGenerator.KEY_SIZES` -> callers see a shared dictionary, not a
    frozen configuration snapshot. Source: [key_generator.py](../key/key_generator.py).

## Performance and concurrency

- `get()` reads process memory after initialization; decoding still creates
    objects and can parse literals on each call. `all()` materializes a new mapping
    and reparses every entry; work scales with entries and payload sizes. Source:
    [DotEnv.get, all and __parseValue](../core/dot_env.py).
- Initial construction and `reload` call both `load_dotenv` and `dotenv_values`:
    two synchronous file parses, with interpolation enabled by the dependency.
    Persistent set/unset rewrite the file; they are not in-place scalar updates.
- The primitive `parseTyped` branches do not construct `EnvironmentCaster`;
    this does **not** mean zero allocations. Complex values construct a caster
    and parse or convert their payload. Source: [parseTyped](../dynamic/caster.py).
- `ValidateKeyName` retains successful entries in an LRU of 512, keyed by call
    arguments. `_normalize_type_hint` retains 64 original hint arguments, not
    values or full environment reads; case variants occupy distinct entries.
    Both use standard LRU eviction and expose only the cache controls described
    in their respective API sections. There is no cache of decoded reads.
- `DotEnv._lock` serializes its construction and five public operations within
    this process. The singleton factory has a separate per-class lock. Neither
    coordinates direct `os.environ` mutations, external file edits or other
    processes. These mechanisms do not establish global thread safety or a
    transaction spanning process/cache/file views.
- Installed `python-dotenv` 1.2.4 `dotenv.main.rewrite` writes a uniquely named
    temporary file in the destination directory and uses `os.replace`. It cleans
    up failed temporaries but performs no cross-process read-modify-write lock or
    fsync durability step. Windows replacement `PermissionError` can propagate.
    These are dependency-version observations, not a guarantee for every allowed
    future dependency version; the module simply calls `set_key`/`unset_key`.
- No `async def` is defined in the module. Calls can block an event loop on
    `threading.Lock` and file I/O. The inherited `Singleton.__acall__` factory is
    awaitable but has synchronous construction; it does not offload I/O.

Evidence: [dot_env.py](../core/dot_env.py), [caster.py](../dynamic/caster.py),
[key_name.py](../validators/key_name.py), [types.py](../validators/types.py) and
[Singleton](../../support/patterns/singleton/meta.py). Dependency functions were
inspected in installed `python-dotenv` 1.2.4; its declared range and lockfile are
listed below. No benchmarks were run.

> ⚠️ Not specified in source code: a concurrency contract for sharing one mutable
> `EnvironmentCaster` instance or mutating `SecureKeyGenerator.KEY_SIZES` while
> using it. Neither operation is synchronized by these classes.

## Compatibility notes

| Aspect | Verified evidence |
| --- | --- |
| Declared framework minimum | `requires-python = ">=3.14"` in [pyproject.toml](../../../pyproject.toml). |
| Observed syntax | Builtin generic annotations and `X | Y` unions; several files use postponed annotations, but the enum and initializers do not. This alone does not establish framework support for older Python. |
| Validation interpreter | CPython 3.14.6, Windows, repository virtual environment. |
| Mandatory dependency | `python-dotenv>=1.2.3,<2.0` in [pyproject.toml](../../../pyproject.toml); no module-specific extra or installation step. |
| Resolved dependency | `python-dotenv` 1.2.4 in [uv.lock](../../../uv.lock); installed validation version also 1.2.4. This is not a minimum-version declaration. |
| Standard library | `os`, `ast`, `pathlib`, `threading`, `functools`, `re`, `base64`, `enum`, `abc` and `typing`, as imported by the listed sources. |
| Direct Orionis dependencies | [Singleton](../../support/patterns/singleton/meta.py) and [Cipher](../../foundation/config/app/enums/ciphers.py). |

The dependency defaults used by this implementation are UTF-8 encoding,
`interpolate=True` and, for `set_key`, `quote_mode="always"`. Values are
single-quoted on persistence; `${OTHER}` interpolation occurs when loading,
including values written by `set`. The immediate cached/process serialized
value can therefore differ from the value after a reload. Invalid lines and
missing-key removals can emit dependency logger warnings; a malformed line
is not guaranteed to raise an Orionis exception.

`PYTHON_DOTENV_DISABLED` can suppress the dependency's process load while
`dotenv_values` still builds the cache; Orionis does not check the loader's
boolean result. This behavior was inspected in `dotenv.main.load_dotenv` 1.2.4.
Explicit paths and `path` conversion follow the host's `pathlib` semantics;
POSIX separators do not imply a POSIX filesystem or cross-platform path validity.
No file sandbox, traversal validation or universal home expansion is provided.

## Verification and limitations

### Coverage and source fidelity

The inventory covers 17 module Python files and ten primary public symbols:
`Env`, `env`, `DotEnv`, `EnvironmentCaster`, `EnvironmentValueType`,
`ValidateKeyName`, `ValidateTypes`, `SecureKeyGenerator`, `IEnv` and
`IEnvironmentCaster`. Their explicit methods/constructors, ten enum members,
two class constants, two callable bindings and reexports are included. There
are 48 source reference entries plus the inherited singleton factory. Private
symbols and imported dependencies are excluded for the reasons given in
[Module structure](#module-structure), not mistaken for missing public coverage.

Source inspection took precedence over existing documentation and docstrings.
Notable differences are the permissive unhinted writer, frozen-set return type,
constructor prefix guard, nonuniform boolean parsing and concrete set/unset
success values. Import-time `.env`/`APP_KEY` creation and unconditionally
non-atomic dependency rewrites described by older documentation do not match
the current inspected implementation.

### Executable checks

In a write-protected repository validation, the runtime probes passed for local
imports, first custom-file construction, process/cache divergence, unchanged
default identity, retained removed process keys, hint normalization, boolean and
empty-string parser differences, hinted/unhinted `None`, Base64 restrictions,
caster state mutation, path ordering, cache bounds, slots and UTF-8 reload errors.

The existing [tests/environment](../../../tests/environment) suite ran through
the native `Application.boot -> TestingEngine.run -> TestRunner.run` path using
11 byte-identical test-file copies outside the checkout: **210 passed, zero
failures, zero errors, zero skips**. Raw runner failures/errors were checked,
not just rendered summary text. Bytecode, application files, test fixtures and
reports were kept outside the repository; no dependencies were installed.

| Example | Syntax | Local imports | Execution status |
| --- | --- | --- | --- |
| Reading and persisting values | Passed | Local source verified | Executed successfully |
| Storing typed values | Passed | Local source verified | Executed successfully |
| Handling real validation errors | Passed | Local source verified | Executed successfully |
| Using the caster directly | Passed | Local source verified | Executed successfully |
| Generating keys | Passed | Local source verified | Executed successfully |
| Integrating with App configuration | Passed | Local source verified | Executed successfully |
| Custom file, reload and recovery | Passed | Local source verified | Executed successfully |

All seven scripts were extracted verbatim from this README, compiled separately
and run in individual subprocesses with write barriers for the checkout and
external connections disabled. Loaded Orionis modules resolved to the local
source, each script exited with code 0 and every assertion completed; stdout and
stderr were empty. No environment key or generated key material was printed.
The 48 reference entries matched the inventory. All 106 links in each README
and all 18 skill references resolved, including their internal anchors. The
README pair has 48 equivalent headings and 47 identical code blocks. The skill
frontmatter parsed as valid YAML with exactly `name` and `description`, and its
name was verified as `orionis-environment`. The output directory contains exactly
the two README files and the skill, without subdirectories or validation artifacts.

### Boundaries of verification

Validation used CPython 3.14.6 and `python-dotenv` 1.2.4. Other allowed dependency
versions, other operating systems and free-threaded interpreters were not
executed. The inspected locks describe coordination, not an executed
multi-thread or multi-process stress certification. No benchmark, external
service or real credential was used. The module has no custom exception class;
propagated dependency, builtin and user-object failures are not exhaustively
enumerated.

> ⚠️ Not executed in this environment: concurrent writers in multiple processes,
> power-loss durability and validation on platforms or dependency versions other
> than those recorded above. No results or guarantees are inferred for them.

[SKILL.md](SKILL.md) is a local documentation entry point named `orionis-environment`;
its placement here does not install or automatically register it as a skill.

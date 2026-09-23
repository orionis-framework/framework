# Orionis Hashing (`orionis.hashing`)

> Password hashing service with pluggable drivers (Argon2id and bcrypt) that
> burns its cost on a worker thread, exposed through the `IHashManager`
> contract and the `Hash` facade.
>
> 🇪🇸 Versión en español: [README.es.md](README.es.md)

## Table of contents

- [Functional description](#functional-description)
  - [Where it fits](#where-it-fits)
  - [Module map](#module-map)
  - [Configuration](#configuration)
  - [Design notes](#design-notes)
- [API reference](#api-reference)
  - [`IHasher`](#ihasher)
  - [`IHashManager`](#ihashmanager)
  - [`HashManager`](#hashmanager)
    - [`HashManager.__init__()`](#hashmanager__init__)
    - [`HashManager.driver()`](#hashmanagerdriver)
    - [`HashManager.getDefaultDriver()`](#hashmanagergetdefaultdriver)
    - [`HashManager.make()`](#hashmanagermake)
    - [`HashManager.check()`](#hashmanagercheck)
    - [`HashManager.needsRehash()`](#hashmanagerneedsrehash)
    - [`HashManager.getAlgorithm()`](#hashmanagergetalgorithm)
    - [`HashManager.setRounds()`](#hashmanagersetrounds)
    - [`HashManager._build()`](#hashmanager_build)
  - [`Argon2Hasher`](#argon2hasher)
    - [Argon2 module constants](#argon2-module-constants)
    - [`Argon2Hasher.__init__()`](#argon2hasher__init__)
    - [`Argon2Hasher.make()`](#argon2hashermake)
    - [`Argon2Hasher.check()`](#argon2hashercheck)
    - [`Argon2Hasher.needsRehash()`](#argon2hasherneedsrehash)
    - [`Argon2Hasher.getAlgorithm()`](#argon2hashergetalgorithm)
    - [Argon2 fluent setters](#argon2-fluent-setters)
    - [Argon2 internal helpers](#argon2-internal-helpers)
  - [`BcryptHasher`](#bcrypthasher)
    - [bcrypt module constants](#bcrypt-module-constants)
    - [`BcryptHasher.__init__()`](#bcrypthasher__init__)
    - [`BcryptHasher.make()`](#bcrypthashermake)
    - [`BcryptHasher.check()`](#bcrypthashercheck)
    - [`BcryptHasher.needsRehash()`](#bcrypthasherneedsrehash)
    - [`BcryptHasher.getAlgorithm()`](#bcrypthashergetalgorithm)
    - [`BcryptHasher.setRounds()`](#bcrypthashersetrounds)
    - [bcrypt internal helpers](#bcrypt-internal-helpers)
  - [`import_hasher_backend()`](#import_hasher_backend)
  - [Exceptions](#exceptions)
  - [`HashProvider`](#hashprovider)
  - [`Hash` facade](#hash-facade)
- [Usage examples](#usage-examples)
  - [Hashing and verifying a password](#hashing-and-verifying-a-password)
  - [Selecting a driver and tuning the cost](#selecting-a-driver-and-tuning-the-cost)
  - [Handling errors](#handling-errors)
  - [Upgrading a legacy hash](#upgrading-a-legacy-hash)
  - [Resolving the service and the facade](#resolving-the-service-and-the-facade)
- [Performance and concurrency considerations](#performance-and-concurrency-considerations)
- [Compatibility notes](#compatibility-notes)

## Functional description

`orionis.hashing` stores and verifies passwords. `HashManager` reads the
`hashing` configuration section, resolves the configured driver — `Argon2Hasher`
(Argon2id) or `BcryptHasher` — and exposes the same five operations as a single
driver, so application code never names an algorithm. The encoded hash carries
its own algorithm, parameters and salt, which is what makes `check()` and
`needsRehash()` work across configuration changes.

### Where it fits

| Component | Relationship |
|---|---|
| `orionis.foundation.contracts.application.IApplication` | Read once in `HashManager.__init__` through `app.config("hashing")`. |
| `orionis.foundation.config.hashing.entities.hashing.Hashing` | Configuration entity the manager builds from the raw section. |
| `orionis.foundation.config.hashing.enums.drivers.Drivers` | Driver catalogue (`argon2`, `bcrypt`) matched by `HashManager._build`. |
| `orionis.foundation.core_config.CORE_CONFIG` | Ships the `hashing` section, so the manager always finds its configuration. |
| `orionis.foundation.core_providers.CORE_PROVIDERS` | Contains `HashProvider`, so `IHashManager` is bound at application startup. |
| `orionis.container.providers.service_provider.ServiceProvider` | Base class of `HashProvider`. |
| `orionis.support.facades.hash.Hash` | Facade whose accessor is `IHashManager`; pinned by `HashProvider.boot()`. |
| `pwdlib` | Third-party backend providing the actual Argon2id and bcrypt primitives. |

### Module map

| File | Contents |
|---|---|
| `orionis/hashing/__init__.py` | Exports `Argon2Hasher`, `BcryptHasher` and `HashManager`. |
| `orionis/hashing/hash_manager.py` | `HashManager`, the algorithm-agnostic entry point. |
| `orionis/hashing/exceptions.py` | `HashException` and its three specialised subclasses. |
| `orionis/hashing/provider.py` | `HashProvider`. |
| `orionis/hashing/contracts/__init__.py` | Exports `IHashManager` and `IHasher`. |
| `orionis/hashing/contracts/hasher.py` | `IHasher` abstract contract. |
| `orionis/hashing/contracts/hash_manager.py` | `IHashManager`, which extends `IHasher`. |
| `orionis/hashing/hashers/__init__.py` | Exports `Argon2Hasher` and `BcryptHasher`. |
| `orionis/hashing/hashers/argon2_hasher.py` | Argon2id driver and its default cost constants. |
| `orionis/hashing/hashers/bcrypt_hasher.py` | bcrypt driver and its cost bounds. |
| `orionis/hashing/hashers/functions.py` | `import_hasher_backend`, the lazy backend importer. |

### Configuration

`HashManager` reads a single section. With the configuration shipped in this
repository, `app.config("hashing")` returns:

```python
{
    "driver": "argon2",
    "argon2": {"memory": 65536, "threads": 4, "time": 3},
    "bcrypt": {"rounds": 12},
}
```

| Key | Environment variable | Default | Validation |
|---|---|---|---|
| `hashing.driver` | `HASH_DRIVER` | `"argon2"` | Must be a `Drivers` member or one of `"argon2"` / `"bcrypt"`. |
| `hashing.argon2.memory` | `ARGON_MEMORY` | `65536` | Integer ≥ 1 (kibibytes). |
| `hashing.argon2.threads` | `ARGON_THREADS` | `4` | Integer ≥ 1 (lanes). |
| `hashing.argon2.time` | `ARGON_TIME` | `3` | Integer ≥ 1 (iterations). |
| `hashing.bcrypt.rounds` | `BCRYPT_ROUNDS` | `12` | Integer between `4` and `31`. |

The entity validation lives in `orionis/foundation/config/hashing/entities/`
and raises `TypeError` / `ValueError`; the drivers validate the same ranges
again and raise `HashConfigurationException`.

When the application exposes no `hashing` section — `config()` resolves an
unknown key to `None` — the manager falls back to the defaults declared by the
`Hashing` entity.

### Design notes

- `HashManager` declares `__slots__ = ("_config", "_default", "_drivers")`, and
  both `IHasher` and `IHashManager` declare `__slots__ = ()`, so the manager and
  the drivers carry no attribute dictionary.
- `IHashManager` **extends** `IHasher` instead of duplicating it, so the manager
  can stand in wherever a single driver is expected.
- Drivers are created lazily and cached in `_drivers`, keyed by driver name, so
  each algorithm is instantiated at most once per manager.
- The backend package is imported on first use through `import_hasher_backend`,
  so both drivers stay constructible even if the optional dependency is absent;
  the failure surfaces only when the driver is actually used.
- Each driver caches one backend instance built from its configured costs and
  drops it whenever a fluent setter changes a cost; per-call overrides build a
  throwaway backend and never touch the cached one.
- `HashProvider` binds `IHashManager` as a **singleton**, so a whole application
  shares one manager and therefore one backend per algorithm.
- `HashProvider` is a plain `ServiceProvider`, not a deferred one, so its
  `boot()` runs at application startup and the `Hash` facade is pinned before
  any request is served. The members that stay synchronous — `needsRehash()`,
  `getAlgorithm()`, `setRounds()` and `driver()` — depend on that.
- `make()` and `check()` are the only costly operations, and both run their
  blocking work through `asyncio.to_thread`, so a login never stalls the other
  requests served by the same worker.

## API reference

### `IHasher`

Location: `orionis/hashing/contracts/hasher.py`. Also re-exported from
`orionis.hashing.contracts`.

```python
class IHasher(ABC):

    __slots__ = ()

    @abstractmethod
    async def make(
        self,
        value: str,
        *,
        rounds: int | None = None,
        memory: int | None = None,
        threads: int | None = None,
    ) -> str: ...

    @abstractmethod
    async def check(self, value: str, hashed: str) -> bool: ...

    @abstractmethod
    def needsRehash(self, hashed: str) -> bool: ...

    @abstractmethod
    def getAlgorithm(self) -> str: ...

    @abstractmethod
    def setRounds(self, rounds: int) -> Self: ...
```

Abstract members: `make`, `check`, `needsRehash`, `getAlgorithm` and
`setRounds`. All five are declared without a body, so a subclass that does not
implement them cannot be instantiated. `make` and `check` are **coroutine
functions**: they carry the cost of the algorithm and must be awaited. The
docstring states that implementations must rely on algorithms designed for
password storage and never on general purpose digests such as MD5 or the SHA
family.

`__slots__ = ()` means subclasses declaring their own `__slots__` stay free of a
per-instance `__dict__`.

### `IHashManager`

Location: `orionis/hashing/contracts/hash_manager.py`. Also re-exported from
`orionis.hashing.contracts`.

```python
class IHashManager(IHasher):

    __slots__ = ()

    @abstractmethod
    def driver(self, name: str | None = None) -> IHasher: ...

    @abstractmethod
    def getDefaultDriver(self) -> str: ...
```

Adds exactly two abstract members to the five inherited from `IHasher`. This is
the contract used as the container key and as the `Hash` facade accessor.

### `HashManager`

Location: `orionis/hashing/hash_manager.py`. The only implementation of
`IHashManager` shipped by the framework.

```python
class HashManager(IHashManager):

    __slots__ = ("_config", "_default", "_drivers")
```

Instance attributes, all assigned in `__init__`:

| Attribute | Type | Meaning |
|---|---|---|
| `_config` | `Hashing` | Configuration entity, built from the raw section when it is a `dict`. |
| `_default` | `str` | Name of the configured default driver. |
| `_drivers` | `dict[str, IHasher]` | Cache of already built drivers, keyed by name. |

#### `HashManager.__init__()`

```python
def __init__(self, app: IApplication) -> None:
```

| Parameter | Type | Description |
|---|---|---|
| `app` | `IApplication` | Object providing configuration access. Only `app.config("hashing")` is read; there is no `isinstance` check, so any object exposing `config(path)` works. |

**Returns:** `None`.

**Behaviour:** when the section is a `dict` it is expanded into a `Hashing`
entity (`Hashing(**config_data)`); any other value is stored as is, which is
what makes an already built entity acceptable. A missing section — `None` — is
replaced by an empty mapping, so the manager falls back to the entity defaults
instead of failing on the first operation. `_default` is
`str(self._config.driver)`.

**Side effects:** none beyond reading the configuration. No driver is built
here, no container registration happens, and the configuration is read only
once — later changes to the application configuration are not observed.

#### `HashManager.driver()`

```python
def driver(self, name: str | None = None) -> IHasher:
```

| Parameter | Type | Description |
|---|---|---|
| `name` | `str \| None` | Driver name (`'argon2'` or `'bcrypt'`). `None` selects the configured default driver. |

**Returns:** `IHasher` — the driver instance, created on first access and cached
afterwards.

**Raises:** `HashDriverNotSupportedException` when the requested driver has no
implementation.

**Behaviour:** the resolution is `name or self._default`, so any falsy value —
`None` and the empty string alike — selects the default driver. Repeated calls
with the same resolved name return the very same instance.

#### `HashManager.getDefaultDriver()`

```python
def getDefaultDriver(self) -> str:
```

**Returns:** `str` — the configured driver name, such as `'argon2'` or
`'bcrypt'`. This is the configuration value, not the algorithm identifier
returned by `getAlgorithm()`.

#### `HashManager.make()`

```python
async def make(
    self,
    value: str,
    *,
    rounds: int | None = None,
    memory: int | None = None,
    threads: int | None = None,
) -> str:
```

| Parameter | Type | Description |
|---|---|---|
| `value` | `str` | Plain text value to hash. |
| `rounds` | `int \| None` | Per-call cost override. |
| `memory` | `int \| None` | Per-call memory cost override, in kibibytes. |
| `threads` | `int \| None` | Per-call parallelism override. |

**Returns:** `str` — the encoded hash produced by the default driver. The call
must be awaited.

**Raises:** whatever the resolved driver raises, in particular
`HashConfigurationException` for an invalid override.

**Behaviour:** driver resolution happens synchronously before the first
suspension, then the call delegates to `self.driver()`, so the overrides are
interpreted by the active driver (see
[`Argon2Hasher.make()`](#argon2hashermake) and
[`BcryptHasher.make()`](#bcrypthashermake)).

#### `HashManager.check()`

```python
async def check(self, value: str, hashed: str) -> bool:
```

| Parameter | Type | Description |
|---|---|---|
| `value` | `str` | Plain text value to verify. |
| `hashed` | `str` | Previously generated hash. |

**Returns:** `bool` — `True` when the value matches the hash, `False` otherwise.
A hash produced by a different algorithm, a malformed hash and an empty string
all return `False` instead of raising.

#### `HashManager.needsRehash()`

```python
def needsRehash(self, hashed: str) -> bool:
```

| Parameter | Type | Description |
|---|---|---|
| `hashed` | `str` | Previously generated hash. |

**Returns:** `bool` — `True` when the hash should be regenerated with the
current configuration. A hash from another algorithm always returns `True`,
which is how a migration between drivers is detected.

#### `HashManager.getAlgorithm()`

```python
def getAlgorithm(self) -> str:
```

**Returns:** `str` — the algorithm identifier of the default driver:
`'argon2id'` or `'bcrypt'`.

#### `HashManager.setRounds()`

```python
def setRounds(self, rounds: int) -> Self:
```

| Parameter | Type | Description |
|---|---|---|
| `rounds` | `int` | New cost factor for the default driver. |

**Returns:** `Self` — the same manager instance, allowing fluent configuration.

**Raises:** `HashConfigurationException` when the value is not valid for the
active driver.

**Side effects:** mutates the cached default driver, so every later call of the
manager — and of any code holding that driver — uses the new cost. Hashes
produced before the change remain verifiable and start reporting
`needsRehash() == True`.

#### `HashManager._build()`

```python
def _build(self, name: str) -> IHasher:
```

Internal factory called by `driver()` on a cache miss. Matches `name` against
`Drivers.ARGON2.value` and `Drivers.BCRYPT.value`, forwarding the configured
cost parameters (`memory`, `threads`, `time` for Argon2id; `rounds` for bcrypt).
Any other name raises `HashDriverNotSupportedException` with the message
`Unsupported hashing driver: '<name>'. Must be one of ['argon2', 'bcrypt'].`

### `Argon2Hasher`

Location: `orionis/hashing/hashers/argon2_hasher.py`. Default driver of the
framework; hashes with Argon2id.

```python
class Argon2Hasher(IHasher):

    __slots__ = ("_backend", "_backend_class", "_memory", "_threads", "_time")
```

| Attribute | Type | Meaning |
|---|---|---|
| `_memory` | `int` | Configured memory cost, in kibibytes. |
| `_threads` | `int` | Configured degree of parallelism. |
| `_time` | `int` | Configured number of iterations. |
| `_backend_class` | `Any` | Backend class, `None` until the first use. |
| `_backend` | `Any` | Backend instance for the configured costs, `None` until the first use. |

#### Argon2 module constants

| Name | Value | Used for |
|---|---|---|
| `DEFAULT_MEMORY` | `65536` | Default memory cost, in kibibytes. |
| `DEFAULT_THREADS` | `4` | Default degree of parallelism. |
| `DEFAULT_TIME` | `3` | Default number of iterations. |
| `_BACKEND_MODULE` | `"pwdlib.hashers.argon2"` | Module imported on first use. |
| `_BACKEND_CLASS` | `"Argon2Hasher"` | Backend class read from that module. |
| `_BACKEND_PACKAGE` | `"pwdlib[argon2]"` | Distribution reported when the import fails. |

#### `Argon2Hasher.__init__()`

```python
def __init__(
    self,
    *,
    memory: int = DEFAULT_MEMORY,
    threads: int = DEFAULT_THREADS,
    time: int = DEFAULT_TIME,
) -> None:
```

| Parameter | Type | Description |
|---|---|---|
| `memory` | `int` | Memory cost in kibibytes. |
| `threads` | `int` | Degree of parallelism. |
| `time` | `int` | Number of iterations. |

**Returns:** `None`.

**Raises:** `HashConfigurationException` when a cost parameter is not an integer
greater than zero. Booleans are rejected explicitly, even though `bool` is a
subclass of `int`. The message names the offending option and its value, for
example `The Argon2 'memory' option must be an integer greater than zero,
got 0.`

**Side effects:** none. The backend is neither imported nor built here.

#### `Argon2Hasher.make()`

```python
async def make(
    self,
    value: str,
    *,
    rounds: int | None = None,
    memory: int | None = None,
    threads: int | None = None,
) -> str:
```

| Parameter | Type | Description |
|---|---|---|
| `value` | `str` | Plain text value to hash. |
| `rounds` | `int \| None` | Per-call **time cost** override. |
| `memory` | `int \| None` | Per-call memory cost override, in kibibytes. |
| `threads` | `int \| None` | Per-call parallelism override. |

**Returns:** `str` — an encoded Argon2id hash such as
`$argon2id$v=19$m=32,t=1,p=1$<salt>$<digest>`. A fresh random salt is generated
on every call, so two hashes of the same value never match.

**Raises:** `HashConfigurationException` when an override is not a positive
integer. Errors raised by the backend propagate unchanged; for instance
Argon2 requires `memory >= 8 * threads` and otherwise raises
`argon2.exceptions.HashingError: Memory cost is too small`.

**Behaviour:** the whole derivation runs in `asyncio.to_thread(self._make, ...)`,
so validation errors and backend errors surface when the call is awaited. With
no override the cached backend is reused; with any override a throwaway backend
is built for that call and the cached one is left untouched.

#### `Argon2Hasher.check()`

```python
async def check(self, value: str, hashed: str) -> bool:
```

**Returns:** `bool`. The verification runs in
`asyncio.to_thread(self._check, ...)`. It answers `False` immediately when
`hashed` is empty or when the backend does not identify it as an Argon2 hash;
otherwise it delegates to the backend, which returns `False` for a mismatch
instead of raising. The costs encoded in the hash are the ones used for
verification, so a hash produced with another configuration still verifies.

#### `Argon2Hasher.needsRehash()`

```python
def needsRehash(self, hashed: str) -> bool:
```

**Returns:** `bool`. Returns `True` when `hashed` is empty or is not an Argon2
hash; otherwise it asks the backend whether the encoded parameters differ from
the configured ones.

#### `Argon2Hasher.getAlgorithm()`

```python
def getAlgorithm(self) -> str:
```

**Returns:** `str` — always `'argon2id'`.

#### Argon2 fluent setters

```python
def setRounds(self, rounds: int) -> Self:

def setMemory(self, memory: int) -> Self:

def setThreads(self, threads: int) -> Self:
```

`setRounds` sets the **time cost**, mirroring the vocabulary of the shared
contract. All three validate their argument with the same rule as `__init__`,
raise `HashConfigurationException` on failure, drop the cached backend so the
new cost takes effect, and return the same instance.

#### Argon2 internal helpers

| Method | Purpose |
|---|---|
| `_validate(name, value)` | `staticmethod` enforcing "integer greater than zero", rejecting `bool`. |
| `_backendClass()` | Imports the backend class on first use through `import_hasher_backend` and caches it. |
| `_build(memory, threads, time)` | Builds a backend instance with `time_cost`, `memory_cost` and `parallelism`. |
| `_default()` | Returns the backend built from the configured costs, creating it on first use. |
| `_make(value, *, rounds, memory, threads)` | Blocking hashing body that `make()` runs on a worker thread. |
| `_check(value, hashed)` | Blocking verification body that `check()` runs on a worker thread. |
| `_identify(hashed)` | Asks the backend class whether the hash belongs to the Argon2 family. |

### `BcryptHasher`

Location: `orionis/hashing/hashers/bcrypt_hasher.py`. Kept for interoperability
with applications that already store bcrypt hashes.

```python
class BcryptHasher(IHasher):

    __slots__ = ("_backend", "_backend_class", "_rounds")
```

| Attribute | Type | Meaning |
|---|---|---|
| `_rounds` | `int` | Configured cost factor. |
| `_backend_class` | `Any` | Backend class, `None` until the first use. |
| `_backend` | `Any` | Backend instance for the configured cost, `None` until the first use. |

#### bcrypt module constants

| Name | Value | Used for |
|---|---|---|
| `MIN_ROUNDS` | `4` | Lower bound imposed by bcrypt. |
| `MAX_ROUNDS` | `31` | Upper bound imposed by bcrypt. |
| `DEFAULT_ROUNDS` | `12` | Default cost factor. |
| `_BACKEND_MODULE` | `"pwdlib.hashers.bcrypt"` | Module imported on first use. |
| `_BACKEND_CLASS` | `"BcryptHasher"` | Backend class read from that module. |
| `_BACKEND_PACKAGE` | `"pwdlib[bcrypt]"` | Distribution reported when the import fails. |

#### `BcryptHasher.__init__()`

```python
def __init__(self, *, rounds: int = DEFAULT_ROUNDS) -> None:
```

| Parameter | Type | Description |
|---|---|---|
| `rounds` | `int` | Cost factor, expressed as the base-2 logarithm of the iteration count. |

**Returns:** `None`.

**Raises:** `HashConfigurationException` when `rounds` is not an integer between
`MIN_ROUNDS` and `MAX_ROUNDS`. Booleans are rejected explicitly. The message
reports both bounds and the rejected value, for example `The bcrypt 'rounds'
option must be an integer between 4 and 31, got 99.`

**Side effects:** none. The backend is neither imported nor built here.

#### `BcryptHasher.make()`

```python
async def make(
    self,
    value: str,
    *,
    rounds: int | None = None,
    memory: int | None = None,
    threads: int | None = None,
) -> str:
```

| Parameter | Type | Description |
|---|---|---|
| `value` | `str` | Plain text value to hash. |
| `rounds` | `int \| None` | Per-call cost factor override. |
| `memory` | `int \| None` | Ignored, bcrypt has no memory cost parameter. |
| `threads` | `int \| None` | Ignored, bcrypt has no parallelism parameter. |

**Returns:** `str` — a 60-character bcrypt hash such as `$2b$04$<salt+digest>`,
with a fresh random salt on every call.

**Raises:** `HashConfigurationException` when the override falls outside the
supported range. Errors raised by the backend propagate unchanged; the `bcrypt`
package rejects values longer than 72 bytes with `ValueError: password cannot be
longer than 72 bytes, truncate manually if necessary (e.g. my_password[:72])`.

**Behaviour:** the derivation runs in `asyncio.to_thread(self._make, ...)`. With
no override the cached backend is reused; with an override a throwaway backend
is built for that call.

#### `BcryptHasher.check()`

```python
async def check(self, value: str, hashed: str) -> bool:
```

**Returns:** `bool`. The verification runs in
`asyncio.to_thread(self._check, ...)`. It answers `False` immediately when
`hashed` is empty or when the backend does not identify it as a bcrypt hash;
otherwise it delegates to the backend. The cost encoded in the hash is the one
used for verification, so a hash produced with another cost still verifies.

#### `BcryptHasher.needsRehash()`

```python
def needsRehash(self, hashed: str) -> bool:
```

**Returns:** `bool`. Returns `True` when `hashed` is empty or when the backend
does not identify it as a bcrypt hash — an Argon2id hash included; otherwise it
asks the backend whether the encoded cost factor or prefix differ from the
configured ones.

#### `BcryptHasher.getAlgorithm()`

```python
def getAlgorithm(self) -> str:
```

**Returns:** `str` — always `'bcrypt'`.

#### `BcryptHasher.setRounds()`

```python
def setRounds(self, rounds: int) -> Self:
```

Validates the value with the same rule as `__init__`, raises
`HashConfigurationException` on failure, drops the cached backend so the new
cost takes effect, and returns the same instance.

#### bcrypt internal helpers

| Method | Purpose |
|---|---|
| `_validate(rounds)` | `staticmethod` enforcing the `MIN_ROUNDS`–`MAX_ROUNDS` range, rejecting `bool`. |
| `_backendClass()` | Imports the backend class on first use through `import_hasher_backend` and caches it. |
| `_build(rounds)` | Builds a backend instance with the given cost factor. |
| `_default()` | Returns the backend built from the configured cost, creating it on first use. |
| `_make(value, *, rounds, memory, threads)` | Blocking hashing body that `make()` runs on a worker thread. |
| `_check(value, hashed)` | Blocking verification body that `check()` runs on a worker thread. |
| `_identify(hashed)` | Asks the backend class whether the hash belongs to this driver. |

### `import_hasher_backend()`

Location: `orionis/hashing/hashers/functions.py`.

```python
def import_hasher_backend(module: str, attribute: str, package: str) -> Any:
```

| Parameter | Type | Description |
|---|---|---|
| `module` | `str` | Fully qualified module exposing the backend class. |
| `attribute` | `str` | Name of the backend class inside `module`. |
| `package` | `str` | Distribution name reported to the user when the import fails. |

**Returns:** `Any` — the backend class, ready to be instantiated. The class
itself is returned; nothing is instantiated here.

**Raises:** `MissingHashDependencyException` when `importlib.import_module`
raises `ImportError` or when the backend module raises
`pwdlib.exceptions.HasherNotAvailable` while being imported. The original error
is preserved as `__cause__` and the message reads `The '<package>' package is
required by this hashing driver. Install it with: pip install <package>`.

An `attribute` that does not exist in the imported module raises a plain
`AttributeError`, which is not translated.

### Exceptions

Location: `orionis/hashing/exceptions.py`.

```python
class HashException(Exception): ...

class HashConfigurationException(HashException): ...

class HashDriverNotSupportedException(HashException): ...

class MissingHashDependencyException(HashException): ...
```

| Exception | Raised when |
|---|---|
| `HashException` | Base class; never raised directly, but catches every failure of the module. |
| `HashConfigurationException` | A driver receives invalid cost parameters, either at construction, through a fluent setter, or as a per-call override. |
| `HashDriverNotSupportedException` | `HashManager._build` receives a driver name without an implementation. |
| `MissingHashDependencyException` | The backend package of a driver cannot be imported. |

### `HashProvider`

Location: `orionis/hashing/provider.py`.

```python
class HashProvider(ServiceProvider):

    def register(self) -> None:
        self.app.singleton(IHashManager, HashManager)

    async def boot(self) -> None:
        await HashFacade.pin()
```

`register()` performs a single binding: `IHashManager` → `HashManager`, as a
singleton. `boot()` is asynchronous and only pins the `Hash` facade; it
registers nothing.

`HashProvider` is listed in `orionis.foundation.core_providers.CORE_PROVIDERS`
and does **not** extend `DeferrableProvider`, so both phases run during
application startup.

### `Hash` facade

Location: `orionis/support/facades/hash.py`, re-exported from
`orionis.support.facades`.

```python
class Hash(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> type:
        return IHashManager
```

The facade resolves `IHashManager` from the container. `HashProvider.boot()`
pins it during application startup, so under the CLI or HTTP runtime
`Hash.needsRehash(...)`, `Hash.getAlgorithm(...)` and the rest of the
synchronous members are plain calls, while `await Hash.make(...)` and
`await Hash.check(...)` are awaited — which is what
`app/http/controllers/auth/register_controller.py` relies on. In a
bare script that only imports `bootstrap.app`, startup has not run, the facade is
still unpinned, and attribute access returns a `_FacadeDispatch` object that must
be awaited; awaiting it resolves the manager and calls the method, but it does
not pin the facade. The `orionis/support/facades/hash.pyi` stub exists only for
editor completion and is never executed.

## Usage examples

### Hashing and verifying a password

`HashManager` reads the `hashing` section straight from the container, so it can
be built without registering the provider.

```python
import asyncio

from bootstrap.app import app
from orionis.hashing.hash_manager import HashManager


async def main() -> None:
    hasher = HashManager(app)

    hashed = await hasher.make("s3cr3t-password")

    print("driver:", hasher.getDefaultDriver())
    print("algorithm:", hasher.getAlgorithm())
    print("stored prefix:", hashed.split("$")[1])
    print("verified:", await hasher.check("s3cr3t-password", hashed))
    print("wrong value:", await hasher.check("another-password", hashed))
    print("needs rehash:", hasher.needsRehash(hashed))


asyncio.run(main())
```

Output with the default configuration of this repository:

```text
driver: argon2
algorithm: argon2id
stored prefix: argon2id
verified: True
wrong value: False
needs rehash: False
```

### Selecting a driver and tuning the cost

`__init__` only calls `config(path)`, so any object exposing that method can
supply the section. Per-call overrides never modify the configured costs.

```python
import asyncio

from orionis.hashing.hash_manager import HashManager


class StaticConfig:
    """Any object exposing config(path) satisfies what HashManager reads."""

    def __init__(self, section: dict) -> None:
        self._section = section

    def config(self, path: str) -> object:
        return self._section


hasher = HashManager(
    StaticConfig(
        {
            "driver": "bcrypt",
            "argon2": {"memory": 32, "threads": 1, "time": 1},
            "bcrypt": {"rounds": 4},
        },
    ),
)

argon2 = hasher.driver("argon2")


async def main() -> None:
    print("default driver:", hasher.getDefaultDriver())
    print("bcrypt cost:", (await hasher.make("secret"))[:7])
    print("bcrypt override:", (await hasher.make("secret", rounds=5))[:7])
    print("argon2 costs:", (await argon2.make("secret")).split("$")[3])
    override = await argon2.make("secret", rounds=2, memory=64)
    print("argon2 override:", override.split("$")[3])
    print("driver is cached:", argon2 is hasher.driver("argon2"))
    print("configured cost is untouched:", (await hasher.make("secret"))[:7])


asyncio.run(main())
```

Output:

```text
default driver: bcrypt
bcrypt cost: $2b$04$
bcrypt override: $2b$05$
argon2 costs: m=32,t=1,p=1
argon2 override: m=64,t=2,p=1
driver is cached: True
configured cost is untouched: $2b$04$
```

### Handling errors

Configuration failures raise subclasses of `HashException`; verification never
raises.

```python
import asyncio

from orionis.hashing.exceptions import (
    HashConfigurationException,
    HashDriverNotSupportedException,
)
from orionis.hashing.hash_manager import HashManager
from orionis.hashing.hashers.argon2_hasher import Argon2Hasher
from orionis.hashing.hashers.bcrypt_hasher import BcryptHasher


class StaticConfig:
    """Any object exposing config(path) satisfies what HashManager reads."""

    def __init__(self, section: dict) -> None:
        self._section = section

    def config(self, path: str) -> object:
        return self._section


hasher = HashManager(
    StaticConfig(
        {
            "driver": "argon2",
            "argon2": {"memory": 32, "threads": 1, "time": 1},
            "bcrypt": {"rounds": 4},
        },
    ),
)


async def main() -> None:
    # 1. A driver without an implementation is rejected on resolution.
    try:
        hasher.driver("md5")
    except HashDriverNotSupportedException as exc:
        print("driver ->", exc)

    # 2. Cost parameters are validated when the driver is built.
    try:
        Argon2Hasher(memory=0)
    except HashConfigurationException as exc:
        print("argon2 cost ->", exc)

    try:
        BcryptHasher(rounds=99)
    except HashConfigurationException as exc:
        print("bcrypt cost ->", exc)

    # 3. A per-call override is validated before anything is hashed.
    try:
        await hasher.make("secret", rounds=0)
    except HashConfigurationException as exc:
        print("override ->", exc)

    # 4. Verifying never raises: a foreign or malformed hash simply fails.
    legacy = await BcryptHasher(rounds=4).make("secret")
    print("foreign hash verifies:", await hasher.check("secret", legacy))
    print("foreign hash needs rehash:", hasher.needsRehash(legacy))
    print("malformed hash verifies:", await hasher.check("secret", "not-a-hash"))
    print("empty hash verifies:", await hasher.check("secret", ""))


asyncio.run(main())
```

Output:

```text
driver -> Unsupported hashing driver: 'md5'. Must be one of ['argon2', 'bcrypt'].
argon2 cost -> The Argon2 'memory' option must be an integer greater than zero, got 0.
bcrypt cost -> The bcrypt 'rounds' option must be an integer between 4 and 31, got 99.
override -> The Argon2 'time' option must be an integer greater than zero, got 0.
foreign hash verifies: False
foreign hash needs rehash: True
malformed hash verifies: False
empty hash verifies: False
```

### Upgrading a legacy hash

`needsRehash()` reports `True` for a hash produced by another driver, and the
old driver stays reachable through `driver(name)` to verify the submitted value
before replacing the stored hash.

```python
import asyncio

from orionis.hashing.hash_manager import HashManager


class StaticConfig:
    """Any object exposing config(path) satisfies what HashManager reads."""

    def __init__(self, section: dict) -> None:
        self._section = section

    def config(self, path: str) -> object:
        return self._section


hasher = HashManager(
    StaticConfig(
        {
            "driver": "argon2",
            "argon2": {"memory": 32, "threads": 1, "time": 1},
            "bcrypt": {"rounds": 4},
        },
    ),
)


async def main() -> None:
    # A credential stored years ago by another application.
    stored = await hasher.driver("bcrypt").make("s3cr3t-password")
    submitted = "s3cr3t-password"

    print("stored algorithm:", stored[:4])
    print("needs rehash:", hasher.needsRehash(stored))

    if hasher.needsRehash(stored) and await hasher.driver("bcrypt").check(
        submitted, stored,
    ):
        stored = await hasher.make(submitted)

    print("upgraded algorithm:", stored.split("$")[1])
    print("needs rehash now:", hasher.needsRehash(stored))
    print("login still works:", await hasher.check(submitted, stored))


asyncio.run(main())
```

Output:

```text
stored algorithm: $2b$
needs rehash: True
upgraded algorithm: argon2id
needs rehash now: False
login still works: True
```

### Resolving the service and the facade

`HashProvider` is booted by the framework, so `IHashManager` is already bound and
the `Hash` facade is pinned once the CLI or HTTP runtime has started. The script
below runs outside that runtime, so the facade is still unpinned; either way
`make()` and `check()` are awaited.

```python
import asyncio

from bootstrap.app import app
from orionis.hashing.contracts.hash_manager import IHashManager
from orionis.support.facades.hash import Hash


async def main() -> None:
    service = await app.make(IHashManager)
    print("resolved:", type(service).__name__)
    print("singleton:", service is await app.make(IHashManager))
    print("facade pinned:", Hash._pinned_instance is not None)

    hashed = await Hash.make("through the facade", rounds=1, memory=8, threads=1)
    print("facade returns:", type(hashed).__name__)
    print("verified:", await Hash.check("through the facade", hashed))


asyncio.run(main())
```

Output:

```text
resolved: HashManager
singleton: True
facade pinned: False
facade returns: str
verified: True
```

## Performance and concurrency considerations

- `make()` and `check()` are **coroutines** that run their blocking body through
  `asyncio.to_thread`; every other member is synchronous and never awaits,
  touches the filesystem or the network, or calls into the container after
  construction.
- Password hashing is intentionally CPU and memory bound. With the default
  configuration of this repository, one Argon2id call performs 3 iterations over
  64 MiB (`memory=65536` kibibytes) using 4 lanes; the derivation blocks the
  worker thread it runs on for its whole duration, but the event loop stays free
  to serve other requests.
- Instances carry no `__dict__` (verified: `hasattr(hasher, "__dict__")` is
  `False`) because every class declares `__slots__` and both contracts declare
  `__slots__ = ()`.
- The backend module is imported on the first operation, not at construction:
  `_backend_class` and `_backend` are `None` until then.
- Each driver keeps one backend instance for its configured costs. Per-call
  overrides build a throwaway backend, so a call that overrides a cost is more
  expensive than one that does not.
- `HashManager` builds at most one driver per name and keeps it in `_drivers`;
  `HashProvider` binds the manager as a singleton, so an application ends up with
  one manager and one backend per algorithm.
- `check()` and `needsRehash()` read the parameters encoded in the hash, so their
  cost follows the stored hash, not the current configuration.
- Every `make()` call generates a fresh random salt through the backend, so
  hashing the same value twice never produces the same string.
- Concurrency is declared in the class docstrings of `HashManager`,
  `Argon2Hasher` and `BcryptHasher`: no locks and no `asyncio` synchronisation
  primitives are used. The mutable state is the driver cache of the manager and
  the backend cache of each driver, both written on first use; a concurrent
  first use from several threads may build the same object twice, and the last
  write wins. Every later operation only reads that state, and the state is read
  before the call suspends, so tasks sharing an event loop never observe a
  partially built cache. The fluent setters mutate the shared state on purpose,
  so the new cost is visible to every holder of the manager or the driver.

## Compatibility notes

- **Python:** the project declares `requires-python = ">=3.14"` in
  `pyproject.toml`. The module uses `X | None` and `Self` annotations evaluated
  lazily (PEP 649); `hash_manager.py` deliberately avoids
  `from __future__ import annotations` and carries `# ruff: noqa: TC001` so the
  container can reflect `HashManager.__init__` and inject `IApplication`. The
  contract files, which are never reflected, do use that future import.
- **Third-party dependency**, already a base requirement of the framework —
  nothing extra to install: `pwdlib[argon2,bcrypt]>=0.3.1`, which pulls
  `argon2-cffi` and `bcrypt`. If a driver's backend is missing, the failure is
  reported as `MissingHashDependencyException` on first use, not at import time.
- **Driver catalogue:** only `argon2` and `bcrypt` are accepted, and the names
  come from `orionis.foundation.config.hashing.enums.drivers.Drivers`. Adding a
  member to that enum does not add a driver: `HashManager._build` must know how
  to build it.
- **Argon2id limits:** the backend requires `memory >= 8 * threads`; the driver
  only validates that each cost is a positive integer, so the backend error
  (`argon2.exceptions.HashingError`) propagates unchanged.
- **bcrypt limits:** the cost factor is restricted to `4`–`31`, and the `bcrypt`
  package rejects passwords longer than 72 bytes with a `ValueError` that the
  driver does not translate.
- **Hash portability:** hashes are self-describing. A hash produced with other
  cost parameters — or by another Orionis application using the same algorithm —
  verifies correctly and is reported by `needsRehash()` when its parameters no
  longer match the configuration.
- **Container wiring:** `HashProvider` is part of `CORE_PROVIDERS`, so
  `IHashManager` is bound as a singleton and the `Hash` facade is pinned during
  application startup. Because the compiled bootstrap cache
  (`storage/framework/bootstrap`) is not invalidated by changes inside
  `orionis/`, an application that already cached its providers must clear that
  folder — or run `reactor optimize:clear` — to pick up this wiring.

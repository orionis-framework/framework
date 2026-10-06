# orionis.hashing

> `orionis.hashing` provides asynchronous password hashing with Argon2id and bcrypt, driver selection, verification, and cost-upgrade detection.

## Overview

The package exports `HashManager`, `Argon2Hasher`, and `BcryptHasher`. The manager reads validated application configuration, lazily caches the requested drivers, and delegates a common `IHasher` API. Orionis defaults to Argon2id; bcrypt remains available for existing password stores and explicit interoperability.

Hash creation and verification are CPU/memory intensive, so both drivers run blocking backend work through `asyncio.to_thread`. Encoded hashes include the salt, algorithm, and cost parameters needed for later verification. This module hashes passwords; it does not encrypt recoverable data.

## Requirements

- Python 3.14 or newer.
- `pwdlib[argon2,bcrypt]>=0.3.1`, installed by Orionis.
- Sufficient worker-thread capacity and memory for the configured cost.
- A booted Orionis container when using the `Hash` facade.

## Quick start

```python
import asyncio
from orionis.hashing import Argon2Hasher


async def main() -> None:
    hasher = Argon2Hasher(memory=32, threads=1, time=1)
    encoded = await hasher.make("correct horse")
    assert await hasher.check("correct horse", encoded)
    assert not await hasher.check("wrong", encoded)
    assert not hasher.needsRehash(encoded)
    print(hasher.getAlgorithm())


asyncio.run(main())
```

Validation: **Executed successfully** on CPython 3.14.6; low costs are used only to keep the documentation run fast.

## Core concepts

### One-way password storage

`make()` produces a salted encoded hash. `check()` sends a candidate and stored hash to the same algorithm; plaintext cannot be recovered. Store the encoded result as-is and never compare hashes directly, because a new random salt changes each result.

### Driver and algorithm

Configuration driver `argon2` reports algorithm `argon2id`; `bcrypt` reports `bcrypt`. `HashManager.make/check/needsRehash` always use the configured default. To verify a known legacy algorithm explicitly, select `manager.driver("bcrypt")`.

### Rehash policy

`needsRehash()` compares an encoded hash with the current driver's parameters. Empty, malformed, or foreign-algorithm hashes require rehash. After a successful login, generate and persist a replacement when this method returns `True`.

## Module structure

| Path | Responsibility |
|---|---|
| `hash_manager.py` | Configuration, lazy driver selection, common delegation. |
| `hashers/argon2_hasher.py` | Argon2id costs, async hashing, verification, rehash checks. |
| `hashers/bcrypt_hasher.py` | bcrypt cost factor, async hashing, verification, rehash checks. |
| `hashers/functions.py` | Lazy optional-backend import with installation guidance. |
| `contracts/` | `IHasher` and `IHashManager` interfaces. |
| `exceptions.py` | Configuration, driver, and dependency error hierarchy. |
| `provider.py` | Manager singleton binding and facade pinning. |

## Public API

### `HashManager(app)`

Reads `hashing`, falling back to the native `Hashing` entity when missing. `driver(name=None)` returns a cached `IHasher`; `getDefaultDriver()` returns `argon2` or `bcrypt`. Manager-level `make`, `check`, `needsRehash`, `getAlgorithm`, and `setRounds` delegate to the default driver.

### `Argon2Hasher(memory=65536, threads=4, time=3)`

Uses Argon2id. `memory` is KiB, `threads` is parallelism, and `time` is iteration cost. All must be positive integers; validated application config additionally requires at least 8 KiB per thread. Per-call `rounds` maps to `time`. `setMemory`, `setThreads`, and `setRounds` change defaults and clear the cached backend.

### `BcryptHasher(rounds=12)`

Accepts integer cost factors from 4 through 31 inclusive. `memory` and `threads` call overrides are ignored because bcrypt does not support them. `setRounds` changes the default and clears the cached backend.

### Shared methods

- `await make(value, *, rounds=None, memory=None, threads=None) -> str`
- `await check(value, hashed) -> bool`
- `needsRehash(hashed) -> bool`
- `getAlgorithm() -> str`
- `setRounds(rounds) -> Self`

## Common workflows

### Register a password

Call `await Hash.make(password)` and persist only the result. Do not log either input or hash. Application-level validation should apply password length/policy before hashing.

### Authenticate and upgrade

Call `await Hash.check(candidate, stored)`. Only after a successful match, call `Hash.needsRehash(stored)` and replace the stored hash with `await Hash.make(candidate)` when necessary.

### Migrate from bcrypt to Argon2id

Identify legacy records in application data, verify them with `await manager.driver("bcrypt").check(...)`, and rewrite a successful login through the default Argon2 manager. A default Argon2 checker deliberately returns `False` for a bcrypt hash.

## Examples

### Use bcrypt explicitly

```python
import asyncio
from orionis.hashing import BcryptHasher


async def main() -> None:
    hasher = BcryptHasher(rounds=4)
    encoded = await hasher.make("secret")
    assert await hasher.check("secret", encoded)
    assert not await hasher.check("other", encoded)
    print(hasher.getAlgorithm())


asyncio.run(main())
```

Validation: **Executed successfully** on CPython 3.14.6; cost 4 is for this fast example, not a production recommendation.

### Resolve drivers through the manager

```python
import asyncio
from orionis.hashing import HashManager


class App:
    def config(self, name: str):
        assert name == "hashing"
        return {
            "driver": "argon2",
            "argon2": {"memory": 32, "threads": 1, "time": 1},
            "bcrypt": {"rounds": 4},
        }


async def main() -> None:
    manager = HashManager(App())
    encoded = await manager.make("password")
    assert manager.getDefaultDriver() == "argon2"
    assert await manager.check("password", encoded)
    assert manager.driver("bcrypt").getAlgorithm() == "bcrypt"
    print(manager.getAlgorithm())


asyncio.run(main())
```

Validation: **Executed successfully** on CPython 3.14.6.

### Upgrade cost parameters

```python
import asyncio
from orionis.hashing import Argon2Hasher


async def main() -> None:
    old = Argon2Hasher(memory=32, threads=1, time=1)
    encoded = await old.make("secret")
    stronger = Argon2Hasher(memory=64, threads=1, time=2)
    assert stronger.needsRehash(encoded)
    replacement = await stronger.make("secret")
    assert await stronger.check("secret", replacement)
    print("rehash required")


asyncio.run(main())
```

Validation: **Executed successfully** on CPython 3.14.6.

### Use the application facade

```python
from orionis.support.facades import Hash

encoded = await Hash.make("secret")
valid = await Hash.check("secret", encoded)
if valid and Hash.needsRehash(encoded):
    encoded = await Hash.make("secret")
```

Validation: **Import-only** on CPython 3.14.6; calls require a booted application and pinned facade.

## Configuration

`config/hashing.py` maps environment values to frozen native entities:

| Setting | Environment | Default | Constraint |
|---|---|---:|---|
| `hashing.driver` | `HASH_DRIVER` | `argon2` | `argon2` or `bcrypt`. |
| `hashing.argon2.memory` | `ARGON_MEMORY` | `65536` KiB | Positive integer; at least `8 * threads`. |
| `hashing.argon2.threads` | `ARGON_THREADS` | `4` | Positive integer. |
| `hashing.argon2.time` | `ARGON_TIME` | `3` | Positive integer. |
| `hashing.bcrypt.rounds` | `BCRYPT_ROUNDS` | `12` | Integer from 4 through 31. |

Tune costs on production-class hardware and monitor latency/memory. Changing settings does not invalidate verification of old hashes; it makes `needsRehash` signal an upgrade.

## Integration with Orionis

`HashProvider` is a core provider. It binds `IHashManager` to `HashManager` as a singleton and pins `orionis.support.facades.Hash` during boot so both async and synchronous members resolve correctly.

Authentication, registration, password-reset, seeders, and user models can use the facade or inject `IHashManager`. Package-level concrete classes remain useful for migrations and focused tests.

## Errors and edge cases

- Invalid costs raise `HashConfigurationException`; config entities may raise `TypeError`/`ValueError` earlier during application creation.
- Unknown driver names raise `HashDriverNotSupportedException` when resolved.
- Missing backend modules become `MissingHashDependencyException` with a `uv add` hint.
- `check` returns `False` for empty, malformed, or foreign-algorithm hashes; `needsRehash` returns `True` for them.
- Per-call overrides create a temporary backend and do not mutate configured defaults.
- `setRounds` mutates the cached singleton driver application-wide; prefer configuration or per-call overrides unless global mutation is intentional.
- Backend input restrictions still apply, including bcrypt's practical password-size limitations.

## Performance and concurrency

Every `make` and `check` uses `asyncio.to_thread`, keeping the event loop responsive but consuming the loop's worker pool. Argon2 also consumes its configured memory and parallel lanes; cap concurrent login/registration work according to host capacity.

Managers cache driver objects, and drivers lazily cache backend classes/instances. No locks protect the first cache fill, so multiple native threads may construct equivalent instances and the last write wins safely. Event-loop tasks cannot observe a partial synchronous construction. Fluent setters mutate shared driver state and should not race with requests.

## Compatibility

Orionis declares Python 3.14+ and `pwdlib[argon2,bcrypt]>=0.3.1`. Validation used CPython 3.14.6 on Windows with both backends installed. Encoded formats are backend-standard Argon2 and bcrypt strings, but cost availability and very long bcrypt input behavior can vary with backend versions.

## Verification notes

Validation used CPython 3.14.6. Exports, contracts, manager, both hashers, lazy backend loading, errors, provider/facade, config entities, application integrations, and `tests/hashing` were inspected. All 180 hashing tests passed through the Orionis runner. Four direct password-hashing programs executed successfully; the facade example was import-validated only.

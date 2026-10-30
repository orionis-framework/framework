# Storing, verifying, and upgrading passwords

A password workflow consists of validation, hashing, storing the result, and verification on the next login. Cost policy and algorithm migration belong to the same workflow.

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

## Design registration and login

Validate password policy before calling `make()`, store the complete encoded result, and verify the next attempt with `check()`. Do not compare against a freshly generated hash: each execution uses a salt and changes the output. This service does not persist records, rate-limit attempts, or maintain sessions; those responsibilities belong to your authentication flow.

Upgrade only after successful verification. When a record is outdated, compute the replacement and persist it with the concurrency mechanism used by your user model. Never replace a hash after a failed attempt. During a bcrypt migration, explicitly select `driver("bcrypt")` when verifying legacy records; the default Argon2 driver does not automatically choose another algorithm.

Reduced costs in examples are exclusively for tests. Measure production latency and memory under real concurrency: the default Argon2 memory cost of `65536` KiB is approximately 64 MiB per operation, in addition to process and backend overhead. The executor prevents loop blocking but does not eliminate resource consumption. Bound concurrent login and account-creation work.

`HashManager` exposes no `extend()`. For a custom implementation, satisfy `IHasher` and, when replacing global selection, `IHashManager`, then register the service according to provider ordering. Do not mutate `_drivers` or depend on private hasher methods. Prefer configuration or per-call overrides; setters such as `setRounds()` affect the shared instance.

## Core concepts

### One-way password storage

`make()` produces a salted encoded hash. `check()` sends a candidate and stored hash to the same algorithm; plaintext cannot be recovered. Store the encoded result as-is and never compare hashes directly, because a new random salt changes each result.

### Driver and algorithm

Configuration driver `argon2` reports algorithm `argon2id`; `bcrypt` reports `bcrypt`. `HashManager.make/check/needsRehash` always use the configured default. To verify a known legacy algorithm explicitly, select `manager.driver("bcrypt")`.

### Rehash policy

`needsRehash()` compares an encoded hash with the current driver's parameters. Empty hashes and values not identified by the selected backend require rehash; backend errors can still propagate for other invalid encodings. After a successful login, generate and persist a replacement when this method returns `True`.

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


### Use the application facade

```python
from orionis.support.facades import Hash

async def verify_example() -> None:
    encoded = await Hash.make("secret")
    valid = await Hash.check("secret", encoded)
    if valid and Hash.needsRehash(encoded):
        encoded = await Hash.make("secret")
```

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
- `check` returns `False` for empty hashes and values the selected backend does not identify; `needsRehash` returns `True` for those values. Validation errors from a backend may propagate for an otherwise identified but invalid encoding.
- Per-call overrides create a temporary backend and do not mutate configured defaults.
- `setRounds` mutates the cached singleton driver application-wide; prefer configuration or per-call overrides unless global mutation is intentional.
- Backend input restrictions still apply, including bcrypt's practical password-size limitations.

## Performance and concurrency

Every `make` and `check` uses the dedicated bounded hashing executor (two active and 14 pending calls by default), keeping the event loop responsive without occupying its default worker pool. Overload raises `WorkQueueFullError`. Argon2 also consumes its configured memory and parallel lanes; size a custom executor according to host capacity.

Managers cache driver objects, and drivers lazily cache backend classes/instances. No locks protect the first cache fill, so multiple native threads may construct equivalent instances and the last write wins safely. Event-loop tasks cannot observe a partial synchronous construction. Fluent setters mutate shared driver state and should not race with requests.

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

## Implementation reference for extensions

| Path | Responsibility |
|---|---|
| `hash_manager.py` | Configuration, lazy driver selection, common delegation. |
| `hashers/argon2_hasher.py` | Argon2id costs, async hashing, verification, rehash checks. |
| `hashers/bcrypt_hasher.py` | bcrypt cost factor, async hashing, verification, rehash checks. |
| `hashers/functions.py` | Lazy optional-backend import with installation guidance. |
| `contracts/` | `IHasher` and `IHashManager` interfaces. |
| `exceptions.py` | Configuration, driver, and dependency error hierarchy. |
| `provider.py` | Manager singleton binding and facade pinning. |

---

[Index](README.md) · [auth](../../../auth/docs/en/README.md) · [encrypter](../../../encrypter/docs/en/README.md)

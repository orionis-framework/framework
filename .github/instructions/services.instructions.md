---
name: "Orionis Infrastructure Services"
description: "Use when working on Orionis infrastructure modules: cache manager, stores and locks, filesystem storage and cloud drivers, password hashing, AES encryption, logging channels and rotation, i18n translations, and environment variables with typed casting."
applyTo: "orionis/cache/**,orionis/storage/**,orionis/hashing/**,orionis/encrypter/**,orionis/logging/**,orionis/localization/**,orionis/environment/**"
---

# Infrastructure services

## Read the module docs first

Every module covered by this file ships a bilingual manual with exact signatures,
executed examples, concurrency guarantees and compatibility notes:

| Module | Manual |
|---|---|
| Cache | `orionis/cache/docs/README.md` (`.es.md`) |
| Storage | `orionis/storage/docs/README.md` (`.es.md`) |
| Hashing | `orionis/hashing/docs/README.md` (`.es.md`) |
| Encrypter | `orionis/encrypter/docs/README.md` (`.es.md`) |
| Logging | `orionis/logging/docs/README.md` (`.es.md`) |
| Localization | `orionis/localization/docs/README.md` (`.es.md`) |
| Environment | `orionis/environment/docs/README.md` (`.es.md`) |

**Read the relevant manual before writing code and before answering about an
API.** What follows are only the invariants that must not regress, plus traps the
docs do not enforce. If you change behaviour, update the manual in both languages.

## Cache

- `add()` and `increment()` **must stay atomic**: file uses exclusive creation
  (`open("xb")`) plus an `asyncio.Lock`; database uses INSERT-by-PK plus a
  25-attempt compare-and-swap. Never reintroduce check-then-act
  (`if exists(): set()`), it produced 10 winners out of 10 against PostgreSQL.
- `increment()` must preserve the entry TTL.
- Expiration lives in a **`Double`** column, not `BigInteger` — sub-second TTLs and
  lease times are a real, tested feature and PostgreSQL truncates floats stored in
  bigint. Changing the store definition also requires changing the real migration.
- An unknown store name silently falls back to `FileCacheBackend`;
  `CacheStoreException` is only for unconfigured redis/memcached/database.
- `CacheProvider` is **deferrable** → the `Cache` facade is not pinned at startup.
  Inject `ICacheManager` in anything built during boot.

## Storage

- The `Disks` entity has five fixed fields (`local`, `public`, `s3`, `azure`,
  `gcs`): **disk names are not extensible**, only the `driver` each one points to
  (that is the key used by `manager.extend(driver, factory)`).
- Cloud SDKs must stay **lazily imported** through `importDriverDependency` →
  `MissingStorageDependencyException` with an install hint, so constructors remain
  testable without the SDK.
- Always normalise paths with `normalizePath`/`normalizeFilePath`
  (`orionis/storage/paths.py`): they reject traversal, `:` and null bytes; `""` is
  the disk root.
- Local writes are atomic through a **uniquely named** temp file
  (`<file>.<token_hex(8)>.tmp`) with cleanup on `OSError`; `files()` filters `.tmp`.

## Hashing

- **The API is synchronous on purpose**, which is exactly why `HashProvider` is
  eager and not deferrable — a deferred provider would return `_FacadeDispatch` on
  the first synchronous `Hash.make(...)`.
- Backends are imported lazily and cached in `_backend`; the cache must be
  invalidated by `setRounds`/`setMemory`/`setThreads`.
- Both drivers call `identify()` first, so a foreign hash returns `False`/`True`
  instead of raising or even instantiating the backend.
- Backend limits: argon2 requires `memory_cost >= 8 * parallelism`; bcrypt accepts
  `rounds` 4..31 and passwords up to 72 bytes.

## Encrypter

- Every failure inside the actual decryption surfaces as **`RuntimeError`**; only
  the pre-checks (payload shape, IV size, cipher mismatch) raise `ValueError`.
  Do not document `EncryptionError`/`DecryptionError` — those classes do not exist.
- `EncrypterProvider` is eager and part of `CORE_PROVIDERS`; it must stay eager
  because `Stringable.encrypt()` is synchronous.

## Logging

- **One active channel at a time.** Initialisation is lazy: `getActiveChannels()`
  is `[]` until the first log.
- `switchChannel(name)` must call the "ensure initialised" helper **before** taking
  `__init_lock` — it is a plain `threading.Lock`, not reentrant.
- Iterate handlers with `self.__logger.handlers[:]` when removing them (mutating
  while iterating skips handlers; `list(...)` trips a SonarLint rule).
- Normalise the channel config **once** and reuse it for `setLevel`: an enum or a
  lowercase level string blows up `logging._checkLevel`.

## Localization

- Locale validation (anti-traversal regex) lives **only** in `Translator` (the
  boundary); loader and repository trust validated input.
- Root JSON wins over grouped files on key collisions.
- `count` in `choice()` is used as given — no coercion, no validation.
- `__readFile` must catch `(msgspec.DecodeError, UnicodeDecodeError)`: msgspec
  raises the builtin one for non-UTF-8 bytes, and it is not a `DecodeError`.

## Environment

- The static facade lives in **`orionis/environment/facade.py`**, never `env.py` —
  that name shadowed the sibling submodule and made
  `import orionis.environment.env` return the function.
- Typed prefixes (`int:`, `float:`, `bool:`, `str:`, `list:`, `dict:`, `tuple:`,
  `set:`, `path:`, `base64:`) match **case-sensitively and unstripped**.
- `get()` reads `os.environ`; `all()` reads the in-memory cache — a value written
  with `set(..., only_os=True)` is visible to `get()` but not to `all()`. The
  `default` of `get()` is returned verbatim, never parsed.
- Real exception types for `set/get/unset`: `TypeError`, `ValueError` and, for an
  unknown type hint, `RuntimeError`.
- Importing anything from `orionis.*` creates and writes the `.env` of the current
  working directory (`core_config.py` builds `App()` at module level, which
  generates `APP_KEY`). In probes, `os.chdir(tempdir)` **before** the import.

## Cross-cutting rules for this folder

- Every ABC in `contracts/` declares `__slots__ = ()`; every stateful concrete
  class declares `__slots__`.
- Config entities must only declare options a driver actually reads (dead fields
  such as S3 `throw` and View `enable_async` were removed).
- Declare a `Concurrency` section in the class docstring when a class caches state
  without locks.

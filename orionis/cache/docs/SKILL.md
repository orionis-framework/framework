---
name: "orionis-cache"
description: >-
  Use when a task involves understanding, integrating, or troubleshooting
  the orionis.cache module, its async key/value stores, backend-specific
  locks, or synchronous typed artifact cache. Consult the bundled
  documentation and inspect the local implementation to select verified
  APIs, respect resource and concurrency constraints, and validate usage.
---

# Work with orionis.cache

Use this file as a repository-local entry point, not as a claim of automatic
skill installation. Modify framework code only for an explicit request and
within the authorized scope.

## Select the surface

1. Read [README.md](README.md) or [README.es.md](README.es.md). Use
   [public imports](README.md#public-imports-and-package-behavior) and
   [module structure](README.md#module-structure) to locate actual symbols.
2. Inspect [../cache_manager.py](../cache_manager.py),
   [../repository.py](../repository.py), and the selected backend before
   proposing behavior. Distinguish application JSON values from tagged
   artifact data in [../serializer.py](../serializer.py) and
   [../file_based_cache.py](../file_based_cache.py).
3. Use the three lazy root exports or defining-module imports. Import the
   three contracts from `orionis.cache.contracts`; import backend `build`
   functions from their individual store modules. Do not invent a root
   `Cache` facade, named-store registry, extension API, or manager `replace`.
4. Consult [contracts](README.md#contracts). `lock` is implemented on concrete
   manager/repository classes but is absent from both contracts; `replace`
   belongs to the repository contract, not the manager proxy surface.

## Preserve backend behavior

- Read [requirements](README.md#requirements) before constructing a manager.
  It captures configuration and memoizes stores; `None` or an empty name uses
  the default, unknown names raise `CacheStoreException`, and memory creation
  does not depend on `stores.memory`. Do not assume missing configuration is
  replaced with defaults by the manager.
- Await async operations. Treat `store` and `lock` as synchronous factories.
  Check [framework integration](README.md#framework-integration) for the
  facade's deferred/pinned state; after pinning, do not await `Cache.store`.
- Treat prefixes as string transformations, not a cleanup boundary. `clear`
  acts on the entire backend. Restrict file checks to owned temporary trees
  and SQL checks to owned tables/connections.
- Verify null and TTL behavior on the actual backend. With inspected
  aiocache 0.12.3, stored `None` can trigger `remember` again and survive
  `pull`; file/database preserve the sentinel distinction. Zero TTL is not
  uniform across these backends. Consult [repository](README.md#cacherepository)
  and [compatibility](README.md#compatibility-notes).
- Do not describe `remember` as single-flight or `pull` as atomic. A sync
  resolver runs on the caller's loop; callback, codec, and backend failures
  normally propagate. Repository `add` converts any backend `ValueError` to
  `False`; `replace` requires a live entry or a supported CAS primitive.
- Consult [locks](README.md#cachelock) and
  [concurrency](README.md#performance-and-concurrency). Separate loop-local
  file-user locks from file-operation stripes and lease-based database/RedLock
  contexts. Do not promise strict RedLock exclusion, lease renewal, FIFO
  database acquisition, or module-wide thread safety.
- Keep a fresh context object for each active lock acquisition. Respect
  backend resource lifetime through cancellation; started worker work is not
  forcibly stopped by these wrappers. Close clients/connections owned by the
  caller rather than assuming a repository or manager close API.
- Check [database](README.md#databasecachebackend) before using raw table names.
  First use creates schema; direct backend names are trusted SQL identifiers,
  not validated/quoted automatically. Do not certify other drivers or
  transaction/prefix setups from the SQLite examples.
- Check [artifact semantics](README.md#filebasedcache): monitored directories
  include only Python files, hashes use path/mtime/size rather than contents,
  and the per-instance hash has a 0.5-second reuse window.
- Check [typed serialization](README.md#serializer) before storing arbitrary
  objects. Reserved `__type__` keys can collide with user mappings, malformed
  data can raise, and type/enum decoding can import modules. Do not treat
  tagged decoding as inert processing of untrusted input.

## Validate within scope

Read [verification limits](README.md#verification-and-limitations) and the
existing [../../../tests/cache](../../../tests/cache). Use the repository
virtualenv and native runner when application writes are authorized:

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe -B reactor test --start-dir="tests/cache" --verbosity=2
.\.venv\Scripts\python.exe -B -m ruff check --no-cache orionis/cache tests/cache
```

Inspect bootstrap, logs, and result-cache destinations before executing
Reactor under a documentation-only boundary. Isolate native
`TestingEngine`/`TestRunner` with a temporary created application and result
caching disabled, or report the execution limitation. Do not clear shared
application storage to make validation pass.

Compile examples, verify their imports point to the inspected checkout, and
execute safe cases in separate processes with temporary working directories
and bytecode disabled. Prefer file-backed temporary SQLite for concurrent
database checks; do not infer multi-connection behavior from `:memory:`.
Check discovered counts and raw failures/errors, not only the exit code.

Report missing dependencies/services and unavailable checks precisely.
Distinguish source evidence, executed cases, declared constraints, lockfile
versions, and installed versions. Use the README uncertainty categories and
do not change source, configuration, dependencies, or installation layout to
hide a validation failure.

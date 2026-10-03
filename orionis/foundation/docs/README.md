# Foundation

Spanish manual and performance review: [README.es.md](README.es.md).
Measured samples: [benchmark-results.json](benchmark-results.json).

## Explicit Readiness And Headless Startup

`create()` retains its synchronous configuration/registration behavior.
For a script or a custom worker, use `await app.boot()` before resolving
services or calling facades. This method calls `create()` and awaits pending
eager providers, shares their existing startup lock, and returns the application.
A failure or cancellation retains the unfinished provider for a later retry.
It does not initialize a server/CLI kernel or execute runtime lifecycle hooks.

| Phase | Observable state | Legal service access |
| --- | --- | --- |
| Constructed | `isCreated == False` | Explicit container bindings; configure the application before using configured services. |
| Created | `isCreated == isBooted == True` | Bindings are registered; inject contracts and await resolutions. Eager async provider side effects can still be pending. |
| Providers started | `areProvidersBooted == True` | Eager boot side effects are complete. Deferred providers still boot when their binding is first resolved. |
| HTTP initialized | `isHttpReady == True` | Both HTTP protocol handlers are published after eager provider startup and kernel boot. The flag does not certify sockets, external dependencies or deployment health. |
| Scoped | `app.getCurrentScope()` returns a scope | Scoped instances belong to the current request, WebSocket connection or queue job; never retain them in a singleton. |
| Facade pinned | The provider has awaited `Facade.pin()` | Direct passthrough follows the resolved service's sync/async API. Before pinning, facade attribute dispatch requires `await`, including synchronous service methods. |

`isBooted` remains a compatibility alias for the created stage. Use the new
readiness properties when distinguishing provider startup from HTTP readiness.
These properties report completed startup stages and are not reset by runtime
shutdown; they are not live process or service health checks.
HTTP lifespan and Reactor keep their existing lifecycle callbacks; scripts that
need those callbacks must run the corresponding runtime entry point.

```python
from pathlib import Path
from orionis import Application
from orionis.queues.contracts.manager import IQueueManager

async def main() -> None:
    app = await Application(Path.cwd()).boot()
    manager = await app.make(IQueueManager)
    try:
        # Dispatch or consume jobs through manager here.
        assert app.areProvidersBooted
    finally:
        await manager.close()
```

## Scope

Foundation owns application configuration, provider registration, lifecycle
hooks, HTTP/CLI entry points and application directory access. The review covers
157 Python files and 390 explicit function or method definitions on CPython
3.14.6, Windows 11. Python 3.14 remains the minimum supported version.

## Application Lifecycle

1. Construct `Application(base_path=...)`. The container supplies a singleton
   per concrete application class. Construction initializes state, validates
   Python and resolves the base path; it does not start providers or kernels.
2. Optionally call `compile(path=..., invalidation_paths=...)`. A valid cache
   supplies the frozen bootstrap snapshot and skips declarative overrides.
3. Register routing, middleware, providers, lifecycle callbacks and configuration.
4. Call `create()`. Cold startup discovers configuration and providers, commits
   configuration, registers services, configures timezone/locale and records the
   worker policies. `isBooted` describes this stage, not HTTP readiness.
5. HTTP lifespan startup boots pending eager providers and the HTTP kernel before
   acknowledging readiness. CLI commands initialize their kernel and execute
   startup/shutdown hooks around each command. Legacy synchronous provider boot
   methods are executed during registration.
6. The request path uses cached kernel handlers. First-use initialization is
   guarded by per-application async locks. Deferred provider resolution remains
   owned by the container.

## Public Surface

| Entry Point | Contract |
| --- | --- |
| `Application.current()` | Return the existing singleton or `None`; do not boot it. |
| `create()` | Initialize once and return the application. |
| `compile(path=None, invalidation_paths=None)` | Configure/load bootstrap cache. |
| `on(lifespan, *callbacks, runtime=None)` | Register deduplicated lifecycle callbacks. |
| `withRouting(api=None, web=None, console=None, health=None)` | Register route files. |
| `withProviders(*providers)` | Register provider classes. |
| `withMiddleware(*middleware)` | Register unique global middleware classes. |
| `withExceptionHandler(handler)` / `withScheduler(scheduler)` | Register class metadata. |
| `getExceptionHandler()` / `getScheduler()` | Build an instance asynchronously. |
| `getMiddleware()` | Resolve registered middleware classes. |
| `config(key=None, value=...)` | Read all, read a dotted key, or write a dotted key. |
| `resetRuntimeConfig()` | Restore a mutable copy of the frozen configuration. |
| `path(key=None)` | Read a resolved `Path` or the read-only path mapping. |
| `routingPaths(key=None)` | Return independent mutable routing containers. |
| `isProduction()` / `isDebug()` | Read boot-time environment flags. |
| `underMaintenance()` | Read worker-cached shared maintenance state. |
| `handleCommand(args=None)` | Execute a CLI command and return its exit code. |
| `__call__` / `__rsgi__` | Serve ASGI / RSGI requests. |

Properties include `isBooted`, `startAt`, `basePath`, `entryPoint`,
`routeHealthCheck`, `compiled`, `compiledPath`,
`compiledInvalidationPathsDirs` and `compiledInvalidationPathsFiles`.

Fluent configuration setters exist for App, Auth, Cache, Http, Database,
Filesystems, Logging, Mail, Queue, Session and Testing. Hashing, Scheduler and
View are also core configuration sections, configured through their dataclasses
and application configuration modules.

The existing merge order is defaults, fluent configuration, then discovered
configuration dataclasses. This review does not change precedence or cache
invalidation rules. In particular, changing framework provider/configuration
metadata still requires invalidating the configured bootstrap cache.

### Mutable Configuration

`config()` and `config("section")` expose live mutable dictionaries. Missing or
unreachable keys return `None`; empty path segments remain valid. Assigning below
a scalar replaces that parent with a dictionary. Runtime mutation does not
refresh the boot-time debug, production or disconnect-monitoring policies.

Only parsed key components are cached: a shared, 256-entry LRU contains immutable
tuples, never application values or instances. This preserves changes made
through returned mappings and avoids retaining an application through the cache.

### Directory

`Directory(app)` reads all 38 paths in one `app.path()` call and owns a dictionary
snapshot. Accessors such as `root()`, `appHttpControllers()`, `appJobs()` and
`storageFramework()` retain construction-time values. The class and its contract
are slotted. Its injection annotation keeps `IApplication` available at runtime.

## Performance Findings

No critical production defect was reproduced in the reviewed foundation paths.
Most avoidable work was in startup and service construction, not per-request
database or network I/O. The Spanish manual documents each change and trade-off.

| Impact | Applied Change | Observed Result |
| --- | --- | --- |
| High, debug lifecycle | Remove blocking splash sleeps. | Remove 500 ms startup + 100 ms shutdown waits. |
| Medium, construction | Read the Directory path map once. | 38 application calls become 1; 4.33x locally. |
| Medium, validation | Index scalar enum names/values. | 33-member late match: 23.658 to 1.357 us. |
| Medium, selected imports | Defer database package and enum exports. | SQLite loads 7 instead of 23 database modules. |
| Medium, construction | Check mailer field names without serializing settings. | 13.944 to 3.139 us with existing nested entities. |
| Low, request metadata | Replace full cache flushes with a key-parser LRU. | 692 to 564 parses in 32,500 mixed lookups. |
| Low, bootstrap | Copy flat descriptors directly; remove unused commands map. | 8.357 to 2.172 us for snapshot construction. |
| Low, validation | Reuse disk/channel tables; normalize log levels once. | Remove 18 temporary tuples per pair of validations. |
| Low, layout | Slot stateless validators and the application contract. | Validators have no instance dictionaries. |

The enum index holds at most 64 `(enum class, alias count)` revisions. It keeps
declaration precedence and recognizes newly added name aliases. Non-scalar enum
values use the original live scan, so mutable values never leave stale matches.

Logging normalization preserves errors and numeric results. Validation-only
`IsValidLevel(value)` still returns `None`. Disk/channel conversion retains
validation and per-instance nested entities; only type tables are shared.

### Measurement Limits

Microbenchmarks compare the original Git implementations with the changed
implementations, alternating order over seven rounds. Directory, Mail and
bootstrap use 10,000 iterations; enum/log-level checks use 100,000. Import
measurements use seven independent `python -B` processes. Import memory is a
separate `tracemalloc` run, not process RSS. Samples and the baseline commit are
recorded in the JSON artifact.

Host load varied substantially. Treat the timings as local measurements, not
portable promises. The LRU's allocation reduction is deterministic for its
documented workload; its warm timing differences overlap noise. No HTTP
throughput, p99 latency, free-threaded Python or external database certification
is claimed.

## Initialization Policy

### Package Initializers

| Packages | Policy | Reason |
| --- | --- | --- |
| `config/database/__init__.py` | Lazy PEP 562 exports. | Selecting one driver must not import all other configurations. |
| `config/database/enums/__init__.py` | Lazy PEP 562 exports. | Leaf enum imports must not evaluate unrelated catalogs. |
| The 20 empty initializers | Keep empty. | Namespace markers need no dispatcher or imported implementation. |
| The remaining 25 configuration/enum/validator aggregators | Keep eager. | Small, cohesive exports required together; avoid extra dispatch tables without measured benefit. |

The empty group includes the foundation/config roots, entity namespaces,
contracts, lifespan and session helpers. The eager group includes configuration
roots other than database, their nonempty small enum packages, logging
validators and the foundation lifespan/runtime enum package.

Lazy exports use the existing `orionis._exports.resolve_export` helper. The
resolved object is cached in the module namespace: repeat access is direct.
`__all__`, `dir()`, wildcard imports, direct imports and class identity remain
supported. `TYPE_CHECKING` imports preserve editor discoverability. A first-use
import can defer an import error; tests cover every declared export.

### Constructors And Defaults

| Component | Policy |
| --- | --- |
| `Application.__init__` | Initialize state and locks eagerly; defer services, runtime config copies and unused kernels. |
| `Directory.__init__` | Snapshot paths eagerly; accessors must not resolve paths dynamically. |
| Configuration dataclasses / `__post_init__` | Validate eagerly when constructed; keep environment reads in factories. |
| `Configuration` aggregate | Construct requested sections eagerly; do not make field access trigger validation. |
| Core configuration/provider metadata | Keep imports deferred until explicitly loaded; do not cache environment-derived default instances. |
| Lifecycle display modules | Load for HTTP lifecycle, not individual requests or ordinary CLI dispatch. |

No blanket `slots=True` conversion was applied to existing public configuration
dataclasses. That would change `__dict__`, weak-reference/subclass behavior and
class identity for objects mostly built once. `IApplication.__slots__ = ()`
does not remove the dictionary inherited by Application from Container.

## Concurrency

The supported lifecycle is one worker event loop per application. Existing
kernel/provider coordination, failure retry and cancellation behavior remain.
The cache contains immutable metadata only; it does not make mutable runtime
configuration safe for concurrent writes from different threads.

Direct HTTP dispatch remains the default. Opt-in disconnect monitoring keeps
its bounded queue, task-factory compatibility and joined cancellation cleanup.
Maintenance polling remains cached for 100 ms; its periodic filesystem read is
unchanged. No locks or tasks were added to the warm request dispatch path.

Debug startup/shutdown messages now remain on the normal console while hooks
run instead of using a timed alternate screen. Production display stays silent.

## Verification

Run with the repository virtual environment and `PYTHONIOENCODING=utf-8`:

```powershell
.\.venv\Scripts\python.exe -m ruff check orionis/foundation tests/foundation
.\.venv\Scripts\python.exe reactor test --start-dir=tests/foundation --verbosity=2 --fail-fast=0
```

The runner can hide failing subtests in its Rich summary. Verification also
captures `TestRunner.run()` results and inspects `failures`, `errors` and
`testsRun`, without changing the runner.

The recorded integration run passed Container 243, View 205, Mail 193, Logging
176 and Storage 242 tests. HTTP ran 738 tests with two pre-existing subtest
issues in one router-stub parity test. Database ran 238 with one pre-existing
application-model test error: `active` is fillable but the test expects rejection.
Foundation ran 153 tests: 146 successful methods and seven pre-existing
configuration tests with 31 failing and six errored subtests,
covering template defaults, option declarations, Oracle nullability and logging
environment precedence. These are not reported as passing.

The change adds 24 tests and corrects one cancellation fixture to wait for its
monitor to start before requiring cleanup. All 28 transport tests pass.

Ruff and SonarQube IDE diagnostics are checked in the changed scope. This is not
a remote SonarQube Quality Gate or Security Hotspot certification.

# orionis.foundation

> `orionis.foundation` is Orionis's application runtime: it assembles validated configuration, paths, providers, kernels, routing, lifecycle hooks, and deployment protocols.

## Overview

`Application` extends the dependency-injection `Container` and is the object exported from `orionis`. It is simultaneously the bootstrap coordinator, ASGI/RSGI entry point, CLI dispatcher, configuration repository, path registry, provider loader, and lifecycle owner.

Foundation also defines frozen configuration entities for every major subsystem, immutable core metadata, the `Directory` path service, runtime/lifespan enums, and startup/shutdown presentation. Most applications configure it in `bootstrap/app.py`, call `create()`, and let the HTTP server or Reactor drive runtime startup.

## Requirements

- Python 3.14 or newer; construction rejects older interpreters.
- An application root represented by `str` or `pathlib.Path`.
- Valid frozen dataclass configuration modules under the configured `config` path.
- Route files that exist and import their required facade when registered.
- One event loop per application worker; mutable runtime state is not designed for cross-loop or cross-thread sharing.

## Quick start

```python
import base64
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis import Application
from orionis.environment import Env


class DocsApplication(Application):
    pass


key = "base64:" + base64.b64encode(b"k" * 32).decode()
Env.set("APP_KEY", key, only_os=True)
try:
    with TemporaryDirectory() as directory:
        app = DocsApplication(Path(directory))
        app.withConfigApp(
            name="Docs",
            env="testing",
            debug=False,
            key=key,
            cipher="AES-256-CBC",
        ).withConfigPaths(storage="var")
        app.create()
        assert app.isCreated and DocsApplication.current() is app
        assert app.config("app.name") == "Docs"
        assert app.path("storage") == (Path(directory) / "var").resolve()
        app.config("app.name", "Runtime Docs")
        assert app.config("app.name") == "Runtime Docs"
        app.resetRuntimeConfig()
        assert app.config("app.name") == "Docs"
        print(app.config("app.name"), app.routeHealthCheck)
finally:
    Env.unset("APP_KEY", only_os=True)
```

Validation: **Executed successfully** on CPython 3.14.6 in a temporary application root; output was `Docs /up`.

## Core concepts

### Bootstrap versus runtime state

Before `create()`, fluent `with...` methods build mutable bootstrap metadata. Creation loads configuration and providers, freezes the bootstrap snapshot, registers the application, and exposes a separate mutable runtime-config copy. `config(key, value)` changes only runtime config; `resetRuntimeConfig()` restores it from the frozen snapshot.

### Creation and readiness stages

`create()` completes configuration and provider registration. `boot()` also awaits eager provider boot methods for headless use, but intentionally does not run HTTP/CLI hooks or kernels. `isCreated`/`isBooted`, `areProvidersBooted`, and `isHttpReady` distinguish these stages.

### Runtime ownership

ASGI `http`, `websocket`, and `lifespan` scopes dispatch through `Application.__call__`; RSGI uses the protocol hooks. `handleCommand()` owns CLI startup, command execution, and guaranteed shutdown. HTTP startup publishes both ASGI and RSGI handlers before readiness is reported.

## Module structure

| Area | Responsibility |
|---|---|
| `application.py` | Bootstrap, protocols, kernels, providers, routing, config, paths, maintenance. |
| `contracts/` | `IApplication` and `IDirectory` interfaces. |
| `directory.py`, `core_paths.py` | Snapshot path access and default application tree. |
| `config/` | Native frozen entities, enums, normalization, shared environment helpers. |
| `core_config.py` | Lazy construction of independent core defaults. |
| `core_providers.py`, `core_kernels.py` | Lazy provider classes and kernel metadata. |
| `core_exception_handler.py`, `core_scheduler.py` | Default extension metadata. |
| `enums/` | `Lifespan` and `Runtime`. |
| `lifespan/` | Debug startup/shutdown panels and uptime summary. |

## Public API

### `Application(base_path=Path.cwd())`

`orionis.Application` is a thread-safe singleton per concrete subclass. `Application.current()` returns an existing instance without creating it. Properties expose base/entry paths, start time, compiled-cache state, health route, creation/provider/HTTP readiness, debug/production flags, and maintenance state.

### Bootstrap methods

- `compile(path=None, invalidation_paths=None)` enables cached bootstrap state.
- `withRouting(api, web, console, health, ai, websocket=...)` registers validated route files.
- `withProviders(*classes)` and `withMiddleware(*classes)` register extension classes.
- `withExceptionHandler(cls)` and `withScheduler(cls)` replace defaults.
- `withConfigApp/Auth/Cache/Http/Database/Filesystems/Logging/Mail/Mcp/Queue/Session/Testing(**values)` supplies section overrides.
- `withConfigPaths(**paths)` resolves the full application directory map.
- `on(lifespan, *callbacks, runtime=None)` registers global or runtime-specific hooks.

These methods return the application for chaining and reject mutation after creation. On a valid compiled-cache hit, cached bootstrap metadata wins and registration/configuration methods intentionally become no-ops.

### Runtime methods

`create()` is synchronous registration/configuration. `boot()` is async provider readiness for headless processes. `handleCommand(args=None)` executes the CLI kernel within CLI lifecycle hooks. `config()`, `path()`, and `routingPaths()` expose runtime configuration, immutable bootstrap paths, and thawed route lists.

`getExceptionHandler()` and `getScheduler()` lazily build configured application classes after creation. Container methods inherited by `Application` provide binding, resolution, scopes, and invocation.

### `Directory`

`Directory(app)` snapshots `app.path()` once and exposes typed methods such as `root()`, `appModels()`, `databaseMigrations()`, `resourcesViews()`, and `storageLogs()`. Later path-map replacement does not change that snapshot.

## Common workflows

### Bootstrap a web application

Construct `Application`, optionally enable compilation, register lifecycle callbacks, routing, scheduler, exception handler, providers, and middleware, then call `create()`. Export that instance from `bootstrap.app`; the server invokes it through ASGI or RSGI.

### Run headless services

Use `await app.boot()` when a worker needs registered and fully booted eager providers without starting a kernel. Concurrent calls share an async lock; a failed provider remains pending so a later call can retry.

### Change request-time configuration

Read with dot notation (`app.config("http.cors.allowed_origins")`) and set with a second argument. Missing or unreachable keys return `None`; writes create intermediate dictionaries. Reset when a test or worker must discard runtime overrides.

### Enter maintenance mode

The configured `app.maintenance` is the fallback. The shared `storage/framework/maintenance` marker overrides it with `down` or `up`; each worker refreshes the marker at most every 100 ms and fails closed on read/decoding errors.

## Examples

### Validate native application configuration

```python
from orionis.foundation.config.app import App, Cipher, Environments

config = App(
    name="Docs",
    env=Environments.TESTING,
    debug=False,
    cipher=Cipher.AES_256_GCM,
    key=b"k" * 32,
)
assert config.env == "testing"
assert config.cipher == "AES-256-GCM"
assert config.key == b"k" * 32
print(config.name, config.env, config.cipher)
```

Validation: **Executed successfully** on CPython 3.14.6.

### Snapshot configured directories

```python
from pathlib import Path
from orionis.foundation.directory import Directory


class App:
    def path(self, key=None):
        paths = {
            "root": Path("project").resolve(),
            "storage_logs": Path("project/storage/logs").resolve(),
        }
        return paths if key is None else paths.get(key)


directory = Directory(App())
assert directory.root() == Path("project").resolve()
assert directory.storageLogs() == Path("project/storage/logs").resolve()
print(directory.storageLogs().as_posix())
```

Validation: **Executed successfully** on CPython 3.14.6.

### Configure compiled bootstrap state

```python
import base64
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis import Application
from orionis.environment import Env


class CachedApplication(Application):
    pass


key = "base64:" + base64.b64encode(b"c" * 32).decode()
Env.set("APP_KEY", key, only_os=True)
try:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "config").mkdir()
        (root / ".env").touch()
        app = CachedApplication(root)
        app.compile("bootstrap/cache", ["config", ".env"])
        app.withConfigApp(key=key)
        app.create()
        assert app.compiled
        assert app.compiledPath == (root / "bootstrap/cache").resolve()
        assert (root / "config").resolve() in app.compiledInvalidationPathsDirs
        assert (root / ".env").resolve() in app.compiledInvalidationPathsFiles
        print("compiled cache configured")
finally:
    Env.unset("APP_KEY", only_os=True)
```

Validation: **Executed successfully** on CPython 3.14.6; all files were temporary.

### Register lifecycle callbacks

```python
from orionis.foundation.enums import Lifespan, Runtime


async def open_resources() -> None:
    pass


async def close_resources() -> None:
    pass


app.on(Lifespan.STARTUP, open_resources, runtime=Runtime.HTTP)
app.on(Lifespan.SHUTDOWN, close_resources, runtime=Runtime.HTTP)
```

Validation: **Syntax-validated only** on CPython 3.14.6; `app` belongs to the application's bootstrap module and callbacks run under the HTTP server lifecycle.

## Configuration

Foundation builds independent native defaults, merges explicit `withConfig...` data, then merges discovered frozen configuration dataclasses. Thus application `config/*.py` entities are the normal final source of section values. After validation, the bootstrap snapshot is deeply frozen.

Core sections are:

| Section | Principal concern |
|---|---|
| `app`, `auth`, `session` | Identity, environment, encryption, guards, cookies, sessions. |
| `http`, `mcp`, `realtime` | HTTP/security limits, protocol origins, realtime limits. |
| `database`, `cache`, `queue`, `scheduler` | Persistence connections, stores, workers, scheduled-state stores. |
| `filesystems`, `mail`, `logging`, `view` | External storage, delivery, channels, templates. |
| `hashing`, `testing` | Password algorithms and test runner behavior. |

Entities are frozen dataclasses and normalize nested dicts/enums into validated objects. Environment variables are read by their field default factories; see each subsystem module for the complete option set.

## Integration with Orionis

Foundation loads 20 core providers in deterministic order, auto-discovers concrete providers under `app/providers`, registers eager providers, and publishes deferred-provider metadata before eager registration. Synchronous provider `boot` runs during creation; async boot runs during `boot()` or a runtime startup.

It resolves the CLI and HTTP kernels from metadata, validates route-file facade imports, injects the configured scheduler/exception handler, and exposes itself as `IApplication` with alias `x-orionis-IApplication`. All service modules ultimately consume its config, container, paths, scopes, or lifecycle.

## Errors and edge cases

- `config`, `path`, environment flags, handler, and scheduler access reject use before creation where applicable.
- Bootstrap mutation after creation raises `RuntimeError`; invalid provider, middleware, handler, or scheduler classes raise `TypeError`.
- Routing rejects missing files, invalid argument types, and files without an allowed facade import.
- Invalid config entities fail creation with their original validation error, wrapped only where discovery requires it.
- Application construction is singleton per subclass: later constructor arguments do not reinitialize an existing instance.
- Runtime config is mutable and returned mappings are live; call `resetRuntimeConfig()` to restore the frozen baseline.
- Unknown `path`/routing keys return `None`; `routeHealthCheck` defaults to `/up`.
- A corrupt/unreadable maintenance marker deliberately reports maintenance mode.

## Performance and concurrency

Compiled mode stores bootstrap state in `FileBasedCache` and invalidates it from monitored files/directories. Core providers and config entities use lazy imports. Dot-notation config keys use an LRU capped at 256, and frequently queried production/debug flags are precomputed at creation.

Provider boot, CLI kernel initialization, and HTTP kernel initialization each use async locks so concurrent callers share one successful startup. Maintenance refresh uses a thread lock. Request scopes and container resolution are context-local, but the application explicitly does not promise mutable-state safety across event loops or arbitrary threads.

Optional HTTP disconnect monitoring uses a bounded ASGI queue (eight queued messages plus one producer-held message) or an RSGI watcher and cancels request work on client disconnect. WebSockets bypass that body-monitoring path.

## Compatibility

Orionis foundation targets Python 3.14+ and implements ASGI HTTP/WebSocket/lifespan plus Granian RSGI integration and CLI Reactor dispatch. Validation used CPython 3.14.6 on Windows. Path resolution uses `pathlib`; locale/timezone application remains platform-dependent and unsupported locales are ignored after config validation.

## Verification notes

Validation used CPython 3.14.6. Application protocols, staged readiness, config loading/freezing, all native config families, route/provider discovery, compilation, paths/directory, maintenance, lifecycle, contracts, lazy imports, and `tests/foundation` were inspected. All 178 foundation tests passed through the Orionis runner. Four standalone programs executed successfully; the lifecycle registration snippet was syntax-validated only.

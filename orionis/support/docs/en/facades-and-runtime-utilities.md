# Facades, dates, and runtime utilities

## Core concepts

### Facades

A facade is a class-level proxy to an object resolved by the Orionis service container. Imports are lazy, so importing `orionis.support.facades` does not eagerly load every subsystem. Runtime implementations are intentionally small, while adjacent `.pyi` files expose the proxied API to type checkers and editors.

Most facades are process-wide. `Session` is scoped, so its resolution follows the active request or execution scope. Do not retain resolved request services across scopes.

### Utility values

`Collection` provides fluent transformations around a list. Most query operations return a new collection; explicitly mutating methods such as `push`, `put`, `forget`, `merge`, and `transform` update the current object. `DotDict` enables recursive attribute access, `StdClass` stores validated dynamic attributes, `Stringable` is an immutable `str` subclass with fluent text operations, and `MISSING` distinguishes an omitted value from `None`.

### Entities and structures

`BaseEntity` is meant to be combined with `@dataclass`. It serializes nested dataclasses and enum fields through `toDict()` and describes field types, defaults, and metadata through `getFields()`. `FreezeThaw` recursively converts dictionaries to read-only mapping proxies and sequences to tuples, while preserving repeated references inside the traversed graph.

### Cross-cutting helpers

`Singleton` implements one instance per concrete class with a lock-protected initialization path. `Final` prevents subclassing. `PerformanceCounter` measures synchronous or asynchronous intervals. `Workers` chooses a process count from cached logical CPU and total-memory limits. `Parser.exception()` creates a cached structured representation of an exception. `Inspire` returns a cryptographically selected quote.

## Public API

### Facades

Import facades from `orionis.support.facades`:

| Facade | Service area |
| --- | --- |
| `Application` | Application container and lifecycle. |
| `Auth` | Authentication manager. |
| `Cache` | Cache stores and operations. |
| `Catch` | Exception-reporting service. |
| `Crypt` | Encryption and decryption. |
| `DateTime` | Standalone date, time-zone, duration, and interval helpers. |
| `DB` | Database query builder. |
| `Hash` | Password and value hashing. |
| `Lang` | Translation. |
| `Log` | Structured logging. |
| `Mail` | Mail construction and delivery. |
| `Mcp` | MCP server registration and notifications. |
| `Queue` | Queue dispatch, connections, workers, and failed jobs. |
| `Reactor` | Console command execution. |
| `Realtime` | Realtime hub clients and connections. |
| `Route` | HTTP, WebSocket, MCP, and view routing. |
| `Schedule` | Scheduled commands and callbacks. |
| `Schema` | Database schema operations. |
| `Session` | Scope-local session state. |
| `Storage` | Configured filesystem disks. |
| `Test` | Framework testing engine. |
| `View` | View factory and rendering. |

Except for `DateTime`, these classes obtain their target from the container. Consult the owning module documentation for the complete proxied contract.

### Types and helpers

- `Collection(items=None)`: fluent selection, mapping, grouping, aggregation, pagination, serialization, and list-like protocols.
- `DotDict(mapping)`: key and attribute access; `export()` recursively restores dictionaries and `copy()` recursively copies nested mappings.
- `StdClass(**kwargs)`: dynamic attributes with reserved method and dunder names rejected; supports `fromDict`, `toDict`, `update`, and `remove`.
- `Stringable(value)`: immutable fluent text wrapper with casing, matching, replacement, encoding, hashing, parsing, truncation, and validation helpers.
- `MISSING`: falsey sentinel whose representation is `MISSING`.
- `BaseEntity`: `toDict()` and `getFields()` for dataclass entities.
- `FreezeThaw.freeze()` / `thaw()`: recursive immutable/mutable conversions.
- `PerformanceCounter`: `start`/`stop`, `astart`/`astop`, context-manager APIs, and duration conversions.
- `Workers.setRamPerWorker()` / `calculate()`: process capacity calculation.
- `Parser.exception(error)`: produces an `ExceptionParser`; call `toDict()` for `error_type`, `error_message`, `error_code`, and `stack_trace`.
- `Inspire.random()`: returns a `{"quote": ..., "author": ...}` mapping.
- `Final` and `Singleton`: metaclasses for final and singleton classes.

## Examples

### Measure an operation

```python
from orionis.support.performance import PerformanceCounter

with PerformanceCounter() as counter:
    total = sum(range(100))

assert total == 4950
assert counter.getSeconds() >= 0
assert counter.getMilliseconds() >= 0
```

### Work with dates without bootstrapping the container

```python
from orionis.support.facades import DateTime

instant = DateTime.parse("2026-10-06T12:30:00Z")
later = DateTime.addDays(instant, 2)

assert instant.timezone_name == "UTC"
assert later.to_date_string() == "2026-10-08"
assert DateTime.diffInDays(instant, later) == 2
```

### Call a container-backed facade

```python
from orionis.support.facades import Cache, Log, Storage

# Run after the Orionis application has booted and bound these services.
async def completed_import() -> None:
    Log.info("Import completed")
    await Cache.set("imports:last", "customers.csv", ttl=300)
    await Storage.disk("local").put("imports/customers.txt", b"done")
```

## Configuration

Facade targets are configured by their owning modules and resolved from the current Orionis container. `DateTime` receives the application timezone and locale through its internal configuration loader during boot; explicit `tz` arguments override its default for individual operations.

`Workers` defaults to 0.5 GiB per worker. `setRamPerWorker()` changes a class-level process-wide budget. `Inspire` accepts a custom list of mappings with mandatory `quote` and `author` keys. The other helper types require no global configuration.

## Integration with Orionis

Use facades at application boundaries—controllers, commands, jobs, listeners, and providers—where concise access to a configured service is useful. Prefer constructor injection inside reusable domain services when explicit dependencies and isolated tests matter.

The lazy facade package avoids importing all subsystems at startup. Service type stubs keep static completion aligned with the actual manager contracts. `BaseEntity`, `Collection`, and `Stringable` are also used throughout Orionis to provide consistent serialization and fluent value operations.

## Errors and edge cases

- A service-backed facade fails when its binding is unavailable or no required scope is active.
- `DotDict.missing` returns `None`; use membership testing when `None` is a meaningful stored value.
- `StdClass` rejects dunder names and names that collide with its class API.
- `Collection.chunk()` and `forPage()` reject non-positive sizes; callback-based operations require callables.
- `FreezeThaw` only transforms dictionaries, lists, tuples, and mapping proxies. Objects stored inside them are not deep-copied.
- `PerformanceCounter` rejects reading before a completed measurement and rejects mixing synchronous and asynchronous start/stop methods.
- `Final` rejects inheritance at class creation time. `Singleton` ignores constructor arguments after the first instance exists.
- Invalid time zones and incompatible date inputs raise validation errors from `DateTime`/`pendulum`.
- `Workers.setRamPerWorker()` requires a finite positive value large enough to represent at least one byte.

## Performance and concurrency

Facade imports and root facade exports are lazy and cached. `BaseEntity` caches normalized field metadata per entity class. `ExceptionParser` parses once and returns its cached dictionary on subsequent calls. `DateTime` caches `ZoneInfo` instances until its timezone changes.

`Singleton` protects first construction with a per-class `threading.Lock`; its async access method uses the same short critical section and performs no blocking I/O. `FreezeThaw` uses iterative traversal to avoid recursion depth limits. `Workers` caches CPU count and total RAM at module import, so later calculations are constant-time integer arithmetic.

`Collection` and the mutable helpers are not synchronized. Do not mutate one instance concurrently without application-level coordination.

## Compatibility

The module follows the repository requirement of Python 3.14+. Public names use Orionis's camelCase method convention. The facade `.pyi` files are part of the developer-facing contract and should remain synchronized with their runtime service interfaces. Date formatting tokens passed to `DateTime.fromFormat()` follow Pendulum conventions, which differ from `datetime.strptime()` tokens.

## Module structure

| Path | Responsibility |
| --- | --- |
| `entities/` | Dataclass-oriented `BaseEntity` serialization and field metadata. |
| `facades/` | Lazy service proxies and their `.pyi` public contracts. |
| `formatter/` | Exception-to-dictionary formatting. |
| `inspirational/` | Quote provider and quote catalog. |
| `patterns/final/` | `Final` metaclass. |
| `patterns/singleton/` | Thread-safe `Singleton` metaclass. |
| `performance/` | Sync/async `PerformanceCounter`. |
| `structures/` | Recursive `FreezeThaw` conversions. |
| `system/` | CPU/RAM-aware worker calculation. |
| `types/` | `Collection`, `DotDict`, `StdClass`, `Stringable`, and `MISSING`. |

## Evidence and next steps

[__init__.py](../../facades/__init__.py) · [datetime.py](../../facades/datetime.py) · [counter.py](../../performance/counter.py) · [workers.py](../../system/workers.py)

[Return to the module index](README.md).

# Orionis Support

> Shared utility types, patterns, entities, formatters, and service facades used by Orionis modules.

## Table of contents

- [Functional description](#functional-description)
- [API reference](#api-reference)
  - [BaseEntity](#baseentity)
  - [Facades](#facades)
  - [DateTime](#datetime)
  - [Formatter](#formatter)
  - [Inspirational](#inspirational)
  - [Patterns](#patterns)
  - [Performance](#performance)
  - [Structures](#structures)
  - [System](#system)
  - [Types](#types)
- [Usage examples](#usage-examples)
- [Performance and concurrency considerations](#performance-and-concurrency-considerations)
- [Compatibility notes](#compatibility-notes)

## Functional description

`orionis.support` is a namespace package for reusable framework utilities; its root `__init__.py` is empty and exports no consolidated API. Import symbols from their owning subpackages. These utilities support, among others, `orionis.foundation` configuration, `orionis.orm` results, `orionis.http` error formatting, `orionis.console` timing, and service access through the container facades.

| Subpackage | Main API | Role |
|---|---|---|
| `entities` | `BaseEntity` | Dataclass serialization and field metadata. |
| `facades` | `Application`, `Auth`, `Cache`, `Catch`, `Crypt`, `DateTime`, `DB`, `Hash`, `Lang`, `Log`, `Mail`, `Queue`, `Reactor`, `Route`, `Schedule`, `Schema`, `Session`, `Storage`, `Test`, `View` | Lazy exports for container-backed services and date/time helpers. |
| `formatter` | `Parser`, `ExceptionParser`, `IExceptionParser` | Convert exception details and stack frames into dictionaries. See [Formatter reference](../formatter/docs/README.md). |
| `inspirational` | `Inspire`, `IInspire`, `INSPIRATIONAL_QUOTES` | Select a quote from the bundled quote collection. See [Inspirational reference](../inspirational/docs/README.md). |
| `patterns` | `Final`, `Singleton` | Metaclasses for non-inheritable classes and singleton construction. See [Patterns reference](../patterns/docs/README.md). |
| `performance` | `PerformanceCounter`, `IPerformanceCounter` | Measure elapsed time. See [Performance reference](../performance/docs/README.md). |
| `structures` | `FreezeThaw` | Convert nested containers between mutable and immutable forms. See [Structures reference](../structures/docs/README.md). |
| `system` | `Workers`, `IWorkers` | Calculate a worker count from CPU and memory information. See [System reference](../system/docs/README.md). |
| `types` | `Collection`, `DotDict`, `MISSING`, `StdClass`, `Stringable`, `ICollection`, `IStdClass` | Collection, mapping, sentinel, dynamic-object, and string helpers. See [Types reference](../types/docs/README.md). |

The subpackage manuals contain method-level tables and examples for their respective APIs. The sections below cover the root package behavior, the entity helper, facade exports, and the date/time API that does not have a separate manual here.

## API reference

### BaseEntity

Import with `from orionis.support.entities import BaseEntity`. `BaseEntity` is a slotted mixin, not a dataclass. Its subclasses need dataclass fields for `dataclasses.fields()` and `dataclasses.asdict()` to operate.

```python
class BaseEntity:
    def __post_init__(self) -> None: ...
    def toDict(self) -> dict[str, Any]: ...
    def getFields(self) -> list[dict[str, Any]]: ...
```

- `__post_init__(self) -> None` is a no-op hook available to dataclass subclasses.
- `toDict(self) -> dict[str, Any]` recursively converts dataclass fields to a dictionary and serializes enum members as their `.value`.
- `getFields(self) -> list[dict[str, Any]]` returns field names, normalized type names, defaults, and metadata. Default factories and callable metadata defaults are invoked while building the result.
- The private class method `_cachedFieldMetadata(cls) -> tuple[tuple[Field[Any], tuple[str, ...]], ...]` caches field/type metadata per entity class; it is an implementation detail of `getFields()`.

### Facades

Import from `orionis.support.facades`; the package resolves these names lazily via `__getattr__(name: str) -> object` and lists loaded and declared names with `__dir__() -> list[str]`. The package's `__all__` contains the 20 names below. Nineteen are service facades; `DateTime` is a class-level helper, not a `Facade` subclass.

| Export | Defining module | Runtime base | `getFacadeAccessor` signature and target |
|---|---|---|---|
| `Application` | `facades/application.py` | `Facade` | `getFacadeAccessor(cls) -> str`; returns `"x-orionis-IApplication"`. |
| `Auth` | `facades/auth.py` | `Facade` | `getFacadeAccessor(cls) -> type`; returns `IAuthManager`. |
| `Cache` | `facades/cache.py` | `Facade` | `getFacadeAccessor(cls) -> type`; returns `ICacheManager`. |
| `Catch` | `facades/catch.py` | `Facade` | `getFacadeAccessor(cls) -> str`; returns `"x-orionis-ICatch"`. |
| `Crypt` | `facades/encrypter.py` | `Facade` | `getFacadeAccessor(cls) -> type`; returns `IEncrypter`. |
| `DB` | `facades/db.py` | `Facade` | `getFacadeAccessor(cls) -> type`; returns `IQueryBuilder`. |
| `Hash` | `facades/hash.py` | `Facade` | `getFacadeAccessor(cls) -> type`; returns `IHashManager`. |
| `Lang` | `facades/lang.py` | `Facade` | `getFacadeAccessor(cls) -> type`; returns `ITranslator`. |
| `Log` | `facades/logger.py` | `Facade` | `getFacadeAccessor(cls) -> str`; returns `"x-orionis-ILogger"`. |
| `Mail` | `facades/mail.py` | `Facade` | `getFacadeAccessor(cls) -> type[IMailManager]`; returns `IMailManager`. |
| `Queue` | `facades/queue.py` | `Facade` | `getFacadeAccessor(cls) -> type[IQueueManager]`; returns `IQueueManager`. |
| `Reactor` | `facades/reactor.py` | `Facade` | `getFacadeAccessor(cls) -> str`; returns `"x-orionis-IReactor"`. |
| `Route` | `facades/router.py` | `Facade` | `getFacadeAccessor(cls) -> str`; returns `"x-orionis-IRouter"`. |
| `Schedule` | `facades/schedule.py` | `Facade` | `getFacadeAccessor(cls) -> type`; returns `ISchedule`. |
| `Schema` | `facades/schema.py` | `Facade` | `getFacadeAccessor(cls) -> type[ISchema]`; returns `ISchema`. |
| `Session` | `facades/session.py` | `ScopedFacade` | `getFacadeAccessor(cls) -> type[ISession]`; returns `ISession`. |
| `Storage` | `facades/storage.py` | `Facade` | `getFacadeAccessor(cls) -> type`; returns `IStorageManager`. |
| `Test` | `facades/testing.py` | `Facade` | `getFacadeAccessor(cls) -> type`; returns `ITestingEngine`. |
| `View` | `facades/view.py` | `Facade` | `getFacadeAccessor(cls) -> type`; returns `IViewFactory`. |

Each accessor has the source signature `@classmethod def getFacadeAccessor(cls) -> ...`. These facade classes declare no other runtime methods; service operations are dynamically exposed by the base facade and belong to the returned contract/service. Their availability depends on that service's binding and facade lifecycle. The paired `.pyi` files provide static editor/type-checker declarations and are not runtime implementations.

### DateTime

Import with `from orionis.support.facades import DateTime` or directly from `orionis.support.facades.datetime`. `DateTime` is not a container facade: its methods are class methods backed by `pendulum`. Its default class state starts at timezone `"UTC"` and locale `"en"`; application setup can load values through the private `_loadConfig(...)` hook.

The public API returns Pendulum values unless the return type below says otherwise:

| Methods | Signature shape and behavior |
|---|---|
| `getTimezone`, `getLocale`, `getZoneInfo` | `getTimezone(cls) -> str`, `getLocale(cls) -> str`, `getZoneInfo(cls) -> ZoneInfo`; read configured timezone/locale and a cached `ZoneInfo`. |
| `now`, `today`, `tomorrow`, `yesterday` | Accept `tz: str \| None = None`; return `pendulum.DateTime` for `now` and `pendulum.Date` for the other three. |
| `parse` | `parse(cls, date_string: str, tz: str \| None = None, *, strict: bool = True) -> pendulum.DateTime`. |
| `fromFormat` | `fromFormat(cls, date_string: str, fmt: str, tz: str \| None = None, locale: str \| None = None) -> pendulum.DateTime`. |
| `local`, `naive`, `datetime` | Construct date/time values from integer components; `datetime` also accepts `tz: str \| None = None`. See source signatures for positional defaults. |
| `fromTimestamp` | `fromTimestamp(cls, timestamp: float, tz: str \| None = None) -> pendulum.DateTime`. |
| `fromDatetime` | `fromDatetime(cls, dt: datetime \| pendulum.DateTime, tz: str \| None = None) -> pendulum.DateTime`; unsupported values raise `TypeError`. |
| `duration`, `interval` | Build `pendulum.Duration` and `pendulum.Interval`; `duration` takes keyword-only units and `interval` takes `start`, `end`, and keyword-only `absolute=False`. |
| `startOf`, `endOf` | `(..., unit: str, dt: pendulum.DateTime \| None = None, tz: str \| None = None) -> pendulum.DateTime`; delegate unit boundaries to Pendulum. |
| `startOfDay`, `endOfDay`, `startOfWeek`, `endOfWeek`, `startOfMonth`, `endOfMonth`, `startOfYear`, `endOfYear` | Accept optional `dt` and `tz`, returning the corresponding boundary as `pendulum.DateTime`. |
| `convertToLocal`, `formatLocal` | Convert supported string/datetime inputs to the configured timezone, or format a value as `str`. Unsupported `convertToLocal` inputs raise `TypeError`. |
| `addDays`, `addHours`, `addMinutes` | Add an integer amount to a supplied `pendulum.DateTime`; return a new Pendulum datetime. |
| `diffInDays`, `diffInHours` | Compare two Pendulum datetimes and return the absolute count of complete days or hours as `int`. |
| `isWeekend`, `isToday`, `isFuture`, `isPast`, `isLeapYear`, `isBirthday` | Date predicates returning `bool`; optional dates default to the current configured timezone where declared. |
| `closest`, `farthest` | Compare a reference `pendulum.DateTime` with `*others` and return a `pendulum.DateTime`. |
| `add`, `subtract` | Apply keyword-only year/month/week/day/hour/minute/second/microsecond values to a supplied datetime. |
| `diff`, `diffForHumans` | Return a `pendulum.Interval` or localized human-readable `str`; optional second datetime defaults to current time. |
| `next`, `previous` | Find a weekday occurrence; accept optional `day_of_week` and keyword-only `keep_time=False`. |
| `average` | Return the midpoint between a datetime and an optional second datetime. |
| `firstOf`, `lastOf`, `nthOf` | Find a boundary or weekday occurrence in a month, quarter, or year. |

The public method signatures are shown below as declared in the source. All are class methods.

```text
def getTimezone(cls) -> str
def getLocale(cls) -> str
def getZoneInfo(cls) -> ZoneInfo
def now(cls, tz: str | None = None) -> pendulum.DateTime
def today(cls, tz: str | None = None) -> pendulum.Date
def tomorrow(cls, tz: str | None = None) -> pendulum.Date
def yesterday(cls, tz: str | None = None) -> pendulum.Date
def parse(cls, date_string: str, tz: str | None = None, *, strict: bool = True) -> pendulum.DateTime
def fromFormat(cls, date_string: str, fmt: str, tz: str | None = None, locale: str | None = None) -> pendulum.DateTime
def local(cls, year: int, month: int = 1, day: int = 1, hour: int = 0, minute: int = 0, second: int = 0, microsecond: int = 0) -> pendulum.DateTime
def naive(cls, year: int, month: int = 1, day: int = 1, hour: int = 0, minute: int = 0, second: int = 0, microsecond: int = 0) -> pendulum.DateTime
def fromTimestamp(cls, timestamp: float, tz: str | None = None) -> pendulum.DateTime
def fromDatetime(cls, dt: stdlib_datetime | pendulum.DateTime, tz: str | None = None) -> pendulum.DateTime
def datetime(cls, year: int, month: int = 1, day: int = 1, hour: int = 0, minute: int = 0, second: int = 0, microsecond: int = 0, tz: str | None = None) -> pendulum.DateTime
def duration(cls, *, days: float = 0, seconds: float = 0, microseconds: float = 0, milliseconds: float = 0, minutes: float = 0, hours: float = 0, weeks: float = 0, years: float = 0, months: float = 0) -> pendulum.Duration
def interval(cls, start: pendulum.DateTime, end: pendulum.DateTime, *, absolute: bool = False) -> pendulum.Interval
def startOf(cls, unit: str, dt: pendulum.DateTime | None = None, tz: str | None = None) -> pendulum.DateTime
def endOf(cls, unit: str, dt: pendulum.DateTime | None = None, tz: str | None = None) -> pendulum.DateTime
def startOfDay(cls, dt: pendulum.DateTime | None = None, tz: str | None = None) -> pendulum.DateTime
def endOfDay(cls, dt: pendulum.DateTime | None = None, tz: str | None = None) -> pendulum.DateTime
def convertToLocal(cls, dt: str | stdlib_datetime | pendulum.DateTime) -> pendulum.DateTime
def formatLocal(cls, dt: pendulum.DateTime | None = None, format_string: str = "YYYY-MM-DD HH:mm:ss") -> str
def startOfWeek(cls, dt: pendulum.DateTime | None = None, tz: str | None = None) -> pendulum.DateTime
def endOfWeek(cls, dt: pendulum.DateTime | None = None, tz: str | None = None) -> pendulum.DateTime
def startOfMonth(cls, dt: pendulum.DateTime | None = None, tz: str | None = None) -> pendulum.DateTime
def endOfMonth(cls, dt: pendulum.DateTime | None = None, tz: str | None = None) -> pendulum.DateTime
def startOfYear(cls, dt: pendulum.DateTime | None = None, tz: str | None = None) -> pendulum.DateTime
def endOfYear(cls, dt: pendulum.DateTime | None = None, tz: str | None = None) -> pendulum.DateTime
def addDays(cls, dt: pendulum.DateTime, days: int) -> pendulum.DateTime
def addHours(cls, dt: pendulum.DateTime, hours: int) -> pendulum.DateTime
def addMinutes(cls, dt: pendulum.DateTime, minutes: int) -> pendulum.DateTime
def diffInDays(cls, dt1: pendulum.DateTime, dt2: pendulum.DateTime) -> int
def diffInHours(cls, dt1: pendulum.DateTime, dt2: pendulum.DateTime) -> int
def isWeekend(cls, dt: pendulum.DateTime | None = None) -> bool
def isToday(cls, dt: pendulum.DateTime) -> bool
def isFuture(cls, dt: pendulum.DateTime) -> bool
def isPast(cls, dt: pendulum.DateTime) -> bool
def isLeapYear(cls, dt: pendulum.DateTime | None = None) -> bool
def isBirthday(cls, dt: pendulum.DateTime, other: pendulum.DateTime | None = None) -> bool
def closest(cls, dt: pendulum.DateTime, *others: pendulum.DateTime) -> pendulum.DateTime
def farthest(cls, dt: pendulum.DateTime, *others: pendulum.DateTime) -> pendulum.DateTime
def add(cls, dt: pendulum.DateTime, *, years: int = 0, months: int = 0, weeks: int = 0, days: int = 0, hours: int = 0, minutes: int = 0, seconds: float = 0, microseconds: int = 0) -> pendulum.DateTime
def subtract(cls, dt: pendulum.DateTime, *, years: int = 0, months: int = 0, weeks: int = 0, days: int = 0, hours: int = 0, minutes: int = 0, seconds: float = 0, microseconds: int = 0) -> pendulum.DateTime
def diff(cls, dt1: pendulum.DateTime, dt2: pendulum.DateTime | None = None, *, absolute: bool = True) -> pendulum.Interval
def diffForHumans(cls, dt: pendulum.DateTime, other: pendulum.DateTime | None = None, *, absolute: bool = False, locale: str | None = None) -> str
def next(cls, dt: pendulum.DateTime, day_of_week: int | None = None, *, keep_time: bool = False) -> pendulum.DateTime
def previous(cls, dt: pendulum.DateTime, day_of_week: int | None = None, *, keep_time: bool = False) -> pendulum.DateTime
def average(cls, dt1: pendulum.DateTime, dt2: pendulum.DateTime | None = None) -> pendulum.DateTime
def firstOf(cls, dt: pendulum.DateTime, unit: str, day_of_week: int | None = None) -> pendulum.DateTime
def lastOf(cls, dt: pendulum.DateTime, unit: str, day_of_week: int | None = None) -> pendulum.DateTime
def nthOf(cls, dt: pendulum.DateTime, unit: str, nth: int, day_of_week: int) -> pendulum.DateTime
```

The private configuration mutators are `_loadConfig(cls, timezone_name: str | None = None, locale: str | None = None) -> None`, `_setTimezone(cls, timezone_name: str) -> None`, and `_setLocale(cls, locale: str) -> None`. `_setTimezone` raises `ValueError` for an invalid timezone. Parameter meanings are described in the source docstrings in [datetime.py](../facades/datetime.py).

### Formatter

The public symbols are `Parser`, `ExceptionParser`, and the structural `IExceptionParser` protocol. The common call is `Parser.exception(exception: Exception) -> ExceptionParser`, a static factory. `ExceptionParser(exception: Exception) -> None` captures traceback information at construction; `toDict(self) -> dict[str, Any]` returns `error_type`, `error_message`, `error_code`, and `stack_trace`. Stack entries include source line context when available. See [the formatter manual](../formatter/docs/README.md) for the entry schemas and exact API details.

### Inspirational

`Inspire(quotes: list[dict] | None = None) -> None` implements `IInspire`; `random(self) -> dict` chooses one item from its quote list. `INSPIRATIONAL_QUOTES` is the bundled tuple of quote mappings. The module uses `secrets.choice`; an empty list follows the fallback behavior described in [its manual](../inspirational/docs/README.md).

### Patterns

`Final` and `Singleton` are metaclasses imported from `orionis.support.patterns.final.meta` and `orionis.support.patterns.singleton.meta` respectively. `Final.__new__(metacls: type, name: str, bases: tuple[type, ...], namespace: dict[str, object]) -> type` marks a class and rejects a subclass of a marked base with `TypeError`.

`Singleton` provides `__init__(cls, name: str, bases: tuple[type, ...], namespace: dict[str, object]) -> None`, `__call__(cls, *args: object, **kwargs: object) -> object`, and `async __acall__(cls, *args: object, **kwargs: object) -> object`. The asynchronous constructor is explicitly awaited as `await MyClass.__acall__()`; `MyClass()` uses the synchronous path. Further behavior and concurrency details are in [the patterns manual](../patterns/docs/README.md).

### Performance

`PerformanceCounter() -> None` implements `IPerformanceCounter`. Its public API has paired synchronous/asynchronous operations: `start`/`astart`, `stop`/`astop`, `restart`/`arestart`, elapsed-time readers (`elapsedTime`, `aelapsedTime`, `getSeconds`, `agetSeconds`, `getMilliseconds`, `agetMilliseconds`, `getMicroseconds`, `agetMicroseconds`, `getMinutes`, `agetMinutes`), and `with`/`async with` context-manager methods. Readers require a completed measurement; mixing sync and async start/stop modes raises `RuntimeError`. See [the performance manual](../performance/docs/README.md) for complete signatures and exception conditions.

### Structures

`FreezeThaw` exposes static methods `freeze(obj: object) -> object` and `thaw(obj: object) -> object`. `freeze` maps mutable dictionaries/lists to `MappingProxyType`/tuples recursively; `thaw` maps supported container trees back to mutable dictionaries/lists. The private helper `_isContainer(obj: object) -> bool` is not part of the public API. See [the structures manual](../structures/docs/README.md) for identity and alias handling.

### System

`Workers` implements `IWorkers` with two class methods: `setRamPerWorker(cls, ram_per_worker: float) -> None` and `calculate(cls) -> int`. The first changes the class-level RAM budget used by the second. CPU and total RAM values are collected at module import. See [the system manual](../system/docs/README.md) for defaults and edge behavior.

### Types

The package exports `Collection`, `DotDict`, `MISSING`, `StdClass`, and `Stringable` from `orionis.support.types`. It also defines the contracts `ICollection` and `IStdClass` under `orionis.support.types.contracts`.

| Symbol | Constructor / main API | Behavior |
|---|---|---|
| `Collection` | `Collection(items: list[Any] | None = None) -> None` | List-oriented fluent operations, iteration, indexing, aggregation, filtering, grouping, and serialization. Several methods mutate and return the same collection; see its method table. |
| `DotDict` | `DotDict(*args, **kwargs)` (inherits `dict`) | Adds attribute access to mapping keys; absent attribute lookup returns `None`. |
| `MISSING` | Singleton value | Falsy marker whose representation is `"<MISSING>"`, used to distinguish omitted values from `None`. |
| `StdClass` | `StdClass(**kwargs: object) -> None` | Dynamic attribute container; `update`, `remove`, `toDict`, and class method `fromDict` operate on instance attributes. |
| `Stringable` | `Stringable(object: object = "") -> Stringable` | Immutable `str` subclass with fluent transformation, predicate, conversion, and callback methods. `encrypt`/`decrypt` delegate to the `Crypt` facade. |

The `types` subpackage also exports `ICollection` and `IStdClass` contracts. `DotDict` and `Stringable` have no dedicated contracts. See [the types manual](../types/docs/README.md) for the method catalogue and mutation/return semantics.

## Usage examples

### Common use: transform a collection

```python
from orionis.support.types import Collection, Stringable

names = Collection(["Ada Lovelace", "Grace Hopper"])
slugs = names.map(lambda name: Stringable(name).snake()).all()
print(slugs)
```

### Handle an exception as structured data

```python
from orionis.support.formatter.serializer import Parser

try:
    int("not-an-integer")
except ValueError as exc:
    payload = Parser.exception(exc).toDict()
    assert payload["error_type"] == "ValueError"
    assert payload["stack_trace"]
```

### Combine entity serialization and collection operations

```python
from dataclasses import dataclass

from orionis.support.entities import BaseEntity
from orionis.support.types import Collection


@dataclass(frozen=True)
class Product(BaseEntity):
    name: str
    price: int


products = Collection([
    Product("Notebook", 12),
    Product("Pen", 3),
])
payload = products.map(lambda product: product.toDict()).all()
assert payload[0] == {"name": "Notebook", "price": 12}
```

## Performance and concurrency considerations

> ⚠️ Not specified in the source code: thread-safety guarantees for concurrent changes to `DateTime` configuration, sharing a `PerformanceCounter` instance, or simultaneous mutation of `Collection`, `DotDict`, or `StdClass`.

- `DateTime` stores its default timezone, locale, and timezone cache on the class.
- `PerformanceCounter` has mutable state per instance.
- `Collection`, `DotDict`, and `StdClass` expose mutable data.
- `ExceptionParser` eagerly captures traceback metadata and caches the dictionary from `toDict()`. See its manual for cache behavior and returned object identity.
- `FreezeThaw` uses per-call traversal state and does not retain an input tree on the class.
- `Singleton` and facade concurrency/lifecycle details depend on their implementations in `patterns` and `container`; consult those module references rather than assuming one guarantee applies to every export.

## Compatibility notes

- The project declares `requires-python = ">=3.14"` in `pyproject.toml`. The support package follows that framework-wide minimum; the source does not declare a separate minimum for this package.
- Direct third-party imports in `orionis/support` are `dotty-dict>=1.3.1,<2.0` (`Collection`), `pendulum>=3.2.0,<4.0` (`DateTime`), and `psutil>=7.2.2,<8.0` (`Workers`). All are base project dependencies; no additional installation is required.
- `Stringable.encrypt()` and `Stringable.decrypt()` require the `Crypt` facade and its service binding. Other `types` helpers can be used directly without resolving a facade.
- Facade methods are owned by the contracts/services they proxy. Their signatures and lifecycle requirements may differ between services; consult the corresponding module documentation.
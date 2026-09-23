# `orionis.console`

> Command line runtime of Orionis: discovers commands, parses their arguments, runs them through the container, prints their output and schedules them over time.

## Table of contents

- [Functional description](#functional-description)
  - [Where it fits in the framework](#where-it-fits-in-the-framework)
  - [Command pipeline](#command-pipeline)
  - [File map](#file-map)
  - [Design decisions](#design-decisions)
- [API reference](#api-reference)
  - [`KernelCLI`](#kernelcli)
  - [`Reactor`](#reactor)
  - [`Loader`](#loader)
  - [`BaseCommand`](#basecommand)
  - [`Argument`](#argument)
  - [`Console`](#console)
  - [`ProgressBar`](#progressbar)
  - [`Dumper`](#dumper)
  - [`VarDumper`](#vardumper)
  - [`Executor`](#executor)
  - [`HelpCommand`](#helpcommand)
  - [`HTTPRequestPrinter`](#httprequestprinter)
  - [`Command` (fluent builder)](#command-fluent-builder)
  - [`Schedule`](#schedule)
  - [`Task` (fluent builder)](#task-fluent-builder)
  - [`ScheduleStore`](#schedulestore)
  - [`BaseScheduler` and `BaseTaskListener`](#basescheduler-and-basetasklistener)
  - [Entities](#entities)
  - [Enumerations](#enumerations)
  - [Built-in commands](#built-in-commands)
  - [Service providers](#service-providers)
- [Usage examples](#usage-examples)
  - [Declaring a custom command](#declaring-a-custom-command)
  - [Declaring arguments](#declaring-arguments)
  - [Registering a fluent command](#registering-a-fluent-command)
  - [Calling the reactor programmatically](#calling-the-reactor-programmatically)
  - [Reporting a failing command](#reporting-a-failing-command)
  - [Writing to the console](#writing-to-the-console)
  - [Dumping values while debugging](#dumping-values-while-debugging)
  - [Scheduling tasks](#scheduling-tasks)
- [Performance and concurrency considerations](#performance-and-concurrency-considerations)
- [Compatibility notes](#compatibility-notes)

## Functional description

### Where it fits in the framework

`orionis.console` is the CLI counterpart of `orionis.http`: the same `Application`
container serves both runtimes, but the console side is entered through the
`reactor` script at the project root, which calls
`Application.handleCommand(sys.argv)`.

The module owns four responsibilities:

1. **Discovery** — `Loader` collects the framework commands, the application
   commands under `app/console/commands/` and the fluent commands declared in
   `routes/console.py`.
2. **Execution** — `Reactor` parses arguments with `argparse`, builds the command
   class through the container, invokes it and turns the result into a process
   exit code.
3. **Output** — `Console`, `Executor`, `ProgressBar`, `VarDumper` and `Dumper`
   render everything the CLI prints.
4. **Scheduling** — `Schedule` and the fluent `Task` builder register command
   signatures on an APScheduler `AsyncIOScheduler`.

Direct dependencies on other Orionis modules: `orionis.container` (providers,
facades, scoped resolution), `orionis.foundation` (`IApplication`, core kernels,
core providers), `orionis.logging` (`ILogger`), `orionis.failure` (`ICatch`,
`KernelContext`), `orionis.cache` (`FileBasedCache` for the command metadata
cache), `orionis.introspection` (module discovery), `orionis.support`
(`PerformanceCounter`, `MISSING`, `DateTime`, facades), `orionis.database`
(`IConnectionManager`, used by the scheduler job store), `orionis.test`
(`ITestingEngine`, used by the `test` command).

### Command pipeline

```text
reactor (script)
  └─ Application.handleCommand(sys.argv)
       └─ KernelCLI.handle(args)            strips interpreter flags, routes "list"
            └─ Reactor.call(signature, args)
                 ├─ Application.beginScope()            scope["kernel"] = CONSOLE
                 ├─ PerformanceCounter.astart()
                 ├─ Loader.get(signature)               metadata → Command entity
                 ├─ Executor.running(signature)         "… RUNNING" line
                 ├─ ArgumentParser.parse_args(args)     MISSING values are dropped
                 ├─ Application.build(command.obj)      constructor injection
                 ├─ Application.call(instance, method)  method injection
                 ├─ Executor.done(signature, time)      "… DONE" line
                 └─ ILogger.info(...) / ICatch.exception(...) on failure
```

### File map

| Path | Contents |
|---|---|
| `__init__.py` | Re-exports `Argument`, `Console`, `Dumper`, `ProgressBar`. |
| `kernel.py` | `KernelCLI`, the CLI entry point registered in `CORE_KERNELS`. |
| `reactor_provider.py` | `ReactorProvider`: binds `IReactor` and pins the `Reactor` facade. |
| `scheduler_provider.py` | `ScheduleProvider`: binds `IScheduleStore` and `ISchedule`, pins the `Schedule` facade. |
| `args/argument.py` | `Argument`, the declarative `argparse` argument definition. |
| `base/` | `BaseCommand`, `BaseScheduler`, `BaseTaskListener` and their contracts. |
| `commands/` | The 17 built-in commands (`make:*`, `migrate:*`, `schedule:*`, `serve`, `test`, `about`, `list`, `optimize*`). |
| `contracts/` | `IKernelCLI`, `ISchedule`, `IScheduleStore`. |
| `core/commands.py` | `CORE_COMMANDS`, the immutable tuple of built-in command classes. |
| `core/loader.py` | `Loader`: discovery, metadata cache and `ArgumentParser` construction. |
| `core/reactor.py` | `Reactor`: dispatch, timing, logging and error handling. |
| `debug/dumper.py` | `Dumper.dd()` / `Dumper.dump()`. |
| `dynamic/progress_bar.py` | `ProgressBar`. |
| `entities/` | `Command`, `Task`, `SchedulerEvent`, `TaskEvent` data entities. |
| `enums/` | `ArgumentAction`, `ScheduleStates`, `SchedulerEvent`, `TaskEvent`, `ANSIColors`. |
| `fluent/command.py` | `Command`, the fluent builder used by `Reactor.command()`. |
| `fluent/task.py` | `Task`, the cron-like builder used by `Schedule.command()`. |
| `output/` | `Console`, `Executor`, `HelpCommand`, `HTTPRequestPrinter`, `VarDumper`. |
| `stubs/` | `.stub` templates used by the `make:*` commands. |
| `tasks/schedule.py` | `Schedule` plus the module level `_executeScheduledCommand`. |
| `tasks/store.py` | `ScheduleStore`: builds the Redis / SQLAlchemy job stores. |

### Design decisions

- **Contract first.** Every public piece has an ABC in a sibling `contracts/`
  package (`IReactor`, `ILoader`, `IKernelCLI`, `ISchedule`, `IScheduleStore`,
  `IConsole`, `IBaseCommand`, …). Providers bind the interface, so consumers can
  type-hint the contract and let the container inject the implementation.
- **Metadata, not instances.** `Loader` stores plain dictionaries (module path,
  class name, serialized arguments) and only imports a command class when it is
  actually executed. That keeps `list` cheap and makes the cache serializable.
- **`MISSING` instead of `None`.** `Argument.const` and `Argument.default`
  default to the `orionis.support.types.sentinel.MISSING` sentinel so an absent
  flag can be told apart from an explicit `None`; `Reactor` filters those keys
  out before calling the command.
- **Frozen, slotted `Argument`.** `Argument` is a `@dataclass(kw_only=True,
  frozen=True, slots=True)` that validates itself in `__post_init__`, so an
  invalid definition fails when the class is imported, not when the command runs.
- **Commands inherit the console.** `BaseCommand` extends `Console`, therefore
  `self.info(...)`, `self.table(...)` or `self.progressBar` are available inside
  `handle()` without extra wiring.
- **Module level scheduler callable.** APScheduler jobs are registered with the
  module level function `_executeScheduledCommand`, never a bound method, so a
  persistent job store can serialize the job as a `module:function` reference.
- **Single process server command.** `ServerCommand` implements `__new__` with a
  class level `RLock`, so `serve` is a singleton inside the process.

## API reference

### `KernelCLI`

`orionis.console.kernel.KernelCLI`, implements `IKernelCLI`. Registered in
`orionis/foundation/core_kernels.py` under the key `"KernelCLI"`.

```python
IGNORE_FLAGS: ClassVar[frozenset[str]] = frozenset({
    "reactor", "-c", "-m", "-", "-i", "-q", "-B", "-O", "-OO", "-v",
    "-vv", "-d", "-x", "-E", "-s", "-S", "-u", "-I", "-W",
})

_HELP_FLAGS: ClassVar[frozenset[str]] = frozenset({"help", "--help", "-h"})

__slots__ = ("__reactor",)

async def boot(self, application: IApplication) -> None: ...

async def handle(self, args: list[str] | None = None) -> int: ...
```

- `boot(application)` resolves `IReactor` from the container and stores it. It
  must run before `handle()`; `Application.handleCommand` does that once and
  caches the bound `handle` method.
- `handle(args)` normalises the argument list and dispatches:
  - raises `TypeError` with `"Arguments must be provided as a list."` when `args`
    is neither `None` nor a `list`;
  - drops the first token when it *contains* the substring `"reactor"` (so an
    absolute path such as `/usr/local/bin/reactor` is removed as well);
  - removes the leading run of tokens present in `IGNORE_FLAGS`;
  - calls `reactor.call("list")` when nothing is left or the first token is in
    `_HELP_FLAGS`;
  - otherwise returns `await reactor.call(args[0], args[1:])`.
- Side effect: the list received is modified in place (`del args[0]`,
  `del args[:i]`). The entry point passes `sys.argv`, which is consumed on
  purpose.
- The class declares `__slots__`, so an instance only holds the reactor
  reference and carries no instance dictionary.

### `Reactor`

`orionis.console.core.reactor.Reactor`, implements `IReactor`. Bound as a
singleton under the alias `"x-orionis-IReactor"`; reachable through the
`orionis.support.facades.reactor.Reactor` facade.

```python
def __init__(
    self,
    app: IApplication,
    loader: Loader,
    executer: Executor,
    logger: ILogger,
    catch: ICatch,
    performance_counter: PerformanceCounter,
) -> None: ...

def command(
    self,
    signature: str,
    handler: list[type[Any] | str | None] | str,
) -> ICommand: ...

async def info(self) -> list[dict]: ...

async def call(self, signature: str, args: list[str] | None = None) -> int: ...
```

- `command(signature, handler)` registers a fluent command and returns the
  builder. A bare class is normalised to `[handler, "__call__"]`; a list may
  carry the method name as its second element. Every constructor argument is
  injected by the container.
- `info()` returns one dictionary per registered command with the keys
  `timestamps`, `signature`, `description`, `arguments` (the
  `argparse.ArgumentParser` or `None`), `object` and `method`, sorted by
  signature. Signatures wrapped in double underscores are skipped. The result is
  memoised for the lifetime of the instance.
- `call(signature, args)` returns the exit code:
  - opens a container scope and sets `scope["kernel"] = KernelContext.CONSOLE`;
  - measures the run with `PerformanceCounter` and prints the `RUNNING` / `DONE`
    lines through `Executor` when `command.timestamps` is true and neither `-h`
    nor `--help` is present;
  - returns the value produced by the command when it is an `int`, otherwise `0`;
  - catches every `Exception`, logs it through `ILogger.error`, prints the `FAIL`
    line, prefixes the message with `[<Class>.<method>]`, delegates it to
    `ICatch.exception` and returns `1`. Failures never propagate to the caller.
- `SystemExit` raised by `argparse` is not caught: an invalid flag prints the
  command help and terminates the process with the argparse exit code; `-h`
  prints the help and exits with `0`.

### `Loader`

`orionis.console.core.loader.Loader`, implements `ILoader`. Built by the
container as a constructor dependency of `Reactor`.

```python
def __init__(self, app: IApplication) -> None: ...

async def get(self, signature: str) -> Command | None: ...

async def all(self) -> dict[str, Command]: ...

async def load(self) -> None: ...

def addFluentCommand(
    self,
    signature: str,
    handler: list[type[Any], str | None],
) -> ICommand: ...
```

- Discovery order: `CORE_COMMANDS` → classes under `app/console/commands/` that
  subclass `BaseCommand` → fluent commands imported from the console routing
  files. A later source overwrites an earlier one when the signature matches.
- Metadata caching: when `IApplication.compiled` is true the loader writes the
  metadata dictionary to a `FileBasedCache` named `commands` inside
  `IApplication.compiledPath`, invalidated by the configured monitored paths.
  When it is false, discovery runs on every process start.
- `get(signature)` imports and builds only the requested command;
  `all()` builds every discovered command.
- `addFluentCommand` raises `ValueError` when `handler` is not a list with at
  least one element and `TypeError` when the first element is not a class. The
  method name defaults to `"__call__"`.
- Serialization details: `Argument.type_` is stored as
  `"<module>.<qualname>"` and restored by import; `MISSING` is stored as the
  string `"__MISSING__"`; a `tuple` metavar is stored as a list. A type that can
  no longer be imported is restored as `None`.

### `BaseCommand`

`orionis.console.base.command.BaseCommand`, extends `Console` and implements
`IBaseCommand`. Importable as `from orionis.console.base import BaseCommand`.

```python
timestamps: bool = True
signature: str
description: str
arguments: ClassVar[list[Argument]] = []

def __init__(self) -> None: ...

async def handle(self) -> None: ...

def getArgument(self, key: str, default: Any | None = None) -> Any | None: ...

def getArguments(self) -> dict[str, Any]: ...

def setArguments(self, args: dict[str, Any]) -> None: ...
```

- `signature` is mandatory and validated by the loader: it must be a non-empty
  string matching `^[a-zA-Z][a-zA-Z0-9_:]*[a-zA-Z0-9]$|^[a-zA-Z]$`.
- `handle()` is the entry point; subclasses may declare extra parameters, which
  the container resolves. The inherited implementation raises
  `NotImplementedError`.
- `getArgument(key, default)` raises `TypeError` when `key` is not a string and
  returns `default` when the key is absent — including flags whose value stayed
  `MISSING` and were therefore filtered out by the reactor.
- `getArguments()` returns a shallow copy; `setArguments()` merges the given
  dictionary into the internal one and raises `TypeError` when it is not a dict.
- All `Console` methods are available on `self`.

### `Argument`

`orionis.console.args.argument.Argument`, a
`@dataclass(kw_only=True, frozen=True, slots=True)` extending `BaseEntity`.
Importable as `from orionis.console import Argument`.

```python
name_or_flags: str | Iterable[str]
action: str | ArgumentAction | None = None
nargs: int | str | None = None
const: Any = MISSING
default: Any = MISSING
type_: Callable[[str], Any] | None = None
choices: Iterable[Any] | None = None
required: bool = False
help: str | None = None
metavar: str | tuple[str, ...] | None = None
dest: str | None = None
version: str | None = None
extra: dict[str, Any] = field(default_factory=dict)

def addToParser(self, parser: argparse.ArgumentParser) -> None: ...
```

Validation performed in `__post_init__`:

| Condition | Exception |
|---|---|
| Empty `name_or_flags` | `ValueError` |
| A flag that is not a string | `TypeError` |
| `-h` or `--help` among the flags | `ValueError` |
| `action` that is not `str`, `ArgumentAction` or `None` | `TypeError` |
| `nargs` that is not `int`, `str` or `None` | `TypeError` |
| String `nargs` outside `{"?", "*", "+"}` | `ValueError` |
| Non callable `type_` | `TypeError` |
| `type_` combined with `store_true`, `store_false`, `store_const` or `append_const` | `TypeError` |
| `choices` given as a string, or not iterable | `TypeError` |
| `required` that is not a `bool` | `TypeError` |

`name_or_flags` is normalised to a `tuple[str, ...]`. `addToParser` forwards the
populated fields to `parser.add_argument`, together with everything inside
`extra`.

### `Console`

`orionis.console.output.console.Console`, implements `IConsole`. It is the base
class of `BaseCommand` and `BaseTaskListener`, and it can also be instantiated
directly. Importable as `from orionis.console import Console`.

| Group | Methods |
|---|---|
| Banner messages (prefix + timestamp) | `success(message, *, timestamp=True)`, `info(...)`, `warning(...)`, `fail(...)`, `error(...)` |
| Plain coloured text | `textSuccess`, `textSuccessBold`, `textInfo`, `textInfoBold`, `textWarning`, `textWarningBold`, `textError`, `textErrorBold`, `textMuted`, `textMutedBold`, `textUnderline` |
| Layout | `clear()`, `clearLine()`, `line()`, `newLine(count=1)`, `write(*values, sep=' ', end='\n', file=None, flush=False)`, `writeLine(message)` |
| Input | `ask(question)`, `confirm(question, *, default=False)`, `secret(question)`, `anticipate(question, options, default=None)`, `choice(question, choices, default_index=0)` |
| Rich output | `table(headers, rows)`, `exception(exception)`, `dump(*args, ...)` |
| Process control | `exitSuccess(message=None)`, `exitError(message=None)` |
| Misc | `progressBar` (property), `sleep(seconds)` (async) |

- `progressBar` returns a **new** `ProgressBar()` on every access, built with the
  defaults `total=100, width=50`.
- `exitSuccess` / `exitError` call `sys.exit(0)` / `sys.exit(1)` and fall back to
  `os._exit` with the same code if `SystemExit` is swallowed.
- `exception(exception)` renders a `rich.traceback.Traceback`.
- `dump(...)` uses `VarDumper` with `show_types=True` by default, unlike
  `Dumper.dump(...)`, whose default is `False`.
- `sleep(seconds)` awaits `asyncio.sleep`; it is the only coroutine of the class.

### `ProgressBar`

`orionis.console.dynamic.progress_bar.ProgressBar`, implements `IProgressBar`.
Importable as `from orionis.console import ProgressBar`.

```python
def __init__(self, total: int = 100, width: int = 50) -> None: ...

def start(self) -> None: ...

def advance(self, increment: int = 1) -> None: ...

def finish(self) -> None: ...
```

The bar is drawn with `\r` over a single line using the block characters `█` and
`░`, writing directly to `sys.stdout`. `finish()` completes the bar and emits a
newline.

### `Dumper`

`orionis.console.debug.dumper.Dumper`, implements `IDumper`; both members are
`@staticmethod`. Importable as `from orionis.console import Dumper`.

```python
@staticmethod
def dd(
    *args: tuple[Any],
    show_types: bool = False,
    show_index: bool = False,
    expand_all: bool = True,
    max_depth: int | None = None,
    module_path: str | None = None,
    line_number: int | None = None,
    redirect_output: bool = False,
    insert_line: bool = False,
) -> None: ...

@staticmethod
def dump(
    *args: tuple[Any],
    show_types: bool = False,
    show_index: bool = False,
    expand_all: bool = True,
    max_depth: int | None = None,
    module_path: str | None = None,
    line_number: int | None = None,
    redirect_output: bool = False,
    insert_line: bool = False,
) -> None: ...
```

Both build a `VarDumper` chain with the same options; the only difference is
`forceExit`: `dd` sets it to `True` (the process stops after printing) and
`dump` to `False`. When `module_path` / `line_number` are omitted, the header
shows the location inside `orionis.console.debug.dumper` itself.

### `VarDumper`

`orionis.console.output.var_dumper.VarDumper`, implements `IVarDumper`. Fluent
object behind `Dumper` and `Console.dump`.

```python
def showTypes(self, *, show: bool = True) -> VarDumper: ...
def showIndex(self, *, show: bool = True) -> VarDumper: ...
def expandAll(self, *, expand: bool = True) -> VarDumper: ...
def maxDepth(self, depth: int | None) -> VarDumper: ...
def modulePath(self, path: str | None) -> VarDumper: ...
def lineNumber(self, number: int | None) -> VarDumper: ...
def forceExit(self, *, force: bool = True) -> VarDumper: ...
def redirectOutput(self, *, redirect: bool = True) -> VarDumper: ...
def values(self, *args: tuple | list) -> VarDumper: ...
def value(self, value: type[T]) -> VarDumper: ...
def print(self, *, insert_line: bool = False) -> None: ...
def toHtml(self, *, insert_line: bool = False) -> str: ...
```

`print()` writes the Rich panel; `toHtml()` returns the same rendering as an
HTML string instead of printing it.

### `Executor`

`orionis.console.output.executor.Executor`, implements `IExecutor`. Stateless;
injected into `Reactor` and reused by the migration commands.

```python
def running(self, program: str, time: str = "") -> None: ...
def done(self, program: str, time: str = "") -> None: ...
def fail(self, program: str, time: str = "") -> None: ...
```

Each call prints one line shaped as
`<timestamp> | <program> ...... ~ <time> <STATE>`, padded with dots.

### `HelpCommand`

`orionis.console.output.help_command.HelpCommand`, implements `IHelpCommand`;
both members are `@staticmethod`.

```python
@staticmethod
def parseActions(actions: list[argparse.Action]) -> dict[str, Any]: ...

@staticmethod
def printActions(
    command_name: str,
    actions: list[argparse.Action],
    *,
    is_error: bool = False,
) -> None: ...
```

`Reactor` calls `printActions` when `argparse` raises `SystemExit`, so a bad flag
and `--help` share the same rendering; `is_error` switches the styling.

### `HTTPRequestPrinter`

`orionis.console.output.http_request.HTTPRequestPrinter`, implements
`IHTTPRequestPrinter`. Used by the HTTP runtime, not by the command pipeline.

```python
def setEnabled(self, *, enabled: bool) -> None: ...
async def start(self) -> None: ...
async def stop(self) -> None: ...
def startTimer(self) -> float | None: ...
def printRequest(self, adapter: TransportAdapter, response: Response) -> None: ...
```

`start()` launches an internal worker coroutine that drains the print queue, so
request logging never blocks the response path; `stop()` shuts it down.

### `Command` (fluent builder)

`orionis.console.fluent.command.Command`, implements `ICommand`. Returned by
`Reactor.command(...)`; not meant to be instantiated by hand.

```python
def __init__(
    self,
    signature: str,
    concrete: Callable[..., Any],
    method: str = "handle",
) -> None: ...

def timestamp(self, *, enabled: bool = True) -> Self: ...
def description(self, desc: str) -> Self: ...
def arguments(self, args: list[Argument]) -> Self: ...
def get(self) -> tuple[str, CommandEntity]: ...
```

The constructor raises `TypeError` when `concrete` is not callable or `method` is
not a string, and `AttributeError` when `concrete` has no callable attribute
named `method`. Defaults: timestamps enabled, description
`"No description provided."`, empty argument list. `get()` returns the
`(signature, Command)` pair consumed by the loader.

### `Schedule`

`orionis.console.tasks.schedule.Schedule`, implements `ISchedule`. Bound as a
singleton to `ISchedule` and reachable through the
`orionis.support.facades.schedule.Schedule` facade. Wraps an APScheduler
`AsyncIOScheduler`.

```python
def __init__(
    self,
    reactor: IReactor,
    exception_handler: ICatch,
    stores: IScheduleStore,
) -> None: ...

def command(
    self,
    signature: str,
    args: list[str] | None = None,
    purpose: str | None = None,
) -> ITask: ...

def on(self, event: SchedulerEvent, listener: Callable) -> Self: ...
async def info(self) -> list[dict]: ...
async def boot(self) -> None: ...
def state(self) -> str: ...
def isRunning(self) -> bool: ...
def isPaused(self) -> bool: ...
def isStopped(self) -> bool: ...
def pauseTask(self, signature: str) -> bool: ...
def resumeTask(self, signature: str) -> bool: ...
def removeTask(self, signature: str) -> bool: ...
def removeAllTasks(self) -> bool: ...
def pause(self) -> bool: ...
def resume(self) -> bool: ...
def shutdown(self, wait: int | None = None) -> None: ...
async def wait(self) -> None: ...
```

- `command(...)` and `on(...)` are **declaration time only**: both raise
  `RuntimeError` once the scheduler has left the `STOPPED` state. `command`
  raises `TypeError` when the signature is not a non-empty string or when `args`
  is not a list of strings.
- `info()` validates the declared tasks against the signatures known to the
  reactor and raises `ValueError` for an unknown one. Each entry carries
  `signature`, `args`, `kwargs`, `purpose`, `random_delay`, `coalesce`,
  `max_instances`, `misfire_grace_time`, `start_date`, `end_date` and `details`.
- `boot()` registers every job **before** calling `AsyncIOScheduler.start()`, adds
  the `memory` job store plus the configured one, subscribes the scheduler and
  task listeners, silences the APScheduler loggers and moves the state to
  `RUNNING`. Jobs are added with `replace_existing` taken from
  `scheduler.replace_existing` in the configuration.
- Task control methods raise `RuntimeError` when the scheduler has not booted
  (`"The Orionis task scheduler has not been started."`) or when the task is not
  in the expected state, and `ValueError` when the job does not exist.
- `shutdown(wait)` schedules a graceful shutdown as a managed task: it sleeps
  `wait` seconds (default `0.5`), awaits the in-flight listener tasks, shuts the
  scheduler down in an executor and sets the internal event. `wait` must be a
  non-negative `int` that is not a `bool`, otherwise `TypeError` is raised;
  passing `None` keeps the current value.
- `wait()` blocks until that shutdown event is set.
- The job callable is the module level coroutine
  `_executeScheduledCommand(signature, args)`, which dispatches through the
  `Reactor` facade.

### `Task` (fluent builder)

`orionis.console.fluent.task.Task`, implements `ITask`. Returned by
`Schedule.command(...)`.

Configuration methods return `Self` for chaining:

| Method | Effect |
|---|---|
| `purpose(purpose)` | Human readable name reported by `schedule:list`. |
| `coalesce(*, coalesce=True)` | Collapse missed runs into one. |
| `misfireGraceTime(seconds=60)` | Seconds of tolerance for a late run. |
| `maxInstances(max_instances)` | Concurrent runs allowed for the job. |
| `randomDelay(max_seconds=10)` | Jitter; patches the trigger in place when one already exists. |
| `startDate(year, month, day, hour=0, minute=0, second=0)` | Lower bound of the schedule window. |
| `endDate(year, month, day, hour=0, minute=0, second=0)` | Upper bound of the schedule window. |
| `on(event, callback)` | Register a callback for a `TaskEvent`. |
| `registerListener(listener)` | Register every `onTask*` method of a `BaseTaskListener`. |

Trigger methods return `bool` and **replace** any previously configured trigger:

| Family | Members |
|---|---|
| One shot | `onceAt(year, month, day, hour=0, minute=0, second=0)` |
| Seconds | `everySeconds(seconds)`, `everyFiveSeconds()` … `everyFiftyFiveSeconds()` |
| Minutes | `everyMinutes(minutes)`, `everyMinuteAt(seconds)`, `everyMinutesAt(minutes, seconds)`, `everyFiveMinutes()` … `everyFiftyFiveMinutes()` and their `…At(seconds)` variants |
| Hours | `hourly()`, `hourlyAt(minute, second=0)`, `everyOddHours()`, `everyEvenHours()`, `everyHours(hours)`, `everyHoursAt(hours, minute, second=0)`, `everyTwoHours()` … `everyTwelveHours()` and their `…At(minute, second=0)` variants |
| Days | `daily()`, `dailyAt(hour, minute=0, second=0)`, `everyDays(days)`, `everyDaysAt(days, hour, minute=0, second=0)`, `everyTwoDays()` … `everySevenDays()` and their `…At(...)` variants |
| Weekdays | `everyMondayAt(hour, minute=0, second=0)` … `everySundayAt(...)` |
| Weeks | `weekly()`, `everyWeeks(weeks)` |
| Generic | `every(weeks=0, days=0, hours=0, minutes=0, seconds=0)`, `cron(year=None, month=None, day=None, week=None, day_of_week=None, hour=None, minute=None, second=None)` |

Out of range values raise `ValueError` with the messages
`"Interval value must be a positive integer."`, `"Minute must be between 0 and
59."`, `"Second must be between 0 and 59."` or `"Hour must be between 0 and
23."`.

```python
def entity(
    self,
    random_delay: int | None = 0,
    max_instances: int | None = 1,
    misfire_grace_time: int | None = 0,
    *,
    coalesce: bool | None = True,
) -> TaskEntity: ...
```

`entity(...)` materialises the `Task` entity consumed by `Schedule.boot()`. The
values configured on the task win over the arguments, which carry the global
defaults from the `scheduler` configuration section.

### `ScheduleStore`

`orionis.console.tasks.store.ScheduleStore`, implements `IScheduleStore`. Bound
as a singleton to `IScheduleStore` so it can be injected into `Schedule`.

```python
def __init__(self, app: IApplication, db_manager: IConnectionManager) -> None: ...

@property
def store(self) -> str: ...

@property
def config(self) -> ConfigScheduler: ...

def redis(self) -> RedisJobStore: ...

def database(self) -> SQLAlchemyJobStore: ...
```

The constructor materialises `Scheduler(**app.config("scheduler"))`. `store`
returns the configured driver name; `config` exposes the whole entity (`jitter`,
`max_instances`, `misfire_grace_time`, `coalesce`, `replace_existing`, …).
`redis()` and `database()` raise `RuntimeError` when the matching
`scheduler.stores.*` section was never configured; `database()` builds a
synchronous SQLAlchemy engine URL, so the sync driver of the selected connection
must be installed.

### `BaseScheduler` and `BaseTaskListener`

```python
class BaseScheduler(IBaseScheduler):
    async def tasks(self, schedule: ISchedule) -> None: ...
    async def onStarted(self, event: SchedulerEvent) -> None: ...
    async def onPaused(self, event: SchedulerEvent) -> None: ...
    async def onResumed(self, event: SchedulerEvent) -> None: ...
    async def onShutdown(self, event: SchedulerEvent) -> None: ...

class BaseTaskListener(Console, IBaseTaskListener):
    async def onTaskAdded(self, event: TaskEvent) -> None: ...
    async def onTaskRemoved(self, event: TaskEvent) -> None: ...
    async def onTaskExecuted(self, event: TaskEvent) -> None: ...
    async def onTaskError(self, event: TaskEvent) -> None: ...
    async def onTaskMissed(self, event: TaskEvent) -> None: ...
    async def onTaskSubmitted(self, event: TaskEvent) -> None: ...
    async def onTaskMaxInstances(self, event: TaskEvent) -> None: ...
```

`BaseScheduler` is the base class of `app/console/scheduler.py`: `tasks()` is the
declaration hook and the `on*` methods are lifecycle hooks. It does **not**
extend `Console`. `BaseTaskListener` does, so a listener can print directly.
Both may be implemented with synchronous methods: the dispatcher accepts either
form. Constructor dependencies of both classes are injected by the container.

### Entities

All of them extend `BaseEntity` (`toDict()`, `getFields()`).

```python
@dataclass(kw_only=True)
class Command(BaseEntity):
    obj: type
    method: str = "handle"
    timestamps: bool = True
    signature: str
    description: str
    args: list[Argument] | argparse.ArgumentParser | None = None

@dataclass(kw_only=True)
class Task(BaseEntity):
    signature: str
    args: list[str] | None = field(default_factory=list)
    kwargs: dict | None = field(default_factory=dict)
    purpose: str | None = None
    random_delay: int | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    trigger: CronTrigger | DateTrigger | IntervalTrigger | None = None
    details: str | None = None
    max_instances: int | None = 1
    misfire_grace_time: int | None = None
    coalesce: bool | None = True
    listeners: list[Callable[..., None]] = field(default_factory=list)

@dataclass(kw_only=True)
class SchedulerEvent(BaseEntity):
    code: int
    description: str = field(default="")
    jobstore: str = field(default="memory")

@dataclass(kw_only=True)
class TaskEvent(BaseEntity):
    code: int
    description: str = field(default="")
    signature: str
    jobstore: str = field(default="memory")
    scheduled_run_times: Any | None = field(default=None)
    scheduled_run_time: Any | None = field(default=None)
    retval: Any | None = field(default=None)
    exception: Any | None = field(default=None)
    traceback: Any | None = field(default=None)
```

`Command.args` carries the declarative `list[Argument]` while the fluent builder
is defining the command, and the `argparse.ArgumentParser` that `Loader` builds
from that list once the command is materialised — which is the form `Reactor`
reads. `SchedulerEvent.__post_init__` and `TaskEvent.__post_init__` fill
`description` from `code`.

### Enumerations

| Enum | Members |
|---|---|
| `ArgumentAction(Enum)` | `STORE`, `STORE_CONST`, `STORE_TRUE`, `STORE_FALSE`, `APPEND`, `APPEND_CONST`, `COUNT`, `HELP`, `VERSION` |
| `ScheduleStates(Enum)` | `STOPPED`, `RUNNING`, `PAUSED` |
| `SchedulerEvent(IntEnum)` | `STARTED = 2**0`, `SHUTDOWN = 2**1`, `PAUSED = 2**2`, `RESUMED = 2**3` |
| `TaskEvent(IntEnum)` | `ADDED = 2**9`, `REMOVED = 2**10`, `MODIFIED = 2**11`, `EXECUTED = 2**12`, `ERROR = 2**13`, `MISSED = 2**14`, `SUBMITTED = 2**15`, `MAX_INSTANCES = 2**16` |
| `ANSIColors(Enum)` | 24 escape sequences used by `Console` (`TEXT_INFO`, `BG_SUCCESS`, `TEXT_BOLD_ERROR`, …) |

The event enums are `IntEnum` powers of two because APScheduler subscribes to a
bit mask; `orionis.console.enums` exports the enum flags while
`orionis.console.entities` exports the event payloads with the same names.

### Built-in commands

`CORE_COMMANDS` (`orionis/console/core/commands.py`) is a tuple of 17 classes:

| Signature | Class | Notes |
|---|---|---|
| `about` | `VersionCommand` | Framework metadata panel. |
| `list` | `HelpCommand` | Default target when no command is given. |
| `make:command` | `MakeCommand` | `name`, `--signature/-s`, `--description/-d`. |
| `make:provider` | `MakeProvider` | `name`, `--deferred`. |
| `make:task:listener` | `MakeTaskListener` | `name`. |
| `migrate` | `MigrateCommand` | `--database/-d`. |
| `migrate:fresh` | `MigrateFreshCommand` | Drops and re-runs everything. |
| `migrate:refresh` | `MigrateRefreshCommand` | `--step/-s`. |
| `migrate:reset` | `MigrateResetCommand` | Reverts every migration. |
| `migrate:rollback` | `MigrateRollbackCommand` | `--step/-s`, defaults to the last batch. |
| `migrate:status` | `MigrateStatusCommand` | Status table. |
| `optimize` | `OptimizeCommand` | `compileall` at optimisation level 2. |
| `optimize:clear` | `OptimizeClearCommand` | Removes caches, bytecode and build artefacts. |
| `schedule:list` | `ScheduleListCommand` | Table of declared tasks. |
| `schedule:work` | `ScheduleWorkCommand` | Runs the scheduler until interrupted. |
| `serve` | `ServerCommand` | `--interface/-i`, `--port/-p`, `--log`, `--export`. |
| `test` | `TestCommand` | `--verbosity/-v`, `--fail-fast/-f`, `--start-dir/-s`, `--file-pattern`, `--method-pattern`, `--panel`, `--no-panel`. |

`MigrationCommand` (`commands/migrate/base_command.py`) is the shared base of the
`migrate:*` family: it exposes `targetConnection()`, `progressEvents()` and
`reportEmpty(message)`, and contributes the `--database/-d` argument.

`test` returns a non-zero exit code when any result is `FAILED` or `ERRORED`, so
it can gate a CI pipeline.

### Service providers

```python
class ReactorProvider(ServiceProvider):
    def register(self) -> None: ...
    async def boot(self) -> None: ...

class ScheduleProvider(ServiceProvider):
    def register(self) -> None: ...
    async def boot(self) -> None: ...
```

Both are listed in `CORE_PROVIDERS` and neither is deferred.

- `ReactorProvider.register()` binds `IReactor → Reactor` as a singleton with the
  alias `"x-orionis-IReactor"`, which is exactly the accessor returned by the
  `Reactor` facade. `boot()` pins that facade.
- `ScheduleProvider.register()` binds `IScheduleStore → ScheduleStore` **before**
  `ISchedule → Schedule`, because `Schedule` declares `IScheduleStore` as a
  constructor dependency and an interface is only auto-resolvable once it owns an
  explicit binding. `boot()` pins the `Schedule` facade.

## Usage examples

### Declaring a custom command

Any subclass of `BaseCommand` placed under `app/console/commands/` is discovered
automatically.

```python
# app/console/commands/greet_command.py
from orionis.console import Argument
from orionis.console.base import BaseCommand


class GreetCommand(BaseCommand):

    signature: str = "app:greet"

    description: str = "Greets a user from the console."

    arguments = [
        Argument(
            name_or_flags=["--name", "-n"],
            type_=str,
            required=False,
            help="Name to greet. Defaults to 'world'.",
        ),
        Argument(
            name_or_flags=["--shout"],
            action="store_true",
            help="Print the greeting in upper case.",
        ),
    ]

    async def handle(self) -> None:
        """
        Print the greeting requested through the command line.

        Returns
        -------
        None
            The greeting is written to the console.
        """
        name: str = self.getArgument("name", "world")
        message = f"Hello, {name}!"
        if self.getArgument("shout", default=False):
            message = message.upper()
        self.success(message)
```

```text
$ python reactor app:greet --name Ada

2026-09-01 19:12:50 | app:greet ............................................  RUNNING
 SUCCESS  2026-09-01 19:12:50 Hello, Ada!
2026-09-01 19:12:50 | app:greet .......................................  ~ 0.04s DONE

$ python reactor app:greet --shout

2026-09-01 19:12:56 | app:greet ............................................  RUNNING
 SUCCESS  2026-09-01 19:12:56 HELLO, WORLD!
2026-09-01 19:12:56 | app:greet .......................................  ~ 0.02s DONE
```

### Declaring arguments

`Argument` is a plain description of an `argparse` argument, so it can be used
outside a command as well.

```python
import argparse

from orionis.console import Argument
from orionis.console.enums.actions import ArgumentAction

parser = argparse.ArgumentParser(prog="app:report", add_help=False)

Argument(
    name_or_flags="name",
    type_=str,
    required=True,
    help="Report owner.",
).addToParser(parser)

Argument(
    name_or_flags=["--format", "-f"],
    type_=str,
    choices=["csv", "json"],
    default="json",
    help="Output format.",
).addToParser(parser)

Argument(
    name_or_flags=["--verbose"],
    action=ArgumentAction.STORE_TRUE,
    help="Print every processed row.",
).addToParser(parser)

print(vars(parser.parse_args(["Ada", "-f", "csv", "--verbose"])))
print(vars(parser.parse_args(["Ada"])))

try:
    Argument(name_or_flags=["--flag"], action="store_true", type_=int)
except TypeError as exc:
    print(f"TypeError: {str(exc).split('.')[0]}.")

try:
    Argument(name_or_flags=["-h"])
except ValueError as exc:
    print(f"ValueError: {exc}")
```

```text
{'name': 'Ada', 'format': 'csv', 'verbose': True}
{'name': 'Ada', 'format': 'json', 'verbose': <MISSING>}
TypeError: 'type_' is not compatible with action='store_true'.
ValueError: Custom help flags '-h' and '--help' are not allowed.
```

The second line shows the `MISSING` sentinel left by a flag that was not passed.
`Reactor` removes those keys before invoking the command, which is why
`getArgument("verbose", default=False)` returns `False` instead of the sentinel.

### Registering a fluent command

Any class can become a command without inheriting from `BaseCommand`.

```python
# routes/console.py
from app.services.welcome_service import WelcomeService
from orionis.console.args.argument import Argument
from orionis.support.facades.reactor import Reactor

Reactor.command("app:test", [WelcomeService, "greetUser"])\
       .timestamp()\
       .description("Command Test Defined as Route")\
       .arguments([
            Argument(
                name_or_flags=["--name", "-n"],
                type_=str,
                required=False,
            ),
       ])
```

```text
$ python reactor app:test --name Ada

2026-09-01 19:13:07 | app:test .............................................  RUNNING
Hello, Ada! Welcome to Orionis Framework.
2026-09-01 19:13:08 | app:test .........................................  ~ 1.3s DONE
```

### Calling the reactor programmatically

The reactor is a regular container service, so it can be resolved and driven from
any script.

```python
import asyncio

from bootstrap.app import app
from orionis.console.core.contracts.reactor import IReactor
from orionis.support.facades.reactor import Reactor


async def main() -> None:
    await Reactor.pin()
    reactor: IReactor = await app.make(IReactor)

    signatures = [command["signature"] for command in await reactor.info()]
    print(len(signatures), "commands")
    print(signatures)


asyncio.run(main())
```

```text
19 commands
['about', 'app:inspire', 'app:test', 'list', 'make:command', 'make:provider', 'make:task:listener', 'migrate', 'migrate:fresh', 'migrate:refresh', 'migrate:reset', 'migrate:rollback', 'migrate:status', 'optimize', 'optimize:clear', 'schedule:list', 'schedule:work', 'serve', 'test']
```

The 19 signatures are the 17 built-in commands plus the two declared by this
project (`app:inspire` as a class, `app:test` as a fluent route).

`await Reactor.pin()` is required in a plain script: eager providers only boot
under the CLI or HTTP runtime, so the facade is still unpinned and
`routes/console.py` — imported during discovery — would fail with
`AttributeError: '_FacadeDispatch' object has no attribute 'timestamp'`. The
error only shows up when the command metadata cache is cold, because a warm
cache skips the import of the routing files altogether.

### Reporting a failing command

`Reactor.call` never lets an exception escape: it hands it to `ICatch`, which
prints the traceback, and returns `1`.

```python
import asyncio

from bootstrap.app import app
from orionis.console.core.contracts.reactor import IReactor
from orionis.support.facades.reactor import Reactor


async def main() -> None:
    await Reactor.pin()
    reactor: IReactor = await app.make(IReactor)

    exit_code = await reactor.call("does:not:exist")
    print("missing command exit code:", exit_code)


asyncio.run(main())
```

Tail of the output; the Rich traceback rendered by `ICatch` is printed above
these two lines and is omitted here because it contains absolute paths:

```text
ValueError: Command 'does:not:exist' not found.
missing command exit code: 1
```

### Writing to the console

`Console` can be instantiated directly; inside a command the very same methods
are available on `self`.

```python
from orionis.console import Console

console = Console()
console.textInfoBold("Deploying release 2.7.0")
console.textMuted("target: production")
console.textSuccess("done")
console.line()

console.table(
    ["Service", "Status"],
    [["api", "running"], ["worker", "stopped"]],
)
```

```text
Deploying release 2.7.0
target: production
done

┌─────────┬─────────┐
│ Service │ Status  │
├─────────┼─────────┤
│ api     │ running │
│ worker  │ stopped │
└─────────┴─────────┘
```

### Dumping values while debugging

```python
from orionis.console import Dumper

Dumper.dump({"user": "ada", "roles": ["admin", "dev"]}, show_types=True)
```

```text
🐞 Module(orionis.console.debug.dumper) #111
╭─ dict ──────────────────────────────────────────────────────────╮
│                                                                 │
│ {                                                               │
│ │ 'user': 'ada',                                                │
│ │ 'roles': [                                                    │
│ │ │ 'admin',                                                    │
│ │ │ 'dev'                                                       │
│ │ ]                                                             │
│ }                                                               │
╰─────────────────────────────────────────────────────────────────╯
```

Replace `dump` with `dd` to stop the process right after printing. The panel is
drawn by Rich, so its width follows the terminal.

### Scheduling tasks

Application tasks are declared in `app/console/scheduler.py`, inside the `tasks`
hook of a `BaseScheduler` subclass:

```python
# app/console/scheduler.py
from orionis.console.base import BaseScheduler
from orionis.console.contracts import ISchedule


class Scheduler(BaseScheduler):

    def tasks(self, schedule: ISchedule) -> None:
        """
        Declare the scheduled commands of the application.

        Parameters
        ----------
        schedule : ISchedule
            Scheduler injected by the framework.

        Returns
        -------
        None
            Tasks are registered as a side effect.
        """
        schedule.command("app:inspire", purpose="Daily quote").dailyAt(7, 30)
        schedule.command("app:test", ["--name", "Ada"]).everyFiveSeconds()
```

The same API works from a script, which is handy to inspect what would be
registered before running `schedule:work`:

```python
import asyncio

from bootstrap.app import app
from orionis.console.contracts import ISchedule
from orionis.support.facades.reactor import Reactor


async def main() -> None:
    await Reactor.pin()
    schedule: ISchedule = await app.make(ISchedule)

    schedule.command("app:inspire", purpose="Daily quote").dailyAt(7, 30)
    schedule.command("app:test", ["--name", "Ada"]).everyFiveSeconds()

    print("state:", schedule.state())
    for task in await schedule.info():
        print(task)

    try:
        schedule.command("app:missing").hourly()
        await schedule.info()
    except ValueError as exc:
        print(f"ValueError: {exc}")


asyncio.run(main())
```

```text
state: STOPPED
{'signature': 'app:inspire', 'args': [], 'kwargs': {}, 'purpose': 'Daily quote', 'random_delay': 0, 'coalesce': True, 'max_instances': 1, 'misfire_grace_time': 30, 'start_date': None, 'end_date': None, 'details': 'Every day at 07:30:00'}
{'signature': 'app:test', 'args': ['--name', 'Ada'], 'kwargs': {}, 'purpose': None, 'random_delay': 0, 'coalesce': True, 'max_instances': 1, 'misfire_grace_time': 30, 'start_date': None, 'end_date': None, 'details': 'Every 5 seconds'}
ValueError: Task signature 'app:missing' is not available in the reactor.
```

`random_delay`, `coalesce`, `max_instances` and `misfire_grace_time` come from
the `scheduler` configuration section unless the task overrides them.

## Performance and concurrency considerations

- **Everything is `asyncio`.** `handle()` may be declared `async def` or
  `def`; the container awaits the result when it is a coroutine. `Reactor.call`
  runs inside the loop created by `Loop.run(...)` in the `reactor` script.
- **Lazy imports.** `Loader` keeps metadata only and imports a command module the
  first time it is executed, caching the imported module in a dictionary. A
  process that runs one command never imports the other sixteen.
- **Metadata cache.** With `compiled=True` the discovery result is written to
  `storage/framework/bootstrap` (a `FileBasedCache` entry named `commands`). The
  cache is invalidated through the monitored paths configured on the application;
  changes under `orionis/` itself are not monitored, so editing the framework
  requires clearing that folder (or running `optimize:clear`).
- **Memoised listings.** `Reactor.info()` caches its result per instance, and
  `Schedule` caches the set of available signatures after the first lookup.
- **Scoped resolution.** Each `Reactor.call` opens its own container scope; scoped
  services do not leak between two commands executed in the same process.
- **Scheduler concurrency.** `AsyncIOScheduler` runs jobs on the same event loop.
  `max_instances` (default `1`) bounds the concurrent runs of a signature and
  `coalesce` collapses missed runs. Listener callbacks are wrapped in managed
  `asyncio.Task` objects tracked in a set and awaited during
  `shutdown()`; `Schedule.__gracefulShutdown` performs the blocking APScheduler
  shutdown in an executor to keep the loop responsive.
- **No locks in the command path.** Neither `Loader` nor `Reactor` declare any
  synchronisation primitive: both assume a single command per process, which is
  how the CLI entry point uses them. The only lock in the module is the class
  level `RLock` guarding `ServerCommand.__new__`.
- **Direct stdout writes.** `ProgressBar` caches `sys.stdout.write` /
  `sys.stdout.flush` and repaints one line with `\r`; interleaving it with other
  output on the same line garbles the rendering.
- **APScheduler logging.** `Schedule.boot()` disables the `apscheduler`,
  `apscheduler.executors` and `apscheduler.scheduler` loggers, so their records
  never reach the application logging channels.

## Compatibility notes

- Python `>= 3.14` (`requires-python` in `pyproject.toml`). The module relies on
  PEP 604 unions, `typing.Self` and PEP 649 deferred annotations.
- Base dependencies already installed with the framework: `apscheduler~=3.11`
  (scheduler and job stores), `rich~=15.0` (tables, panels, tracebacks),
  `granian[dotenv,pname,reload,uvloop,winloop]~=2.7` (used by `serve`),
  `sqlalchemy[asyncio]~=2.0` (database job store). Nothing extra needs to be
  installed to use this module.
- `serve` behaves differently per platform: on Unix it replaces the process image
  through `execvpe`, and on Windows it either spawns a subprocess or serves in
  process.
- The `redis` job store additionally needs a reachable Redis server and the
  `scheduler.stores.redis` section; the `database` job store needs the
  **synchronous** driver of the selected connection, because APScheduler creates
  its engine eagerly.
- Adding or removing a core command or provider does not invalidate the compiled
  bootstrap cache. Delete `storage/framework/bootstrap` after changing anything
  under `orionis/`.
- Console colours are emitted as raw ANSI escape sequences from `ANSIColors`; a
  terminal without ANSI support shows the escape codes verbatim.

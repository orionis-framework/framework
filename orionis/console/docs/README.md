# orionis.console

> `orionis.console` powers the Orionis `reactor` CLI, custom commands, terminal interaction, code generators, and persistent command scheduling.

## Overview

The console module converts command classes and fluent registrations into an `argparse`-driven command registry. `KernelCLI` normalizes process arguments, `Reactor` discovers and executes commands inside a fresh container scope, and `Console` supplies styled output and prompts. The same command registry feeds an APScheduler-based `Schedule` service.

Application authors mainly use `BaseCommand`, `Argument`, `Console`, the `Reactor` facade for fluent registration/programmatic calls, and the `Schedule` facade for recurring commands. Orionis ships commands for serving, tests, migrations/database inspection, queues, scheduling, route listing, cache/log/view maintenance, project generators, MCP, and application setup.

## Requirements

- Python 3.14 or newer.
- Orionis's declared `rich>=15,<16`, `apscheduler>=3.11.3,<4.0`, and `psutil>=7.2.2,<8.0` dependencies.
- A terminal for interactive prompts and dynamic output; non-interactive commands can be called programmatically.
- Redis or a database only when its scheduler store or a command needing that service is selected.
- Run project commands through the repository's `reactor` entry point so the application and providers are booted.

## Quick start

Define a command class with validated arguments:

```python
from orionis.console import Argument
from orionis.console.base import BaseCommand


class GreetCommand(BaseCommand):
    signature = "greet"
    description = "Print a greeting."
    arguments = [
        Argument(name_or_flags="name", help="Name to greet."),
    ]

    async def handle(self) -> int:
        self.writeLine(f"Hello, {self.getArgument('name')}!")
        return 0
```

Register `GreetCommand` as an application console command, then run `python reactor greet Orionis`. The reactor parses `name`, builds the command through dependency injection, calls `handle`, and returns its integer exit code.

Validation: **Import-validated only** on CPython 3.14.6; CLI execution requires application registration and bootstrap.

## Core concepts

### Definition, discovery, and execution

`BaseCommand` defines metadata and a `handle` method. `Loader` validates core, application, and fluent commands and builds immutable command entities with parsers. `Reactor.call` opens a console scope, parses arguments, builds the handler through the container, measures execution, logs the result, and converts non-integer returns to exit code `0`.

### Declared arguments

`Argument` is a frozen, validated description of one `argparse` argument. It normalizes names to a tuple and forwards supported fields to `add_argument`. Orionis reserves `-h`/`--help`; positional arguments ignore the `required` flag because argparse already requires them unless `nargs` changes that behavior.

### Commands versus scheduled tasks

A command describes work callable now. `Schedule.command(signature, args, purpose)` creates a fluent task that references an existing command and adds an APScheduler trigger. The scheduler can persist definitions in memory, Redis, or a database and invokes commands through `Reactor` when due.

### Output surfaces

`Console` provides styled status/text methods, tables, prompts, exception rendering, dumps, progress bars, and async sleep. `Dumper` formats arbitrary values; `ProgressBar` is a lightweight terminal bar. `BaseCommand` inherits `Console`, so commands call output methods directly.

## Module structure

| Area | Responsibility |
|---|---|
| `base/`, `args/`, `entities/` | Command/listener/scheduler bases, argument definitions, normalized metadata. |
| `core/`, `kernel.py`, providers | Discovery, validation, DI dispatch, CLI argument routing, facade binding. |
| `output/`, `debug/`, `dynamic/` | Styled output, prompts, help, execution status, dumps, progress. |
| `fluent/` | Builders for runtime commands and scheduled tasks. |
| `tasks/`, `scheduler_provider.py` | APScheduler lifecycle, stores, listeners, and command execution. |
| `commands/` | Built-in serve, test, make, DB/migration, queue, MCP, schedule, route, and support commands. |
| `templates/` | Stub loading and rendering used by make commands. |

## Public API

### `BaseCommand`

Import from `orionis.console.base`. Subclasses declare `signature`, `description`, optional `arguments`, and async `handle`. `timestamps` defaults to `True`. `setArguments` merges a parsed dictionary; `getArgument(key, default=None)` preserves an explicitly supplied `None`; `getArguments()` returns a shallow copy.

Constructor dependencies and `handle` parameters can be resolved by the application container. Return an integer to control the process exit code; other successful returns become `0`.

### `Argument`

Important fields are `name_or_flags`, `action`, `nargs`, `const`, `default`, `type_`, `choices`, `required`, `help`, `metavar`, `dest`, `version`, and `extra`. `action` accepts a string or `ArgumentAction`. `type_` is rejected for boolean/const actions; string `choices` are rejected; `action="version"` requires `version`.

### `Reactor` facade

Import `Reactor` from `orionis.support.facades.reactor` after bootstrap:

| Method | Purpose |
|---|---|
| `command(signature, handler)` | Register a fluent command and return its builder. |
| `hasCommand(signature)` | Check the loaded registry asynchronously. |
| `info()` | Return sorted public command metadata, cached after first build. |
| `call(signature, args=None)` | Execute inside a new console scope and return an exit code. |

The fluent command builder configures `timestamp`, `description`, and `arguments`. Register commands before command metadata is cached or application boot finishes.

### `Console`, `Dumper`, and `ProgressBar`

`Console` groups its API as follows:

- Status: `success`, `info`, `warning`, `fail`, `error` with optional timestamps.
- Inline styles: `textSuccess`, `textInfo`, `textWarning`, `textError`, muted/bold/underline variants.
- Layout: `write`, `writeLine`, `line`, `newLine`, `clear`, `clearLine`, `table`.
- Input: `ask`, `confirm`, `secret`, `anticipate`, `choice`.
- Diagnostics/control: `exception`, `dump`, `progressBar`, `sleep`, `exitSuccess`, `exitError`.

`Dumper.dump` prints formatted values and returns them; `dd` prints and terminates. `ProgressBar(total=100, width=50)` exposes `start`, `advance`, and `finish` with range validation.

### `Schedule` facade and fluent `Task`

Import `Schedule` from `orionis.support.facades.schedule`. Add tasks only while stopped:

```python
Schedule.command("reports:daily", ["--format", "csv"], "Daily report").dailyAt(2, 30)
```

Task builders cover one-time dates, second/minute/hour/day/week intervals, weekday helpers, arbitrary cron expressions, start/end dates, jitter, coalescing, misfire grace, maximum instances, purpose, store selection, and event listeners. Scheduler operations include `boot`, `info`, `state`, `pauseTask`, `resumeTask`, `removeTask`, `removeAllTasks`, `pause`, `resume`, `shutdown`, and `wait`.

### Extension API

`BaseScheduler` supplies application scheduling hooks; `BaseTaskListener` supplies lifecycle callbacks. Contracts cover kernel, schedule/store, reactor/loader, command, output, progress, and fluent builders. Custom handlers remain container-buildable classes.

## Common workflows

### Create and run a custom command

Subclass `BaseCommand`, declare `Argument` objects, register the class in the application's console command list, and invoke it through `reactor`. Read parsed values with `getArgument`; request services through constructor or `handle` injection.

### Register a fluent command

Call `Reactor.command("signature", [Handler, "method"])`, then configure description, arguments, and timestamps on the returned builder. Fluent registrations are normalized by the same loader as class commands.

### Call a command from application code

Use `await Reactor.call("signature", ["--flag", "value"])`. Each call gets its own container scope marked with `KernelContext.CONSOLE`. Failures are logged, sent to the failure catcher, and return `1`.

### Schedule an existing command

During scheduler configuration, call `Schedule.command(...)` and finish the fluent trigger. Run `python reactor schedule:work`; the scheduler loads commands, adds the configured store, registers jobs/listeners, handles signals, and waits until shutdown.

## Examples

### Validate and parse an `Argument`

```python
import argparse

from orionis.console import Argument


parser = argparse.ArgumentParser(add_help=False)
argument = Argument(
    name_or_flags=("-n", "--name"),
    required=True,
    type_=str,
    dest="name",
)
argument.addToParser(parser)
print(vars(parser.parse_args(["--name", "Orionis"])))  # {'name': 'Orionis'}
```

Validation: **Executed successfully** on CPython 3.14.6.

### Exercise command argument storage

```python
from orionis.console.base import BaseCommand


class CountCommand(BaseCommand):
    signature = "count"
    description = "Read a count."

    async def handle(self) -> int:
        return int(self.getArgument("count", 0))


command = CountCommand()
command.setArguments({"count": 3})
print(command.getArgument("count"))  # 3
print(command.getArguments())         # {'count': 3}
```

The returned dictionary is a copy; changing it cannot mutate the command's stored arguments.

Validation: **Executed successfully** on CPython 3.14.6.

### Register a fluent command

```python
from orionis.console import Argument
from orionis.support.facades.reactor import Reactor


class ReportHandler:
    async def run(self, format_name: str) -> int:
        return 0


def register_commands() -> None:
    Reactor.command("reports:build", [ReportHandler, "run"]).description(
        "Build a report."
    ).arguments([
        Argument(name_or_flags="--format", dest="format_name", default="json"),
    ])
```

Validation: **Import-validated only** on CPython 3.14.6; registration requires a booted, pinned reactor facade.

### Define a scheduled command

```python
from orionis.support.facades.schedule import Schedule


def register_schedule() -> None:
    Schedule.command(
        "queue:clear",
        purpose="Remove completed queue records nightly.",
    ).coalesce().misfireGraceTime(60).dailyAt(3, 15)
```

Configure chainable options before the terminal trigger method (`dailyAt` returns `True`). The task must be registered before the scheduler starts; its timezone comes from the application configuration.

Validation: **Import-validated only** on CPython 3.14.6; persistent execution requires application bootstrap and the selected scheduler store.

## Configuration

The CLI itself has no dedicated config section. Commands consume their owning module's configuration. Scheduling uses:

| Key | Environment variable | Default |
|---|---|---|
| `scheduler.store` | `TASKS_STORE` | `memory` |
| `scheduler.max_instances` | `TASKS_MAX_INSTANCES` | `1` |
| `scheduler.coalesce` | `TASKS_COALESCE` | `True` |
| `scheduler.misfire_grace_time` | `TASKS_MISFIRE_GRACE_TIME` | `30` seconds |
| `scheduler.replace_existing` | `TASKS_REPLACE_EXISTING` | `True` |
| `scheduler.jitter` | `TASKS_JITTER` | `0` |
| Redis store | `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`, `REDIS_TASKS_KEY`, `REDIS_RUN_TIMES_KEY` | local Redis and `scheduler:*` keys |
| Database store | `DB_TASK_CONNECTION`, `DB_TASK_TABLE` | default connection, `scheduler_tasks` |

Task timezone is `app.timezone` (`APP_TIMEZONE`, default `UTC`). Persistent stores require `replace_existing=True` to make restarts idempotent.

## Integration with Orionis

The root `reactor` script enters `protocol_stdio`, boots the application, and drives `app.handleCommand` with `Loop.run`. Providers bind and pin reactor/schedule facades. The loader combines built-in commands, application command classes, and fluent registrations. The reactor uses the container, failure handler, logger, and performance counter.

Built-in commands integrate with HTTP serving, tests, database/ORM migrations and seeders, queues, MCP, route discovery, cache/view/log maintenance, file templates, environment/encryption, and package installation. Scheduler job stores integrate with APScheduler, Redis, or Orionis database connections.

## Errors and edge cases

- Invalid `Argument` combinations fail during construction; argparse parsing errors/help raise `SystemExit` internally and are handled by the command flow.
- Duplicate or malformed command metadata is rejected by the loader. Unknown signatures make `Reactor.call` report failure and return `1` through its catch path.
- A command exception is logged and delegated to `ICatch`; callers receive exit code `1`, not the original exception from the normal reactor path.
- Scheduling a command after the scheduler starts raises `RuntimeError`; invalid intervals, times, cron fields, listeners, and state transitions raise validation errors.
- Interactive prompt methods can block and should not be used when stdin is unavailable.
- `exitSuccess` and `exitError` terminate by raising `SystemExit`.
- The full aggregated console suite can leave long-lived worker/process cases; verify process-oriented command groups independently when diagnosing a hang.

## Performance and concurrency

Command metadata and `Reactor.info()` are cached after loading. Each command call receives a distinct container scope, while the reactor and scheduler are singletons. Blocking generator/file operations are moved to executors where their implementations explicitly do so.

APScheduler controls concurrent task instances, coalescing, misfires, and jitter. Listener coroutines are tracked as managed asyncio tasks and drained during graceful shutdown. Memory scheduling is process-local; Redis/database job stores coordinate persisted schedules across restarts, subject to APScheduler's store semantics.

Console output is synchronous terminal I/O. `Console.sleep` is async, but prompts and printing block the calling thread for their I/O duration.

## Compatibility

Orionis declares Python 3.14+, Rich 15.x, and APScheduler 3.11.x; validation used CPython 3.14.6 on Windows. CLI protocol handling adapts binary stdout on Windows. The server command selects platform-appropriate Granian loop behavior. Scheduler database/Redis support depends on their configured drivers/services.

## Verification notes

Validation used CPython 3.14.6. Exports, command/argument bases, loader/reactor/kernel, output tools, fluent APIs, scheduler/stores, providers, built-in command registry, configuration, and console tests were inspected. Focused examples were executed or import-validated as marked. The full `tests/console` aggregation was not reported as passed because it remained blocked in process-oriented cases after several minutes and was interrupted cleanly; no documentation claim relies on an invented suite result.

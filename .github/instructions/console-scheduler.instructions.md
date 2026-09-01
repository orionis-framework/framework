---
name: "Orionis Console and Scheduler"
description: "Use when creating or modifying Orionis console commands, the reactor CLI kernel, fluent commands declared in routes/console.py, argparse Argument definitions, Rich console output or APScheduler-based scheduled tasks."
applyTo: "orionis/console/**,app/console/**,routes/console.py"
---

# Console (`reactor`) and scheduler

## Read the module docs first

`orionis/console/docs/README.md` (`.es.md`) is the manual: `KernelCLI`, `Reactor`,
`Loader`, `BaseCommand`, `Argument`, the `Console` output API, `Dumper`,
`Schedule`/`Task` and the catalogue of core commands, with executed examples.
**Check it before assuming a command, flag or output helper exists.**

This file only lists the invariants and traps.

## Pipeline

`KernelCLI.handle(argv)` → `Reactor.call(signature, args)` → `Loader` resolves the
command → argparse → DI (`build` + `call`) → `Executor` prints running/done/fail →
`ILogger` → `ICatch` on failure.

- `KernelCLI.handle` **mutates** the list it receives (`del args[0]` /
  `del args[:i]`). That is intentional — it is called with `sys.argv`.
  `"reactor" in args[0]` is a substring check so it works with a full path.
- The `Loader` discovers commands from three sources: `CORE_COMMANDS`
  (`orionis/console/core/commands.py`, **17 classes**), `app/console/commands/*`
  (subclasses of `BaseCommand`) and the fluent commands in `routes/console.py`.
  Metadata is cached in `IFileBasedCache` when `app.compiled` is on.
- There is no `route:list` command — the empty placeholder files were deleted.

## Arguments and flags

- `Argument` is a `frozen`, slotted, `kw_only` dataclass. `const`/`default` use the
  `MISSING` sentinel (not `None`) to distinguish "not provided", and it rejects
  `type_` for `STORE_TRUE/FALSE/APPEND_CONST/STORE_CONST`.
- Register it on a parser with `addToParser(parser)` — there is no `register()`.
- `Reactor.__parseCommandArgs` filters out `MISSING`, so an absent flag is **not**
  in the dict and `cli_args.get(x)` returns `None`. CLI checks must use `is None`;
  writing `cli_args.get(x) or app.config(...)` makes `--flag=0` silently fall back
  to config (that was a real bug in `reactor test`).
- Only apply an option to the underlying service when it actually resolved to
  something; calling the setter with `None` wipes the service defaults.

## Exit codes

`handle() -> int` → `Reactor.call` (`if isinstance(result, int): return result`,
`except Exception: return 1`) → `KernelCLI.handle` → `sys.exit(Loop.run(...))`.
A command that must fail CI has to return a non-zero int, and status comparisons
must use the enum (comparing lowercase strings let `ERRORED` suites exit 0).

## Output

`Console` is the base of `BaseCommand` and `BaseTaskListener` — **not** of
`BaseScheduler`. `progressBar` is a property that returns a **new instance on every
access**. `Dumper.dd()` terminates the process; `Dumper.dump()` does not.

## Scheduler

- Job stores: `memory`, `database` (sync SQLAlchemy engine), `redis`. Choose with
  `store(...)` **before** `boot()`.
- The job callable must be the **module-level** function
  `_executeScheduledCommand`. Never a bound method: `SQLAlchemyJobStore` pickles
  `self`, dragging `Schedule → Reactor → Application → mappingproxy` (not
  picklable).
- Keep `add_job(..., replace_existing=True)`: persistent stores keep jobs across
  restarts and re-declaring them would raise `ConflictingIdError`.
- `scheduler.start()` runs **after** the registration loop; starting first means a
  mid-loop failure cancels jobs that are already firing.
- In `Task`, **each trigger method overwrites the previous trigger** — they do not
  accumulate. Per-task options must win over global config:
  `self.__x if self.__x is not None else param`, never `param or self.__x`.
- `randomDelay()` patches `trigger.jitter` in place when a trigger already exists.

## Running the CLI

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe reactor about
.\.venv\Scripts\python.exe reactor optimize:clear
```

Always use the repo venv. After adding a core command or a provider, clear
`storage/framework/bootstrap` or the loader keeps serving stale metadata.

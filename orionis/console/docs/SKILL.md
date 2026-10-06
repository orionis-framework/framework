---
name: "orionis-console"
description: >-
  Use when a task involves understanding, integrating, or troubleshooting
  the orionis.console module, Reactor CLI commands and arguments, console
  output, generated stubs, scheduled jobs, or MCP protocol stdio routing.
  Consult the bundled documentation and inspect the local implementation
  to select verified APIs, respect resource and execution boundaries, and
  validate proposed usage.
---

# Work with orionis.console

Treat this as a repository-local entry point, not an automatically installed
skill. Modify framework implementation only for an explicit request and
within the authorized scope.

## Establish the owner

1. Read [README.md](README.md) or [README.es.md](README.es.md). Start with
   [imports](README.md#imports-and-namesakes),
   [module structure](README.md#module-structure), and
   [literal declarations](README.md#literal-declarations).
2. Inspect the linked implementation before proposing behavior. Distinguish
   fluent `Command`/`Task` from entities, event enums from payloads, and
   output `HelpCommand` from the built-in `list` command. Import the four
   lazy root exports only where appropriate; use defining modules for others.
3. Consult the [core catalogue](README.md#built-in-command-catalogue). Verify
   current signatures and Argument declarations rather than reusing an older
   core count or a similar command name. Check the [template catalogue](README.md#template-catalogue)
   when a generator is involved.

## Preserve CLI boundaries

- Inspect [../kernel.py](../kernel.py) and
  [../core/reactor.py](../core/reactor.py). KernelCLI strips tokens by mutating
  its list. Reactor returns integer handler results or zero; ordinary
  execution exceptions become one only if error reporting succeeds.
  Scope/timer/reporting failures and BaseException paths can escape.
- Read [arguments](README.md#argument-and-command-declarations).
  `Argument` is frozen/keyword-only/slotted, but referenced values can remain
  mutable. Use `addToParser`, not a fabricated register method. Preserve
  `MISSING` versus `None`, unsupported type/action combinations, reserved help
  flags, and the reactor's identity-based filtering.
- Inspect [loader state](README.md#loader-and-reactor-state) for signature
  validation, discovery precedence, imports, serialization markers, cached
  listings, and compiled metadata. Do not assume every command module stays
  unimported, or newly registered fluent metadata refreshes a warm cache.
- Boot or resolve real services before using facades from a plain script.
  Do not confuse importing the application's bootstrap with provider boot.
  Prefer isolated examples over the checkout bootstrap during documentation.

## Respect output and resources

- Consult [output](README.md#console-and-output-resources).
  `Console.exitSuccess`, `exitError`, `Dumper.dd`, and forced dumper output can
  terminate the process. Exercise them only in a deliberately owned subprocess.
  `VarDumper.toHtml` also prints; progress captures stdout callbacks and the
  progressBar property constructs a new object each time.
- Check [HTTP/stdout](README.md#http-printer-and-protocol-stdio).
  HTTPRequestPrinter has one timer, drops queue overflow, and requires its
  worker lifecycle. Use `protocol_stdio` around MCP startup to reserve binary
  stdout and route text diagnostics to stderr; do not promise thread safety
  for process-global stream redirection.
- Review [generators](README.md#generators-and-auxiliary-apis).
  Stub creation is exclusive, not rollback-capable; a relative-path error can
  happen after writing. Keep validation outputs in owned temporary trees.
  Async cancellation does not undo started file-worker writes.

## Respect scheduling semantics

- Inspect [../tasks/schedule.py](../tasks/schedule.py),
  [../tasks/store.py](../tasks/store.py), and
  [../fluent/task.py](../fluent/task.py). There is no public Schedule.store
  mutator; choose the store through actual configuration. Persistent database
  job storage needs the synchronous driver; Redis requires a real service.
- Configure task options before calling a trigger when needed. Trigger
  methods return bool and overwrite prior triggers; do not chain from that
  bool. Preserve per-task `is not None` precedence and retained references.
- Consult [scheduling](README.md#scheduling-and-listener-behavior) and
  [triggers](README.md#task-triggers-and-payloads). Jobs use a module-level
  Reactor facade dispatcher; declared kwargs are not forwarded by that job
  callable. Listener callable classification and duplicate replacement are
  specific behaviors, not guarantees for every returned awaitable.
- Treat shutdown as managed asynchronous cleanup, not an automatic reset to
  STOPPED. Await completion and respect failure paths that can leave wait
  pending; do not infer safe repeated boot or concurrent singleton dispatch.

## Validate within scope

Read [requirements](README.md#requirements) and
  [verification](README.md#verification-and-limitations). Use the existing
[../../../tests/console](../../../tests/console), repo virtualenv, and native
runner. Standard scoped commands are:

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe -B reactor test --start-dir="tests/console" --verbosity=2
.\.venv\Scripts\python.exe -B -m ruff check --no-cache orionis/console tests/console
```

Review bootstrap, logs, result caches, subprocesses and external services
before running commands. Under a documentation-only boundary, isolate native
TestingEngine/TestRunner with a temporary booted Application and result cache
disabled. Do not clear shared storage, install into the existing environment,
launch an indefinite service, or run destructive database/queue commands merely
to confirm documentation.

Compile examples, check their imports resolve to the inspected checkout, and
execute safe scripts in independent processes with bytecode disabled and
temporary resources outside the repo. Verify discovery counts and raw failures/
errors, not only the printed summary. Keep paths short enough for terminal
layout tests; record long-path truncation failures instead of silently hiding
them. Close logging handlers before temporary directory cleanup on Windows.

Report missing dependencies, configured services, source contracts, or
execution capacity precisely. Separate declared ranges, lockfile resolutions,
installed versions, inspected mechanisms, and executed cases. Follow the
README uncertainty categories; do not change source or installation layout
to conceal a validation failure.

---
name: "orionis-background"
description: >-
  Use when a task involves understanding, integrating, or troubleshooting
  the orionis.background module, its callable wrappers, or ordered task
  collections. Consult the bundled documentation and local implementation
  to select verified APIs, respect execution and logging constraints, and
  validate proposed usage.
---

# Work with orionis.background

Use this repository entry point as local guidance, not as an installed or
automatically registered skill. Modify framework code only when explicitly
requested and within the authorized scope.

## Establish the API

1. Read [README.md](README.md) or [README.es.md](README.es.md) for the task's
   language. Start with [public imports](README.md#public-imports-and-exports)
   and the [API reference](README.md#api-reference).
2. Inspect [../__init__.py](../__init__.py), [../task.py](../task.py),
   [../tasks.py](../tasks.py), and
   [../contracts/task.py](../contracts/task.py) before proposing usage.
   Prefer the two root exports for concrete tasks; import `IBackgroundTask`
   and `is_async_callable` from their defining modules.
3. Copy actual signatures, including `addTask` capitalization. Do not invent
   a provider, facade, queue, scheduler, result accessor, or fluent return.
   Consult [compatibility notes](README.md#compatibility-notes) before using
   annotation introspection: `get_type_hints` can fail on `Callable`.

## Respect execution constraints

- Pass a callable, not an already computed result. Non-callables can survive
  construction and fail only during execution.
- Await `task()` or `task.run()`, not the task instance. Registration does not
  schedule execution; successful execution returns `None` and discards results.
- Distinguish cached coroutine-function classification from the executor's
  awaitable-result check. A synchronous coroutine factory starts on a worker;
  its returned coroutine is then awaited on the caller's loop.
- Treat captured arguments and `tasks` as live references. Collection
  construction copies only the outer list. Preserve sequential ordering,
  duplicates, repeated execution, and stop-on-first-error behavior; do not
  assume tasks are consumed or that mutation waits until the next run.
- Respect the [HTTP integration](README.md#http-integration): `Response`
  requires `BackgroundTask` or `None`, and accepts `BackgroundTasks` through
  inheritance. A contract-only implementation belongs behind `run` or a
  wrapped bound method, not directly in `Response(background=...)`.
- Check [logging requirements](README.md#requirements). Unpinned, unawaited
  `Log` calls do not emit records. With a pinned logger, synchronous logging
  can perform I/O or fail, including before a callback error is re-raised.
- Consult [concurrency](README.md#performance-and-concurrency). Do not promise
  cross-thread safety, serialization, exactly-once execution, automatic context
  propagation, or forced termination of an already running worker on cancel.
  Keep callback-owned resources alive until their actual work finishes.

## Validate and report

Read [verification limits](README.md#verification-and-limitations) and the
existing [../../../tests/background](../../../tests/background) before
selecting checks. Use the repository virtualenv and its native runner:

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe -B reactor test --start-dir="tests/background" --verbosity=2
.\.venv\Scripts\python.exe -B -m ruff check --no-cache orionis/background tests/background
```

Review bootstrap, logging, and result-cache writes before running Reactor.
Under a documentation-only boundary, use an isolated native
`TestingEngine`/`TestRunner` with a temporary created `Application`, the logger
provider booted, and result caching disabled, or report the execution limit.
Do not clean the checkout's application storage to validate this module.

Compile proposed examples, check imports separately against local module
paths, and execute safe cases in fresh processes with temporary working
directories and bytecode disabled. Check discovered counts and raw errors,
not just a successful command exit. Close logging handlers before removing
temporary directories on Windows.

Report missing files, dependencies, execution capability, or callback/resource
contracts precisely. Distinguish source inspection from executed cases and
use the README uncertainty categories. Keep declared dependency constraints,
lockfile resolutions, and tested versions separate. Do not silently change
implementation or install dependencies to hide a validation failure.

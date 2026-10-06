---
name: "orionis-aio"
description: >-
  Use when a task involves understanding, integrating, or troubleshooting
  the orionis.aio module, including event-loop selection, native coroutines,
  callable offloading, task creation, synchronous bridges, and loop cleanup.
  Consult the bundled documentation and inspect the local implementation
  to select verified APIs, respect behavioral constraints, and validate usage.
---

# Work With orionis.aio

## Locate Evidence

1. Locate this module from this file's parent directory. Inspect
   [orionis/aio/__init__.py](../__init__.py) and
   [orionis/aio/loop.py](../loop.py); do not substitute another installation.
2. Read the `API reference` section in [README.md](./README.md) or the
  `Referencia de API` section in [README.es.md](./README.es.md). Then consult
  `Compatibility notes` in the English manual or its Spanish equivalent.
3. Compare the requested behavior with the actual branch before proposing code.
   Preserve literal annotations, defaults, decorators, and parameter markers.
   Use `from orionis.aio import Loop` or `from orionis.aio.loop import Loop`.
   Treat underscored helpers and state as implementation details, not settings.

## Choose The Execution Path

- Use `Loop.run(coro)` only for a native coroutine object in a thread without
  a running loop. Do not pass its coroutine function, a Task, or a Future.
  Handle the integer `0` returned for caught `KeyboardInterrupt` when relevant.
- Prefer an ordinary `await` when the caller can already await async work.
  Use `Loop.runSync(coro)` only for a required synchronous boundary. Account
  for its blocking wait, separate worker loop, and single shared worker.
  Keep the work independent of the blocked caller and recursive bridge calls.
- Await `Loop.execute(func, *args, **kwargs)` with `func` positional-only.
  Distinguish direct coroutine-function dispatch from default-executor dispatch.
  Check actual results: the executor branch awaits only a `__await__` attribute,
  not every object that `inspect.isawaitable` recognizes.
- Obtain tasks with `task = await Loop.createTask(coro, name=...)`, retain them,
  and then await or cancel and join them. Calling the helper without awaiting
  does not schedule the supplied coroutine.
- Use `with Loop.eventLoopContext()`, never `async with`. Expect cancellation
  of all snapshotted pending tasks only when the loop is stopped on exit.
  Do not use it as task-group ownership or automatic loop closure.

## Respect Resources And Failures

- Consult `Performance and concurrency` in [README.md](./README.md).
  Do not infer global thread safety, reentrancy, context propagation, or a timeout.
  Do not transfer loop-bound clients through `runSync` without verifying their
  ownership. Arguments to executor callbacks remain shared references.
- Close stopped loops only when the caller owns them. Manage callback-created
  resources in the callback. Cancelling a wait does not stop an active worker;
  do not delete its resources before its actual work completes.
- Preserve body failures and the context's conditional cleanup behavior.
  Remember that cancellation-resistant tasks can hold cleanup open indefinitely.
- Close a native coroutine discarded after nested `run()` rejection. Distinguish
  explicit type guards, runner errors, callable failures, and cancellation.
  Do not infer a missing API from `typing.get_type_hints` alone: imports guarded
  by `TYPE_CHECKING` can make that resolution fail.

## Validate Within Authorized Scope

1. Start with `Usage examples` and `Verification and limitations` in
  [README.md](./README.md), or the equivalent Spanish sections. Check syntax,
   local import origins, and actual outcomes separately in isolated processes.
2. For explicit framework changes, use the existing native tests. Run the
   following from the repository root only when application/cache writes there
   are authorized; otherwise use an isolated application root and unchanged
   temporary test copies as described in the verification notes:

   ```powershell
   $env:PYTHONIOENCODING = "utf-8"
   $env:PYTHONDONTWRITEBYTECODE = "1"
   .\.venv\Scripts\python.exe -B reactor test --start-dir="tests/aio" --verbosity=2
   ```

3. Use the existing virtual environment and report the discovered count plus
   failed, errored, and skipped outcomes; an empty successful run is not evidence.
   Apply read-only lint when source changes are explicitly requested:

   ```powershell
   .\.venv\Scripts\python.exe -B -m ruff check --no-cache orionis/aio tests/aio
   ```

4. Keep temporary scripts, caches, and reports outside the repository when
   write scope is restricted. Do not install dependencies or change lockfiles
   merely to make an example appear verified.
5. State missing files, dependencies, interpreter/backend limitations, and
   unexecuted cases precisely. Do not claim real uvloop validation from doubles.
   Modify framework source only for an explicit request and within its authorized
   scope; do not silently repair implementation behavior during documentation.

Use this file as an operational entry point. Its location does not install or
automatically register a skill with any editor or agent platform.

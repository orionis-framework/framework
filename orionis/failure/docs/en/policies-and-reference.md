# Error policies and reference

## Public API

### Application handler contract

`IBaseExceptionHandler`, available from `orionis.failure.contracts.handler`, declares two abstract async methods:

| Method | Return | Responsibility |
|---|---|---|
| `handleFailure(exception, context)` | `FailureHandling \| None` | Receive the original exception and select deferred effects once per incident. |
| `handleResult(value, context)` | `FailureHandling \| None` | Receive a declared failed outcome without manufacturing an exception. |

`BaseExceptionHandler` implements both. Its `handleFailure` returns a plan preserving default logging and HTTP/CLI presentation; its `handleResult` returns `None`. The helper `toThrowable(exception)` uses `str(exception)` for the message, preserving custom exception text and native details such as an `OSError` filename. It stringifies each original argument without adding entries to an empty argument tuple and retains the native traceback. `isExceptionIgnored(exception)` tests exact exception-class membership in `dont_catch` and rejects non-exceptions with `TypeError`.

### `FailureHandling`

Import from `orionis.failure.entities`. This mutable, incident-local plan is separate from immutable context and receipts.

| Member | Meaning |
|---|---|
| `logging` | Optional async callable with no arguments. The runtime owns execution. |
| `presentation` | Optional async callable accepting keyword arguments `flow` and `request=None`. The protocol owner requests execution. |
| `complete()` | Runs logging once; success marks `reported=True`. Repeated calls do not retry a failed callback. |
| `present(*, flow, request=None)` | Runs presentation once and caches its result or failure. |
| `reported`, `degraded` | Status of the plan's handling. Runtime receipts expose delivery status without retaining the plan or exception. |

Calling `complete()` recursively from its logging callback, or `present()` recursively from its presentation callback in the same task, raises `RuntimeError` instead of waiting on itself. Cached callback failures preserve the original exception and its first callback traceback; repeated callers do not append an ever-growing chain of previous rethrows.

The handler selects callbacks and returns the plan. Runtime reporting protection wraps completion; `complete()` is not an independent emergency reporter. Presentation is deferred until the execution owner has its live request. Keep plans out of singleton attributes and never retain them across independent incidents.

### Context, receipt, and throwable

`FailureContext`, `FailureReceipt`, and `Throwable` are exported from `orionis.failure.entities`.

- `FailureContext` is immutable and contains flow, phase, operation, correlation/event identifiers, `expected`, `reporting_allowed`, and bounded scalar metadata. It does not retain transport objects. The runtime disables `reporting_allowed` when reporting resources begin closing.
- `FailureReceipt` contains `event_id`, `delivered`, `reported`, `duplicate`, and `degraded`. Delivery does not imply logging: expected, ignored, or observation-only failures can be delivered without an ERROR record.
- `Throwable` is frozen, keyword-only, and slotted, with `classtype`, `message`, stringified `args`, and optional native `traceback`. It does not serialize or format itself.

### Catch, facade, and runtime helpers

`Catch` is exported by `orionis.failure`; `ICatch` by `orionis.failure.contracts`. Applications normally receive `ICatch` by injection or use `orionis.support.facades.Catch`. `CatchProvider` binds the singleton service and pins the facade.

`Catch.exception(exception, request=None)` reads the active scope's `kernel`, captures the incident, and asks its plan for HTTP/CLI presentation. Existing incident state is reused without a second application-hook call. `Catch.capture(exception, *, context)` requires no scope and requests no presentation.

`capture`, `capture_result`, and `operation` are available from `orionis.failure.runtime`. Capture requires an active post-startup runtime. Owners explicitly notify failures and retain their response, retry, recovery, and propagation behavior. A custom result plan may log, but `capture_result` does not replace the original result or render automatically.

`capture_nowait` submits observation without awaiting it, returning an event-loop
task or a thread-safe future according to the caller, or `None` when observation
is unavailable. Cancelling the returned future does not let `drain()` overtake
cleanup of an already running report.
If scheduling rejects a submission, the runtime closes the unstarted coroutine,
releases its incident claim, and diagnoses the scheduling failure once.

When cleanup crosses a task boundary, an owner may pass the original receipt's
`event_id` as `capture(..., parent_event_id=...)`. This preserves causal incident
metadata without changing the secondary exception's Python cause or context.
Cause lookup compares exception identity without evaluating the exception as a
boolean. Tasks that outlive their operation do not reuse that closed operation's
metadata or incident ledger.

## Configuration and defaults

There is no dedicated configuration file. Register the handler class through `app.withExceptionHandler(...)` before `create()`. The base HTTP policy reads `app.debug`:

| Value | Unknown HTTP exception behavior |
|---|---|
| `False` | Sanitized status 500 with `Internal Server Error`. |
| `True` | Detailed exception response with request path and method. |

Known exceptions map to 401 authentication, 403 authorization, 404 route not found, 405 method not allowed, 413 payload too large, 415 unsupported media type, and 419 CSRF mismatch. HTTP mapping walks the MRO and therefore includes subclasses. Content negotiation uses `request.wantsJson()`.

`dont_catch` is a class-level `frozenset` of exact classes. Matching suppresses both default logging and presentation. Subclasses are not implicitly ignored. `context.expected=True` suppresses default ERROR logging while retaining presentation. `context.reporting_allowed=False` suppresses default logger use during final shutdown; custom logging callbacks must honor this flag.

## Failure and lifecycle boundaries

- Missing scope or `kernel` raises `RuntimeError` in `Catch.exception()`; use capture for observation without a scope.
- Pass the live request or adapter for HTTP presentation. The base plan has no HTTP output without it.
- The runtime protects hook execution and deferred logging with recursion checks, a cooperative timeout, and a bounded stderr fallback. Reporting failure can degrade delivery while allowing presentation.
- Presentation requested through `Catch` uses the same cooperative timeout and reentry guard. A failed or internally cancelled presenter is diagnosed once on stderr and propagates the primary failure without replacing its cause. Genuine caller cancellation still propagates. Output that may have partially completed is never retried; subsequent calls reuse the failed plan.
- Cancellation, `KeyboardInterrupt`, `SystemExit`, and `GeneratorExit` are not converted into server failures, including direct and nonblocking capture. Mixed exception groups retain their original structure when they include an ordinary failure.
- Before activation, capture returns `None`. `create()` alone does not activate the runtime, and failures before successful startup are outside the coverage guarantee.
- External code that consumes exceptions must notify explicitly. Orionis installs no global Python exception hooks for arbitrary external execution.
- A failed result must be explicitly declared by its execution owner; the runtime does not infer failure from every ordinary return value.

## Performance and concurrency

The application reuses one prepared handler. Operation context, deduplication, and handling plans isolate incident state; completed operations release retained references. Independent operations and retry attempts are not one global incident. Constructor dependencies and custom policy must be safe for the shared handler lifetime.

Shutdown closes admission of supervised work and waits for shared cleanup.
Supervised work that has not started is cancelled before its body runs.
An external asynchronous start waits for shutdown to finish; starting from the
runtime's own cleanup or reporting callback raises `RuntimeError` to avoid
waiting on itself. Synchronous activation also rejects an unfinished shutdown.
Once shutdown finishes, the runtime can be activated again. If discarding a
cancelled task's awaitable fails, its original cleanup exception is reported
once with phase `cancelled_cleanup`.

When an already running `Task` or `Future` from the same event loop is passed
directly to `FailureRuntime.createTask()`, cancelling its supervision wrapper
before entry still leaves `drain()` responsible for waiting for the original
cleanup. An already cancelling task is not cancelled again, and a task already
supervised by that runtime does not produce a duplicate failure report.

Incident records and identifiers are allocated on failure paths. Execution boundaries and supervised tasks still perform context and lifecycle work during successful execution; this is not a zero-overhead guarantee. Deferred logging and presentation avoid doing protocol work where the execution owner does not request it.

## Migrate a custom handler

The handler contract exposes only `handleFailure` and `handleResult`. `BaseExceptionHandler` retains `report`, `handleHTTP`, and `handleCLI` for direct calls and delegation through `super()`, preserving their previous behavior. These compatibility methods emit `DeprecationWarning` and will be removed in a future release.

The runtime and Catch continue routing exceptions through `handleFailure`; they do not automatically invoke legacy overrides. Migrate custom handling to the two current hooks:

1. Move exception policy into `handleFailure(exception, context)` and failed-result policy into `handleResult(value, context)`.
2. Start from `plan = await super().handleFailure(exception, context)` to retain native behavior. Return that plan; awaiting and discarding it loses the deferred effects.
3. Replace logging or presentation by assigning async callbacks to the plan. Preserve the inherited presentation callback when other flows still need it. Use `context.reporting_allowed` when adding logging.
4. Keep callback state local to the incident. Let the runtime complete logging and the protocol owner request presentation. Do not call capture again from either hook.

Direct implementations of `IBaseExceptionHandler` must implement both abstract methods and may return `None` for observation without effects. The base `handleResult` returns `None`, so delegating overrides should return its result too.

Orionis requires Python 3.14+ and uses its HTTP, auth, logging, console, and container services without adding a separate third-party dependency for this module.

## Module structure

| Path | Responsibility |
|---|---|
| `catch.py` | Capture and presentation dispatch using the selected incident plan. |
| `runtime.py` | Post-startup activation, protected completion, capture, supervision, and deduplication. |
| `entities/context.py` | Immutable context and delivery receipt. |
| `entities/handling.py` | Deferred logging and cached presentation for one incident. |
| `base/handler.py` | Default policy selected through the two application hooks. |
| `entities/throwable.py` | Structured exception record with native traceback. |
| `enums/kernel_type.py` | `CONSOLE` and `HTTP` scope markers. |
| `contracts/` | Catch and two-hook handler interfaces. |
| `provider.py` | Singleton binding and facade pinning. |

## Sources and next steps

[Handler contract](../../contracts/handler.py) · [Base handler](../../base/handler.py) · [Handling plan](../../entities/handling.py) · [Context](../../entities/context.py)

[Return to the module index](README.md).

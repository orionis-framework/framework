# Exception handling

## Overview

Framework execution boundaries deliver exceptions to one application handler after successful startup. `handleFailure(exception, context)` receives the original exception once per incident and returns a `FailureHandling` plan or `None`. `handleResult(value, context)` receives declared failed outcomes without inventing exceptions; its default implementation returns `None`.

`BaseExceptionHandler` builds deferred logging and presentation. The runtime completes logging under its reporting safeguards; `Catch.exception()` requests HTTP or CLI presentation from the same plan without calling the handler again. The defaults preserve `Throwable` and native traceback logging, known HTTP status mapping, safe production 500 responses, debug detail, and CLI output.

Failures before startup are outside this coverage. External code that consumes errors still needs an explicit owner to notify the runtime. Observation remains available during shutdown; once reporting resources start closing, `context.reporting_allowed` is false and the base plan stops scheduling logger calls.

## Requirements

- Python 3.14 or newer and a started Orionis application.
- An active scope containing `kernel` for `Catch.exception()`; `capture()` does not require a scope.
- A request or transport adapter for HTTP presentation.
- Application services for logging, console output, and default responses.
- Custom handlers implementing the two-hook contract; overrides must return the inherited plan to preserve default effects.

The removal of `report`, `handleHTTP`, and `handleCLI` is a breaking change. Custom handlers must migrate; no compatibility dispatch calls those methods.

## Module learning path

- [Handling exceptions](handling-exceptions.md)
- [Error policies and reference](policies-and-reference.md)
- [Capture after startup](handling-exceptions.md#capture-after-startup)
- [Migrate a custom handler](policies-and-reference.md#migrate-a-custom-handler)

Continue with: [http](../../../http/docs/en/README.md) · [logging](../../../logging/docs/en/README.md).

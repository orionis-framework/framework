# Exception handling

## Overview

`Catch` is the package-level service that receives an exception, lazily resolves the application's exception handler, reports the exception, and dispatches rendering according to the active kernel scope. Console contexts use `handleCLI`; HTTP contexts use `handleHTTP`; unknown contexts report only.

`BaseExceptionHandler` supplies the default policy: structured `Throwable` conversion, logging, CLI rendering, known HTTP status mapping, sanitized production 500 responses, and detailed debug responses. Applications can register another handler through the application API as long as it satisfies `IBaseExceptionHandler`.

## Requirements

- Python 3.14 or newer.
- A booted Orionis application/container for `Catch.exception()` or the `Catch` facade.
- An active application scope containing the `kernel` context.
- A request or transport adapter when handling an HTTP exception.
- Logging, console, and default-response services resolvable for the selected handler method.

## Module learning path

- [Reporting and handling exceptions](handling-exceptions.md)
- [Error policies and reference](policies-and-reference.md)

Continue with: [http](../../../http/docs/en/README.md) · [logging](../../../logging/docs/en/README.md).

Examples that require bootstrap, a request, or external services state that context. Verification for this reconstruction is distinct from historical notes; a production integration is not assumed to have been executed.

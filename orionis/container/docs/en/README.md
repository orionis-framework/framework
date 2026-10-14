# Service container

## Overview

The container maps contracts or aliases to implementations and creates object graphs from type annotations. It supports prebuilt instances, transient services, process-level singletons, and context-local scoped services. `build` constructs a class, `invoke` injects a function, and `call` injects a named instance method.

Application code usually interacts through `Application`, which extends the container, while framework authors define `ServiceProvider` classes and `Facade` entry points. Deferred providers postpone importing/registering services until a declared contract is requested. HTTP and console kernels create scopes so request/command-local dependencies cannot leak into one another.

## Requirements

- Python 3.14 or newer.
- No optional dependency or external service.
- Runtime type annotations on injectable constructor/function parameters.
- An active `beginScope()` context before resolving a `scoped` binding.
- Forward references must be import-resolvable in the callable's module context.

## Module learning path

- [Registering and invoking services](bindings-and-invocation.md)
- [Service Providers, facades, and extension](providers-and-facades.md)
- [Scopes, isolation, and concurrency](scopes-and-concurrency.md)

Continue with: [foundation](../../../foundation/docs/en/README.md) · [schemas](../../../schemas/docs/en/README.md).

Examples that require bootstrap, a request, or external services state that context. Verification for this reconstruction is distinct from historical notes; a production integration is not assumed to have been executed.

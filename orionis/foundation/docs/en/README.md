# Orionis foundations

## Overview

`Application` extends the dependency-injection `Container` and is the object exported from `orionis`. It is simultaneously the bootstrap coordinator, ASGI/RSGI entry point, CLI dispatcher, configuration repository, path registry, provider loader, and lifecycle owner.

Foundation also defines frozen configuration entities for every major subsystem, immutable core metadata, the `Directory` path service, runtime/lifespan enums, and startup/shutdown presentation. Most applications configure it in `bootstrap/app.py`, call `create()`, and let the HTTP server or Reactor drive runtime startup.

## Requirements

- Python 3.14 or newer; construction rejects older interpreters.
- An application root represented by `str` or `pathlib.Path`.
- Valid frozen dataclass configuration modules under the configured `config` path.
- Route files that exist and import their required facade when registered.
- One event loop per application worker; mutable runtime state is not designed for cross-loop or cross-thread sharing.

## Module learning path

- [Application lifecycle and resource ownership](application-lifecycle.md)
- [Typed configuration and runtime values](configuration.md)
- [Deployment, diagnostics, and Application reference](deployment-and-reference.md)
- [Creating and starting an application](getting-started.md)
- [Directories and bootstrap caching](paths-and-caching.md)

Continue with: [environment](../../../environment/docs/en/README.md) · [container](../../../container/docs/en/README.md) · [http](../../../http/docs/en/README.md) · [console](../../../console/docs/en/README.md).

Examples that require bootstrap, a request, or external services state that context. Verification for this reconstruction is distinct from historical notes; a production integration is not assumed to have been executed.

- [Installation and your first project](installation.md)

- [Documentation audit and coverage](documentation-audit.md)

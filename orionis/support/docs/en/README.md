# Support types and utilities

## Overview

`orionis.support` is Orionis's shared utility layer. It contains the facades used to reach framework services, value-oriented helper types, entity serialization, immutable structure helpers, reusable metaclasses, exception formatting, timing, worker sizing, and the built-in inspirational quote provider.

The package deliberately has two levels of API. `orionis.support.facades` and `orionis.support.types` provide curated imports; lower-level helpers are imported from their defining modules. The root `orionis.support` package itself does not re-export these objects.

## Requirements

- Python 3.14 or newer.
- The Orionis runtime and its declared dependencies. This module directly uses `pendulum`, `dotty-dict`, and `psutil`.
- A bootstrapped Orionis application before calling service-backed facades. `DateTime` is a standalone class and does not require the container for ordinary date operations.

## Module learning path

- [Transforming collections and strings](collections-and-strings.md)
- [Entities and data structures](entities-and-structures.md)
- [Facades, dates, and runtime utilities](facades-and-runtime-utilities.md)

Continue with: [container](../../../container/docs/en/README.md) · [schemas](../../../schemas/docs/en/README.md).

Examples that require bootstrap, a request, or external services state that context. Verification for this reconstruction is distinct from historical notes; a production integration is not assumed to have been executed.

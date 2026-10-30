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

## Bounded execution and performance

Import `threaded` and `BoundedExecutor` from `orionis.support.concurrency`. Decorate a blocking synchronous handler with `@threaded` to execute it away from the application loop while preserving its DI signature and copying context variables. The shared callback pool admits four running and 32 pending calls. Dependencies must support worker threads; pure Python CPU work still competes for the GIL. Ordinary synchronous handlers retain their existing execution behavior.

`BoundedExecutor(workers, max_pending=capacity)` provides an explicit budget for application work. `await pool.run(callback, *args)` raises `WorkQueueFullError` immediately at capacity. Decide the application's overload response explicitly. Cancelling queued work prevents its execution; cancelling running work waits for native completion before releasing capacity. Native calls need their own finite I/O timeout. Close caller-owned pools with `await pool.aclose()`.

`Collection.unique()` indexes exact built-in nested lists/dictionaries/sets in expected linear time in total input size. Small unhashable inputs (up to 128 items) retain the cheaper equality scan. Arbitrary unhashable objects and cycles also retain equality-based fallback. Supply a hashable business identity with `collection.unique(lambda item: item.identifier)` to avoid that fallback. Keyed uniqueness keeps the first representative, including when the selected field contains a list or dictionary.

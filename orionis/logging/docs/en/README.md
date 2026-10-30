# Logging

The logger records application events in UTF-8 files with one active channel and severity filtering.

## Learning path

1. [Recording events](writing-logs.md): facade, injection, severity, and diagnostics.
2. [Rotation and operations](rotation-and-lifecycle.md): configuration, retention, reload, and concurrency.

Related: [foundation](../../../foundation/docs/en/README.md) · [failure](../../../failure/docs/en/README.md)

## Bounded execution and performance

Set `LOG_QUEUE_CAPACITY=1024`, `Application(...).withConfigLogging(queue_capacity=1024)` or the `Logging` configuration field to move handler emission, file rotation and compression to bounded background queues. Zero (the default) retains synchronous emission. Capacity is per handler. A full queue raises `queue.Full` for every level, including critical; the framework neither silently drops nor falls back to blocking file I/O. Sink failures surface as `LoggingDeliveryError` on subsequent emission, flush or close.

`await logger.aclose()` stops admission, drains accepted records and closes every handler, reporting background failures after cleanup. Application HTTP/CLI shutdown drains configured queued logging after lifecycle callbacks, including when a callback fails. Standalone loggers must be explicitly closed. These queues provide no durable delivery guarantee after process termination and do not add cross-process rotation locks.

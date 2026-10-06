# orionis.queues

> API reference derived from the current implementation.

## Table of contents

- Requirements
- Functional overview
- Module structure
- API reference
- Usage examples
- Design characteristics
- Performance and concurrency
- Compatibility notes
- Verification and limitations

## Requirements

Python 3.14 or newer, as declared by pyproject.toml.

## Functional overview

The orionis.queues initializer exports 4 public symbols. This reference uses __all__, export routes, and current source files as evidence.

## Module structure

| Path | Responsibility |
| --- | --- |
| ../__init__.py | Defines package exports. |
| orionis.queues/ | Implementations and subpackages for those exports. |

## API reference

| Symbol | Verified import | Source | Declaration | Observed behavior |
| --- | --- | --- | --- | --- |
| BaseJob | from orionis.queues import BaseJob | [job.py](../job.py) | BaseJob | Declare serializable job fields and asynchronous service dependencies. Attributes ---------- tries : int / None Maximum reservations, or the configured worker default. timeout : float / None Cooperative execution timeout, or the configured worker default. backoff : tuple[float, ...] / None Delay after each failed attempt, or the configured worker default. |
| BaseJob.retryUntil | from orionis.queues import BaseJob | [job.py](../job.py) | def retryUntil(self) -> float / None | Return an optional absolute retry deadline. Returns ------- float / None Epoch seconds from DateTime, or no deadline. |
| JobContext | from orionis.queues import JobContext | [context.py](../context.py) | JobContext | Expose the current reservation and explicit lifecycle operations. |
| JobContext.id | from orionis.queues import JobContext | [context.py](../context.py) | def id(self) -> str | Return the immutable job identifier. Returns ------- str Dispatch identifier. |
| JobContext.attempts | from orionis.queues import JobContext | [context.py](../context.py) | def attempts(self) -> int | Return the number of reservations including this execution. Returns ------- int One-based attempt count. |
| JobContext.queue | from orionis.queues import JobContext | [context.py](../context.py) | def queue(self) -> str | Return the logical queue name. Returns ------- str Channel containing the job. |
| JobContext.connection | from orionis.queues import JobContext | [context.py](../context.py) | def connection(self) -> str | Return the logical backend connection name. Returns ------- str Configured connection name. |
| JobContext.finished | from orionis.queues import JobContext | [context.py](../context.py) | def finished(self) -> bool | Report whether an explicit lifecycle operation completed. Returns ------- bool Whether automatic worker acknowledgement must be skipped. |
| JobContext.failure | from orionis.queues import JobContext | [context.py](../context.py) | def failure(self) -> Exception / None | Return an explicitly reported terminal exception. Returns ------- Exception / None Error passed to ``fail``. |
| JobContext.release | from orionis.queues import JobContext | [context.py](../context.py) | async def release(self, delay: float) -> None | Release the reservation for another attempt. Parameters ---------- delay : float, optional Nonnegative delay in seconds. Returns ------- None Complete the documented operation without returning a value. Raises ------ QueueConfigurationError If the delay is invalid. QueueLeaseError If the reservation is no longer owned by this execution. |
| JobContext.delete | from orionis.queues import JobContext | [context.py](../context.py) | async def delete(self) -> None | Acknowledge the job and remove its reservation. Returns ------- None Complete the documented operation without returning a value. Raises ------ QueueLeaseError If the reservation is no longer owned by this execution. |
| JobContext.fail | from orionis.queues import JobContext | [context.py](../context.py) | async def fail(self, exception: Exception) -> None | Persist a terminal error and acknowledge the reservation. Parameters ---------- exception : Exception Original application exception. Returns ------- None Complete the documented operation without returning a value. Raises ------ QueueLeaseError If the reservation is no longer owned by this execution. |
| JobEnvelope | from orionis.queues import JobEnvelope | [entities/envelope.py](../entities/envelope.py) | JobEnvelope | Carry immutable, versioned job data independently of backend state. |
| PendingDispatch | from orionis.queues import PendingDispatch | [pending.py](../pending.py) | PendingDispatch | Defer a single dispatch until awaited and allow options before submission. |
| PendingDispatch.onConnection | from orionis.queues import PendingDispatch | [pending.py](../pending.py) | def onConnection(self, name: str) -> PendingDispatch | Select the configured backend before submission. Parameters ---------- name : str Connection name from queue configuration. Returns ------- PendingDispatch This pending operation. |
| PendingDispatch.onQueue | from orionis.queues import PendingDispatch | [pending.py](../pending.py) | def onQueue(self, name: str) -> PendingDispatch | Select a logical channel before submission. Parameters ---------- name : str Channel within the selected connection. Returns ------- PendingDispatch This pending operation. |
| PendingDispatch.delay | from orionis.queues import PendingDispatch | [pending.py](../pending.py) | def delay(self, seconds: float) -> PendingDispatch | Schedule availability relative to submission time. Parameters ---------- seconds : float Finite nonnegative delay. Returns ------- PendingDispatch This pending operation. |

## Usage examples

    from orionis.queues import BaseJob

The import path matches the API table. Import status: executed successfully under Python 3.14.3.

## Design characteristics

The package uses an explicit public surface. Private names are excluded; declarations link to their concrete owner.

## Performance and concurrency

No uniform guarantee is declared at package level. Inspect each linked file for I/O, coroutines, caches, locks, and shared state.

## Compatibility notes

Declared minimum: Python 3.14. Validation used Python 3.14.3. Dependency bounds are in pyproject.toml.

## Verification and limitations

Python files were analysed and exports verified. Failures from dependencies, callbacks, I/O, or configuration may propagate and are not presented as exhaustive.

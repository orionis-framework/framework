# Workers, retries, and failures

## Consume durable work

Start a worker from the application root with the same code version and configuration as the producer:

```shell
python reactor queue:work database --queue high,default --concurrency 4
python reactor queue:work database --queue reports --stop-when-empty --max-jobs 100
```

Queues are checked in priority order; a continuous `high` stream can delay `default`. Each worker owns consumers up to its concurrency, and each execution receives an isolated DI scope. `--max-jobs` counts processed reservations, including failed attempts and retries, rather than only unique completed jobs.

`--stop-when-empty` exits when no work is **ready**; delayed messages may remain. Omit it for continuous service and configure external supervision/restarts. This layer does not include a distributed supervisor.

The equivalent service API is:

```python
from orionis.support.facades import Queue


async def drain_reports() -> int:
    worker = await Queue.worker("database", queues=("reports",), concurrency=2)
    return await worker.run(stop_when_empty=True, max_jobs=100)
```

`worker.stop()` requests an end to reservation while active executions finish. CLI signal handling follows this flow. Cancelling internal execution attempts to release unfinished reservations where possible; a lost lease cannot be acknowledged. Stopping does not undo completed business effects.

## Reservations, timeout, and recovery

Drivers reserve atomically for `retry_after` and supply a fencing token. Completion requires the reservation still to belong to that attempt. After worker failure and lease expiration, another consumer may reserve the job again. This prevents stale-token acknowledgement, but does not prevent an external provider from having already received the action.

`timeout` is cooperative through `asyncio.timeout`, bounded by the remaining lease. It must be below `retry_after`; leave time for acknowledgement and failure handling. It does not stop blocking Python/SDK code that never yields to the event loop. Split long operations and use async APIs; increasing concurrency does not fix blocking work.

Envelopes retain timeout, maximum attempts, backoff, and deadline selected during dispatch. Changing worker defaults later does not rewrite stored messages. Jobs may override `tries`, `timeout`, `backoff`, and `retryUntil()`; the latter returns absolute epoch seconds or `None`.

## Retries and explicit decisions

`tries=3` permits the first attempt plus two retries. With `backoff=(1.0, 5.0)`, the first failure waits one second and subsequent failures use five; exhausted sequences reuse their last value. Payload, configuration, and retry-eligibility errors are not treated as temporary business errors. Expired deadlines or exhausted attempts cause terminal failure.

A `handle(self, context: JobContext)` method may decide:

| Async operation | Effect |
|---|---|
| `await context.release(delay=5.0)` | Release for another attempt. |
| `await context.delete()` | Acknowledge and remove the reservation. |
| `await context.fail(error)` | Record terminal failure and acknowledge. |

Inspect `id`, `attempts`, `queue`, `connection`, `finished`, and `failure`. Another transition after completion raises `QueueLeaseError`. Return from `handle` after `release`, `delete`, or `fail`: continuing may cause effects after the context has finished. Normal completion without an explicit decision is acknowledged automatically.

## Inspect and recover failures

```shell
python reactor queue:failed
python reactor queue:retry failure-id
python reactor queue:forget failure-id
```

Original payloads are stored with exception details and tracebacks. Protect this storage: it can contain sensitive business data. `await Queue.failed()` returns a repository providing async `all()`, `find(id)`, and `forget(id)`. `await Queue.retryFailed(id)` pushes the envelope through its original connection and removes the failure record **after** successful push; it preserves job identity and resets backend attempts. Expired original deadlines prevent retry; failed pushes retain the failure record.

`queue:forget` removes failure evidence without executing work. `queue:clear [connection] --queue reports` removes ready, delayed, **and reserved** states; it does not clean completed jobs and can invalidate active work.

When failed-job storage fails, a worker may retain an unacknowledged reservation for expiration recovery and log the problem. Monitor storage failures as well as business errors. Queue recording/acknowledgement does not atomically coordinate an external payment or delivery: use idempotency keys, conditional operations, or reconciliation in the business service.

## Sync driver and current boundaries

Sync executes one attempt during dispatch, propagates its error, and does not retain retries; terminal failures may still require the SQL failure repository. Do not use `.delay()` or `context.release()` with it. Built-in APIs do not provide job chains, job batches, decorator routing, lease heartbeats, or remote cancellation of external effects. Such capabilities require application or extension design and should not be inferred from other frameworks.

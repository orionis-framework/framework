# HTTP rate limiting

The global limiter runs after trusted-proxy resolution and identifies clients by
the transport's resolved IP. It remains disabled by default. Missing client IPs
retain the previous behavior: the limiter skips them. Configure trusted proxies
and verify that your server supplies client addresses before relying on IP quotas.

```python
from orionis.foundation.config.http import HTTP, HTTPRateLimit

http = HTTP(rate_limit=HTTPRateLimit(
    rate_limit_enabled=True,
    rate_limit_requests=100,
    rate_limit_window_seconds=60,
    rate_limit_store="memory",
    rate_limit_max_keys=10_000,
    rate_limit_max_events=100_000,
))
```

Both stores count accepted attempts in a sliding window. An attempt exactly one
window old expires. Rejected attempts do not prolong the client's quota. A 429
response includes the configured window as a conservative `Retry-After` value.

## Bounded memory store

The default store retains at most 10,000 client buckets and 100,000 accepted
timestamps across the entire store. `RATE_LIMIT_MAX_KEYS` and
`RATE_LIMIT_MAX_EVENTS` configure these positive integer capacities. Active quotas
are retained when capacity is exhausted: the store rejects additional attempts
with 429 instead of evicting a client's history. Existing clients may continue
until their quota or the timestamp capacity is reached. This bounds retained
objects, not an exact byte allocation or total framework/process memory.

Expired buckets are reclaimed incrementally, including during rejected traffic.
Each collection inspects at most 64 buckets; a saturated store may conservatively
reject a request while another collection pass has yet to reach expired clients.
Cleanup is driven by traffic and does not create a background task. Accepted
timestamps are also reclaimed when that client returns. A `threading.Lock`
serializes all updates, including calls from independent threads and event loops.
Each process still has its own independent memory store.

## Shared Redis store

```python
http = HTTP(rate_limit=HTTPRateLimit(
    rate_limit_enabled=True,
    rate_limit_requests=100,
    rate_limit_window_seconds=60,
    rate_limit_store="redis",
    rate_limit_redis_url="redis://127.0.0.1:6379/0",
    rate_limit_redis_prefix="my-app:http:rate-limit",
    rate_limit_redis_timeout_seconds=1,
))
```

The corresponding environment settings are `RATE_LIMIT_STORE`,
`RATE_LIMIT_REDIS_URL`, `RATE_LIMIT_REDIS_PREFIX` and `RATE_LIMIT_REDIS_TIMEOUT`.
Use `rediss://` for TLS. All workers enforcing the same quota must use the same
database, prefix, limit and window. Different applications should use distinct
prefixes. Construct one store per worker event loop: Redis clients are bound to
their event loop and must not be shared between threads.

One Lua script removes expired sorted-set entries, checks the quota, adds a unique
accepted attempt and sets the key's TTL atomically. Redis supplies the clock, so
Python worker clocks do not need synchronization. Client identities are stored
as SHA-256 digests in key names. Each script touches one key. The current transport
is a regular Redis client; Redis Cluster and Sentinel routing are not provided.

Connections open lazily. An owned pool defaults to 100 simultaneous connections;
Redis URL query options can override connection-pool settings. The configured
timeout bounds a complete Redis attempt, including
connection establishment; automatic retries are disabled. Connection failures,
timeouts, pool exhaustion, incompatible key types and Redis OOM errors reject
the request with 503 and `Retry-After: 1`. The limiter never silently replaces a
shared quota with a local quota on failure. Server cancellation still propagates.
Application HTTP shutdown closes owned connections without deleting quotas;
manually constructed middleware/store instances should call `await close()`.

Redis keys expire one window after their latest accepted attempt and each sorted
set retains at most the quota's number of attempts. Redis does not implement the
memory store's global client/event capacity settings. Provision Redis's memory
limit and use `noeviction` when quotas must not be reset by eviction. Persistence,
failover, restarts, administrative deletion and eviction may lose accepted
history; this implementation does not claim strict quotas across those events.

## Verification and certification boundary

The regular suites cover memory capacity exhaustion without quota resets,
expiration, eight worker-thread event loops sharing one quota, Redis command
boundaries, cancellation, client ownership, backend selection and 429/503 policy.
The opt-in suite uses real Redis Lua scripts, two separately owned clients making
100 concurrent attempts, three spawned processes sharing a quota, expiration,
store recreation and incompatible stored key types:

These tests are discovered normally and explicitly skipped when
`ORIONIS_HTTP_REDIS_URL` is unset. A configured but unavailable server remains a
test failure.

```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:ORIONIS_HTTP_REDIS_URL = "redis://127.0.0.1:6379/0"
.\.venv\Scripts\python.exe reactor test --start-dir="tests/http/layer/store" --file-pattern="test_redis_rate_limit_integration.py" --verbosity=1
```

The real integration checks were executed on Windows with Python 3.14 and Redis
5.0.14.1. The concurrency integration configures a 10-second timeout to accommodate
the test runner's asyncio debug overhead; the product default remains 1 second.
These are correctness checks, not throughput, failover or long-running memory
benchmarks. Certify supported Redis versions, Linux workers, TLS, authentication,
network failure and deployment capacity using your own service configuration.

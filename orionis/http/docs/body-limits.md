# Request resource limits

`KernelHTTP` snapshots `http.body_limits` at boot. Applications configure it with
`HTTPBodyLimits` or a dictionary through `HTTP(body_limits=...)`. The bootstrap
configuration in `config/http.py` exposes environment variables for every limit.

```python
from orionis.foundation.config.http import HTTP, HTTPBodyLimits

http = HTTP(body_limits=HTTPBodyLimits(
    max_body_size=16 * 1024 * 1024,
    max_buffer_size=2 * 1024 * 1024,
    max_concurrent_requests=128,
))
```

| Setting | Default | Scope |
|---|---:|---|
| `max_body_size` | 16 MiB | Transport bytes for one request, including multipart framing. |
| `max_buffer_size` | 2 MiB | Bytes materialized by `body()`, JSON, MessagePack, XML, text, binary and URL-encoded parsing. |
| `max_concurrent_requests` | 128 | Active HTTP requests per kernel, including response sending and awaited background work. |
| `max_files` | 32 | Multipart files per request. Zero disables file parts. |
| `max_fields` | 128 | Multipart text fields per request. Zero disables text parts. |
| `max_part_size` | 10 MiB | Raw payload bytes in one multipart part. |
| `max_field_size` | 1 MiB | Raw payload bytes in one multipart text field. |
| `max_header_size` | 16 KiB | MIME headers and delimiter suffix length. |
| `memory_threshold` | 256 KiB | File bytes held before spooling to temporary disk storage. |
| `max_memory_size` | 8 MiB | Retained multipart field strings and unspooled file payloads. |

Configuration rejects booleans, nonintegers, `None` and invalid ranges during
construction. Counts may be zero; other configuration limits must be positive.
Limits are independently configurable: a smaller buffering limit permits large
streamed uploads while limiting contiguous JSON/raw-body allocations.

Requests with a declared `Content-Length` above `max_body_size` receive **413**
before reading body bytes. Invalid, repeated, or combined Content-Length and
Transfer-Encoding headers receive **400**. Decimal lengths are compared without
converting attacker-controlled thousands of digits into an integer. An absent or
false Content-Length does not bypass actual-byte accounting when the body is read.

`BodyStream.stream()` checks accumulated bytes before yielding each transport
chunk. `read()` additionally checks the buffering budget before extending a
bytearray, then caches one bytes object for repeated reads and replay. It no
longer retains a list of every input chunk. A failed read consumes the stream and
leaves no complete replay cache.

The multipart parser counts the complete incoming stream, including discarded
preamble and epilogue, and drains the epilogue after a valid closing delimiter.
It limits boundary tokens to 70 bytes without CR/LF, processes incoming chunks in
64 KiB slices, applies file/field/count/header limits and tracks retained field
strings using `sys.getsizeof`. Unspooled file bytes count toward the same memory
budget; disk-backed payload bytes do not. Transfer-encoded file decoding currently
materializes its encoded and decoded bytes, so it requires an additional budget
of twice the encoded size or receives **413**. Malformed multipart syntax still
raises `ValueError`; resource-limit failures raise `PayloadTooLargeException`,
which now also inherits `ValueError` for parser compatibility.

Admission uses a thread-safe `BoundedSemaphore` without an application waiting
queue. Saturation receives **503** with `Retry-After: 1`; capacity is released in
`finally` after successful sending, errors or cancellation. WebSocket admission
uses its separate limits. The kernel calls `Request.close()` after HTTP delivery
and background work to close request-owned multipart files, including on
cancellation. Copy/save uploads during the request before retaining them for work
that outlives it. Manually created requests/forms can be closed explicitly.

These are finite input and retained-payload budgets, not a promise about absolute
process RSS. A server can deliver one large chunk before Python can reject it;
transport buffers, bytearray capacity, parsed JSON objects, temporary conversions,
application allocations and response output also consume memory. Admission is per
kernel instance and worker; multiple workers multiply the available capacity.
Bodies ignored by a handler are not drained just to measure them. Configure the
server/reverse proxy body limit, connection and read deadlines, worker count and
OS/container memory limit for the deployment. Persistent application references
to request-derived bytes or objects can outlive request admission.

## Compatibility and verification

Defaults deliberately replace the prior effectively unbounded body reader and
1000-file/1000-field multipart defaults. Requests that previously accepted large
buffered bodies or many fields may now return 413; configure larger finite budgets
when needed. Direct `BodyStream` construction still accepts an **explicit**
`max_body_size=None` or `max_buffer_size=None` opt-out; these options are not
accepted by application `HTTPBodyLimits` configuration. `stream()` and successful
`read()` replay semantics remain unchanged. The additive `IRequest.close()` method
must be implemented by custom request implementations.

Regression tests cover exact-limit replay, default finite limits, ASGI/RSGI actual
byte overflow, forged/malformed Content-Length, multipart framing and retained
memory, file spooling, shared HTTP admission, cancellation recovery and upload
cleanup. Run:

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe reactor test --start-dir="tests/http" --verbosity=1
```

These tests do not certify production RSS, throughput, slow-client resistance or
cross-process server coordination. Deployment certification and load measurements
must state their actual server, operating system, worker count and traffic mix.

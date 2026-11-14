# HTTP Comparison of Orionis, FastAPI, Litestar, and Starlette

The suite compares five configurations on the same machine using `GET /`.
Each returns `200 OK` with the exact text `Hello World` (11 bytes).

## Servers

| Framework | Interface | Server |
| --- | --- | --- |
| Orionis | RSGI | Granian |
| Orionis | ASGI | Granian |
| FastAPI | ASGI | Uvicorn |
| Litestar | ASGI | Uvicorn |
| Starlette | ASGI | Uvicorn |

Exact versions are pinned in the `benchmark` group of
[`pyproject.toml`](../../pyproject.toml) and resolved in `uv.lock`.
The runner validates the selected servers against those same versions.

Each configuration runs with **1, 2, 3, and 4 workers**, HTTP/1.1 keep-alive,
and the `asyncio` event loop.

The server requests an ephemeral port from the operating system (`--port 0`).
The runner discovers the listener port from its own processes without releasing
a reserved port for rebinding or guessing another process's port. This adds no
HTTP preparation requests: only Orionis receives warmup.

On Linux, the Uvicorn launcher enables `TCP_NODELAY` on the TCP socket before
sharing it between workers. This preserves the policy used by `asyncio` with
one worker and avoids Nagle and delayed ACK latency for small responses.
Handlers, the `h11` protocol, and load settings remain unchanged. The setting
is recorded as `uvicorn_multi_worker_tcp_nodelay` in `diagnostics.json`.

## Installation and Execution

From the repository root:

```text
uv python install 3.14.8
uv sync --locked --group benchmark --no-default-groups --python 3.14.8
uv run --no-sync python -B -m benchmarks.http_compare.run
```

The full comparison runs on Ubuntu 24.04 with Python 3.14.8.
On Windows, use `--workers 1`. Select cases with `--frameworks` and inspect
available options with `--help`.
Each run requires a new or empty output directory.

## Results

The [main README charts](../../README.md#http-benchmarks) show HTTP 200 requests
per second for each worker count. The [published reports][reports] include
throughput, mean latency, p50, p95, p99, status, and errors.

Results use the median of three 10-second measurements per configuration.
Latencies are expressed in milliseconds, and worker counts are kept separate.

Files are saved in `benchmark-results/http-compare/`:

| File | Contents |
| --- | --- |
| `summary.md` | Results table. |
| `summary.csv` | Results for spreadsheets. |
| `summary.json` | Structured results by framework and worker count. |
| `throughput-N-workers.svg` | Throughput chart for each worker count. |

Failed cases are explicitly labeled and do not publish metrics.
Technical details are retained separately in `diagnostics.json`.
Configuration errors and execution exceptions also appear on stderr, including
the GitHub Actions log. Charts are generated only when the entire comparison
finishes without errors.

GitHub Actions runs the comparison on every push to `1.x`. It can also be started
from **Actions → HTTP Framework Comparison → Run workflow**.
The table appears in the job summary. Successful runs on `1.x` publish charts
and summaries to the `benchmark-results` branch.

[reports]:
    https://github.com/orionis-framework/framework/tree/benchmark-results/http-compare

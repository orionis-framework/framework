# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 16686.64 | 5.99 | 5.96 | 7.14 | 7.65 | 0 |
| orionis-asgi | asgi | 1 | ok | 17662.88 | 5.66 | 5.65 | 6.69 | 7.07 | 0 |
| fastapi | asgi | 1 | ok | 12843.29 | 7.78 | 7.88 | 8.89 | 10.06 | 0 |
| starlette | asgi | 1 | ok | 25328.82 | 3.95 | 3.97 | 4.64 | 5.12 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 19378.17 | 5.16 | 5.26 | 6.10 | 6.62 | 0 |
| litestar | asgi | 2 | ok | 31221.54 | 3.20 | 3.25 | 4.25 | 4.79 | 0 |
| fastapi | asgi | 2 | ok | 21687.96 | 4.61 | 4.58 | 5.80 | 6.40 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 35844.98 | 2.79 | 2.73 | 3.49 | 4.14 | 0 |
| starlette | asgi | 2 | ok | 47056.17 | 2.12 | 2.08 | 3.16 | 3.88 | 0 |
| orionis-asgi | asgi | 2 | ok | 32643.61 | 3.06 | 3.11 | 4.33 | 4.88 | 0 |
| litestar | asgi | 3 | ok | 47477.52 | 2.10 | 2.01 | 3.37 | 4.23 | 0 |
| orionis-asgi | asgi | 3 | ok | 45891.23 | 2.18 | 2.07 | 3.57 | 4.52 | 0 |
| fastapi | asgi | 3 | ok | 36000.58 | 2.77 | 2.61 | 4.12 | 5.21 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 48815.24 | 2.05 | 1.94 | 3.35 | 4.29 | 0 |
| starlette | asgi | 3 | ok | 59921.12 | 1.67 | 1.59 | 2.80 | 3.61 | 0 |
| orionis-asgi | asgi | 4 | ok | 46152.63 | 2.16 | 2.03 | 3.81 | 4.96 | 0 |
| fastapi | asgi | 4 | ok | 35223.94 | 2.84 | 2.68 | 4.98 | 6.37 | 0 |
| litestar | asgi | 4 | ok | 43397.59 | 2.30 | 2.17 | 4.05 | 5.26 | 0 |
| starlette | asgi | 4 | ok | 60532.40 | 1.65 | 1.55 | 2.92 | 3.85 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 48861.91 | 2.04 | 1.90 | 3.69 | 4.90 | 0 |

## Environment

- os: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39
- cpu: Intel(R) Xeon(R) 6973P-C
- logical_cpus: 4
- python: 3.14.8
- commit: e2b6f2ca96f1ff7bc566601c50beda9c3224b87b
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/39319648309
- orionis: 1.0.2
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

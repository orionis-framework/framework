# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 10401.43 | 9.60 | 8.38 | 13.81 | 14.24 | 0 |
| orionis-asgi | asgi | 1 | ok | 12984.63 | 7.69 | 6.48 | 11.52 | 11.96 | 0 |
| fastapi | asgi | 1 | ok | 7280.44 | 13.72 | 14.90 | 17.54 | 17.88 | 0 |
| starlette | asgi | 1 | ok | 17464.74 | 5.72 | 4.42 | 9.65 | 9.98 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 10618.55 | 9.41 | 9.13 | 12.36 | 12.61 | 0 |
| litestar | asgi | 2 | ok | 15997.40 | 6.24 | 6.24 | 7.69 | 8.50 | 0 |
| fastapi | asgi | 2 | ok | 11357.83 | 8.79 | 8.77 | 10.84 | 11.53 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 18555.85 | 5.38 | 5.34 | 6.84 | 7.44 | 0 |
| starlette | asgi | 2 | ok | 26189.95 | 3.81 | 3.76 | 5.33 | 6.17 | 0 |
| orionis-asgi | asgi | 2 | ok | 19279.31 | 5.18 | 5.15 | 6.77 | 7.59 | 0 |
| litestar | asgi | 3 | ok | 21195.80 | 4.71 | 4.55 | 7.02 | 8.54 | 0 |
| orionis-asgi | asgi | 3 | ok | 24626.80 | 4.06 | 3.95 | 6.14 | 7.40 | 0 |
| fastapi | asgi | 3 | ok | 16193.53 | 6.17 | 6.10 | 8.12 | 9.32 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 24202.01 | 4.13 | 3.95 | 6.09 | 7.40 | 0 |
| starlette | asgi | 3 | ok | 29799.19 | 3.35 | 3.25 | 5.23 | 6.36 | 0 |
| orionis-asgi | asgi | 4 | ok | 24267.55 | 4.12 | 3.95 | 6.73 | 8.48 | 0 |
| fastapi | asgi | 4 | ok | 16392.49 | 6.09 | 5.73 | 9.92 | 12.08 | 0 |
| litestar | asgi | 4 | ok | 21224.63 | 4.71 | 4.47 | 7.88 | 9.88 | 0 |
| starlette | asgi | 4 | ok | 29360.79 | 3.40 | 3.29 | 5.49 | 6.82 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 24484.75 | 4.08 | 3.91 | 6.65 | 8.42 | 0 |

## Environment

- os: Linux-7.0.0-1017-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 7763 64-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: 92b15fe07a10ba89a2f35d9e867cc7b02abd75c0
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/40707861679
- orionis: 1.0.11
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 9146.17 | 10.92 | 10.17 | 14.18 | 14.58 | 0 |
| orionis-asgi | asgi | 1 | ok | 10644.25 | 9.38 | 8.33 | 12.49 | 13.02 | 0 |
| fastapi | asgi | 1 | ok | 6777.67 | 14.73 | 15.61 | 19.31 | 19.63 | 0 |
| starlette | asgi | 1 | ok | 15246.35 | 6.55 | 5.76 | 8.79 | 9.12 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 10094.30 | 9.90 | 9.25 | 12.49 | 12.72 | 0 |
| litestar | asgi | 2 | ok | 15371.59 | 6.50 | 6.40 | 8.21 | 9.03 | 0 |
| fastapi | asgi | 2 | ok | 11194.90 | 8.92 | 8.90 | 10.44 | 11.10 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 18478.96 | 5.41 | 5.31 | 7.09 | 7.84 | 0 |
| starlette | asgi | 2 | ok | 26580.54 | 3.76 | 3.70 | 5.26 | 6.04 | 0 |
| orionis-asgi | asgi | 2 | ok | 17868.21 | 5.59 | 5.55 | 7.23 | 7.98 | 0 |
| litestar | asgi | 3 | ok | 21300.45 | 4.69 | 4.50 | 6.99 | 8.16 | 0 |
| orionis-asgi | asgi | 3 | ok | 23320.71 | 4.28 | 4.13 | 6.51 | 7.76 | 0 |
| fastapi | asgi | 3 | ok | 17339.91 | 5.76 | 5.64 | 8.04 | 9.66 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 23397.15 | 4.27 | 4.13 | 6.49 | 7.95 | 0 |
| starlette | asgi | 3 | ok | 30022.10 | 3.33 | 3.24 | 5.16 | 6.21 | 0 |
| orionis-asgi | asgi | 4 | ok | 22700.05 | 4.40 | 4.25 | 7.16 | 8.85 | 0 |
| fastapi | asgi | 4 | ok | 16249.73 | 6.15 | 5.84 | 10.00 | 12.16 | 0 |
| litestar | asgi | 4 | ok | 20850.11 | 4.79 | 4.59 | 7.92 | 9.79 | 0 |
| starlette | asgi | 4 | ok | 28974.03 | 3.45 | 3.32 | 5.65 | 6.95 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 22964.62 | 4.35 | 4.15 | 7.19 | 8.82 | 0 |

## Environment

- os: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 7763 64-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: bbae830dba12072b5733186cf942c0d1b6417dca
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/39319232652
- orionis: 1.0.1
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

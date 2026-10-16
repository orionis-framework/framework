# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 29582.52 | 3.38 | 3.21 | 4.56 | 4.81 | 0 |
| orionis-asgi | asgi | 1 | ok | 32922.97 | 3.04 | 2.91 | 4.11 | 4.33 | 0 |
| fastapi | asgi | 1 | ok | 20400.50 | 4.90 | 4.60 | 6.55 | 6.89 | 0 |
| starlette | asgi | 1 | ok | 48956.70 | 2.04 | 2.04 | 2.67 | 2.87 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 26235.70 | 3.81 | 3.79 | 4.23 | 4.36 | 0 |
| litestar | asgi | 2 | ok | 43960.44 | 2.27 | 2.29 | 2.94 | 3.32 | 0 |
| fastapi | asgi | 2 | ok | 28493.24 | 3.51 | 3.54 | 4.36 | 4.87 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 47413.73 | 2.11 | 2.10 | 2.86 | 3.24 | 0 |
| starlette | asgi | 2 | ok | 67095.35 | 1.49 | 1.44 | 2.29 | 2.76 | 0 |
| orionis-asgi | asgi | 2 | ok | 46491.64 | 2.15 | 2.12 | 2.81 | 3.34 | 0 |
| litestar | asgi | 3 | ok | 49792.86 | 2.01 | 1.92 | 3.30 | 4.16 | 0 |
| orionis-asgi | asgi | 3 | ok | 51130.94 | 1.95 | 1.87 | 3.23 | 4.05 | 0 |
| fastapi | asgi | 3 | ok | 40902.46 | 2.44 | 2.37 | 3.72 | 4.69 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 54736.83 | 1.83 | 1.76 | 2.97 | 3.78 | 0 |
| starlette | asgi | 3 | ok | 64744.05 | 1.54 | 1.46 | 2.64 | 3.35 | 0 |
| orionis-asgi | asgi | 4 | ok | 51291.64 | 1.95 | 1.84 | 3.34 | 4.34 | 0 |
| fastapi | asgi | 4 | ok | 38705.58 | 2.58 | 2.41 | 4.59 | 5.91 | 0 |
| litestar | asgi | 4 | ok | 49224.36 | 2.03 | 1.93 | 3.51 | 4.52 | 0 |
| starlette | asgi | 4 | ok | 63041.08 | 1.58 | 1.49 | 2.80 | 3.64 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 48850.00 | 2.05 | 1.93 | 3.60 | 4.71 | 0 |

## Environment

- os: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 9V45 96-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: bd628468b11e1f90093178da422364984111d868
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/38834555464
- orionis: 1.0.1
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

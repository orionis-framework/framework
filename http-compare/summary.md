# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 30948.73 | 3.23 | 3.04 | 4.51 | 4.86 | 0 |
| orionis-asgi | asgi | 1 | ok | 32920.21 | 3.04 | 2.89 | 4.15 | 4.46 | 0 |
| fastapi | asgi | 1 | ok | 19896.04 | 5.02 | 4.76 | 6.49 | 6.92 | 0 |
| starlette | asgi | 1 | ok | 49309.46 | 2.03 | 2.01 | 2.72 | 2.91 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 25888.58 | 3.86 | 3.85 | 4.23 | 4.47 | 0 |
| litestar | asgi | 2 | ok | 44738.74 | 2.23 | 2.21 | 2.85 | 3.32 | 0 |
| fastapi | asgi | 2 | ok | 27847.06 | 3.59 | 3.54 | 4.22 | 4.63 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 46770.30 | 2.14 | 1.97 | 2.78 | 3.29 | 0 |
| starlette | asgi | 2 | ok | 67422.84 | 1.48 | 1.43 | 2.29 | 2.80 | 0 |
| orionis-asgi | asgi | 2 | ok | 46097.07 | 2.17 | 2.13 | 2.92 | 3.40 | 0 |
| litestar | asgi | 3 | ok | 50815.14 | 1.97 | 1.86 | 3.24 | 4.09 | 0 |
| orionis-asgi | asgi | 3 | ok | 53347.77 | 1.87 | 1.80 | 3.08 | 3.89 | 0 |
| fastapi | asgi | 3 | ok | 41130.66 | 2.43 | 2.33 | 3.78 | 4.67 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 55332.23 | 1.81 | 1.73 | 2.91 | 3.71 | 0 |
| starlette | asgi | 3 | ok | 65851.06 | 1.52 | 1.43 | 2.58 | 3.32 | 0 |
| orionis-asgi | asgi | 4 | ok | 51821.97 | 1.93 | 1.83 | 3.35 | 4.37 | 0 |
| fastapi | asgi | 4 | ok | 38907.35 | 2.57 | 2.38 | 4.59 | 5.84 | 0 |
| litestar | asgi | 4 | ok | 49220.40 | 2.03 | 1.92 | 3.56 | 4.59 | 0 |
| starlette | asgi | 4 | ok | 63472.97 | 1.57 | 1.46 | 2.85 | 3.73 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 52414.50 | 1.91 | 1.79 | 3.33 | 4.36 | 0 |

## Environment

- os: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 9V45 96-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: 1f145dcf8577e6262e2970906d8ad9383152bfd7
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/39784880504
- orionis: 1.0.6
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

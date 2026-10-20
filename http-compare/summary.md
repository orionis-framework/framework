# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 31415.58 | 3.18 | 3.00 | 4.30 | 4.46 | 0 |
| orionis-asgi | asgi | 1 | ok | 32740.30 | 3.05 | 3.03 | 3.99 | 4.20 | 0 |
| fastapi | asgi | 1 | ok | 20076.16 | 4.98 | 5.02 | 6.42 | 6.69 | 0 |
| starlette | asgi | 1 | ok | 55780.46 | 1.79 | 1.70 | 2.49 | 2.68 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 27134.65 | 3.68 | 3.69 | 4.01 | 4.18 | 0 |
| litestar | asgi | 2 | ok | 42696.24 | 2.34 | 2.25 | 3.19 | 3.72 | 0 |
| fastapi | asgi | 2 | ok | 27839.38 | 3.59 | 3.57 | 4.54 | 5.04 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 45715.04 | 2.19 | 2.19 | 2.84 | 3.28 | 0 |
| starlette | asgi | 2 | ok | 68615.86 | 1.46 | 1.42 | 2.27 | 2.78 | 0 |
| orionis-asgi | asgi | 2 | ok | 45372.13 | 2.20 | 2.16 | 2.84 | 3.21 | 0 |
| litestar | asgi | 3 | ok | 49889.68 | 2.00 | 1.92 | 3.23 | 4.04 | 0 |
| orionis-asgi | asgi | 3 | ok | 50278.98 | 1.99 | 1.90 | 3.28 | 4.11 | 0 |
| fastapi | asgi | 3 | ok | 38864.39 | 2.57 | 2.48 | 4.12 | 5.23 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 52102.96 | 1.92 | 1.83 | 3.16 | 4.04 | 0 |
| starlette | asgi | 3 | ok | 62288.90 | 1.60 | 1.52 | 2.72 | 3.49 | 0 |
| orionis-asgi | asgi | 4 | ok | 48670.93 | 2.05 | 1.95 | 3.54 | 4.59 | 0 |
| fastapi | asgi | 4 | ok | 36854.28 | 2.71 | 2.52 | 4.78 | 6.15 | 0 |
| litestar | asgi | 4 | ok | 46925.09 | 2.13 | 2.01 | 3.70 | 4.79 | 0 |
| starlette | asgi | 4 | ok | 62240.55 | 1.61 | 1.51 | 2.86 | 3.72 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 52221.97 | 1.91 | 1.80 | 3.37 | 4.47 | 0 |

## Environment

- os: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 9V45 96-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: e61b990a755e8b3db52f6028d36ca12ba6389885
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/39497116855
- orionis: 1.0.4
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

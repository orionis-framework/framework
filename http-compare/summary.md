# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 28142.10 | 3.55 | 3.78 | 4.54 | 4.97 | 0 |
| orionis-asgi | asgi | 1 | ok | 30875.72 | 3.24 | 3.43 | 4.06 | 4.37 | 0 |
| fastapi | asgi | 1 | ok | 19027.42 | 5.25 | 5.48 | 6.53 | 6.91 | 0 |
| starlette | asgi | 1 | ok | 43342.62 | 2.30 | 2.39 | 2.97 | 3.29 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 26694.70 | 3.74 | 3.87 | 4.22 | 4.32 | 0 |
| litestar | asgi | 2 | ok | 40749.30 | 2.45 | 2.44 | 3.24 | 3.74 | 0 |
| fastapi | asgi | 2 | ok | 28947.83 | 3.45 | 3.48 | 4.27 | 4.60 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 48833.93 | 2.05 | 2.00 | 2.84 | 3.29 | 0 |
| starlette | asgi | 2 | ok | 64205.01 | 1.56 | 1.49 | 2.40 | 2.91 | 0 |
| orionis-asgi | asgi | 2 | ok | 47331.75 | 2.11 | 2.10 | 3.00 | 3.59 | 0 |
| litestar | asgi | 3 | ok | 49928.51 | 2.00 | 1.89 | 3.30 | 4.20 | 0 |
| orionis-asgi | asgi | 3 | ok | 55689.41 | 1.79 | 1.71 | 2.95 | 3.74 | 0 |
| fastapi | asgi | 3 | ok | 40523.88 | 2.46 | 2.34 | 3.84 | 4.57 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 57077.55 | 1.75 | 1.68 | 2.80 | 3.61 | 0 |
| starlette | asgi | 3 | ok | 65686.75 | 1.52 | 1.46 | 2.48 | 3.19 | 0 |
| orionis-asgi | asgi | 4 | ok | 53644.50 | 1.86 | 1.75 | 3.27 | 4.25 | 0 |
| fastapi | asgi | 4 | ok | 37451.54 | 2.67 | 2.46 | 4.79 | 6.23 | 0 |
| litestar | asgi | 4 | ok | 48094.43 | 2.08 | 1.96 | 3.64 | 4.80 | 0 |
| starlette | asgi | 4 | ok | 64308.04 | 1.55 | 1.46 | 2.76 | 3.68 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 55547.01 | 1.80 | 1.69 | 3.17 | 4.20 | 0 |

## Environment

- os: Linux-7.0.0-1017-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 9V45 96-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: 7bfbc060da6adb4ebbfb11d7818ac498e333d2ba
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/40935979878
- orionis: 1.0.13
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

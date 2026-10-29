# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 23807.25 | 4.19 | 4.07 | 6.77 | 9.06 | 0 |
| orionis-asgi | asgi | 1 | ok | 30208.70 | 3.31 | 3.51 | 4.26 | 5.55 | 0 |
| fastapi | asgi | 1 | ok | 18426.96 | 5.42 | 5.65 | 6.67 | 8.91 | 0 |
| starlette | asgi | 1 | ok | 44552.83 | 2.24 | 2.32 | 2.95 | 3.51 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 28824.78 | 3.47 | 3.55 | 3.97 | 4.21 | 0 |
| litestar | asgi | 2 | ok | 41887.55 | 2.38 | 2.41 | 3.13 | 3.77 | 0 |
| fastapi | asgi | 2 | ok | 28516.33 | 3.50 | 3.55 | 4.32 | 4.72 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 46642.23 | 2.14 | 2.09 | 2.73 | 3.52 | 0 |
| starlette | asgi | 2 | ok | 64965.29 | 1.54 | 1.48 | 2.42 | 2.89 | 0 |
| orionis-asgi | asgi | 2 | ok | 49385.03 | 2.02 | 2.00 | 2.83 | 3.48 | 0 |
| litestar | asgi | 3 | ok | 51459.26 | 1.94 | 1.85 | 3.15 | 3.99 | 0 |
| orionis-asgi | asgi | 3 | ok | 55837.22 | 1.79 | 1.72 | 2.86 | 3.60 | 0 |
| fastapi | asgi | 3 | ok | 40451.31 | 2.47 | 2.32 | 3.87 | 4.55 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 55008.01 | 1.82 | 1.72 | 3.02 | 3.88 | 0 |
| starlette | asgi | 3 | ok | 63847.80 | 1.56 | 1.49 | 2.64 | 3.43 | 0 |
| orionis-asgi | asgi | 4 | ok | 54137.46 | 1.85 | 1.73 | 3.22 | 4.19 | 0 |
| fastapi | asgi | 4 | ok | 37329.88 | 2.68 | 2.46 | 4.86 | 6.50 | 0 |
| litestar | asgi | 4 | ok | 46856.32 | 2.13 | 2.00 | 3.75 | 4.98 | 0 |
| starlette | asgi | 4 | ok | 61104.81 | 1.63 | 1.54 | 2.88 | 3.79 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 54196.00 | 1.84 | 1.74 | 3.27 | 4.29 | 0 |

## Environment

- os: Linux-7.0.0-1017-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 9V45 96-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: 2fbe243106ce237d88fc3e2c3f9f89a2d1c45b59
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/40961207427
- orionis: 1.0.14
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

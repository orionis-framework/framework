# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 30493.95 | 3.28 | 3.11 | 4.52 | 4.85 | 0 |
| orionis-asgi | asgi | 1 | ok | 32910.67 | 3.04 | 2.85 | 4.17 | 4.44 | 0 |
| fastapi | asgi | 1 | ok | 20335.25 | 4.91 | 4.64 | 6.54 | 6.88 | 0 |
| starlette | asgi | 1 | ok | 50118.36 | 1.99 | 1.96 | 2.68 | 2.96 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 26533.57 | 3.77 | 3.75 | 4.13 | 4.25 | 0 |
| litestar | asgi | 2 | ok | 43241.65 | 2.31 | 2.34 | 2.95 | 3.45 | 0 |
| fastapi | asgi | 2 | ok | 28494.82 | 3.51 | 3.43 | 4.27 | 4.62 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 47943.87 | 2.08 | 2.08 | 2.76 | 3.23 | 0 |
| starlette | asgi | 2 | ok | 66620.69 | 1.50 | 1.44 | 2.33 | 2.81 | 0 |
| orionis-asgi | asgi | 2 | ok | 46825.56 | 2.13 | 2.14 | 2.85 | 3.35 | 0 |
| litestar | asgi | 3 | ok | 51022.86 | 1.96 | 1.89 | 3.15 | 3.96 | 0 |
| orionis-asgi | asgi | 3 | ok | 53619.75 | 1.86 | 1.79 | 3.01 | 3.77 | 0 |
| fastapi | asgi | 3 | ok | 40551.12 | 2.46 | 2.35 | 3.80 | 4.72 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 52606.83 | 1.90 | 1.81 | 3.07 | 3.92 | 0 |
| starlette | asgi | 3 | ok | 63839.98 | 1.56 | 1.49 | 2.68 | 3.44 | 0 |
| orionis-asgi | asgi | 4 | ok | 49228.29 | 2.03 | 1.91 | 3.54 | 4.60 | 0 |
| fastapi | asgi | 4 | ok | 37304.45 | 2.68 | 2.50 | 4.77 | 6.15 | 0 |
| litestar | asgi | 4 | ok | 47552.73 | 2.10 | 2.00 | 3.63 | 4.70 | 0 |
| starlette | asgi | 4 | ok | 62513.19 | 1.60 | 1.50 | 2.81 | 3.64 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 53671.76 | 1.86 | 1.75 | 3.25 | 4.29 | 0 |

## Environment

- os: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 9V45 96-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: 3d3beb97370c2b351356fefaeb5e8e60833d356d
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/38826095860
- orionis: 1.0.0
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

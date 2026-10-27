# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 28576.44 | 3.50 | 3.30 | 4.69 | 5.08 | 0 |
| orionis-asgi | asgi | 1 | ok | 30027.85 | 3.33 | 3.24 | 4.32 | 4.66 | 0 |
| fastapi | asgi | 1 | ok | 18870.72 | 5.30 | 4.99 | 6.82 | 7.33 | 0 |
| starlette | asgi | 1 | ok | 50342.76 | 1.98 | 1.93 | 2.68 | 3.04 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 25744.32 | 3.88 | 3.87 | 4.28 | 4.71 | 0 |
| litestar | asgi | 2 | ok | 41696.06 | 2.40 | 2.43 | 3.11 | 3.54 | 0 |
| fastapi | asgi | 2 | ok | 27285.74 | 3.66 | 3.65 | 4.46 | 4.87 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 47125.12 | 2.12 | 2.11 | 2.91 | 3.48 | 0 |
| starlette | asgi | 2 | ok | 65983.89 | 1.51 | 1.45 | 2.39 | 2.93 | 0 |
| orionis-asgi | asgi | 2 | ok | 42396.17 | 2.36 | 2.39 | 3.03 | 3.60 | 0 |
| litestar | asgi | 3 | ok | 48399.21 | 2.06 | 1.97 | 3.38 | 4.24 | 0 |
| orionis-asgi | asgi | 3 | ok | 50671.81 | 1.97 | 1.90 | 3.23 | 4.08 | 0 |
| fastapi | asgi | 3 | ok | 38046.52 | 2.63 | 2.50 | 4.03 | 4.97 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 52710.73 | 1.90 | 1.81 | 3.14 | 3.99 | 0 |
| starlette | asgi | 3 | ok | 63865.04 | 1.56 | 1.48 | 2.64 | 3.41 | 0 |
| orionis-asgi | asgi | 4 | ok | 49900.46 | 2.00 | 1.89 | 3.49 | 4.51 | 0 |
| fastapi | asgi | 4 | ok | 37063.69 | 2.70 | 2.51 | 4.74 | 6.03 | 0 |
| litestar | asgi | 4 | ok | 47428.01 | 2.11 | 1.99 | 3.68 | 4.69 | 0 |
| starlette | asgi | 4 | ok | 62559.01 | 1.60 | 1.49 | 2.85 | 3.73 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 51114.45 | 1.95 | 1.85 | 3.44 | 4.48 | 0 |

## Environment

- os: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 9V45 96-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: 63118a323607916eaf89992769fe1f9b31fbe1c4
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/40549561045
- orionis: 1.0.10
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

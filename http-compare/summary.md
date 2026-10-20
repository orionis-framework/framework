# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 15250.77 | 6.55 | 5.47 | 10.98 | 11.46 | 0 |
| orionis-asgi | asgi | 1 | ok | 17294.90 | 5.78 | 4.77 | 9.80 | 10.14 | 0 |
| fastapi | asgi | 1 | ok | 10298.37 | 9.70 | 8.07 | 14.88 | 15.20 | 0 |
| starlette | asgi | 1 | ok | 21252.47 | 4.70 | 4.16 | 7.09 | 7.47 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 15460.48 | 6.46 | 5.86 | 9.31 | 9.50 | 0 |
| litestar | asgi | 2 | ok | 20099.65 | 4.97 | 4.92 | 6.99 | 7.59 | 0 |
| fastapi | asgi | 2 | ok | 14304.92 | 6.98 | 6.94 | 9.26 | 9.86 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 21294.98 | 4.69 | 4.72 | 6.32 | 6.80 | 0 |
| starlette | asgi | 2 | ok | 34927.15 | 2.86 | 2.77 | 4.29 | 5.17 | 0 |
| orionis-asgi | asgi | 2 | ok | 23202.60 | 4.30 | 4.26 | 6.09 | 6.77 | 0 |
| litestar | asgi | 3 | ok | 25778.82 | 3.87 | 3.61 | 6.30 | 7.95 | 0 |
| orionis-asgi | asgi | 3 | ok | 28743.76 | 3.47 | 3.29 | 5.59 | 6.90 | 0 |
| fastapi | asgi | 3 | ok | 19457.46 | 5.13 | 4.85 | 7.90 | 8.78 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 29619.07 | 3.37 | 3.17 | 5.45 | 6.84 | 0 |
| starlette | asgi | 3 | ok | 36072.29 | 2.77 | 2.67 | 4.43 | 5.38 | 0 |
| orionis-asgi | asgi | 4 | ok | 28007.69 | 3.57 | 3.39 | 5.97 | 7.56 | 0 |
| fastapi | asgi | 4 | ok | 18910.55 | 5.28 | 4.99 | 8.92 | 11.21 | 0 |
| litestar | asgi | 4 | ok | 24847.73 | 4.02 | 3.84 | 6.70 | 8.45 | 0 |
| starlette | asgi | 4 | ok | 34501.90 | 2.89 | 2.78 | 4.76 | 5.98 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 28149.96 | 3.55 | 3.38 | 6.02 | 7.72 | 0 |

## Environment

- os: Linux-7.0.0-1017-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 9V74 80-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: 821e90c3667eb7b88c0aefcb037ba6f77337fcff
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/39494644920
- orionis: 1.0.3
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

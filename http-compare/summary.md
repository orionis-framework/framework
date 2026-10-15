# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 9264.29 | 10.78 | 9.40 | 14.03 | 14.44 | 0 |
| orionis-asgi | asgi | 1 | ok | 10806.58 | 9.24 | 8.02 | 12.52 | 12.90 | 0 |
| fastapi | asgi | 1 | ok | 6625.33 | 15.07 | 15.88 | 19.15 | 19.52 | 0 |
| starlette | asgi | 1 | ok | 15025.39 | 6.65 | 5.92 | 8.69 | 8.99 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 10192.47 | 9.80 | 9.06 | 12.65 | 12.93 | 0 |
| litestar | asgi | 2 | ok | 15364.08 | 6.50 | 6.45 | 8.05 | 8.80 | 0 |
| fastapi | asgi | 2 | ok | 11038.95 | 9.05 | 8.97 | 10.52 | 11.25 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 17091.72 | 5.84 | 5.76 | 7.53 | 8.39 | 0 |
| starlette | asgi | 2 | ok | 25999.36 | 3.84 | 3.78 | 5.42 | 6.31 | 0 |
| orionis-asgi | asgi | 2 | ok | 17344.66 | 5.76 | 5.67 | 7.26 | 8.15 | 0 |
| litestar | asgi | 3 | ok | 20985.94 | 4.76 | 4.61 | 7.19 | 8.62 | 0 |
| orionis-asgi | asgi | 3 | ok | 22645.16 | 4.41 | 4.24 | 6.70 | 8.00 | 0 |
| fastapi | asgi | 3 | ok | 16942.93 | 5.89 | 5.72 | 8.39 | 9.57 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 22936.20 | 4.35 | 4.17 | 6.59 | 7.88 | 0 |
| starlette | asgi | 3 | ok | 29543.22 | 3.38 | 3.29 | 5.25 | 6.33 | 0 |
| orionis-asgi | asgi | 4 | ok | 22321.95 | 4.47 | 4.32 | 7.24 | 8.87 | 0 |
| fastapi | asgi | 4 | ok | 16083.91 | 6.21 | 5.86 | 10.21 | 12.35 | 0 |
| litestar | asgi | 4 | ok | 20489.45 | 4.88 | 4.68 | 7.97 | 9.82 | 0 |
| starlette | asgi | 4 | ok | 28387.09 | 3.52 | 3.40 | 5.71 | 7.03 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 22512.26 | 4.44 | 4.26 | 7.28 | 9.03 | 0 |

## Environment

- os: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 7763 64-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: 79c9c7e33ac0b01b55c6dfd50fbb292c5e65126b
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/38798015256
- orionis: 0.932.0
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

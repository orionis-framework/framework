# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 19524.00 | 5.12 | 4.24 | 8.36 | 8.82 | 0 |
| orionis-asgi | asgi | 1 | ok | 24197.23 | 4.13 | 3.41 | 7.25 | 7.55 | 0 |
| fastapi | asgi | 1 | ok | 13900.50 | 7.19 | 5.97 | 11.31 | 11.57 | 0 |
| starlette | asgi | 1 | ok | 28901.45 | 3.46 | 2.88 | 5.72 | 5.97 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 18464.41 | 5.41 | 5.39 | 6.85 | 7.04 | 0 |
| litestar | asgi | 2 | ok | 25412.91 | 3.93 | 3.83 | 5.41 | 6.06 | 0 |
| fastapi | asgi | 2 | ok | 18185.50 | 5.49 | 5.42 | 7.12 | 7.65 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 29865.71 | 3.34 | 3.30 | 4.68 | 5.65 | 0 |
| starlette | asgi | 2 | ok | 42915.74 | 2.33 | 2.23 | 3.61 | 4.33 | 0 |
| orionis-asgi | asgi | 2 | ok | 32946.86 | 3.03 | 2.96 | 4.31 | 4.96 | 0 |
| litestar | asgi | 3 | ok | 32561.72 | 3.07 | 2.89 | 4.95 | 6.20 | 0 |
| orionis-asgi | asgi | 3 | ok | 37632.49 | 2.65 | 2.53 | 4.38 | 5.45 | 0 |
| fastapi | asgi | 3 | ok | 25566.61 | 3.91 | 3.76 | 6.23 | 7.14 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 38543.63 | 2.59 | 2.47 | 4.30 | 5.51 | 0 |
| starlette | asgi | 3 | ok | 44122.87 | 2.26 | 2.18 | 3.65 | 4.58 | 0 |
| orionis-asgi | asgi | 4 | ok | 37603.66 | 2.66 | 2.52 | 4.54 | 5.82 | 0 |
| fastapi | asgi | 4 | ok | 24684.33 | 4.05 | 3.80 | 7.03 | 9.30 | 0 |
| litestar | asgi | 4 | ok | 31370.97 | 3.18 | 3.03 | 5.45 | 7.01 | 0 |
| starlette | asgi | 4 | ok | 42797.04 | 2.33 | 2.22 | 4.00 | 5.08 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 37922.35 | 2.63 | 2.50 | 4.58 | 6.00 | 0 |

## Environment

- os: Linux-7.0.0-1017-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 9V74 80-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: 00a13e84e8feb950453218ac67ae6cbeeca9d51e
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/40975546981
- orionis: 1.0.16
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

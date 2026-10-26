# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 14125.83 | 7.07 | 7.28 | 8.22 | 8.39 | 0 |
| orionis-asgi | asgi | 1 | ok | 16282.62 | 6.14 | 6.13 | 7.31 | 7.51 | 0 |
| fastapi | asgi | 1 | ok | 10437.82 | 9.57 | 9.83 | 11.62 | 11.81 | 0 |
| starlette | asgi | 1 | ok | 21186.81 | 4.72 | 4.78 | 5.12 | 5.30 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 17593.01 | 5.68 | 5.35 | 7.24 | 7.41 | 0 |
| litestar | asgi | 2 | ok | 23335.00 | 4.28 | 4.44 | 5.33 | 6.38 | 0 |
| fastapi | asgi | 2 | ok | 16827.07 | 5.94 | 5.92 | 7.40 | 7.87 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 27928.91 | 3.58 | 3.55 | 4.76 | 5.36 | 0 |
| starlette | asgi | 2 | ok | 41555.68 | 2.40 | 2.35 | 3.55 | 4.19 | 0 |
| orionis-asgi | asgi | 2 | ok | 27308.43 | 3.66 | 3.76 | 4.68 | 5.24 | 0 |
| litestar | asgi | 3 | ok | 32112.12 | 3.11 | 2.98 | 4.97 | 6.03 | 0 |
| orionis-asgi | asgi | 3 | ok | 35712.63 | 2.80 | 2.69 | 4.52 | 5.51 | 0 |
| fastapi | asgi | 3 | ok | 25730.93 | 3.88 | 3.74 | 5.81 | 7.02 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 37076.30 | 2.69 | 2.58 | 4.28 | 5.36 | 0 |
| starlette | asgi | 3 | ok | 45827.84 | 2.18 | 2.10 | 3.51 | 4.30 | 0 |
| orionis-asgi | asgi | 4 | ok | 34785.46 | 2.87 | 2.74 | 4.83 | 6.04 | 0 |
| fastapi | asgi | 4 | ok | 24344.58 | 4.10 | 3.88 | 6.99 | 8.86 | 0 |
| litestar | asgi | 4 | ok | 31152.76 | 3.21 | 3.05 | 5.42 | 6.76 | 0 |
| starlette | asgi | 4 | ok | 42242.17 | 2.36 | 2.25 | 4.04 | 5.11 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 34807.69 | 2.87 | 2.74 | 4.86 | 6.18 | 0 |

## Environment

- os: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 9V74 80-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: c35b512a53a9c0948cebb097b7bf1b825d67c367
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/40353513672
- orionis: 1.0.7
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

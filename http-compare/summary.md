# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 9184.55 | 10.88 | 10.04 | 14.31 | 14.69 | 0 |
| orionis-asgi | asgi | 1 | ok | 10322.20 | 9.68 | 8.65 | 12.69 | 13.19 | 0 |
| fastapi | asgi | 1 | ok | 6479.75 | 15.41 | 15.97 | 19.22 | 19.60 | 0 |
| starlette | asgi | 1 | ok | 14510.67 | 6.88 | 7.56 | 8.76 | 9.10 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 10225.87 | 9.77 | 8.97 | 12.55 | 12.82 | 0 |
| litestar | asgi | 2 | ok | 15536.14 | 6.43 | 6.42 | 8.16 | 9.05 | 0 |
| fastapi | asgi | 2 | ok | 10871.82 | 9.19 | 9.13 | 10.97 | 12.31 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 17634.83 | 5.66 | 5.59 | 7.17 | 7.99 | 0 |
| starlette | asgi | 2 | ok | 26779.01 | 3.73 | 3.68 | 5.19 | 5.96 | 0 |
| orionis-asgi | asgi | 2 | ok | 17317.27 | 5.77 | 5.69 | 7.59 | 8.38 | 0 |
| litestar | asgi | 3 | ok | 21173.45 | 4.72 | 4.54 | 7.00 | 8.22 | 0 |
| orionis-asgi | asgi | 3 | ok | 22903.57 | 4.36 | 4.17 | 6.65 | 7.94 | 0 |
| fastapi | asgi | 3 | ok | 17623.19 | 5.67 | 5.65 | 7.64 | 9.41 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 23069.37 | 4.33 | 4.19 | 6.58 | 7.93 | 0 |
| starlette | asgi | 3 | ok | 29649.18 | 3.37 | 3.28 | 5.25 | 6.31 | 0 |
| orionis-asgi | asgi | 4 | ok | 22396.06 | 4.46 | 4.29 | 7.32 | 9.13 | 0 |
| fastapi | asgi | 4 | ok | 16303.22 | 6.13 | 5.77 | 10.01 | 12.21 | 0 |
| litestar | asgi | 4 | ok | 20559.17 | 4.86 | 4.64 | 8.06 | 9.94 | 0 |
| starlette | asgi | 4 | ok | 28657.62 | 3.49 | 3.35 | 5.69 | 7.05 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 22693.45 | 4.40 | 4.23 | 7.25 | 9.03 | 0 |

## Environment

- os: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 7763 64-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: b878e14ad29085e28911b950067d7e50bdf4a97a
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/38834413806
- orionis: 1.0.0
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

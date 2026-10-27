# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 14023.76 | 7.12 | 7.36 | 8.19 | 8.41 | 0 |
| orionis-asgi | asgi | 1 | ok | 16138.57 | 6.19 | 6.37 | 7.15 | 7.34 | 0 |
| fastapi | asgi | 1 | ok | 10730.41 | 9.31 | 9.05 | 11.33 | 11.51 | 0 |
| starlette | asgi | 1 | ok | 21488.19 | 4.65 | 4.69 | 4.99 | 5.13 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 18099.45 | 5.52 | 5.14 | 7.16 | 7.27 | 0 |
| litestar | asgi | 2 | ok | 24451.18 | 4.09 | 4.16 | 5.29 | 5.77 | 0 |
| fastapi | asgi | 2 | ok | 17512.24 | 5.71 | 5.81 | 6.89 | 7.46 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 28692.16 | 3.48 | 3.58 | 4.68 | 5.13 | 0 |
| starlette | asgi | 2 | ok | 41553.85 | 2.40 | 2.34 | 3.62 | 4.26 | 0 |
| orionis-asgi | asgi | 2 | ok | 28023.23 | 3.57 | 3.70 | 4.76 | 5.24 | 0 |
| litestar | asgi | 3 | ok | 33821.79 | 2.95 | 2.83 | 4.63 | 5.65 | 0 |
| orionis-asgi | asgi | 3 | ok | 37434.73 | 2.67 | 2.56 | 4.25 | 5.24 | 0 |
| fastapi | asgi | 3 | ok | 26415.83 | 3.78 | 3.69 | 5.48 | 6.76 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 38073.07 | 2.62 | 2.50 | 4.21 | 5.18 | 0 |
| starlette | asgi | 3 | ok | 46196.23 | 2.16 | 2.09 | 3.46 | 4.27 | 0 |
| orionis-asgi | asgi | 4 | ok | 35663.99 | 2.80 | 2.68 | 4.69 | 5.93 | 0 |
| fastapi | asgi | 4 | ok | 25175.86 | 3.97 | 3.76 | 6.77 | 8.57 | 0 |
| litestar | asgi | 4 | ok | 32282.74 | 3.09 | 2.94 | 5.28 | 6.62 | 0 |
| starlette | asgi | 4 | ok | 44303.05 | 2.25 | 2.15 | 3.82 | 4.82 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 35910.98 | 2.78 | 2.66 | 4.72 | 6.05 | 0 |

## Environment

- os: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 9V74 80-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: 5e6d4b43042b41aa17e47cb47859ebbce1f3f021
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/40549276342
- orionis: 1.0.9
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 25726.08 | 3.88 | 4.19 | 4.78 | 5.53 | 0 |
| orionis-asgi | asgi | 1 | ok | 29292.89 | 3.41 | 3.58 | 4.22 | 4.67 | 0 |
| fastapi | asgi | 1 | ok | 18151.84 | 5.50 | 5.77 | 6.78 | 7.53 | 0 |
| starlette | asgi | 1 | ok | 43696.33 | 2.29 | 2.37 | 2.94 | 3.25 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 27316.72 | 3.66 | 3.78 | 4.19 | 4.43 | 0 |
| litestar | asgi | 2 | ok | 39826.27 | 2.51 | 2.53 | 3.36 | 3.97 | 0 |
| fastapi | asgi | 2 | ok | 27152.52 | 3.68 | 3.68 | 4.76 | 5.09 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 46164.74 | 2.16 | 2.18 | 2.80 | 3.44 | 0 |
| starlette | asgi | 2 | ok | 63516.06 | 1.57 | 1.50 | 2.48 | 2.99 | 0 |
| orionis-asgi | asgi | 2 | ok | 48465.41 | 2.06 | 2.03 | 2.96 | 3.61 | 0 |
| litestar | asgi | 3 | ok | 48676.24 | 2.05 | 1.95 | 3.34 | 4.23 | 0 |
| orionis-asgi | asgi | 3 | ok | 52332.42 | 1.91 | 1.80 | 3.15 | 4.07 | 0 |
| fastapi | asgi | 3 | ok | 39131.91 | 2.55 | 2.38 | 4.00 | 5.00 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 55017.56 | 1.82 | 1.72 | 3.05 | 3.93 | 0 |
| starlette | asgi | 3 | ok | 63151.68 | 1.58 | 1.52 | 2.63 | 3.38 | 0 |
| orionis-asgi | asgi | 4 | ok | 53178.91 | 1.88 | 1.77 | 3.26 | 4.22 | 0 |
| fastapi | asgi | 4 | ok | 36967.62 | 2.70 | 2.54 | 4.84 | 6.34 | 0 |
| litestar | asgi | 4 | ok | 47657.57 | 2.10 | 1.98 | 3.68 | 4.77 | 0 |
| starlette | asgi | 4 | ok | 59419.69 | 1.68 | 1.60 | 2.90 | 3.83 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 52430.66 | 1.90 | 1.79 | 3.36 | 4.39 | 0 |

## Environment

- os: Linux-7.0.0-1017-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 9V45 96-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: 64fd20a920efb384453ce9004dfb94027a97d501
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/40711551008
- orionis: 1.0.12
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 13609.57 | 7.34 | 7.10 | 10.07 | 10.49 | 0 |
| orionis-asgi | asgi | 1 | ok | 14742.88 | 6.78 | 5.91 | 9.45 | 9.89 | 0 |
| fastapi | asgi | 1 | ok | 9529.30 | 10.48 | 11.09 | 12.88 | 13.34 | 0 |
| starlette | asgi | 1 | ok | 23902.14 | 4.18 | 3.39 | 6.33 | 6.87 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 14558.23 | 6.86 | 6.66 | 9.33 | 9.61 | 0 |
| litestar | asgi | 2 | ok | 24877.39 | 4.02 | 3.95 | 5.27 | 5.85 | 0 |
| fastapi | asgi | 2 | ok | 16767.02 | 5.96 | 5.93 | 7.50 | 8.14 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 25940.70 | 3.85 | 3.78 | 5.13 | 5.62 | 0 |
| starlette | asgi | 2 | ok | 40004.20 | 2.50 | 2.44 | 3.60 | 4.17 | 0 |
| orionis-asgi | asgi | 2 | ok | 26390.81 | 3.79 | 3.73 | 5.01 | 5.60 | 0 |
| litestar | asgi | 3 | ok | 34985.69 | 2.86 | 2.72 | 4.40 | 5.39 | 0 |
| orionis-asgi | asgi | 3 | ok | 36368.75 | 2.75 | 2.59 | 4.30 | 5.39 | 0 |
| fastapi | asgi | 3 | ok | 25995.77 | 3.84 | 3.71 | 5.09 | 6.43 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 38282.52 | 2.61 | 2.47 | 4.00 | 5.00 | 0 |
| starlette | asgi | 3 | ok | 47463.04 | 2.10 | 2.03 | 3.36 | 4.17 | 0 |
| orionis-asgi | asgi | 4 | ok | 35124.77 | 2.84 | 2.69 | 4.89 | 6.30 | 0 |
| fastapi | asgi | 4 | ok | 25064.55 | 3.99 | 3.76 | 6.80 | 9.16 | 0 |
| litestar | asgi | 4 | ok | 32975.93 | 3.03 | 2.87 | 5.19 | 6.74 | 0 |
| starlette | asgi | 4 | ok | 47260.96 | 2.11 | 2.00 | 3.60 | 4.63 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 36534.19 | 2.73 | 2.57 | 4.78 | 6.16 | 0 |

## Environment

- os: Linux-7.0.0-1017-azure-x86_64-with-glibc2.39
- cpu: INTEL(R) XEON(R) PLATINUM 8573C
- logical_cpus: 4
- python: 3.14.8
- commit: a8eb83b5557779772bbd38a193459ee77f7849c6
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/39338527556
- orionis: 1.0.3
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

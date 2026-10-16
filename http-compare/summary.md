# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 29347.58 | 3.41 | 3.21 | 4.58 | 4.92 | 0 |
| orionis-asgi | asgi | 1 | ok | 30664.26 | 3.26 | 3.14 | 4.36 | 4.78 | 0 |
| fastapi | asgi | 1 | ok | 19972.73 | 5.00 | 4.73 | 6.66 | 6.99 | 0 |
| starlette | asgi | 1 | ok | 49692.87 | 2.01 | 1.96 | 2.70 | 2.93 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 24840.15 | 4.02 | 4.00 | 4.40 | 4.82 | 0 |
| litestar | asgi | 2 | ok | 40153.77 | 2.49 | 2.48 | 3.28 | 3.97 | 0 |
| fastapi | asgi | 2 | ok | 26871.10 | 3.72 | 3.55 | 5.20 | 5.99 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 44845.02 | 2.23 | 2.14 | 3.11 | 3.66 | 0 |
| starlette | asgi | 2 | ok | 66051.67 | 1.51 | 1.42 | 2.43 | 3.04 | 0 |
| orionis-asgi | asgi | 2 | ok | 44698.20 | 2.24 | 2.23 | 3.02 | 3.68 | 0 |
| litestar | asgi | 3 | ok | 47162.50 | 2.12 | 2.02 | 3.48 | 4.41 | 0 |
| orionis-asgi | asgi | 3 | ok | 48506.53 | 2.06 | 1.96 | 3.45 | 4.34 | 0 |
| fastapi | asgi | 3 | ok | 35638.20 | 2.80 | 2.70 | 4.37 | 5.58 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 50827.20 | 1.97 | 1.89 | 3.20 | 4.14 | 0 |
| starlette | asgi | 3 | ok | 61900.20 | 1.61 | 1.52 | 2.77 | 3.57 | 0 |
| orionis-asgi | asgi | 4 | ok | 47514.87 | 2.10 | 1.99 | 3.68 | 4.75 | 0 |
| fastapi | asgi | 4 | ok | 35333.01 | 2.83 | 2.64 | 5.00 | 6.33 | 0 |
| litestar | asgi | 4 | ok | 44786.99 | 2.23 | 2.11 | 3.88 | 5.04 | 0 |
| starlette | asgi | 4 | ok | 59623.61 | 1.68 | 1.56 | 3.05 | 4.03 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 48361.82 | 2.07 | 1.96 | 3.59 | 4.70 | 0 |

## Environment

- os: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 9V45 96-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: 61b02fe4096abf53ff7ed9f35ba45492c1bc57eb
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/38828050745
- orionis: 1.0.0
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

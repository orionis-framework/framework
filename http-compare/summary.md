# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 10431.01 | 9.58 | 8.04 | 13.77 | 14.10 | 0 |
| orionis-asgi | asgi | 1 | ok | 13285.30 | 7.52 | 6.05 | 11.45 | 11.84 | 0 |
| fastapi | asgi | 1 | ok | 7344.60 | 13.60 | 14.77 | 17.31 | 17.69 | 0 |
| starlette | asgi | 1 | ok | 19350.31 | 5.16 | 4.08 | 9.49 | 9.97 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 11258.19 | 8.87 | 8.48 | 11.86 | 12.12 | 0 |
| litestar | asgi | 2 | ok | 16122.30 | 6.20 | 6.21 | 7.80 | 8.62 | 0 |
| fastapi | asgi | 2 | ok | 11708.64 | 8.53 | 8.48 | 10.81 | 11.59 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 18464.73 | 5.41 | 5.25 | 7.00 | 7.88 | 0 |
| starlette | asgi | 2 | ok | 26346.77 | 3.79 | 3.72 | 5.38 | 6.26 | 0 |
| orionis-asgi | asgi | 2 | ok | 19703.03 | 5.07 | 5.02 | 6.95 | 7.81 | 0 |
| litestar | asgi | 3 | ok | 21316.93 | 4.68 | 4.51 | 6.90 | 8.33 | 0 |
| orionis-asgi | asgi | 3 | ok | 24636.12 | 4.05 | 3.88 | 6.18 | 7.38 | 0 |
| fastapi | asgi | 3 | ok | 16295.03 | 6.13 | 6.10 | 8.39 | 9.62 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 24451.41 | 4.08 | 3.95 | 5.91 | 7.08 | 0 |
| starlette | asgi | 3 | ok | 30047.39 | 3.32 | 3.23 | 5.22 | 6.40 | 0 |
| orionis-asgi | asgi | 4 | ok | 24250.32 | 4.12 | 3.94 | 6.76 | 8.42 | 0 |
| fastapi | asgi | 4 | ok | 16261.93 | 6.14 | 5.83 | 9.95 | 12.16 | 0 |
| litestar | asgi | 4 | ok | 20890.29 | 4.78 | 4.57 | 7.89 | 9.72 | 0 |
| starlette | asgi | 4 | ok | 29272.02 | 3.41 | 3.31 | 5.51 | 6.78 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 24419.25 | 4.09 | 3.91 | 6.82 | 8.50 | 0 |

## Environment

- os: Linux-7.0.0-1017-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 7763 64-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: 64fd20a920efb384453ce9004dfb94027a97d501
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/40750829235
- orionis: 1.0.12
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

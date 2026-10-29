# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 9777.33 | 10.22 | 10.39 | 13.05 | 13.32 | 0 |
| orionis-asgi | asgi | 1 | ok | 12325.70 | 8.10 | 7.78 | 10.92 | 11.32 | 0 |
| fastapi | asgi | 1 | ok | 7314.16 | 13.65 | 14.82 | 16.61 | 16.92 | 0 |
| starlette | asgi | 1 | ok | 16656.60 | 6.00 | 5.40 | 9.25 | 9.60 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 11809.00 | 8.46 | 7.75 | 11.22 | 11.51 | 0 |
| litestar | asgi | 2 | ok | 16256.69 | 6.14 | 6.12 | 8.00 | 8.74 | 0 |
| fastapi | asgi | 2 | ok | 11765.15 | 8.49 | 8.40 | 11.03 | 11.76 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 19499.02 | 5.12 | 5.00 | 6.45 | 7.17 | 0 |
| starlette | asgi | 2 | ok | 26676.70 | 3.74 | 3.66 | 5.29 | 6.16 | 0 |
| orionis-asgi | asgi | 2 | ok | 19747.19 | 5.06 | 5.00 | 6.49 | 7.29 | 0 |
| litestar | asgi | 3 | ok | 21315.38 | 4.69 | 4.50 | 6.91 | 8.42 | 0 |
| orionis-asgi | asgi | 3 | ok | 24640.54 | 4.05 | 3.89 | 6.17 | 7.47 | 0 |
| fastapi | asgi | 3 | ok | 16241.88 | 6.15 | 5.80 | 8.14 | 9.06 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 24747.79 | 4.04 | 3.85 | 6.15 | 7.55 | 0 |
| starlette | asgi | 3 | ok | 29818.39 | 3.35 | 3.24 | 5.24 | 6.34 | 0 |
| orionis-asgi | asgi | 4 | ok | 24318.82 | 4.11 | 3.94 | 6.77 | 8.43 | 0 |
| fastapi | asgi | 4 | ok | 16430.37 | 6.08 | 5.74 | 9.85 | 11.99 | 0 |
| litestar | asgi | 4 | ok | 20913.15 | 4.78 | 4.58 | 7.84 | 9.90 | 0 |
| starlette | asgi | 4 | ok | 29067.34 | 3.44 | 3.32 | 5.56 | 6.88 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 24414.29 | 4.09 | 3.92 | 6.79 | 8.60 | 0 |

## Environment

- os: Linux-7.0.0-1017-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 7763 64-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: a7af0099135c1f6100fc138755e8d632e3d56f02
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/40922473871
- orionis: 1.0.12
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

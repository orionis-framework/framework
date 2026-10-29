# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 10734.36 | 9.31 | 7.68 | 13.47 | 13.88 | 0 |
| orionis-asgi | asgi | 1 | ok | 13702.42 | 7.29 | 5.92 | 11.18 | 11.58 | 0 |
| fastapi | asgi | 1 | ok | 7666.32 | 13.03 | 12.10 | 17.03 | 17.42 | 0 |
| starlette | asgi | 1 | ok | 19545.83 | 5.11 | 4.04 | 9.20 | 9.60 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 11569.20 | 8.63 | 8.17 | 11.81 | 12.08 | 0 |
| litestar | asgi | 2 | ok | 16221.33 | 6.16 | 6.17 | 7.53 | 8.28 | 0 |
| fastapi | asgi | 2 | ok | 11821.57 | 8.45 | 8.43 | 10.32 | 11.05 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 18997.61 | 5.26 | 5.15 | 7.38 | 7.99 | 0 |
| starlette | asgi | 2 | ok | 27081.35 | 3.69 | 3.61 | 5.33 | 6.42 | 0 |
| orionis-asgi | asgi | 2 | ok | 19876.87 | 5.02 | 4.91 | 6.99 | 7.83 | 0 |
| litestar | asgi | 3 | ok | 21730.83 | 4.60 | 4.40 | 6.85 | 8.33 | 0 |
| orionis-asgi | asgi | 3 | ok | 25172.72 | 3.97 | 3.83 | 6.04 | 7.44 | 0 |
| fastapi | asgi | 3 | ok | 16495.30 | 6.05 | 5.88 | 8.75 | 9.49 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 25058.01 | 3.99 | 3.83 | 6.02 | 7.32 | 0 |
| starlette | asgi | 3 | ok | 30518.55 | 3.27 | 3.19 | 5.07 | 6.12 | 0 |
| orionis-asgi | asgi | 4 | ok | 24811.09 | 4.03 | 3.82 | 6.68 | 8.32 | 0 |
| fastapi | asgi | 4 | ok | 16780.36 | 5.95 | 5.56 | 9.81 | 12.02 | 0 |
| litestar | asgi | 4 | ok | 21628.42 | 4.62 | 4.41 | 7.52 | 9.54 | 0 |
| starlette | asgi | 4 | ok | 29724.87 | 3.36 | 3.25 | 5.45 | 6.80 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 25040.11 | 3.99 | 3.83 | 6.57 | 8.18 | 0 |

## Environment

- os: Linux-7.0.0-1017-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 7763 64-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: 07cb89a856b780c4272f052557e51392824e6dca
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/40960718446
- orionis: 1.0.13
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

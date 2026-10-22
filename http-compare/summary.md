# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 8672.16 | 11.52 | 10.93 | 14.65 | 15.11 | 0 |
| orionis-asgi | asgi | 1 | ok | 10088.74 | 9.90 | 8.89 | 12.75 | 13.13 | 0 |
| fastapi | asgi | 1 | ok | 6508.45 | 15.35 | 16.19 | 19.57 | 19.84 | 0 |
| starlette | asgi | 1 | ok | 14616.49 | 6.83 | 6.17 | 8.66 | 8.96 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 9981.50 | 10.01 | 9.34 | 12.47 | 12.66 | 0 |
| litestar | asgi | 2 | ok | 15287.64 | 6.53 | 6.48 | 8.49 | 9.51 | 0 |
| fastapi | asgi | 2 | ok | 11077.99 | 9.02 | 8.98 | 11.18 | 12.06 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 17118.97 | 5.83 | 5.82 | 7.28 | 8.29 | 0 |
| starlette | asgi | 2 | ok | 26091.87 | 3.83 | 3.72 | 5.78 | 6.84 | 0 |
| orionis-asgi | asgi | 2 | ok | 17278.44 | 5.78 | 5.80 | 7.29 | 8.28 | 0 |
| litestar | asgi | 3 | ok | 20281.39 | 4.92 | 4.74 | 7.41 | 8.81 | 0 |
| orionis-asgi | asgi | 3 | ok | 22165.05 | 4.51 | 4.33 | 6.88 | 8.23 | 0 |
| fastapi | asgi | 3 | ok | 16111.27 | 6.20 | 6.05 | 8.81 | 10.25 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 22621.35 | 4.41 | 4.24 | 6.61 | 7.96 | 0 |
| starlette | asgi | 3 | ok | 28860.69 | 3.46 | 3.37 | 5.41 | 6.50 | 0 |
| orionis-asgi | asgi | 4 | ok | 21214.50 | 4.71 | 4.54 | 7.63 | 9.37 | 0 |
| fastapi | asgi | 4 | ok | 15368.82 | 6.50 | 6.09 | 11.05 | 13.48 | 0 |
| litestar | asgi | 4 | ok | 20180.72 | 4.95 | 4.76 | 8.12 | 9.91 | 0 |
| starlette | asgi | 4 | ok | 27971.85 | 3.57 | 3.43 | 5.86 | 7.27 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 22079.76 | 4.52 | 4.30 | 7.62 | 9.48 | 0 |

## Environment

- os: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 7763 64-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: 0f0900de6721509cef5996617aa84a495c3d37eb
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/39784581581
- orionis: 1.0.5
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

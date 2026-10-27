# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 11088.94 | 9.01 | 9.26 | 10.45 | 10.74 | 0 |
| orionis-asgi | asgi | 1 | ok | 12344.65 | 8.09 | 8.50 | 9.35 | 9.59 | 0 |
| fastapi | asgi | 1 | ok | 8095.90 | 12.34 | 12.78 | 14.93 | 15.15 | 0 |
| starlette | asgi | 1 | ok | 16941.80 | 5.90 | 6.01 | 6.39 | 6.59 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 14258.24 | 7.01 | 6.56 | 9.31 | 9.48 | 0 |
| litestar | asgi | 2 | ok | 18442.67 | 5.42 | 5.55 | 6.88 | 7.62 | 0 |
| fastapi | asgi | 2 | ok | 13509.86 | 7.39 | 7.50 | 8.80 | 9.51 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 22430.11 | 4.45 | 4.40 | 6.02 | 6.52 | 0 |
| starlette | asgi | 2 | ok | 33669.64 | 2.97 | 2.88 | 4.37 | 5.22 | 0 |
| orionis-asgi | asgi | 2 | ok | 23786.46 | 4.20 | 4.11 | 6.25 | 6.86 | 0 |
| litestar | asgi | 3 | ok | 25561.66 | 3.91 | 3.75 | 6.15 | 7.36 | 0 |
| orionis-asgi | asgi | 3 | ok | 28315.15 | 3.53 | 3.40 | 5.56 | 6.75 | 0 |
| fastapi | asgi | 3 | ok | 19562.57 | 5.11 | 4.87 | 7.49 | 9.17 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 28795.87 | 3.47 | 3.33 | 5.47 | 6.74 | 0 |
| starlette | asgi | 3 | ok | 35445.15 | 2.82 | 2.72 | 4.50 | 5.42 | 0 |
| orionis-asgi | asgi | 4 | ok | 27105.80 | 3.69 | 3.54 | 6.09 | 7.61 | 0 |
| fastapi | asgi | 4 | ok | 18859.75 | 5.30 | 4.96 | 9.01 | 11.06 | 0 |
| litestar | asgi | 4 | ok | 23975.51 | 4.17 | 4.00 | 6.94 | 8.60 | 0 |
| starlette | asgi | 4 | ok | 32952.21 | 3.03 | 2.90 | 5.06 | 6.39 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 26906.06 | 3.71 | 3.55 | 6.23 | 7.80 | 0 |

## Environment

- os: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 9V74 80-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: cd986045be361834e5464443ca50bc88182ee159
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/40423108349
- orionis: 1.0.9
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

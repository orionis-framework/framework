# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 9163.42 | 10.90 | 9.56 | 14.38 | 14.76 | 0 |
| orionis-asgi | asgi | 1 | ok | 10591.85 | 9.43 | 8.27 | 12.58 | 13.08 | 0 |
| fastapi | asgi | 1 | ok | 6617.69 | 15.09 | 15.86 | 19.38 | 19.67 | 0 |
| starlette | asgi | 1 | ok | 14677.15 | 6.81 | 6.10 | 8.81 | 9.17 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 10344.22 | 9.66 | 8.82 | 12.43 | 12.70 | 0 |
| litestar | asgi | 2 | ok | 15603.36 | 6.40 | 6.42 | 7.88 | 8.88 | 0 |
| fastapi | asgi | 2 | ok | 10973.75 | 9.10 | 9.05 | 10.92 | 11.67 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 17403.64 | 5.74 | 5.63 | 7.55 | 8.60 | 0 |
| starlette | asgi | 2 | ok | 26048.62 | 3.83 | 3.77 | 5.33 | 6.15 | 0 |
| orionis-asgi | asgi | 2 | ok | 17268.59 | 5.78 | 5.61 | 7.33 | 8.27 | 0 |
| litestar | asgi | 3 | ok | 20395.73 | 4.90 | 4.72 | 7.29 | 8.57 | 0 |
| orionis-asgi | asgi | 3 | ok | 22715.54 | 4.40 | 4.24 | 6.77 | 8.08 | 0 |
| fastapi | asgi | 3 | ok | 16187.16 | 6.17 | 5.87 | 9.26 | 11.45 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 23002.35 | 4.34 | 4.14 | 6.64 | 8.03 | 0 |
| starlette | asgi | 3 | ok | 29456.71 | 3.39 | 3.31 | 5.31 | 6.49 | 0 |
| orionis-asgi | asgi | 4 | ok | 22466.40 | 4.45 | 4.27 | 7.30 | 9.00 | 0 |
| fastapi | asgi | 4 | ok | 16153.52 | 6.18 | 5.81 | 10.33 | 12.62 | 0 |
| litestar | asgi | 4 | ok | 20675.39 | 4.83 | 4.64 | 7.98 | 9.86 | 0 |
| starlette | asgi | 4 | ok | 28645.17 | 3.49 | 3.36 | 5.70 | 7.08 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 22635.33 | 4.41 | 4.21 | 7.30 | 9.10 | 0 |

## Environment

- os: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 7763 64-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: d0b6e9346ada59e69003df1a4114216ebd819140
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/39338417809
- orionis: 1.0.2
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

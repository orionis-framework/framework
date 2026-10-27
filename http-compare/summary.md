# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 9420.59 | 10.60 | 9.34 | 14.19 | 14.66 | 0 |
| orionis-asgi | asgi | 1 | ok | 11337.86 | 8.81 | 7.69 | 11.72 | 12.06 | 0 |
| fastapi | asgi | 1 | ok | 6568.63 | 15.20 | 16.05 | 19.61 | 19.93 | 0 |
| starlette | asgi | 1 | ok | 14826.77 | 6.74 | 5.99 | 8.82 | 9.11 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 10370.68 | 9.63 | 9.19 | 11.84 | 12.08 | 0 |
| litestar | asgi | 2 | ok | 15381.21 | 6.49 | 6.46 | 8.28 | 9.20 | 0 |
| fastapi | asgi | 2 | ok | 11163.25 | 8.95 | 9.00 | 10.31 | 11.15 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 19057.76 | 5.24 | 5.24 | 6.71 | 7.46 | 0 |
| starlette | asgi | 2 | ok | 26319.11 | 3.80 | 3.75 | 5.29 | 6.06 | 0 |
| orionis-asgi | asgi | 2 | ok | 18421.77 | 5.42 | 5.41 | 6.81 | 7.63 | 0 |
| litestar | asgi | 3 | ok | 20849.26 | 4.79 | 4.63 | 7.31 | 8.71 | 0 |
| orionis-asgi | asgi | 3 | ok | 24197.58 | 4.13 | 3.99 | 6.22 | 7.42 | 0 |
| fastapi | asgi | 3 | ok | 16939.91 | 5.90 | 5.90 | 8.29 | 10.20 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 24320.69 | 4.11 | 3.95 | 6.26 | 7.57 | 0 |
| starlette | asgi | 3 | ok | 29618.01 | 3.37 | 3.28 | 5.28 | 6.39 | 0 |
| orionis-asgi | asgi | 4 | ok | 23386.92 | 4.27 | 4.10 | 6.93 | 8.51 | 0 |
| fastapi | asgi | 4 | ok | 16088.90 | 6.21 | 5.86 | 10.23 | 12.53 | 0 |
| litestar | asgi | 4 | ok | 20511.29 | 4.87 | 4.67 | 8.04 | 9.89 | 0 |
| starlette | asgi | 4 | ok | 28329.98 | 3.53 | 3.40 | 5.71 | 7.05 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 23757.18 | 4.20 | 4.03 | 6.93 | 8.60 | 0 |

## Environment

- os: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 7763 64-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: 49353208eff746554bbd833a5cdbf03d9e7f7ccc
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/40582033183
- orionis: 1.0.11
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 10725.17 | 9.31 | 9.72 | 10.83 | 12.46 | 0 |
| orionis-asgi | asgi | 1 | ok | 11927.41 | 8.38 | 8.57 | 9.79 | 10.19 | 0 |
| fastapi | asgi | 1 | ok | 8060.03 | 12.39 | 12.89 | 14.86 | 15.18 | 0 |
| starlette | asgi | 1 | ok | 16442.70 | 6.08 | 6.14 | 6.72 | 7.09 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 14340.53 | 6.97 | 6.59 | 9.47 | 10.01 | 0 |
| litestar | asgi | 2 | ok | 19090.35 | 5.23 | 5.28 | 6.72 | 7.40 | 0 |
| fastapi | asgi | 2 | ok | 13474.83 | 7.41 | 7.49 | 9.17 | 9.92 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 21897.15 | 4.56 | 4.70 | 5.90 | 6.55 | 0 |
| starlette | asgi | 2 | ok | 34026.29 | 2.94 | 2.83 | 4.39 | 5.16 | 0 |
| orionis-asgi | asgi | 2 | ok | 22363.18 | 4.47 | 4.45 | 6.06 | 6.95 | 0 |
| litestar | asgi | 3 | ok | 25503.11 | 3.92 | 3.77 | 6.32 | 7.74 | 0 |
| orionis-asgi | asgi | 3 | ok | 29204.14 | 3.42 | 3.31 | 5.53 | 6.87 | 0 |
| fastapi | asgi | 3 | ok | 20203.61 | 4.94 | 4.79 | 7.18 | 8.58 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 29335.27 | 3.41 | 3.26 | 5.40 | 6.59 | 0 |
| starlette | asgi | 3 | ok | 36601.92 | 2.73 | 2.65 | 4.27 | 5.23 | 0 |
| orionis-asgi | asgi | 4 | ok | 27719.21 | 3.60 | 3.45 | 5.96 | 7.37 | 0 |
| fastapi | asgi | 4 | ok | 18976.90 | 5.26 | 4.94 | 9.08 | 11.23 | 0 |
| litestar | asgi | 4 | ok | 24844.36 | 4.02 | 3.84 | 6.74 | 8.42 | 0 |
| starlette | asgi | 4 | ok | 34195.88 | 2.92 | 2.79 | 4.86 | 6.07 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 27905.31 | 3.58 | 3.43 | 6.01 | 7.50 | 0 |

## Environment

- os: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 9V74 80-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: d3e0ca8010b6fec48a4a8ecf49e1fba164858e53
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/40542746373
- orionis: 1.0.9
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

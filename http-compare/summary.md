# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 9223.66 | 10.83 | 9.67 | 14.43 | 14.82 | 0 |
| orionis-asgi | asgi | 1 | ok | 10490.77 | 9.52 | 8.46 | 12.50 | 12.90 | 0 |
| fastapi | asgi | 1 | ok | 6471.22 | 15.43 | 16.05 | 19.52 | 19.88 | 0 |
| starlette | asgi | 1 | ok | 15078.04 | 6.63 | 5.89 | 8.66 | 8.97 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 10163.11 | 9.83 | 8.97 | 12.63 | 12.89 | 0 |
| litestar | asgi | 2 | ok | 15315.84 | 6.52 | 6.50 | 8.12 | 8.86 | 0 |
| fastapi | asgi | 2 | ok | 11032.94 | 9.05 | 9.01 | 10.94 | 11.66 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 17348.14 | 5.76 | 5.75 | 7.06 | 7.84 | 0 |
| starlette | asgi | 2 | ok | 26539.49 | 3.76 | 3.71 | 5.31 | 6.15 | 0 |
| orionis-asgi | asgi | 2 | ok | 17054.84 | 5.86 | 5.90 | 7.29 | 8.07 | 0 |
| litestar | asgi | 3 | ok | 20632.37 | 4.84 | 4.73 | 7.29 | 8.63 | 0 |
| orionis-asgi | asgi | 3 | ok | 22332.90 | 4.47 | 4.33 | 6.77 | 8.10 | 0 |
| fastapi | asgi | 3 | ok | 16719.83 | 5.97 | 5.90 | 8.65 | 9.98 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 23085.47 | 4.33 | 4.15 | 6.58 | 7.89 | 0 |
| starlette | asgi | 3 | ok | 29667.98 | 3.37 | 3.28 | 5.21 | 6.29 | 0 |
| orionis-asgi | asgi | 4 | ok | 22513.07 | 4.44 | 4.26 | 7.27 | 8.91 | 0 |
| fastapi | asgi | 4 | ok | 15964.02 | 6.26 | 5.92 | 10.15 | 12.40 | 0 |
| litestar | asgi | 4 | ok | 20504.22 | 4.87 | 4.65 | 7.98 | 9.86 | 0 |
| starlette | asgi | 4 | ok | 28401.09 | 3.52 | 3.39 | 5.71 | 7.06 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 22712.62 | 4.40 | 4.22 | 7.21 | 9.00 | 0 |

## Environment

- os: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 7763 64-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: 3342f87f6813af8adb112c7acef6132d0a5cb7f0
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/39873624486
- orionis: 1.0.7
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 18767.02 | 5.32 | 4.39 | 8.61 | 8.78 | 0 |
| orionis-asgi | asgi | 1 | ok | 23839.23 | 4.19 | 3.52 | 7.43 | 7.73 | 0 |
| fastapi | asgi | 1 | ok | 13289.91 | 7.52 | 6.23 | 11.29 | 11.47 | 0 |
| starlette | asgi | 1 | ok | 30936.22 | 3.23 | 2.70 | 5.56 | 5.80 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 18161.59 | 5.50 | 5.57 | 7.04 | 7.18 | 0 |
| litestar | asgi | 2 | ok | 24977.61 | 4.00 | 4.03 | 5.16 | 5.66 | 0 |
| fastapi | asgi | 2 | ok | 18770.03 | 5.32 | 5.31 | 6.85 | 7.35 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 27920.42 | 3.58 | 3.67 | 4.68 | 5.38 | 0 |
| starlette | asgi | 2 | ok | 42941.13 | 2.33 | 2.24 | 3.51 | 4.24 | 0 |
| orionis-asgi | asgi | 2 | ok | 30078.62 | 3.32 | 3.23 | 4.80 | 5.34 | 0 |
| litestar | asgi | 3 | ok | 33333.98 | 3.00 | 2.83 | 4.85 | 6.19 | 0 |
| orionis-asgi | asgi | 3 | ok | 37783.63 | 2.64 | 2.50 | 4.29 | 5.45 | 0 |
| fastapi | asgi | 3 | ok | 25935.13 | 3.85 | 3.67 | 5.68 | 6.53 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 37997.57 | 2.63 | 2.49 | 4.25 | 5.33 | 0 |
| starlette | asgi | 3 | ok | 45354.70 | 2.20 | 2.12 | 3.61 | 4.53 | 0 |
| orionis-asgi | asgi | 4 | ok | 36223.48 | 2.76 | 2.62 | 4.74 | 6.11 | 0 |
| fastapi | asgi | 4 | ok | 25531.30 | 3.91 | 3.60 | 6.83 | 8.80 | 0 |
| litestar | asgi | 4 | ok | 33026.09 | 3.02 | 2.88 | 5.14 | 6.55 | 0 |
| starlette | asgi | 4 | ok | 44480.97 | 2.25 | 2.14 | 3.79 | 4.83 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 36172.02 | 2.76 | 2.62 | 4.71 | 6.09 | 0 |

## Environment

- os: Linux-7.0.0-1017-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 9V74 80-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: 556ad8188c961d05fcb4b3c4630b626100494d72
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/39690556448
- orionis: 1.0.5
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

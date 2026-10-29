# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 26910.56 | 3.71 | 4.07 | 4.58 | 4.96 | 0 |
| orionis-asgi | asgi | 1 | ok | 30081.52 | 3.32 | 3.59 | 4.11 | 4.35 | 0 |
| fastapi | asgi | 1 | ok | 18370.69 | 5.44 | 5.80 | 6.61 | 6.77 | 0 |
| starlette | asgi | 1 | ok | 43595.84 | 2.29 | 2.47 | 2.87 | 3.17 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 27617.65 | 3.62 | 3.73 | 4.07 | 4.18 | 0 |
| litestar | asgi | 2 | ok | 40757.98 | 2.45 | 2.48 | 3.20 | 3.59 | 0 |
| fastapi | asgi | 2 | ok | 28046.79 | 3.56 | 3.62 | 4.49 | 4.89 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 50393.95 | 1.98 | 1.99 | 2.61 | 3.10 | 0 |
| starlette | asgi | 2 | ok | 70249.21 | 1.42 | 1.37 | 2.16 | 2.59 | 0 |
| orionis-asgi | asgi | 2 | ok | 51137.46 | 1.95 | 1.91 | 2.68 | 3.06 | 0 |
| litestar | asgi | 3 | ok | 52807.45 | 1.89 | 1.80 | 3.06 | 3.77 | 0 |
| orionis-asgi | asgi | 3 | ok | 57353.53 | 1.74 | 1.68 | 2.77 | 3.47 | 0 |
| fastapi | asgi | 3 | ok | 41510.38 | 2.41 | 2.28 | 3.66 | 4.38 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 57941.98 | 1.72 | 1.65 | 2.79 | 3.60 | 0 |
| starlette | asgi | 3 | ok | 66991.52 | 1.49 | 1.42 | 2.47 | 3.17 | 0 |
| orionis-asgi | asgi | 4 | ok | 54484.73 | 1.83 | 1.72 | 3.23 | 4.17 | 0 |
| fastapi | asgi | 4 | ok | 38189.50 | 2.62 | 2.41 | 4.69 | 6.25 | 0 |
| litestar | asgi | 4 | ok | 48744.49 | 2.05 | 1.93 | 3.60 | 4.75 | 0 |
| starlette | asgi | 4 | ok | 60898.76 | 1.64 | 1.56 | 2.83 | 3.76 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 53893.68 | 1.85 | 1.75 | 3.26 | 4.29 | 0 |

## Environment

- os: Linux-7.0.0-1017-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 9V45 96-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: c9adbab899f21572adceb137f01e4fae37e9824a
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/40968186797
- orionis: 1.0.15
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

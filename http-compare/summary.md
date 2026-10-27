# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 8836.78 | 11.30 | 10.88 | 14.40 | 14.74 | 0 |
| orionis-asgi | asgi | 1 | ok | 11326.25 | 8.82 | 7.87 | 11.53 | 11.83 | 0 |
| fastapi | asgi | 1 | ok | 6716.55 | 14.87 | 15.75 | 19.44 | 19.71 | 0 |
| starlette | asgi | 1 | ok | 14465.29 | 6.91 | 6.38 | 8.73 | 9.03 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 10874.91 | 9.19 | 8.56 | 11.57 | 11.74 | 0 |
| litestar | asgi | 2 | ok | 15393.76 | 6.49 | 6.41 | 7.89 | 8.80 | 0 |
| fastapi | asgi | 2 | ok | 11171.30 | 8.94 | 8.96 | 10.62 | 11.67 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 19616.52 | 5.09 | 5.01 | 6.56 | 7.33 | 0 |
| starlette | asgi | 2 | ok | 26477.34 | 3.77 | 3.72 | 5.36 | 6.31 | 0 |
| orionis-asgi | asgi | 2 | ok | 18454.95 | 5.41 | 5.42 | 6.86 | 7.72 | 0 |
| litestar | asgi | 3 | ok | 21206.26 | 4.71 | 4.62 | 7.02 | 8.29 | 0 |
| orionis-asgi | asgi | 3 | ok | 24271.10 | 4.12 | 3.98 | 6.35 | 7.50 | 0 |
| fastapi | asgi | 3 | ok | 16300.74 | 6.13 | 5.89 | 8.72 | 10.70 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 23945.29 | 4.17 | 4.01 | 6.49 | 7.78 | 0 |
| starlette | asgi | 3 | ok | 29042.43 | 3.44 | 3.34 | 5.35 | 6.45 | 0 |
| orionis-asgi | asgi | 4 | ok | 22862.56 | 4.37 | 4.20 | 7.18 | 8.85 | 0 |
| fastapi | asgi | 4 | ok | 15901.14 | 6.28 | 5.99 | 10.41 | 12.64 | 0 |
| litestar | asgi | 4 | ok | 20165.46 | 4.95 | 4.75 | 8.08 | 9.91 | 0 |
| starlette | asgi | 4 | ok | 27818.57 | 3.59 | 3.47 | 5.80 | 7.18 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 23666.63 | 4.22 | 4.06 | 7.00 | 8.71 | 0 |

## Environment

- os: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 7763 64-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: f88e40fa6bacbde74c6697b08481386ffd1000bb
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/40579116867
- orionis: 1.0.10
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

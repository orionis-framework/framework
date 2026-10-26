# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 8796.78 | 11.35 | 10.49 | 14.32 | 14.73 | 0 |
| orionis-asgi | asgi | 1 | ok | 9823.78 | 10.17 | 9.54 | 12.58 | 12.90 | 0 |
| fastapi | asgi | 1 | ok | 6571.62 | 15.20 | 16.09 | 19.24 | 19.53 | 0 |
| starlette | asgi | 1 | ok | 13530.81 | 7.38 | 7.96 | 8.77 | 9.05 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 9610.69 | 10.39 | 10.86 | 12.50 | 12.70 | 0 |
| litestar | asgi | 2 | ok | 15266.51 | 6.54 | 6.47 | 8.25 | 9.20 | 0 |
| fastapi | asgi | 2 | ok | 11082.26 | 9.01 | 9.04 | 10.66 | 11.50 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 17584.61 | 5.68 | 5.62 | 7.55 | 8.57 | 0 |
| starlette | asgi | 2 | ok | 26589.21 | 3.76 | 3.68 | 5.50 | 6.35 | 0 |
| orionis-asgi | asgi | 2 | ok | 17037.23 | 5.86 | 5.88 | 7.54 | 8.49 | 0 |
| litestar | asgi | 3 | ok | 20192.92 | 4.95 | 4.78 | 7.50 | 8.86 | 0 |
| orionis-asgi | asgi | 3 | ok | 22075.22 | 4.52 | 4.38 | 6.94 | 8.32 | 0 |
| fastapi | asgi | 3 | ok | 16207.37 | 6.16 | 6.01 | 8.65 | 10.23 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 22682.25 | 4.40 | 4.21 | 6.65 | 7.88 | 0 |
| starlette | asgi | 3 | ok | 29240.91 | 3.42 | 3.33 | 5.33 | 6.42 | 0 |
| orionis-asgi | asgi | 4 | ok | 21842.60 | 4.57 | 4.41 | 7.48 | 9.16 | 0 |
| fastapi | asgi | 4 | ok | 15774.59 | 6.33 | 5.99 | 10.41 | 12.73 | 0 |
| litestar | asgi | 4 | ok | 19943.98 | 5.01 | 4.79 | 8.29 | 10.11 | 0 |
| starlette | asgi | 4 | ok | 27535.84 | 3.63 | 3.49 | 5.90 | 7.37 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 22109.67 | 4.52 | 4.35 | 7.38 | 9.03 | 0 |

## Environment

- os: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 7763 64-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: 5d8ab302566d47c59ba423cc46f29ab0c77f6231
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/40353724611
- orionis: 1.0.8
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 27088.17 | 3.69 | 3.95 | 4.58 | 5.07 | 0 |
| orionis-asgi | asgi | 1 | ok | 30272.41 | 3.30 | 3.51 | 4.10 | 4.50 | 0 |
| fastapi | asgi | 1 | ok | 18598.34 | 5.37 | 5.63 | 6.73 | 7.18 | 0 |
| starlette | asgi | 1 | ok | 42012.49 | 2.38 | 2.47 | 3.03 | 3.59 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 26660.69 | 3.75 | 3.81 | 4.32 | 5.66 | 0 |
| litestar | asgi | 2 | ok | 39968.95 | 2.50 | 2.49 | 3.42 | 4.26 | 0 |
| fastapi | asgi | 2 | ok | 27220.22 | 3.67 | 3.73 | 4.56 | 4.95 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 48147.91 | 2.07 | 2.05 | 2.85 | 3.69 | 0 |
| starlette | asgi | 2 | ok | 61689.98 | 1.62 | 1.54 | 2.55 | 3.10 | 0 |
| orionis-asgi | asgi | 2 | ok | 48348.59 | 2.07 | 2.03 | 2.89 | 3.60 | 0 |
| litestar | asgi | 3 | ok | 49864.72 | 2.00 | 1.90 | 3.33 | 4.24 | 0 |
| orionis-asgi | asgi | 3 | ok | 56287.19 | 1.77 | 1.70 | 2.94 | 3.74 | 0 |
| fastapi | asgi | 3 | ok | 41984.77 | 2.38 | 2.27 | 3.64 | 4.50 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 58257.12 | 1.71 | 1.64 | 2.77 | 3.61 | 0 |
| starlette | asgi | 3 | ok | 65093.34 | 1.53 | 1.46 | 2.58 | 3.34 | 0 |
| orionis-asgi | asgi | 4 | ok | 54143.85 | 1.85 | 1.73 | 3.21 | 4.20 | 0 |
| fastapi | asgi | 4 | ok | 38515.35 | 2.59 | 2.42 | 4.68 | 6.12 | 0 |
| litestar | asgi | 4 | ok | 49823.62 | 2.00 | 1.89 | 3.47 | 4.52 | 0 |
| starlette | asgi | 4 | ok | 63538.34 | 1.57 | 1.48 | 2.76 | 3.67 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 51834.33 | 1.93 | 1.80 | 3.42 | 4.56 | 0 |

## Environment

- os: Linux-7.0.0-1017-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 9V45 96-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: 8ae1c9cdea922c91698bddea5d5837e41068ceb3
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/40990349139
- orionis: 1.0.16
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

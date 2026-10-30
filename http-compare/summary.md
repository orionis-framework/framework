# HTTP framework comparison

100 connections; 2.0s warmup; 3 x 10.0s per configuration.
HTTP/1.1 keep-alive; Granian runtime threads: 1; asyncio; oha worker threads: 1.
Medians of individual runs; throughput counts HTTP 200 only. Latency is in ms.

| Framework | Interface | Workers | Status | Requests/s | Mean | p50 | p95 | p99 | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 28748.66 | 3.48 | 3.63 | 4.46 | 5.03 | 0 |
| orionis-asgi | asgi | 1 | ok | 31248.45 | 3.20 | 3.40 | 4.01 | 4.44 | 0 |
| fastapi | asgi | 1 | ok | 19610.62 | 5.10 | 5.33 | 6.27 | 6.55 | 0 |
| starlette | asgi | 1 | ok | 46734.50 | 2.14 | 2.21 | 2.75 | 3.08 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 28498.62 | 3.51 | 3.56 | 3.99 | 4.20 | 0 |
| litestar | asgi | 2 | ok | 44507.77 | 2.24 | 2.23 | 2.96 | 3.49 | 0 |
| fastapi | asgi | 2 | ok | 28894.39 | 3.46 | 3.27 | 4.83 | 5.16 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 50888.50 | 1.96 | 1.86 | 2.61 | 3.34 | 0 |
| starlette | asgi | 2 | ok | 66520.25 | 1.50 | 1.44 | 2.32 | 2.77 | 0 |
| orionis-asgi | asgi | 2 | ok | 50504.23 | 1.98 | 1.93 | 2.80 | 3.39 | 0 |
| litestar | asgi | 3 | ok | 51862.77 | 1.93 | 1.83 | 3.10 | 3.85 | 0 |
| orionis-asgi | asgi | 3 | ok | 56357.53 | 1.77 | 1.70 | 2.87 | 3.64 | 0 |
| fastapi | asgi | 3 | ok | 40936.96 | 2.44 | 2.32 | 3.84 | 4.68 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 57846.24 | 1.73 | 1.64 | 2.85 | 3.68 | 0 |
| starlette | asgi | 3 | ok | 65316.60 | 1.53 | 1.45 | 2.58 | 3.37 | 0 |
| orionis-asgi | asgi | 4 | ok | 53940.63 | 1.85 | 1.75 | 3.25 | 4.22 | 0 |
| fastapi | asgi | 4 | ok | 37857.63 | 2.64 | 2.41 | 4.78 | 6.20 | 0 |
| litestar | asgi | 4 | ok | 50120.20 | 1.99 | 1.89 | 3.49 | 4.57 | 0 |
| starlette | asgi | 4 | ok | 62922.03 | 1.59 | 1.51 | 2.75 | 3.61 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 55174.20 | 1.81 | 1.72 | 3.13 | 4.12 | 0 |

## Environment

- os: Linux-7.0.0-1017-azure-x86_64-with-glibc2.39
- cpu: AMD EPYC 9V45 96-Core Processor
- logical_cpus: 4
- python: 3.14.8
- commit: 8ae1c9cdea922c91698bddea5d5837e41068ceb3
- dirty: False
- run_url: https://github.com/orionis-framework/framework/actions/runs/40976091720
- orionis: 1.0.16
- granian: 2.8.4
- fastapi: 0.143.1
- litestar: 2.24.0
- starlette: 1.8.0
- oha: 1.16.0

GitHub-hosted runners vary; this Hello World test does not represent a full application.

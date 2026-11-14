# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 10047.15 | 9.95 | 9.55 | 11.20 | 11.53 | 0 |
| orionis-asgi | asgi | 1 | ok | 27833.81 | 3.59 | 3.82 | 4.43 | 4.71 | 0 |
| fastapi | asgi | 1 | ok | 8774.87 | 11.39 | 11.13 | 12.92 | 15.02 | 0 |
| starlette | asgi | 1 | ok | 12093.55 | 8.26 | 8.06 | 9.53 | 9.79 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 26929.11 | 3.71 | 3.63 | 4.22 | 4.47 | 0 |
| litestar | asgi | 2 | ok | 18530.74 | 5.39 | 4.85 | 6.35 | 7.36 | 0 |
| fastapi | asgi | 2 | ok | 16208.43 | 6.16 | 5.80 | 7.48 | 8.12 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 42225.41 | 2.37 | 2.44 | 3.02 | 3.50 | 0 |
| starlette | asgi | 2 | ok | 21856.85 | 4.57 | 4.11 | 5.52 | 6.18 | 0 |
| orionis-asgi | asgi | 2 | ok | 42834.08 | 2.33 | 2.33 | 3.12 | 3.83 | 0 |
| litestar | asgi | 3 | ok | 19824.91 | 5.04 | 5.16 | 6.59 | 8.07 | 0 |
| orionis-asgi | asgi | 3 | ok | 53221.37 | 1.88 | 1.79 | 3.04 | 3.83 | 0 |
| fastapi | asgi | 3 | ok | 17466.57 | 5.72 | 5.80 | 7.81 | 9.18 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 54231.92 | 1.84 | 1.75 | 3.03 | 3.94 | 0 |
| starlette | asgi | 3 | ok | 22978.22 | 4.35 | 4.47 | 5.91 | 6.67 | 0 |
| orionis-asgi | asgi | 4 | ok | 50615.36 | 1.97 | 1.85 | 3.48 | 4.58 | 0 |
| fastapi | asgi | 4 | ok | 18325.37 | 5.45 | 6.07 | 9.34 | 11.87 | 0 |
| litestar | asgi | 4 | ok | 21223.33 | 4.71 | 4.52 | 7.97 | 10.13 | 0 |
| starlette | asgi | 4 | ok | 24790.97 | 4.03 | 3.88 | 6.44 | 7.98 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 52461.28 | 1.90 | 1.78 | 3.35 | 4.47 | 0 |

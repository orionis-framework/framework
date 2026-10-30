# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 19963.15 | 5.01 | 4.02 | 8.53 | 8.82 | 0 |
| orionis-asgi | asgi | 1 | ok | 25512.18 | 3.92 | 3.33 | 7.22 | 7.45 | 0 |
| fastapi | asgi | 1 | ok | 13604.61 | 7.34 | 6.07 | 11.15 | 11.38 | 0 |
| starlette | asgi | 1 | ok | 31351.91 | 3.19 | 2.69 | 5.49 | 5.73 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 18896.36 | 5.29 | 5.73 | 6.68 | 6.79 | 0 |
| litestar | asgi | 2 | ok | 25808.39 | 3.87 | 3.85 | 5.45 | 5.86 | 0 |
| fastapi | asgi | 2 | ok | 18913.29 | 5.28 | 5.25 | 6.84 | 7.25 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 29833.72 | 3.35 | 3.40 | 4.49 | 4.82 | 0 |
| starlette | asgi | 2 | ok | 44433.87 | 2.25 | 2.16 | 3.37 | 4.01 | 0 |
| orionis-asgi | asgi | 2 | ok | 32266.76 | 3.10 | 3.04 | 4.48 | 4.96 | 0 |
| litestar | asgi | 3 | ok | 33760.73 | 2.96 | 2.81 | 4.73 | 5.82 | 0 |
| orionis-asgi | asgi | 3 | ok | 39541.61 | 2.53 | 2.41 | 4.07 | 5.09 | 0 |
| fastapi | asgi | 3 | ok | 25822.07 | 3.87 | 3.65 | 5.73 | 6.69 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 39564.08 | 2.52 | 2.40 | 4.09 | 5.13 | 0 |
| starlette | asgi | 3 | ok | 46695.45 | 2.14 | 2.06 | 3.40 | 4.20 | 0 |
| orionis-asgi | asgi | 4 | ok | 36401.65 | 2.74 | 2.61 | 4.62 | 5.89 | 0 |
| fastapi | asgi | 4 | ok | 24414.48 | 4.09 | 3.86 | 7.00 | 8.97 | 0 |
| litestar | asgi | 4 | ok | 31478.70 | 3.17 | 3.02 | 5.29 | 6.75 | 0 |
| starlette | asgi | 4 | ok | 42972.44 | 2.32 | 2.21 | 3.88 | 4.93 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 37004.28 | 2.70 | 2.56 | 4.63 | 5.96 | 0 |

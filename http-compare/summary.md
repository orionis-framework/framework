# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 7398.71 | 13.50 | 12.94 | 16.90 | 17.14 | 0 |
| orionis-asgi | asgi | 1 | ok | 24799.30 | 4.03 | 3.38 | 7.24 | 7.54 | 0 |
| fastapi | asgi | 1 | ok | 6358.97 | 15.71 | 15.03 | 19.08 | 19.41 | 0 |
| starlette | asgi | 1 | ok | 9340.86 | 10.70 | 10.25 | 14.07 | 14.28 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 21122.12 | 4.73 | 4.33 | 6.61 | 6.74 | 0 |
| litestar | asgi | 2 | ok | 12700.32 | 7.87 | 6.62 | 10.32 | 10.81 | 0 |
| fastapi | asgi | 2 | ok | 11081.95 | 9.01 | 7.78 | 11.31 | 11.64 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 31217.06 | 3.20 | 3.17 | 4.59 | 4.98 | 0 |
| starlette | asgi | 2 | ok | 15347.47 | 6.51 | 5.26 | 9.07 | 9.46 | 0 |
| orionis-asgi | asgi | 2 | ok | 31282.91 | 3.19 | 3.17 | 4.40 | 4.98 | 0 |
| litestar | asgi | 3 | ok | 12300.04 | 8.12 | 8.15 | 9.76 | 10.61 | 0 |
| orionis-asgi | asgi | 3 | ok | 39530.06 | 2.53 | 2.41 | 4.04 | 4.96 | 0 |
| fastapi | asgi | 3 | ok | 10977.16 | 9.10 | 9.61 | 11.64 | 12.36 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 40688.48 | 2.46 | 2.34 | 3.94 | 4.90 | 0 |
| starlette | asgi | 3 | ok | 14543.47 | 6.87 | 6.91 | 8.11 | 9.49 | 0 |
| orionis-asgi | asgi | 4 | ok | 37789.64 | 2.64 | 2.52 | 4.43 | 5.69 | 0 |
| fastapi | asgi | 4 | ok | 11741.24 | 8.51 | 7.70 | 13.99 | 16.34 | 0 |
| litestar | asgi | 4 | ok | 13254.67 | 7.54 | 7.66 | 11.91 | 15.09 | 0 |
| starlette | asgi | 4 | ok | 15708.97 | 6.36 | 6.27 | 9.53 | 13.06 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 39086.62 | 2.56 | 2.42 | 4.40 | 5.82 | 0 |

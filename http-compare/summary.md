# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 6993.71 | 14.28 | 13.77 | 17.76 | 18.06 | 0 |
| orionis-asgi | asgi | 1 | ok | 20601.61 | 4.85 | 4.04 | 7.94 | 8.24 | 0 |
| fastapi | asgi | 1 | ok | 6061.01 | 16.48 | 15.43 | 19.58 | 19.91 | 0 |
| starlette | asgi | 1 | ok | 9182.94 | 10.88 | 10.48 | 14.28 | 14.55 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 16483.48 | 6.06 | 6.69 | 7.46 | 7.64 | 0 |
| litestar | asgi | 2 | ok | 12508.58 | 7.98 | 6.72 | 10.59 | 10.87 | 0 |
| fastapi | asgi | 2 | ok | 11114.06 | 8.99 | 7.57 | 12.07 | 12.36 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 25918.17 | 3.85 | 4.01 | 4.84 | 5.57 | 0 |
| starlette | asgi | 2 | ok | 15473.68 | 6.46 | 5.20 | 9.20 | 9.54 | 0 |
| orionis-asgi | asgi | 2 | ok | 27378.27 | 3.65 | 3.64 | 4.90 | 5.50 | 0 |
| litestar | asgi | 3 | ok | 12303.30 | 8.12 | 8.33 | 9.90 | 11.41 | 0 |
| orionis-asgi | asgi | 3 | ok | 35718.31 | 2.80 | 2.66 | 4.46 | 5.52 | 0 |
| fastapi | asgi | 3 | ok | 11039.85 | 9.05 | 9.43 | 10.71 | 11.86 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 35492.32 | 2.81 | 2.66 | 4.55 | 5.80 | 0 |
| starlette | asgi | 3 | ok | 14380.04 | 6.95 | 7.53 | 8.08 | 10.16 | 0 |
| orionis-asgi | asgi | 4 | ok | 32921.96 | 3.03 | 2.89 | 5.08 | 6.45 | 0 |
| fastapi | asgi | 4 | ok | 11673.68 | 8.56 | 8.30 | 15.06 | 17.43 | 0 |
| litestar | asgi | 4 | ok | 12929.33 | 7.73 | 8.53 | 11.98 | 13.40 | 0 |
| starlette | asgi | 4 | ok | 15408.91 | 6.48 | 6.34 | 9.70 | 11.59 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 33849.53 | 2.95 | 2.80 | 5.02 | 6.50 | 0 |

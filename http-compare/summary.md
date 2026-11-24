# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 8151.20 | 12.26 | 12.03 | 12.81 | 12.93 | 0 |
| orionis-asgi | asgi | 1 | ok | 27626.96 | 3.62 | 3.57 | 4.39 | 4.76 | 0 |
| fastapi | asgi | 1 | ok | 7351.45 | 13.59 | 13.43 | 14.39 | 14.49 | 0 |
| starlette | asgi | 1 | ok | 9791.00 | 10.21 | 10.04 | 10.71 | 10.82 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 24080.58 | 4.15 | 4.36 | 4.80 | 4.99 | 0 |
| litestar | asgi | 2 | ok | 15515.00 | 6.44 | 6.26 | 7.18 | 7.32 | 0 |
| fastapi | asgi | 2 | ok | 13752.76 | 7.27 | 7.06 | 7.93 | 9.93 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 38807.55 | 2.57 | 2.55 | 3.32 | 3.75 | 0 |
| starlette | asgi | 2 | ok | 18330.53 | 5.45 | 5.28 | 6.01 | 6.75 | 0 |
| orionis-asgi | asgi | 2 | ok | 40228.31 | 2.48 | 2.45 | 3.17 | 3.67 | 0 |
| litestar | asgi | 3 | ok | 17266.39 | 5.79 | 6.19 | 6.77 | 8.28 | 0 |
| orionis-asgi | asgi | 3 | ok | 50023.32 | 2.00 | 1.91 | 2.98 | 3.65 | 0 |
| fastapi | asgi | 3 | ok | 15355.67 | 6.51 | 7.06 | 7.87 | 8.46 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 52124.41 | 1.92 | 1.86 | 2.93 | 3.70 | 0 |
| starlette | asgi | 3 | ok | 20519.57 | 4.87 | 5.25 | 5.80 | 7.15 | 0 |
| orionis-asgi | asgi | 4 | ok | 47108.05 | 2.12 | 2.01 | 3.64 | 4.73 | 0 |
| fastapi | asgi | 4 | ok | 16210.50 | 6.16 | 6.91 | 10.26 | 11.83 | 0 |
| litestar | asgi | 4 | ok | 18181.11 | 5.50 | 6.03 | 9.03 | 10.22 | 0 |
| starlette | asgi | 4 | ok | 21792.10 | 4.59 | 4.72 | 7.33 | 8.09 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 49098.92 | 2.03 | 1.91 | 3.66 | 4.88 | 0 |

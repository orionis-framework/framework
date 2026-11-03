# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 5618.62 | 17.78 | 16.79 | 22.05 | 22.30 | 0 |
| orionis-asgi | asgi | 1 | ok | 17944.98 | 5.57 | 4.62 | 9.37 | 9.66 | 0 |
| fastapi | asgi | 1 | ok | 4797.20 | 20.82 | 19.75 | 25.05 | 25.60 | 0 |
| starlette | asgi | 1 | ok | 7066.52 | 14.14 | 13.54 | 18.49 | 18.80 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 15493.67 | 6.45 | 6.39 | 8.62 | 8.78 | 0 |
| litestar | asgi | 2 | ok | 9742.95 | 10.25 | 8.60 | 13.95 | 14.19 | 0 |
| fastapi | asgi | 2 | ok | 8506.14 | 11.74 | 10.03 | 15.16 | 15.61 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 24741.10 | 4.04 | 3.90 | 5.57 | 6.03 | 0 |
| starlette | asgi | 2 | ok | 11819.24 | 8.45 | 6.85 | 13.99 | 14.39 | 0 |
| orionis-asgi | asgi | 2 | ok | 24838.39 | 4.02 | 3.94 | 6.04 | 6.72 | 0 |
| litestar | asgi | 3 | ok | 9528.70 | 10.48 | 9.99 | 13.09 | 13.89 | 0 |
| orionis-asgi | asgi | 3 | ok | 30863.00 | 3.24 | 3.11 | 5.19 | 6.58 | 0 |
| fastapi | asgi | 3 | ok | 8378.26 | 11.92 | 12.22 | 14.50 | 15.54 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 30882.86 | 3.23 | 3.10 | 5.18 | 6.45 | 0 |
| starlette | asgi | 3 | ok | 11149.72 | 8.96 | 9.36 | 10.71 | 12.49 | 0 |
| orionis-asgi | asgi | 4 | ok | 28539.42 | 3.50 | 3.32 | 5.94 | 7.56 | 0 |
| fastapi | asgi | 4 | ok | 8932.54 | 11.18 | 11.57 | 17.76 | 20.19 | 0 |
| litestar | asgi | 4 | ok | 9997.99 | 9.99 | 10.60 | 15.93 | 21.27 | 0 |
| starlette | asgi | 4 | ok | 11959.08 | 8.35 | 8.40 | 12.96 | 17.63 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 29891.66 | 3.34 | 3.17 | 5.66 | 7.19 | 0 |

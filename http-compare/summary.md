# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 4173.81 | 23.92 | 23.31 | 29.15 | 29.50 | 0 |
| orionis-asgi | asgi | 1 | ok | 14042.17 | 7.11 | 5.92 | 11.39 | 11.74 | 0 |
| fastapi | asgi | 1 | ok | 3706.02 | 26.94 | 26.16 | 32.07 | 32.56 | 0 |
| starlette | asgi | 1 | ok | 4858.59 | 20.56 | 19.87 | 25.73 | 26.01 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 10496.21 | 9.51 | 9.49 | 11.72 | 11.92 | 0 |
| litestar | asgi | 2 | ok | 7279.61 | 13.71 | 11.90 | 17.44 | 17.76 | 0 |
| fastapi | asgi | 2 | ok | 6538.55 | 15.27 | 13.71 | 18.95 | 19.44 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 18823.14 | 5.31 | 5.17 | 6.84 | 7.56 | 0 |
| starlette | asgi | 2 | ok | 8400.96 | 11.89 | 10.20 | 15.39 | 16.55 | 0 |
| orionis-asgi | asgi | 2 | ok | 19673.81 | 5.08 | 5.05 | 6.56 | 7.37 | 0 |
| litestar | asgi | 3 | ok | 8054.15 | 12.40 | 12.26 | 13.85 | 14.81 | 0 |
| orionis-asgi | asgi | 3 | ok | 24806.65 | 4.03 | 3.89 | 6.13 | 7.52 | 0 |
| fastapi | asgi | 3 | ok | 7087.43 | 14.09 | 14.90 | 16.35 | 17.47 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 25327.72 | 3.94 | 3.82 | 5.98 | 7.18 | 0 |
| starlette | asgi | 3 | ok | 9121.03 | 10.95 | 11.06 | 12.39 | 13.24 | 0 |
| orionis-asgi | asgi | 4 | ok | 24400.63 | 4.09 | 3.92 | 6.63 | 8.28 | 0 |
| fastapi | asgi | 4 | ok | 7998.95 | 12.48 | 12.09 | 20.84 | 23.26 | 0 |
| litestar | asgi | 4 | ok | 9106.86 | 10.96 | 10.44 | 18.06 | 20.30 | 0 |
| starlette | asgi | 4 | ok | 10355.34 | 9.64 | 9.21 | 15.22 | 19.43 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 24882.65 | 4.01 | 3.84 | 6.65 | 8.37 | 0 |

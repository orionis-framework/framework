# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 8220.22 | 12.16 | 11.92 | 12.75 | 12.99 | 0 |
| orionis-asgi | asgi | 1 | ok | 28274.98 | 3.53 | 3.43 | 4.29 | 4.63 | 0 |
| fastapi | asgi | 1 | ok | 7291.88 | 13.70 | 13.48 | 14.36 | 14.45 | 0 |
| starlette | asgi | 1 | ok | 9818.41 | 10.18 | 10.02 | 10.64 | 10.71 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 24144.06 | 4.14 | 4.35 | 4.77 | 4.90 | 0 |
| litestar | asgi | 2 | ok | 15558.31 | 6.42 | 6.27 | 7.13 | 8.02 | 0 |
| fastapi | asgi | 2 | ok | 13837.23 | 7.22 | 7.16 | 8.47 | 8.91 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 39299.16 | 2.54 | 2.50 | 3.40 | 3.84 | 0 |
| starlette | asgi | 2 | ok | 18589.37 | 5.38 | 5.14 | 5.99 | 6.49 | 0 |
| orionis-asgi | asgi | 2 | ok | 40735.61 | 2.45 | 2.41 | 3.15 | 3.60 | 0 |
| litestar | asgi | 3 | ok | 17431.49 | 5.73 | 5.79 | 7.48 | 8.73 | 0 |
| orionis-asgi | asgi | 3 | ok | 50521.96 | 1.98 | 1.88 | 2.97 | 3.68 | 0 |
| fastapi | asgi | 3 | ok | 15272.88 | 6.54 | 6.90 | 8.09 | 8.88 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 51933.63 | 1.92 | 1.84 | 3.06 | 3.92 | 0 |
| starlette | asgi | 3 | ok | 20486.61 | 4.88 | 5.06 | 5.87 | 7.15 | 0 |
| orionis-asgi | asgi | 4 | ok | 47038.06 | 2.12 | 2.00 | 3.68 | 4.83 | 0 |
| fastapi | asgi | 4 | ok | 15950.27 | 6.26 | 7.07 | 9.66 | 10.59 | 0 |
| litestar | asgi | 4 | ok | 18066.13 | 5.53 | 6.25 | 8.67 | 10.08 | 0 |
| starlette | asgi | 4 | ok | 21444.17 | 4.66 | 5.08 | 7.73 | 8.53 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 49121.50 | 2.03 | 1.89 | 3.72 | 4.94 | 0 |

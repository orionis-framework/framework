# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 10613.13 | 9.41 | 7.87 | 13.82 | 14.11 | 0 |
| orionis-asgi | asgi | 1 | ok | 12739.30 | 7.84 | 6.34 | 11.61 | 12.01 | 0 |
| fastapi | asgi | 1 | ok | 7378.56 | 13.53 | 13.80 | 17.54 | 17.87 | 0 |
| starlette | asgi | 1 | ok | 18411.44 | 5.43 | 4.22 | 9.45 | 9.81 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 10922.01 | 9.14 | 8.75 | 11.93 | 12.22 | 0 |
| litestar | asgi | 2 | ok | 15826.23 | 6.31 | 6.28 | 8.01 | 8.91 | 0 |
| fastapi | asgi | 2 | ok | 11557.13 | 8.64 | 8.59 | 10.67 | 11.40 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 17985.22 | 5.55 | 5.41 | 6.77 | 7.54 | 0 |
| starlette | asgi | 2 | ok | 26171.93 | 3.82 | 3.71 | 5.63 | 6.75 | 0 |
| orionis-asgi | asgi | 2 | ok | 19166.41 | 5.21 | 5.17 | 7.00 | 7.85 | 0 |
| litestar | asgi | 3 | ok | 21027.53 | 4.75 | 4.55 | 6.98 | 8.38 | 0 |
| orionis-asgi | asgi | 3 | ok | 24308.54 | 4.11 | 3.98 | 6.14 | 7.32 | 0 |
| fastapi | asgi | 3 | ok | 16135.90 | 6.19 | 5.96 | 8.97 | 9.73 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 24533.74 | 4.07 | 3.92 | 5.99 | 7.24 | 0 |
| starlette | asgi | 3 | ok | 29923.72 | 3.34 | 3.25 | 5.15 | 6.25 | 0 |
| orionis-asgi | asgi | 4 | ok | 23944.82 | 4.17 | 3.98 | 6.82 | 8.59 | 0 |
| fastapi | asgi | 4 | ok | 16361.04 | 6.10 | 5.78 | 10.00 | 12.32 | 0 |
| litestar | asgi | 4 | ok | 20991.21 | 4.76 | 4.56 | 7.80 | 9.66 | 0 |
| starlette | asgi | 4 | ok | 29420.92 | 3.39 | 3.28 | 5.49 | 6.76 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 24291.77 | 4.11 | 3.91 | 6.85 | 8.58 | 0 |

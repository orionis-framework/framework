# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 8191.68 | 12.20 | 12.40 | 12.67 | 13.08 | 0 |
| orionis-asgi | asgi | 1 | ok | 28081.84 | 3.56 | 3.45 | 4.34 | 4.70 | 0 |
| fastapi | asgi | 1 | ok | 7280.05 | 13.73 | 13.51 | 14.46 | 14.52 | 0 |
| starlette | asgi | 1 | ok | 9714.58 | 10.29 | 10.16 | 10.81 | 10.87 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 23876.89 | 4.19 | 4.39 | 4.77 | 4.91 | 0 |
| litestar | asgi | 2 | ok | 15765.19 | 6.34 | 5.62 | 8.22 | 8.30 | 0 |
| fastapi | asgi | 2 | ok | 13910.36 | 7.18 | 6.89 | 7.78 | 7.97 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 39304.03 | 2.54 | 2.50 | 3.41 | 3.75 | 0 |
| starlette | asgi | 2 | ok | 18712.75 | 5.34 | 5.13 | 5.93 | 7.08 | 0 |
| orionis-asgi | asgi | 2 | ok | 40390.26 | 2.47 | 2.43 | 3.15 | 3.60 | 0 |
| litestar | asgi | 3 | ok | 17471.16 | 5.72 | 5.94 | 6.94 | 8.27 | 0 |
| orionis-asgi | asgi | 3 | ok | 50377.99 | 1.98 | 1.93 | 3.00 | 3.70 | 0 |
| fastapi | asgi | 3 | ok | 15389.58 | 6.49 | 6.62 | 8.12 | 8.52 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 52083.71 | 1.92 | 1.81 | 2.94 | 3.70 | 0 |
| starlette | asgi | 3 | ok | 20632.39 | 4.84 | 4.90 | 5.91 | 7.20 | 0 |
| orionis-asgi | asgi | 4 | ok | 47004.26 | 2.13 | 2.01 | 3.70 | 4.81 | 0 |
| fastapi | asgi | 4 | ok | 16016.23 | 6.24 | 6.62 | 9.35 | 10.68 | 0 |
| litestar | asgi | 4 | ok | 17456.38 | 5.72 | 6.31 | 6.76 | 8.58 | 0 |
| starlette | asgi | 4 | ok | 21780.99 | 4.59 | 5.01 | 7.12 | 8.47 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 48602.61 | 2.06 | 1.93 | 3.68 | 4.86 | 0 |

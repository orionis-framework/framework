# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 10102.48 | 9.89 | 9.51 | 11.27 | 11.79 | 0 |
| orionis-asgi | asgi | 1 | ok | 27297.23 | 3.66 | 3.94 | 4.43 | 4.69 | 0 |
| fastapi | asgi | 1 | ok | 9060.49 | 11.03 | 10.84 | 12.60 | 12.97 | 0 |
| starlette | asgi | 1 | ok | 12257.38 | 8.15 | 7.90 | 9.40 | 9.84 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 26380.79 | 3.79 | 3.87 | 4.25 | 4.42 | 0 |
| litestar | asgi | 2 | ok | 18575.09 | 5.38 | 4.95 | 6.38 | 6.68 | 0 |
| fastapi | asgi | 2 | ok | 16111.37 | 6.20 | 5.81 | 7.50 | 7.81 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 43610.33 | 2.29 | 2.32 | 3.05 | 3.52 | 0 |
| starlette | asgi | 2 | ok | 21067.16 | 4.74 | 4.35 | 5.73 | 5.92 | 0 |
| orionis-asgi | asgi | 2 | ok | 42466.33 | 2.35 | 2.36 | 3.07 | 3.74 | 0 |
| litestar | asgi | 3 | ok | 17572.47 | 5.69 | 5.46 | 7.75 | 8.89 | 0 |
| orionis-asgi | asgi | 3 | ok | 47825.40 | 2.09 | 1.99 | 3.37 | 4.24 | 0 |
| fastapi | asgi | 3 | ok | 15799.40 | 6.32 | 5.57 | 9.10 | 10.26 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 52067.31 | 1.92 | 1.81 | 3.16 | 4.16 | 0 |
| starlette | asgi | 3 | ok | 22734.98 | 4.39 | 4.48 | 5.52 | 6.82 | 0 |
| orionis-asgi | asgi | 4 | ok | 48871.17 | 2.04 | 1.92 | 3.58 | 4.70 | 0 |
| fastapi | asgi | 4 | ok | 18200.75 | 5.49 | 5.96 | 8.35 | 10.68 | 0 |
| litestar | asgi | 4 | ok | 21188.65 | 4.72 | 4.79 | 7.27 | 8.53 | 0 |
| starlette | asgi | 4 | ok | 25756.77 | 3.88 | 4.05 | 5.94 | 6.90 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 52738.19 | 1.89 | 1.77 | 3.38 | 4.48 | 0 |

# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 8257.03 | 12.10 | 11.86 | 12.66 | 12.78 | 0 |
| orionis-asgi | asgi | 1 | ok | 28343.87 | 3.53 | 3.41 | 4.29 | 4.64 | 0 |
| fastapi | asgi | 1 | ok | 7292.57 | 13.70 | 13.49 | 14.34 | 14.42 | 0 |
| starlette | asgi | 1 | ok | 9822.51 | 10.17 | 9.99 | 10.62 | 10.69 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 24558.71 | 4.07 | 4.31 | 4.72 | 4.85 | 0 |
| litestar | asgi | 2 | ok | 15767.24 | 6.34 | 6.23 | 8.11 | 8.45 | 0 |
| fastapi | asgi | 2 | ok | 13797.81 | 7.24 | 7.12 | 7.94 | 8.40 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 39321.14 | 2.54 | 2.50 | 3.44 | 3.82 | 0 |
| starlette | asgi | 2 | ok | 18510.82 | 5.40 | 5.25 | 6.01 | 6.21 | 0 |
| orionis-asgi | asgi | 2 | ok | 40082.22 | 2.49 | 2.43 | 3.36 | 3.80 | 0 |
| litestar | asgi | 3 | ok | 17412.64 | 5.74 | 5.98 | 7.15 | 8.05 | 0 |
| orionis-asgi | asgi | 3 | ok | 51052.56 | 1.96 | 1.91 | 2.92 | 3.62 | 0 |
| fastapi | asgi | 3 | ok | 15239.66 | 6.56 | 6.85 | 7.85 | 9.19 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 52398.59 | 1.91 | 1.81 | 2.90 | 3.58 | 0 |
| starlette | asgi | 3 | ok | 20766.51 | 4.81 | 5.13 | 5.88 | 6.99 | 0 |
| orionis-asgi | asgi | 4 | ok | 47850.06 | 2.09 | 1.98 | 3.62 | 4.65 | 0 |
| fastapi | asgi | 4 | ok | 15833.15 | 6.31 | 6.87 | 10.10 | 11.80 | 0 |
| litestar | asgi | 4 | ok | 17965.21 | 5.56 | 6.06 | 8.08 | 9.33 | 0 |
| starlette | asgi | 4 | ok | 21741.32 | 4.60 | 4.82 | 7.08 | 8.05 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 49075.77 | 2.04 | 1.92 | 3.55 | 4.72 | 0 |

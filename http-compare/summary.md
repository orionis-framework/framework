# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 9346.11 | 10.69 | 10.28 | 12.31 | 12.68 | 0 |
| orionis-asgi | asgi | 1 | ok | 28655.90 | 3.49 | 3.74 | 4.28 | 4.62 | 0 |
| fastapi | asgi | 1 | ok | 8145.67 | 12.27 | 11.92 | 13.95 | 14.59 | 0 |
| starlette | asgi | 1 | ok | 11081.99 | 9.02 | 8.82 | 10.33 | 10.91 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 27844.17 | 3.59 | 3.74 | 4.13 | 4.29 | 0 |
| litestar | asgi | 2 | ok | 17155.89 | 5.82 | 5.59 | 7.44 | 7.80 | 0 |
| fastapi | asgi | 2 | ok | 14866.67 | 6.72 | 6.16 | 7.94 | 8.26 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 47913.86 | 2.09 | 2.09 | 2.85 | 3.44 | 0 |
| starlette | asgi | 2 | ok | 20062.09 | 4.98 | 4.78 | 6.36 | 6.57 | 0 |
| orionis-asgi | asgi | 2 | ok | 44764.87 | 2.23 | 2.24 | 3.14 | 3.55 | 0 |
| litestar | asgi | 3 | ok | 18186.88 | 5.49 | 6.07 | 7.87 | 8.81 | 0 |
| orionis-asgi | asgi | 3 | ok | 55071.06 | 1.81 | 1.74 | 2.94 | 3.71 | 0 |
| fastapi | asgi | 3 | ok | 15222.97 | 6.56 | 6.42 | 8.86 | 10.31 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 56544.72 | 1.77 | 1.69 | 2.85 | 3.67 | 0 |
| starlette | asgi | 3 | ok | 21481.67 | 4.65 | 4.85 | 6.51 | 7.33 | 0 |
| orionis-asgi | asgi | 4 | ok | 52935.23 | 1.89 | 1.78 | 3.25 | 4.26 | 0 |
| fastapi | asgi | 4 | ok | 17177.13 | 5.82 | 5.86 | 9.93 | 11.08 | 0 |
| litestar | asgi | 4 | ok | 19789.61 | 5.05 | 4.97 | 8.13 | 9.24 | 0 |
| starlette | asgi | 4 | ok | 23718.27 | 4.21 | 3.97 | 6.82 | 8.00 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 53858.05 | 1.85 | 1.75 | 3.27 | 4.26 | 0 |

# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 5424.91 | 18.41 | 17.85 | 21.55 | 21.77 | 0 |
| orionis-asgi | asgi | 1 | ok | 16357.88 | 6.11 | 5.58 | 8.34 | 8.70 | 0 |
| fastapi | asgi | 1 | ok | 4829.15 | 20.69 | 20.02 | 24.02 | 24.26 | 0 |
| starlette | asgi | 1 | ok | 6219.49 | 16.06 | 15.25 | 18.95 | 19.17 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 14306.31 | 6.98 | 7.28 | 8.04 | 8.38 | 0 |
| litestar | asgi | 2 | ok | 2422.82 | 41.18 | 41.01 | 42.04 | 43.01 | 0 |
| fastapi | asgi | 2 | ok | 2419.91 | 41.24 | 41.01 | 42.06 | 43.03 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 24393.23 | 4.10 | 4.22 | 4.90 | 5.33 | 0 |
| starlette | asgi | 2 | ok | 2427.33 | 41.11 | 41.00 | 42.04 | 43.02 | 0 |
| orionis-asgi | asgi | 2 | ok | 25010.18 | 3.99 | 3.98 | 5.11 | 5.60 | 0 |
| litestar | asgi | 3 | ok | 2424.43 | 41.14 | 41.01 | 42.05 | 43.02 | 0 |
| orionis-asgi | asgi | 3 | ok | 34777.64 | 2.87 | 2.79 | 4.33 | 5.22 | 0 |
| fastapi | asgi | 3 | ok | 2422.52 | 41.18 | 41.01 | 42.05 | 43.02 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 35915.99 | 2.78 | 2.70 | 4.19 | 5.05 | 0 |
| starlette | asgi | 3 | ok | 2427.40 | 41.11 | 41.01 | 42.04 | 42.99 | 0 |
| orionis-asgi | asgi | 4 | ok | 33612.58 | 2.97 | 2.81 | 4.97 | 6.28 | 0 |
| fastapi | asgi | 4 | ok | 2422.84 | 41.18 | 41.01 | 42.04 | 43.02 | 0 |
| litestar | asgi | 4 | ok | 2425.07 | 41.15 | 41.01 | 42.04 | 42.99 | 0 |
| starlette | asgi | 4 | ok | 2427.61 | 41.10 | 41.01 | 42.03 | 42.95 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 34891.55 | 2.86 | 2.69 | 4.89 | 6.25 | 0 |

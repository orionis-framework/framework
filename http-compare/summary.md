# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 7307.89 | 13.67 | 12.93 | 17.08 | 17.25 | 0 |
| orionis-asgi | asgi | 1 | ok | 25832.92 | 3.87 | 3.21 | 7.06 | 7.31 | 0 |
| fastapi | asgi | 1 | ok | 6325.54 | 15.79 | 15.10 | 19.26 | 19.40 | 0 |
| starlette | asgi | 1 | ok | 9106.86 | 10.97 | 10.36 | 14.25 | 14.37 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 19296.64 | 5.18 | 5.35 | 6.56 | 6.72 | 0 |
| litestar | asgi | 2 | ok | 2430.17 | 41.05 | 41.00 | 42.02 | 42.96 | 0 |
| fastapi | asgi | 2 | ok | 2428.61 | 41.08 | 41.00 | 42.02 | 43.01 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 31122.00 | 3.21 | 3.23 | 4.34 | 4.79 | 0 |
| starlette | asgi | 2 | ok | 2432.48 | 41.01 | 41.00 | 42.00 | 42.92 | 0 |
| orionis-asgi | asgi | 2 | ok | 32786.17 | 3.05 | 3.00 | 4.31 | 4.79 | 0 |
| litestar | asgi | 3 | ok | 2432.31 | 41.02 | 41.00 | 42.01 | 42.85 | 0 |
| orionis-asgi | asgi | 3 | ok | 39620.38 | 2.52 | 2.42 | 4.02 | 4.98 | 0 |
| fastapi | asgi | 3 | ok | 2430.90 | 41.04 | 41.00 | 42.01 | 42.91 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 40058.19 | 2.49 | 2.36 | 4.09 | 5.15 | 0 |
| starlette | asgi | 3 | ok | 2433.29 | 41.00 | 41.00 | 42.01 | 42.90 | 0 |
| orionis-asgi | asgi | 4 | ok | 38380.09 | 2.60 | 2.48 | 4.35 | 5.54 | 0 |
| fastapi | asgi | 4 | ok | 2429.59 | 41.06 | 41.00 | 42.02 | 42.95 | 0 |
| litestar | asgi | 4 | ok | 2431.32 | 41.03 | 41.00 | 42.01 | 42.91 | 0 |
| starlette | asgi | 4 | ok | 2434.46 | 40.98 | 41.00 | 42.00 | 42.15 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 39104.49 | 2.55 | 2.43 | 4.37 | 5.66 | 0 |

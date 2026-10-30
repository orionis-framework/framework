# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 27123.17 | 3.68 | 3.94 | 4.72 | 5.39 | 0 |
| orionis-asgi | asgi | 1 | ok | 30074.89 | 3.32 | 3.57 | 4.15 | 4.69 | 0 |
| fastapi | asgi | 1 | ok | 18780.20 | 5.32 | 5.61 | 6.64 | 7.07 | 0 |
| starlette | asgi | 1 | ok | 45455.09 | 2.20 | 2.31 | 2.87 | 3.32 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 29376.33 | 3.40 | 3.44 | 3.93 | 4.81 | 0 |
| litestar | asgi | 2 | ok | 42581.29 | 2.35 | 2.37 | 3.14 | 3.85 | 0 |
| fastapi | asgi | 2 | ok | 29157.40 | 3.43 | 3.45 | 4.65 | 5.13 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 49266.20 | 2.03 | 1.96 | 2.81 | 3.55 | 0 |
| starlette | asgi | 2 | ok | 64951.47 | 1.54 | 1.45 | 2.42 | 2.93 | 0 |
| orionis-asgi | asgi | 2 | ok | 50204.83 | 1.99 | 1.96 | 2.83 | 3.54 | 0 |
| litestar | asgi | 3 | ok | 51126.41 | 1.95 | 1.86 | 3.25 | 4.15 | 0 |
| orionis-asgi | asgi | 3 | ok | 54357.31 | 1.84 | 1.74 | 3.07 | 3.93 | 0 |
| fastapi | asgi | 3 | ok | 40046.80 | 2.49 | 2.32 | 4.10 | 5.00 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 52971.40 | 1.89 | 1.77 | 3.24 | 4.21 | 0 |
| starlette | asgi | 3 | ok | 64412.10 | 1.55 | 1.47 | 2.64 | 3.46 | 0 |
| orionis-asgi | asgi | 4 | ok | 51046.15 | 1.96 | 1.84 | 3.42 | 4.45 | 0 |
| fastapi | asgi | 4 | ok | 35337.73 | 2.83 | 2.62 | 5.08 | 6.66 | 0 |
| litestar | asgi | 4 | ok | 48241.94 | 2.07 | 1.95 | 3.64 | 4.74 | 0 |
| starlette | asgi | 4 | ok | 64833.45 | 1.54 | 1.47 | 2.69 | 3.52 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 56009.49 | 1.78 | 1.68 | 3.13 | 4.12 | 0 |

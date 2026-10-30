# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 26721.83 | 3.74 | 3.92 | 4.64 | 5.05 | 0 |
| orionis-asgi | asgi | 1 | ok | 29573.69 | 3.38 | 3.57 | 4.17 | 4.85 | 0 |
| fastapi | asgi | 1 | ok | 19002.83 | 5.26 | 5.57 | 6.45 | 6.85 | 0 |
| starlette | asgi | 1 | ok | 46119.81 | 2.17 | 2.22 | 2.79 | 3.49 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 29237.37 | 3.42 | 3.51 | 3.92 | 4.08 | 0 |
| litestar | asgi | 2 | ok | 41212.50 | 2.42 | 2.46 | 3.21 | 3.78 | 0 |
| fastapi | asgi | 2 | ok | 28228.12 | 3.54 | 3.59 | 4.46 | 4.96 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 47871.98 | 2.09 | 2.05 | 2.85 | 3.60 | 0 |
| starlette | asgi | 2 | ok | 63008.87 | 1.59 | 1.50 | 2.52 | 3.14 | 0 |
| orionis-asgi | asgi | 2 | ok | 47728.09 | 2.09 | 2.06 | 3.05 | 3.78 | 0 |
| litestar | asgi | 3 | ok | 48690.38 | 2.05 | 1.93 | 3.45 | 4.44 | 0 |
| orionis-asgi | asgi | 3 | ok | 53030.50 | 1.88 | 1.78 | 3.17 | 4.02 | 0 |
| fastapi | asgi | 3 | ok | 38806.42 | 2.57 | 2.42 | 4.20 | 5.43 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 54933.77 | 1.82 | 1.72 | 3.06 | 4.03 | 0 |
| starlette | asgi | 3 | ok | 64829.67 | 1.54 | 1.46 | 2.61 | 3.35 | 0 |
| orionis-asgi | asgi | 4 | ok | 52669.51 | 1.90 | 1.78 | 3.33 | 4.33 | 0 |
| fastapi | asgi | 4 | ok | 37050.61 | 2.70 | 2.50 | 4.79 | 6.30 | 0 |
| litestar | asgi | 4 | ok | 47263.41 | 2.11 | 1.99 | 3.71 | 4.82 | 0 |
| starlette | asgi | 4 | ok | 60787.11 | 1.64 | 1.54 | 2.90 | 3.83 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 53674.00 | 1.86 | 1.75 | 3.31 | 4.36 | 0 |

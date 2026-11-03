# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 5646.26 | 17.69 | 16.79 | 21.95 | 22.27 | 0 |
| orionis-asgi | asgi | 1 | ok | 18750.54 | 5.33 | 4.38 | 9.18 | 9.50 | 0 |
| fastapi | asgi | 1 | ok | 4800.25 | 20.81 | 19.83 | 25.13 | 25.28 | 0 |
| starlette | asgi | 1 | ok | 6958.45 | 14.36 | 13.45 | 18.55 | 18.76 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 16394.96 | 6.09 | 5.77 | 8.44 | 8.61 | 0 |
| litestar | asgi | 2 | ok | 9766.06 | 10.23 | 8.56 | 13.64 | 13.88 | 0 |
| fastapi | asgi | 2 | ok | 8437.85 | 11.83 | 10.48 | 14.92 | 15.25 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 23608.11 | 4.23 | 4.16 | 5.65 | 6.12 | 0 |
| starlette | asgi | 2 | ok | 11922.63 | 8.38 | 6.93 | 11.61 | 12.14 | 0 |
| orionis-asgi | asgi | 2 | ok | 25324.09 | 3.94 | 3.87 | 5.52 | 6.09 | 0 |
| litestar | asgi | 3 | ok | 9515.41 | 10.50 | 11.16 | 12.38 | 13.51 | 0 |
| orionis-asgi | asgi | 3 | ok | 31574.36 | 3.16 | 3.03 | 5.02 | 6.18 | 0 |
| fastapi | asgi | 3 | ok | 8470.28 | 11.79 | 11.92 | 14.22 | 14.69 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 30759.66 | 3.25 | 3.08 | 5.32 | 6.68 | 0 |
| starlette | asgi | 3 | ok | 11033.54 | 9.05 | 9.78 | 10.55 | 12.36 | 0 |
| orionis-asgi | asgi | 4 | ok | 29740.02 | 3.36 | 3.20 | 5.63 | 7.17 | 0 |
| fastapi | asgi | 4 | ok | 8985.69 | 11.11 | 11.16 | 15.75 | 21.19 | 0 |
| litestar | asgi | 4 | ok | 10117.72 | 9.87 | 9.56 | 17.77 | 25.11 | 0 |
| starlette | asgi | 4 | ok | 12056.09 | 8.29 | 8.61 | 12.83 | 14.90 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 30483.52 | 3.28 | 3.11 | 5.55 | 7.05 | 0 |

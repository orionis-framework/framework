# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 8243.73 | 12.12 | 11.82 | 12.64 | 13.50 | 0 |
| orionis-asgi | asgi | 1 | ok | 27676.02 | 3.61 | 3.53 | 4.38 | 4.74 | 0 |
| fastapi | asgi | 1 | ok | 7302.23 | 13.68 | 13.49 | 14.40 | 14.47 | 0 |
| starlette | asgi | 1 | ok | 9779.23 | 10.22 | 10.05 | 10.69 | 10.76 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 23834.71 | 4.19 | 4.40 | 4.82 | 4.98 | 0 |
| litestar | asgi | 2 | ok | 15642.93 | 6.39 | 6.16 | 7.09 | 7.22 | 0 |
| fastapi | asgi | 2 | ok | 13762.15 | 7.26 | 7.05 | 7.99 | 9.03 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 39137.02 | 2.55 | 2.51 | 3.33 | 3.75 | 0 |
| starlette | asgi | 2 | ok | 18551.32 | 5.39 | 5.16 | 6.00 | 7.33 | 0 |
| orionis-asgi | asgi | 2 | ok | 40627.64 | 2.46 | 2.45 | 3.09 | 3.52 | 0 |
| litestar | asgi | 3 | ok | 17373.79 | 5.75 | 5.81 | 6.99 | 8.27 | 0 |
| orionis-asgi | asgi | 3 | ok | 50555.50 | 1.98 | 1.91 | 2.99 | 3.72 | 0 |
| fastapi | asgi | 3 | ok | 15438.58 | 6.47 | 7.00 | 7.74 | 8.76 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 51690.17 | 1.93 | 1.82 | 2.96 | 3.72 | 0 |
| starlette | asgi | 3 | ok | 20573.45 | 4.86 | 5.22 | 5.85 | 7.39 | 0 |
| orionis-asgi | asgi | 4 | ok | 47087.24 | 2.12 | 2.01 | 3.70 | 4.85 | 0 |
| fastapi | asgi | 4 | ok | 16084.47 | 6.21 | 6.36 | 9.41 | 10.80 | 0 |
| litestar | asgi | 4 | ok | 18104.40 | 5.52 | 6.08 | 9.11 | 10.06 | 0 |
| starlette | asgi | 4 | ok | 21591.54 | 4.63 | 4.89 | 6.93 | 7.77 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 48463.54 | 2.06 | 1.94 | 3.67 | 4.83 | 0 |

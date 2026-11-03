# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 5631.19 | 17.74 | 16.83 | 22.09 | 22.29 | 0 |
| orionis-asgi | asgi | 1 | ok | 18605.08 | 5.37 | 4.41 | 9.44 | 9.77 | 0 |
| fastapi | asgi | 1 | ok | 4893.93 | 20.41 | 19.36 | 24.97 | 25.09 | 0 |
| starlette | asgi | 1 | ok | 7064.81 | 14.14 | 13.33 | 18.47 | 18.63 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 15296.71 | 6.53 | 6.49 | 8.65 | 8.81 | 0 |
| litestar | asgi | 2 | ok | 9791.05 | 10.20 | 8.54 | 13.41 | 13.66 | 0 |
| fastapi | asgi | 2 | ok | 8522.68 | 11.72 | 10.86 | 15.56 | 16.35 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 23634.71 | 4.23 | 4.00 | 6.40 | 6.82 | 0 |
| starlette | asgi | 2 | ok | 11830.50 | 8.44 | 6.95 | 11.74 | 12.17 | 0 |
| orionis-asgi | asgi | 2 | ok | 24075.87 | 4.15 | 4.11 | 5.97 | 6.51 | 0 |
| litestar | asgi | 3 | ok | 9563.41 | 10.44 | 11.03 | 12.58 | 13.96 | 0 |
| orionis-asgi | asgi | 3 | ok | 30989.00 | 3.22 | 3.09 | 5.23 | 6.57 | 0 |
| fastapi | asgi | 3 | ok | 8537.33 | 11.69 | 12.05 | 14.41 | 16.11 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 31892.38 | 3.13 | 3.00 | 5.02 | 6.20 | 0 |
| starlette | asgi | 3 | ok | 11216.50 | 8.90 | 9.32 | 10.49 | 11.73 | 0 |
| orionis-asgi | asgi | 4 | ok | 29666.54 | 3.37 | 3.20 | 5.62 | 7.12 | 0 |
| fastapi | asgi | 4 | ok | 9059.95 | 11.02 | 9.49 | 20.41 | 26.20 | 0 |
| litestar | asgi | 4 | ok | 10190.59 | 9.80 | 9.08 | 18.04 | 19.55 | 0 |
| starlette | asgi | 4 | ok | 12083.95 | 8.27 | 8.52 | 13.69 | 15.46 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 30358.47 | 3.29 | 3.12 | 5.58 | 7.22 | 0 |

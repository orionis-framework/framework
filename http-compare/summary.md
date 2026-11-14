# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 4106.27 | 24.32 | 23.53 | 29.54 | 31.29 | 0 |
| orionis-asgi | asgi | 1 | ok | 11320.32 | 8.82 | 7.40 | 13.31 | 13.63 | 0 |
| fastapi | asgi | 1 | ok | 3717.34 | 26.86 | 26.17 | 32.24 | 32.79 | 0 |
| starlette | asgi | 1 | ok | 4815.36 | 20.73 | 20.18 | 25.74 | 26.10 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 9353.59 | 10.68 | 10.72 | 13.74 | 13.98 | 0 |
| litestar | asgi | 2 | ok | 7156.82 | 13.95 | 12.19 | 17.68 | 18.18 | 0 |
| fastapi | asgi | 2 | ok | 6447.29 | 15.49 | 13.78 | 19.29 | 19.74 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 15743.33 | 6.34 | 6.26 | 7.92 | 8.62 | 0 |
| starlette | asgi | 2 | ok | 8160.93 | 12.24 | 11.94 | 18.30 | 18.70 | 0 |
| orionis-asgi | asgi | 2 | ok | 16679.10 | 5.99 | 6.00 | 7.58 | 8.39 | 0 |
| litestar | asgi | 3 | ok | 7917.32 | 12.61 | 12.86 | 13.86 | 15.02 | 0 |
| orionis-asgi | asgi | 3 | ok | 21870.40 | 4.57 | 4.43 | 6.83 | 8.42 | 0 |
| fastapi | asgi | 3 | ok | 7050.30 | 14.16 | 13.87 | 16.04 | 18.04 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 22414.19 | 4.46 | 4.25 | 6.70 | 8.14 | 0 |
| starlette | asgi | 3 | ok | 9031.35 | 11.06 | 11.20 | 12.17 | 14.53 | 0 |
| orionis-asgi | asgi | 4 | ok | 21972.46 | 4.55 | 4.36 | 7.46 | 9.27 | 0 |
| fastapi | asgi | 4 | ok | 7969.49 | 12.53 | 12.48 | 21.39 | 23.13 | 0 |
| litestar | asgi | 4 | ok | 9035.78 | 11.05 | 12.65 | 19.47 | 24.81 | 0 |
| starlette | asgi | 4 | ok | 10298.80 | 9.70 | 9.94 | 14.48 | 17.52 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 22447.64 | 4.45 | 4.24 | 7.37 | 9.33 | 0 |

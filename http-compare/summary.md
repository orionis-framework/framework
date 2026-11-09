# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 3841.40 | 25.99 | 25.04 | 31.11 | 31.70 | 0 |
| orionis-asgi | asgi | 1 | ok | 12243.67 | 8.16 | 6.64 | 11.76 | 12.17 | 0 |
| fastapi | asgi | 1 | ok | 3559.03 | 28.05 | 27.71 | 32.02 | 34.09 | 0 |
| starlette | asgi | 1 | ok | 4763.50 | 20.96 | 20.10 | 26.02 | 26.51 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 10352.02 | 9.65 | 9.82 | 11.99 | 12.28 | 0 |
| litestar | asgi | 2 | ok | 7091.00 | 14.08 | 12.56 | 17.43 | 17.87 | 0 |
| fastapi | asgi | 2 | ok | 6241.38 | 15.99 | 17.19 | 24.36 | 24.92 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 18301.06 | 5.46 | 5.52 | 6.75 | 7.50 | 0 |
| starlette | asgi | 2 | ok | 8061.90 | 12.39 | 10.67 | 16.20 | 16.73 | 0 |
| orionis-asgi | asgi | 2 | ok | 19221.86 | 5.20 | 5.17 | 6.86 | 7.69 | 0 |
| litestar | asgi | 3 | ok | 7852.07 | 12.72 | 12.96 | 14.68 | 15.51 | 0 |
| orionis-asgi | asgi | 3 | ok | 24189.75 | 4.13 | 4.02 | 6.23 | 7.48 | 0 |
| fastapi | asgi | 3 | ok | 6781.01 | 14.73 | 14.92 | 17.50 | 18.73 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 24499.36 | 4.08 | 3.94 | 6.14 | 7.53 | 0 |
| starlette | asgi | 3 | ok | 8976.53 | 11.13 | 11.11 | 12.29 | 13.25 | 0 |
| orionis-asgi | asgi | 4 | ok | 23329.68 | 4.28 | 4.10 | 6.95 | 8.61 | 0 |
| fastapi | asgi | 4 | ok | 8003.85 | 12.48 | 12.97 | 17.07 | 19.72 | 0 |
| litestar | asgi | 4 | ok | 9017.63 | 11.07 | 11.30 | 20.30 | 23.81 | 0 |
| starlette | asgi | 4 | ok | 10348.47 | 9.65 | 10.05 | 15.48 | 17.49 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 24799.19 | 4.03 | 3.86 | 6.61 | 8.26 | 0 |

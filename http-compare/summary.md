# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 4118.25 | 24.24 | 23.45 | 29.43 | 30.50 | 0 |
| orionis-asgi | asgi | 1 | ok | 13158.08 | 7.59 | 6.13 | 11.67 | 12.03 | 0 |
| fastapi | asgi | 1 | ok | 3756.51 | 26.58 | 26.16 | 30.65 | 32.60 | 0 |
| starlette | asgi | 1 | ok | 4802.55 | 20.80 | 20.05 | 25.88 | 26.06 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 10998.25 | 9.08 | 8.83 | 11.74 | 11.98 | 0 |
| litestar | asgi | 2 | ok | 7244.44 | 13.78 | 12.02 | 17.58 | 17.93 | 0 |
| fastapi | asgi | 2 | ok | 6505.66 | 15.35 | 13.54 | 19.07 | 19.45 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 18682.50 | 5.35 | 5.29 | 6.97 | 7.54 | 0 |
| starlette | asgi | 2 | ok | 8307.74 | 12.02 | 10.17 | 15.66 | 16.04 | 0 |
| orionis-asgi | asgi | 2 | ok | 19063.14 | 5.24 | 5.22 | 6.79 | 7.60 | 0 |
| litestar | asgi | 3 | ok | 7965.47 | 12.54 | 12.70 | 13.83 | 15.58 | 0 |
| orionis-asgi | asgi | 3 | ok | 24434.63 | 4.09 | 3.94 | 6.16 | 7.54 | 0 |
| fastapi | asgi | 3 | ok | 7053.58 | 14.16 | 14.25 | 15.96 | 16.95 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 25001.38 | 3.99 | 3.81 | 6.07 | 7.53 | 0 |
| starlette | asgi | 3 | ok | 9170.74 | 10.89 | 11.12 | 12.22 | 12.88 | 0 |
| orionis-asgi | asgi | 4 | ok | 24049.74 | 4.15 | 3.98 | 6.80 | 8.49 | 0 |
| fastapi | asgi | 4 | ok | 7990.50 | 12.49 | 12.89 | 19.80 | 21.81 | 0 |
| litestar | asgi | 4 | ok | 9018.13 | 11.07 | 10.71 | 16.04 | 18.72 | 0 |
| starlette | asgi | 4 | ok | 10371.86 | 9.63 | 9.80 | 14.80 | 17.49 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 24598.50 | 4.06 | 3.87 | 6.72 | 8.45 | 0 |

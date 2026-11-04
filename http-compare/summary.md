# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 4185.30 | 23.86 | 23.24 | 28.15 | 29.76 | 0 |
| orionis-asgi | asgi | 1 | ok | 13676.47 | 7.30 | 6.13 | 11.47 | 13.09 | 0 |
| fastapi | asgi | 1 | ok | 3715.25 | 26.87 | 26.38 | 31.00 | 32.81 | 0 |
| starlette | asgi | 1 | ok | 4857.04 | 20.56 | 19.90 | 25.61 | 26.08 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 10518.32 | 9.50 | 9.38 | 11.94 | 12.21 | 0 |
| litestar | asgi | 2 | ok | 7115.78 | 14.03 | 13.33 | 21.46 | 21.94 | 0 |
| fastapi | asgi | 2 | ok | 6270.58 | 15.93 | 15.03 | 20.13 | 22.86 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 18629.90 | 5.36 | 5.28 | 7.12 | 7.66 | 0 |
| starlette | asgi | 2 | ok | 8217.60 | 12.15 | 10.38 | 15.61 | 16.10 | 0 |
| orionis-asgi | asgi | 2 | ok | 18978.40 | 5.26 | 5.21 | 6.78 | 7.60 | 0 |
| litestar | asgi | 3 | ok | 7926.99 | 12.60 | 12.88 | 13.57 | 14.35 | 0 |
| orionis-asgi | asgi | 3 | ok | 24162.14 | 4.13 | 4.00 | 6.09 | 7.24 | 0 |
| fastapi | asgi | 3 | ok | 7011.03 | 14.24 | 14.16 | 16.30 | 18.12 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 24634.73 | 4.05 | 3.92 | 6.21 | 7.58 | 0 |
| starlette | asgi | 3 | ok | 9104.22 | 10.97 | 11.10 | 11.96 | 13.33 | 0 |
| orionis-asgi | asgi | 4 | ok | 23843.17 | 4.19 | 4.01 | 6.91 | 8.65 | 0 |
| fastapi | asgi | 4 | ok | 8029.20 | 12.44 | 12.31 | 19.79 | 20.61 | 0 |
| litestar | asgi | 4 | ok | 9036.78 | 11.05 | 10.18 | 17.79 | 20.74 | 0 |
| starlette | asgi | 4 | ok | 10298.67 | 9.70 | 9.62 | 15.70 | 19.01 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 24487.34 | 4.08 | 3.90 | 6.82 | 8.65 | 0 |

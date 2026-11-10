# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 7341.68 | 13.61 | 13.00 | 16.90 | 17.10 | 0 |
| orionis-asgi | asgi | 1 | ok | 22676.60 | 4.41 | 3.64 | 7.54 | 7.86 | 0 |
| fastapi | asgi | 1 | ok | 6193.04 | 16.13 | 15.04 | 19.23 | 19.38 | 0 |
| starlette | asgi | 1 | ok | 9316.19 | 10.73 | 10.20 | 14.16 | 14.33 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 18166.48 | 5.50 | 5.65 | 7.04 | 7.19 | 0 |
| litestar | asgi | 2 | ok | 12691.28 | 7.87 | 6.66 | 10.24 | 10.67 | 0 |
| fastapi | asgi | 2 | ok | 11014.40 | 9.07 | 8.50 | 13.81 | 14.07 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 29155.07 | 3.43 | 3.42 | 4.78 | 5.16 | 0 |
| starlette | asgi | 2 | ok | 15599.96 | 6.40 | 5.15 | 9.23 | 9.45 | 0 |
| orionis-asgi | asgi | 2 | ok | 30466.45 | 3.28 | 3.23 | 4.46 | 5.10 | 0 |
| litestar | asgi | 3 | ok | 12345.25 | 8.09 | 8.61 | 9.58 | 11.19 | 0 |
| orionis-asgi | asgi | 3 | ok | 37383.97 | 2.67 | 2.54 | 4.28 | 5.32 | 0 |
| fastapi | asgi | 3 | ok | 10858.86 | 9.20 | 9.97 | 10.78 | 12.68 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 38169.28 | 2.62 | 2.46 | 4.30 | 5.44 | 0 |
| starlette | asgi | 3 | ok | 14469.85 | 6.90 | 6.84 | 8.22 | 9.67 | 0 |
| orionis-asgi | asgi | 4 | ok | 34453.33 | 2.90 | 2.75 | 4.94 | 6.29 | 0 |
| fastapi | asgi | 4 | ok | 11532.34 | 8.66 | 9.31 | 13.28 | 16.78 | 0 |
| litestar | asgi | 4 | ok | 13212.92 | 7.56 | 8.43 | 11.81 | 17.70 | 0 |
| starlette | asgi | 4 | ok | 15556.26 | 6.42 | 6.50 | 10.48 | 11.87 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 36727.66 | 2.72 | 2.57 | 4.66 | 6.08 | 0 |

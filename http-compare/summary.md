# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 3998.37 | 24.97 | 23.97 | 30.15 | 31.62 | 0 |
| orionis-asgi | asgi | 1 | ok | 12996.17 | 7.68 | 6.24 | 11.61 | 12.14 | 0 |
| fastapi | asgi | 1 | ok | 3590.10 | 27.81 | 27.07 | 33.28 | 34.18 | 0 |
| starlette | asgi | 1 | ok | 4712.32 | 21.19 | 20.70 | 26.14 | 27.02 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 10642.55 | 9.39 | 9.23 | 11.84 | 12.13 | 0 |
| litestar | asgi | 2 | ok | 7024.43 | 14.22 | 12.60 | 17.77 | 18.12 | 0 |
| fastapi | asgi | 2 | ok | 6354.24 | 15.71 | 14.08 | 19.68 | 21.23 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 18436.28 | 5.42 | 5.32 | 7.14 | 7.79 | 0 |
| starlette | asgi | 2 | ok | 7969.85 | 12.53 | 10.98 | 17.01 | 19.81 | 0 |
| orionis-asgi | asgi | 2 | ok | 19265.04 | 5.18 | 5.15 | 7.00 | 7.84 | 0 |
| litestar | asgi | 3 | ok | 7854.58 | 12.71 | 12.80 | 14.53 | 15.25 | 0 |
| orionis-asgi | asgi | 3 | ok | 23508.88 | 4.25 | 4.11 | 6.51 | 7.85 | 0 |
| fastapi | asgi | 3 | ok | 6907.58 | 14.45 | 14.47 | 17.08 | 17.65 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 24587.89 | 4.06 | 3.90 | 6.14 | 7.54 | 0 |
| starlette | asgi | 3 | ok | 8952.78 | 11.16 | 11.33 | 12.15 | 13.82 | 0 |
| orionis-asgi | asgi | 4 | ok | 23696.55 | 4.21 | 4.04 | 6.89 | 8.58 | 0 |
| fastapi | asgi | 4 | ok | 7818.29 | 12.77 | 11.98 | 21.95 | 22.75 | 0 |
| litestar | asgi | 4 | ok | 8915.07 | 11.20 | 10.67 | 17.86 | 22.35 | 0 |
| starlette | asgi | 4 | ok | 10249.48 | 9.74 | 10.79 | 15.05 | 17.69 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 24456.74 | 4.08 | 3.91 | 6.75 | 8.43 | 0 |

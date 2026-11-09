# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 7394.99 | 13.51 | 12.85 | 16.90 | 17.04 | 0 |
| orionis-asgi | asgi | 1 | ok | 24767.77 | 4.03 | 3.34 | 7.17 | 7.42 | 0 |
| fastapi | asgi | 1 | ok | 6246.83 | 15.99 | 15.05 | 19.11 | 19.31 | 0 |
| starlette | asgi | 1 | ok | 9251.83 | 10.80 | 10.21 | 14.12 | 14.23 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 20402.15 | 4.90 | 4.84 | 6.55 | 6.67 | 0 |
| litestar | asgi | 2 | ok | 12720.52 | 7.85 | 6.44 | 10.40 | 11.32 | 0 |
| fastapi | asgi | 2 | ok | 11203.16 | 8.92 | 7.59 | 11.44 | 11.61 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 29893.71 | 3.34 | 3.30 | 4.65 | 5.64 | 0 |
| starlette | asgi | 2 | ok | 15345.04 | 6.51 | 5.27 | 9.15 | 9.56 | 0 |
| orionis-asgi | asgi | 2 | ok | 33091.99 | 3.02 | 2.96 | 4.35 | 5.28 | 0 |
| litestar | asgi | 3 | ok | 12269.48 | 8.14 | 8.16 | 10.20 | 11.07 | 0 |
| orionis-asgi | asgi | 3 | ok | 39182.19 | 2.55 | 2.42 | 4.16 | 5.23 | 0 |
| fastapi | asgi | 3 | ok | 10998.40 | 9.08 | 9.64 | 10.71 | 12.07 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 40686.11 | 2.45 | 2.33 | 4.03 | 5.14 | 0 |
| starlette | asgi | 3 | ok | 14535.18 | 6.87 | 7.26 | 8.13 | 9.34 | 0 |
| orionis-asgi | asgi | 4 | ok | 38207.56 | 2.61 | 2.49 | 4.42 | 5.65 | 0 |
| fastapi | asgi | 4 | ok | 11752.62 | 8.50 | 7.06 | 15.03 | 19.27 | 0 |
| litestar | asgi | 4 | ok | 13223.47 | 7.55 | 7.48 | 11.57 | 14.33 | 0 |
| starlette | asgi | 4 | ok | 15579.92 | 6.41 | 6.13 | 11.39 | 12.78 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 38725.83 | 2.58 | 2.43 | 4.45 | 5.78 | 0 |

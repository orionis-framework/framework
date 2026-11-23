# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 8146.25 | 12.27 | 12.10 | 12.77 | 13.14 | 0 |
| orionis-asgi | asgi | 1 | ok | 27273.51 | 3.66 | 3.60 | 4.47 | 4.86 | 0 |
| fastapi | asgi | 1 | ok | 7242.41 | 13.80 | 13.59 | 14.52 | 14.63 | 0 |
| starlette | asgi | 1 | ok | 9852.48 | 10.14 | 10.00 | 10.67 | 10.77 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 23472.41 | 4.26 | 4.44 | 4.85 | 4.99 | 0 |
| litestar | asgi | 2 | ok | 15555.86 | 6.42 | 6.24 | 8.32 | 8.44 | 0 |
| fastapi | asgi | 2 | ok | 13907.08 | 7.19 | 7.00 | 7.96 | 8.07 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 38884.07 | 2.57 | 2.54 | 3.26 | 3.71 | 0 |
| starlette | asgi | 2 | ok | 18519.78 | 5.40 | 5.81 | 6.97 | 7.07 | 0 |
| orionis-asgi | asgi | 2 | ok | 41092.92 | 2.43 | 2.41 | 3.04 | 3.54 | 0 |
| litestar | asgi | 3 | ok | 17543.10 | 5.70 | 5.91 | 7.06 | 8.44 | 0 |
| orionis-asgi | asgi | 3 | ok | 51084.71 | 1.96 | 1.88 | 2.88 | 3.59 | 0 |
| fastapi | asgi | 3 | ok | 15309.34 | 6.53 | 7.05 | 7.87 | 9.41 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 52516.55 | 1.90 | 1.83 | 2.85 | 3.53 | 0 |
| starlette | asgi | 3 | ok | 20653.62 | 4.84 | 5.16 | 5.85 | 6.90 | 0 |
| orionis-asgi | asgi | 4 | ok | 47483.16 | 2.10 | 2.00 | 3.70 | 4.77 | 0 |
| fastapi | asgi | 4 | ok | 15846.81 | 6.31 | 6.56 | 12.05 | 12.35 | 0 |
| litestar | asgi | 4 | ok | 18056.18 | 5.53 | 6.29 | 9.46 | 10.32 | 0 |
| starlette | asgi | 4 | ok | 21361.57 | 4.68 | 5.16 | 7.00 | 7.91 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 48907.30 | 2.04 | 1.92 | 3.62 | 4.83 | 0 |

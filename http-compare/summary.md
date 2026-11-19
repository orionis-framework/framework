# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 8217.14 | 12.16 | 11.91 | 12.67 | 13.14 | 0 |
| orionis-asgi | asgi | 1 | ok | 28231.13 | 3.54 | 3.43 | 4.29 | 4.69 | 0 |
| fastapi | asgi | 1 | ok | 7224.59 | 13.83 | 13.58 | 14.45 | 14.52 | 0 |
| starlette | asgi | 1 | ok | 9794.77 | 10.20 | 10.01 | 10.62 | 10.69 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 24436.23 | 4.09 | 4.32 | 4.70 | 4.80 | 0 |
| litestar | asgi | 2 | ok | 15747.14 | 6.35 | 6.11 | 7.03 | 7.83 | 0 |
| fastapi | asgi | 2 | ok | 13924.00 | 7.18 | 6.95 | 7.89 | 8.30 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 39206.60 | 2.55 | 2.51 | 3.48 | 3.84 | 0 |
| starlette | asgi | 2 | ok | 18633.94 | 5.36 | 5.12 | 6.88 | 6.94 | 0 |
| orionis-asgi | asgi | 2 | ok | 40830.92 | 2.45 | 2.42 | 3.11 | 3.54 | 0 |
| litestar | asgi | 3 | ok | 17619.83 | 5.67 | 6.07 | 6.95 | 8.00 | 0 |
| orionis-asgi | asgi | 3 | ok | 51309.10 | 1.95 | 1.89 | 2.93 | 3.63 | 0 |
| fastapi | asgi | 3 | ok | 15633.11 | 6.39 | 6.94 | 7.54 | 8.94 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 52255.41 | 1.91 | 1.83 | 2.95 | 3.69 | 0 |
| starlette | asgi | 3 | ok | 20677.64 | 4.83 | 4.99 | 6.21 | 7.12 | 0 |
| orionis-asgi | asgi | 4 | ok | 47103.87 | 2.12 | 2.01 | 3.66 | 4.75 | 0 |
| fastapi | asgi | 4 | ok | 15928.57 | 6.27 | 6.80 | 10.00 | 12.13 | 0 |
| litestar | asgi | 4 | ok | 18114.16 | 5.52 | 6.34 | 8.59 | 10.45 | 0 |
| starlette | asgi | 4 | ok | 21368.37 | 4.68 | 4.84 | 7.69 | 8.59 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 48624.70 | 2.05 | 1.92 | 3.67 | 4.83 | 0 |

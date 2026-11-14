# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 5572.06 | 17.93 | 17.47 | 20.65 | 20.94 | 0 |
| orionis-asgi | asgi | 1 | ok | 14193.17 | 7.04 | 6.79 | 9.45 | 9.96 | 0 |
| fastapi | asgi | 1 | ok | 5009.27 | 19.94 | 19.62 | 23.02 | 23.36 | 0 |
| starlette | asgi | 1 | ok | 6518.37 | 15.33 | 15.05 | 17.99 | 18.24 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 14209.05 | 7.03 | 6.77 | 9.44 | 9.73 | 0 |
| litestar | asgi | 2 | ok | 9798.24 | 10.20 | 10.42 | 14.64 | 14.99 | 0 |
| fastapi | asgi | 2 | ok | 8724.57 | 11.45 | 10.52 | 13.93 | 15.68 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 24521.36 | 4.07 | 4.04 | 5.17 | 5.79 | 0 |
| starlette | asgi | 2 | ok | 11395.97 | 8.77 | 8.06 | 10.91 | 11.42 | 0 |
| orionis-asgi | asgi | 2 | ok | 25141.67 | 3.97 | 3.93 | 5.38 | 5.96 | 0 |
| litestar | asgi | 3 | ok | 11209.37 | 8.91 | 9.03 | 10.75 | 13.00 | 0 |
| orionis-asgi | asgi | 3 | ok | 35379.21 | 2.82 | 2.68 | 4.23 | 5.25 | 0 |
| fastapi | asgi | 3 | ok | 9762.80 | 10.23 | 10.55 | 11.82 | 13.12 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 37121.31 | 2.69 | 2.57 | 4.11 | 5.03 | 0 |
| starlette | asgi | 3 | ok | 13161.31 | 7.59 | 7.65 | 8.86 | 10.74 | 0 |
| orionis-asgi | asgi | 4 | ok | 33244.00 | 3.00 | 2.86 | 5.09 | 6.52 | 0 |
| fastapi | asgi | 4 | ok | 10922.68 | 9.15 | 10.22 | 16.44 | 18.01 | 0 |
| litestar | asgi | 4 | ok | 12606.56 | 7.92 | 9.34 | 11.76 | 14.54 | 0 |
| starlette | asgi | 4 | ok | 14887.26 | 6.71 | 7.09 | 10.91 | 12.06 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 34722.41 | 2.88 | 2.70 | 5.05 | 6.50 | 0 |

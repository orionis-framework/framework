# HTTP framework comparison

| Framework | Interface | Workers | Status | Requests/s | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| litestar | asgi | 1 | ok | 8105.18 | 12.33 | 12.13 | 12.94 | 13.23 | 0 |
| orionis-asgi | asgi | 1 | ok | 27543.87 | 3.63 | 3.54 | 4.46 | 4.81 | 0 |
| fastapi | asgi | 1 | ok | 7319.81 | 13.65 | 13.46 | 14.38 | 14.47 | 0 |
| starlette | asgi | 1 | ok | 9874.05 | 10.12 | 10.01 | 10.67 | 10.75 | 0 |
| orionis-rsgi | rsgi | 1 | ok | 24170.14 | 4.13 | 4.34 | 4.79 | 4.93 | 0 |
| litestar | asgi | 2 | ok | 15683.10 | 6.37 | 6.27 | 7.08 | 7.89 | 0 |
| fastapi | asgi | 2 | ok | 13847.83 | 7.22 | 7.02 | 7.89 | 7.98 | 0 |
| orionis-rsgi | rsgi | 2 | ok | 39153.26 | 2.55 | 2.52 | 3.27 | 3.60 | 0 |
| starlette | asgi | 2 | ok | 18707.75 | 5.34 | 5.13 | 5.94 | 6.06 | 0 |
| orionis-asgi | asgi | 2 | ok | 40741.16 | 2.45 | 2.41 | 3.21 | 3.60 | 0 |
| litestar | asgi | 3 | ok | 17272.18 | 5.78 | 6.01 | 7.13 | 8.40 | 0 |
| orionis-asgi | asgi | 3 | ok | 50651.89 | 1.97 | 1.91 | 2.94 | 3.63 | 0 |
| fastapi | asgi | 3 | ok | 15385.56 | 6.50 | 6.79 | 7.85 | 9.34 | 0 |
| orionis-rsgi | rsgi | 3 | ok | 52627.89 | 1.90 | 1.80 | 2.95 | 3.64 | 0 |
| starlette | asgi | 3 | ok | 20812.51 | 4.80 | 5.14 | 6.17 | 7.48 | 0 |
| orionis-asgi | asgi | 4 | ok | 47399.46 | 2.11 | 2.00 | 3.64 | 4.66 | 0 |
| fastapi | asgi | 4 | ok | 16130.48 | 6.19 | 6.79 | 10.62 | 10.82 | 0 |
| litestar | asgi | 4 | ok | 17529.19 | 5.70 | 5.93 | 7.09 | 7.81 | 0 |
| starlette | asgi | 4 | ok | 21072.99 | 4.74 | 5.07 | 7.23 | 8.55 | 0 |
| orionis-rsgi | rsgi | 4 | ok | 49236.30 | 2.03 | 1.91 | 3.60 | 4.76 | 0 |

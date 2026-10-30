# Comparación HTTP de Orionis, FastAPI, Litestar y Starlette

La suite compara cinco configuraciones en una misma máquina mediante `GET /`.
Todas responden `200 OK` con el texto exacto `Hello World` (11 bytes).

## Servidores

| Framework | Interfaz | Servidor |
| --- | --- | --- |
| Orionis | RSGI | Granian 2.8.4 |
| Orionis | ASGI | Granian 2.8.4 |
| FastAPI | ASGI | Uvicorn 0.54.0 |
| Litestar | ASGI | Uvicorn 0.54.0 |
| Starlette | ASGI | Uvicorn 0.54.0 |

Cada configuración se ejecuta con **1, 2, 3 y 4 workers**, HTTP/1.1 con
keep-alive y event loop `asyncio`.

## Instalación y ejecución

Desde la raíz del repositorio:

```text
uv python install 3.14.8
uv sync --locked --group benchmark --no-default-groups --python 3.14.8
uv run --no-sync python -B -m benchmarks.http_compare.run
```

La comparación completa se ejecuta en Ubuntu 24.04 con Python 3.14.8.
En Windows, usa `--workers 1`. Puedes seleccionar casos con `--frameworks`
y consultar las opciones de ejecución con `--help`.
Cada ejecución requiere una carpeta de salida nueva o vacía.

## Resultados

Las [gráficas del README principal](../../README.md#http-benchmarks) muestran
las solicitudes HTTP 200 por segundo para cada cantidad de workers.
La [tabla completa de resultados](https://github.com/orionis-framework/framework/blob/benchmark-results/http-compare/summary.md)
incluye throughput, latencia media, p50, p95, p99, estado y errores.

Se publica la mediana de tres mediciones de 10 segundos por configuración.
Las latencias se expresan en milisegundos y no se mezclan cantidades de workers.

Los archivos se guardan en `benchmark-results/http-compare/`:

| Archivo | Contenido |
| --- | --- |
| `summary.md` | Tabla de resultados. |
| `summary.csv` | Resultados para hojas de cálculo. |
| `summary.json` | Resultados estructurados por framework y workers. |
| `throughput-N-workers.svg` | Gráfica de throughput por cantidad de workers. |

Los casos fallidos se indican explícitamente y no publican métricas.
Los detalles técnicos se conservan por separado en `diagnostics.json`.
Las gráficas solo se generan cuando toda la comparación termina sin errores.

GitHub Actions ejecuta la comparación con cada `push` a `1.x` y permite
iniciarla desde **Actions → HTTP Framework Comparison → Run workflow**.
La tabla aparece en el resumen del job. Las ejecuciones exitosas en `1.x`
publican las gráficas y los resúmenes en la rama `benchmark-results`.

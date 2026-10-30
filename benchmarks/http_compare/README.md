# Comparación HTTP de Orionis, FastAPI, Litestar y Starlette

Esta suite compara cinco configuraciones en una misma máquina: Orionis RSGI,
Orionis ASGI, FastAPI, Litestar y Starlette. Solo Orionis usa Granian; FastAPI,
Litestar y Starlette usan Uvicorn. Todas miden una ruta
`GET /` que construye una respuesta de texto `200 OK` con el cuerpo exacto
`Hello World` (11 bytes, sin comillas ni salto de línea).

Orionis utiliza `Application`, su cargador real de rutas y `response.text()`.
Las dos interfaces comparten la misma aplicación. Así se puede comparar Orionis
con los otros frameworks sobre ASGI y observar por separado el efecto de RSGI.
La comparación incluye también la diferencia entre los servidores utilizados.
El resto de las aplicaciones también usa las rutas y respuestas de su framework.

## Entorno y parámetros

Las dependencias directas del grupo `benchmark` tienen versiones exactas y sus
dependencias transitivas están registradas en el `uv.lock` del repositorio.
Python y oha se fijan por separado para completar el entorno de referencia:

| Componente | Versión |
| --- | --- |
| Python | 3.14.8 |
| Granian | 2.8.4 |
| Uvicorn | 0.54.0 |
| oha | 1.16.0 |
| FastAPI | 0.143.1 |
| Litestar | 2.24.0 |
| Starlette | 1.8.0 |

La ejecución de referencia es Ubuntu 24.04 en GitHub Actions, con CPython normal,
sin usar la variante freethreaded. Los valores por defecto del ejecutor son:

| Parámetro | Valor |
| --- | --- |
| Workers por servidor | 1, 2, 3 y 4 |
| Hilos de red de Granian por worker | 1 |
| Event loop | `asyncio` |
| Implementación de tareas de Granian | `asyncio` |
| HTTP | HTTP/1.1 con keep-alive |
| Implementación HTTP de Uvicorn | `h11` |
| Lifespan de Uvicorn | `on` |
| WebSockets | Deshabilitados |
| Conexiones concurrentes de oha | 100 |
| Hilos de trabajo de oha | 1 |
| Calentamiento por configuración de Orionis | 2 segundos |
| Mediciones por configuración | 3 de 10 segundos |
| Semilla del orden de ejecución | 42 |

El orden de los frameworks se aleatoriza de forma reproducible para cada número
de workers mediante `--seed`. Se ejecuta una configuración a la vez. Esto reduce
la dependencia de un orden fijo; no elimina la variación de la máquina.

## Instalación y ejecución

Desde la raíz del repositorio, instala el entorno de referencia y ejecuta:

```text
uv python install 3.14.8
uv sync --locked --group benchmark --no-default-groups --python 3.14.8
uv run --no-sync python -B -m benchmarks.http_compare.run
```

`--no-sync` conserva las dependencias del grupo `benchmark` ya instaladas.
La comparación completa se ejecuta en Ubuntu. En Windows, Granian admite
únicamente un worker y Uvicorn con CPython 3.14 puede fallar al compartir
sockets entre procesos. La suite conserva el límite de un worker para todos
los servidores en Windows; para una comprobación rápida de los cinco casos:

```text
uv run --no-sync python -B -m benchmarks.http_compare.run --workers 1 --warmup 0.5 --duration 1 --repetitions 3 --connections 10 --output-dir benchmark-results/http-compare-smoke
```

Usa `--frameworks` para seleccionar casos, `--workers` para seleccionar
cantidades de workers y `--help` para consultar todas las opciones.
`--warmup` solo se aplica a Orionis RSGI y Orionis ASGI.
Cada ejecución requiere una carpeta de salida nueva o vacía.

El ejecutor exige oha 1.16.0: lo busca en `PATH` o descarga temporalmente el
binario oficial y verifica su SHA-256. Puedes proporcionar uno existente con
`--oha C:\herramientas\oha.exe`.

## Cómo se mide

Las apps contienen únicamente la configuración nativa y la ruta `GET /`.
No tienen endpoints auxiliares, callbacks de seguimiento ni archivos de
marcadores. El ejecutor verifica los mensajes nativos de arranque del servidor
correspondiente, la pertenencia y vida de sus workers y su disponibilidad.
Para Uvicorn, espera también la finalización del startup de todas las apps y
reconoce que con un solo worker el proceso principal atiende las peticiones.
Esta política queda registrada en `settings.readiness`.

Solo Orionis RSGI y Orionis ASGI realizan preparación HTTP y precalentamiento:

1. Envía dos `GET /` consecutivos sobre una misma conexión keep-alive y consume
   ambas respuestas completas: HTTP/1.1, `200`, `text/plain` y el cuerpo exacto
   `Hello World`. La primera petición permite inicializar cachés del recorrido
   HTTP; la segunda comprueba la respuesta en caliente. Ninguna se mide.
2. Ejecuta `--warmup`: **2 segundos de tráfico HTTP real por defecto**, no una
   pausa fija. Conserva este resultado separado de las métricas.

FastAPI, Litestar y Starlette pasan directamente del arranque a las mediciones:
no reciben peticiones HTTP de preparación ni una ejecución de `--warmup`.
Su disponibilidad se comprueba abriendo y cerrando una conexión TCP. Todos
los casos limpian el servidor al finalizar, incluso si hay fallos.

Si el servidor no anuncia todos sus workers, alguno muere o no queda
disponible dentro del timeout de inicio, el caso falla. No se incluyen
las peticiones de preparación ni las de calentamiento de Orionis en los
conteos, tiempos, latencias o tasas publicados.

El precalentamiento de Orionis se ejecuta desde el cliente, no dentro de la app.
Las peticiones iniciales validan la respuesta, pero ya no identifican por HTTP
ni garantizan la preparación individual de cada worker. La ruta medida no
lleva contadores ni cabeceras de seguimiento.

El archivo de rutas de Orionis, [`apps/routes/web.py`](apps/routes/web.py),
lo copia el ejecutor una sola vez al directorio aislado antes de iniciar Granian.
Todos los workers leen ese archivo sin modificarlo. Así se conserva el cargador
real sin importar rutas del proyecto anfitrión ni generar archivos desde la app.

Todos los frameworks comparten HTTP/1.1, keep-alive, `asyncio`, la cantidad de
workers y la carga medida; los parámetros propios de cada servidor se indican
en la tabla anterior. El precalentamiento es exclusivo de Orionis.
El ejecutor descarta las variables heredadas `GRANIAN_*` y `UVICORN_*` para
evitar ajustes externos. El cliente espera las
solicitudes en curso al terminar cada medición, con un timeout de 5 segundos por
solicitud. La tasa se calcula con el tiempo real, no con la duración nominal:

```text
solicitudes por segundo = statusCodeDistribution["200"] / summary.total
```

Solo se publican métricas si todas las muestras son válidas y no hay errores
HTTP ni de transporte. Un fallo conserva el diagnóstico y las muestras
disponibles, deja las métricas vacías y hace que el comando termine con error.
No se descartan muestras fallidas para mejorar el resultado.
La salida de oha se escribe directamente en los archivos de diagnóstico, que
conservan también la salida parcial si el proceso falla o agota su timeout.

Se publica la mediana de las tasas y, por separado, de la latencia media, p50,
p95 y p99 de cada ejecución, convertidas a milisegundos. No son percentiles de
solicitudes agrupadas. El calentamiento de Orionis se conserva, pero no entra en las
métricas ni en los totales.

## Resultados y trazabilidad

La carpeta de salida por defecto es `benchmark-results/http-compare/`:

| Archivo o carpeta | Contenido |
| --- | --- |
| `summary.json` | Resultados estructurados por framework y workers; esquema 2, sin detalles de preparación. |
| `summary.csv` | El mismo resumen para hojas de cálculo y análisis posterior. |
| `summary.md` | Tabla legible para revisar o compartir los resultados. |
| `throughput-N-workers.svg` | Gráfica de throughput por cantidad de workers; solo se genera si toda la comparación termina sin errores. |
| `diagnostics.json` | Registro completo de configuración, entorno, muestras, preparación y fallos detallados. |
| `environment.json` | Versiones y características del entorno de ejecución. |
| `commands.json` | Comandos utilizados para reproducir y auditar la ejecución. |
| `raw/` | Salida JSON original de oha y archivos `.stderr.log`, incluidos los disponibles si hay fallos. |
| `logs/` | Registros de los servidores. |

Los resúmenes Markdown, CSV y JSON y las gráficas muestran únicamente los
resultados, sus identificadores y su estado. No incluyen parámetros de carga,
preparación, datos del entorno ni muestras sin medir. El esquema 2 de
`summary.json` conserva solo los grupos de frameworks y workers y los resultados.

La información técnica completa se conserva separada en `diagnostics.json`,
incluidos `settings.servers`, `warmup_frameworks`, el resultado `warmup` de Orionis
y los motivos detallados de fallo. Los informes indican los fallos sin sustituir métricas
ausentes por cifras inventadas. Los datos originales también permanecen en
`raw/`, `logs/`, `commands.json` y `environment.json`.

En GitHub Actions, la matriz completa se ejecuta automáticamente con cada `push`
a la rama `1.x`, separada del workflow de pruebas unitarias. También puedes
iniciarla desde **Actions → HTTP Framework Comparison → Run workflow**.
La tabla aparece en el resumen del job y los archivos se descargan desde
`http-framework-comparison-…`, incluso cuando hay mediciones fallidas.

Después de una ejecución exitosa en `1.x`, un job con permiso `contents: write`
publica las gráficas, los resúmenes y el entorno en la rama `benchmark-results`,
dentro de `http-compare/`. La rama se crea automáticamente en la primera
publicación. El README principal muestra una gráfica por configuración de
**1, 2, 3 y 4 workers** y enlaza la tabla completa. Las imágenes estarán
disponibles después de la primera publicación exitosa.

Las barras se ordenan por solicitudes HTTP 200 por segundo y usan las mismas
medianas de `summary.json`, sin combinar cantidades de workers ni tomar la mejor
muestra. Cada gráfica muestra los frameworks, las cantidades resultantes y el
número de workers. Los parámetros de ejecución y el entorno se consultan por
separado en los archivos de diagnóstico.

Las ejecuciones fallidas o iniciadas desde otra rama no reemplazan los
resultados publicados. El job de medición conserva permisos de solo lectura;
la publicación no modifica `1.x` ni dispara otro benchmark. Las ejecuciones de
una misma rama se serializan para evitar publicaciones fuera de orden.

## Límites

Hello World no representa una aplicación completa. Cliente y servidor comparten
CPU; los runners de GitHub varían y el cliente puede limitar el rendimiento.
No mezcles sistemas operativos ni parámetros en una clasificación. Conserva el
entorno, el commit, el lock y los datos originales; repite diferencias pequeñas.

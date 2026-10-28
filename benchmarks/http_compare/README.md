# Comparación HTTP de Orionis, FastAPI, Litestar y Starlette

Esta suite compara cinco configuraciones en una misma máquina: Orionis RSGI,
Orionis ASGI, FastAPI, Litestar y Starlette. Todas usan Granian y miden una ruta
`GET /` que construye una respuesta de texto `200 OK` con el cuerpo exacto
`Hello World` (11 bytes, sin comillas ni salto de línea).

Orionis utiliza `Application`, su cargador real de rutas y `response.text()`.
Las dos interfaces comparten la misma aplicación. Así se puede comparar Orionis
con los otros frameworks sobre ASGI y observar por separado el efecto de RSGI.
El resto de las aplicaciones también usa las rutas y respuestas de su framework.

## Entorno y parámetros

Las dependencias directas del grupo `benchmark` tienen versiones exactas y sus
dependencias transitivas están registradas en el `uv.lock` del repositorio.
Python y oha se fijan por separado para completar el entorno de referencia:

| Componente | Versión |
| --- | --- |
| Python | 3.14.8 |
| Granian | 2.8.4 |
| oha | 1.16.0 |
| FastAPI | 0.143.1 |
| Litestar | 2.24.0 |
| Starlette | 1.8.0 |

La ejecución de referencia es Ubuntu 24.04 en GitHub Actions, con CPython normal,
sin usar la variante freethreaded. Los valores por defecto del ejecutor son:

| Parámetro | Valor |
| --- | --- |
| Workers de Granian | 1, 2, 3 y 4 |
| Hilos de red de Granian por worker | 1 |
| Event loop | `asyncio` |
| Implementación de tareas de Granian | `asyncio` |
| HTTP | HTTP/1.1 con keep-alive |
| WebSockets | Deshabilitados |
| Conexiones concurrentes de oha | 100 |
| Hilos de trabajo de oha | 1 |
| Calentamiento por configuración | 2 segundos |
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
únicamente un worker; para una comprobación rápida de los cinco casos:

```text
uv run --no-sync python -B -m benchmarks.http_compare.run --workers 1 --warmup 0.5 --duration 1 --repetitions 3 --connections 10 --output-dir benchmark-results/http-compare-smoke
```

Usa `--frameworks` para seleccionar casos, `--workers` para seleccionar
cantidades de workers y `--help` para consultar todas las opciones.
Cada ejecución requiere una carpeta de salida nueva o vacía.

El ejecutor exige oha 1.16.0: lo busca en `PATH` o descarga temporalmente el
binario oficial y verifica su SHA-256. Puedes proporcionar uno existente con
`--oha C:\herramientas\oha.exe`.

## Cómo se mide

Cada caso sigue estas fases, iguales para todos los frameworks:

1. Inicia un servidor aislado y verifica que todos sus workers estén vivos.
2. Envía dos `GET /` consecutivos sobre una misma conexión keep-alive y consume
   ambas respuestas completas: HTTP/1.1, `200`, `text/plain` y el cuerpo exacto
   `Hello World`. La primera petición permite inicializar cachés del recorrido
   HTTP; la segunda comprueba la respuesta en caliente. Ninguna se mide.
3. En esa misma conexión consulta `GET /_benchmark/worker`, un endpoint auxiliar
   que devuelve el PID. Solo considera preparado ese worker si el PID pertenece
   al servidor. Abre conexiones nuevas hasta haber preparado **cada worker**,
   sin confundir varias peticiones al mismo proceso con varios workers.
4. Ejecuta `--warmup`: **2 segundos de tráfico HTTP real por defecto**, no una
   pausa fija. Conserva este resultado separado de las métricas.
5. Inicia las mediciones y finalmente limpia el servidor.

Si un worker no llega a completar la preparación dentro del timeout de inicio,
el caso falla en lugar de medirlo en frío. No se incluyen las peticiones de
preparación ni las de calentamiento en los conteos, tiempos, latencias o tasas
publicados.

Orionis no espera artificialmente 2 segundos al arrancar: publica su señal nativa
cuando `isHttpReady` es verdadero. Eso no sustituye la primera petición HTTP real
descartada de cada worker. La ruta medida no lleva contadores, escritura de
marcadores ni cabeceras adicionales de seguimiento; el endpoint de PID solo se
usa durante la preparación, fuera de las mediciones.

El archivo de rutas de Orionis, [`apps/routes/web.py`](apps/routes/web.py),
se copia una sola vez por worker al directorio aislado, con un nombre de módulo
único. Así se conserva el cargador real sin importar rutas del proyecto anfitrión
ni escribir archivos compartidos entre workers.

Todos los frameworks comparten los parámetros de servidor y carga de la tabla
anterior; solo cambian la aplicación y su interfaz. El cliente espera las
solicitudes en curso al terminar cada medición, con un timeout de 5 segundos por
solicitud. La tasa se calcula con el tiempo real, no con la duración nominal:

```text
solicitudes por segundo = statusCodeDistribution["200"] / summary.total
```

Solo se publican métricas si todas las muestras son válidas y no hay errores
HTTP ni de transporte. Un fallo conserva el diagnóstico y las muestras
disponibles, deja las métricas vacías y hace que el comando termine con error.
No se descartan muestras fallidas para mejorar el resultado.

Se publica la mediana de las tasas y, por separado, de la latencia media, p50,
p95 y p99 de cada ejecución, convertidas a milisegundos. No son percentiles de
solicitudes agrupadas. El calentamiento se conserva, pero no entra en las
métricas ni en los totales.

## Resultados y trazabilidad

La carpeta de salida por defecto es `benchmark-results/http-compare/`:

| Archivo o carpeta | Contenido |
| --- | --- |
| `summary.json` | Resumen estructurado por framework y workers, estado y métricas válidas. |
| `summary.csv` | El mismo resumen para hojas de cálculo y análisis posterior. |
| `summary.md` | Tabla legible para revisar o compartir los resultados. |
| `throughput-N-workers.svg` | Gráfica de throughput por cantidad de workers; solo se genera si toda la comparación termina sin errores. |
| `environment.json` | Versiones y características del entorno de ejecución. |
| `commands.json` | Comandos utilizados para reproducir y auditar la ejecución. |
| `raw/` | Salida JSON original de oha y archivos `.stderr.log`, incluidos los disponibles si hay fallos. |
| `logs/` | Registros de los servidores. |

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
muestra. Cada gráfica incluye los parámetros de carga, las versiones de Python y
Granian, la fecha y el commit medido.

Las ejecuciones fallidas o iniciadas desde otra rama no reemplazan los
resultados publicados. El job de medición conserva permisos de solo lectura;
la publicación no modifica `1.x` ni dispara otro benchmark. Las ejecuciones de
una misma rama se serializan para evitar publicaciones fuera de orden.

## Pruebas unitarias

```text
uv run --no-sync python -B -m unittest tests.test_http_compare -v
```

Estas pruebas no generan carga: verifican contabilidad, medianas, preparación
de cada worker y exclusión de la primera petición y del calentamiento, parámetros
compartidos, limpieza, fallos, coherencia de reportes y gráficas SVG.

## Límites

Hello World no representa una aplicación completa. Cliente y servidor comparten
CPU; los runners de GitHub varían y el cliente puede limitar el rendimiento.
No mezcles sistemas operativos ni parámetros en una clasificación. Conserva el
entorno, el commit, el lock y los datos originales; repite diferencias pequeñas.

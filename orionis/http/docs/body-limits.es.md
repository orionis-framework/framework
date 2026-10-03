# Límites de recursos de las peticiones

`KernelHTTP` captura `http.body_limits` durante su boot. La aplicación lo configura
con `HTTPBodyLimits` o un diccionario en `HTTP(body_limits=...)`. El bootstrap
`config/http.py` expone variables de entorno para cada límite.

```python
from orionis.foundation.config.http import HTTP, HTTPBodyLimits

http = HTTP(body_limits=HTTPBodyLimits(
    max_body_size=16 * 1024 * 1024,
    max_buffer_size=2 * 1024 * 1024,
    max_concurrent_requests=128,
))
```

| Configuración | Predeterminado | Alcance |
|---|---:|---|
| `max_body_size` | 16 MiB | Bytes de transporte de una petición, incluido el framing multipart. |
| `max_buffer_size` | 2 MiB | Bytes materializados por `body()`, JSON, MessagePack, XML, texto, binario y URL-encoded. |
| `max_concurrent_requests` | 128 | Peticiones HTTP activas por kernel, incluido el envío y las tareas de fondo esperadas. |
| `max_files` | 32 | Archivos multipart por petición. Cero desactiva archivos. |
| `max_fields` | 128 | Campos de texto multipart por petición. Cero desactiva campos. |
| `max_part_size` | 10 MiB | Bytes de contenido sin decodificar por parte multipart. |
| `max_field_size` | 1 MiB | Bytes sin decodificar por campo de texto multipart. |
| `max_header_size` | 16 KiB | Encabezados MIME y longitud del sufijo delimitador. |
| `memory_threshold` | 256 KiB | Bytes de archivo en memoria antes de pasar a disco temporal. |
| `max_memory_size` | 8 MiB | Strings de campos retenidos y contenido de archivos todavía en memoria. |

La configuración rechaza booleanos, valores no enteros, `None` y rangos inválidos.
Los contadores admiten cero; los demás límites deben ser positivos. Los límites
son independientes: un presupuesto de buffering menor permite uploads grandes
por streaming mientras acota las asignaciones contiguas de JSON/cuerpo crudo.

Un `Content-Length` declarado mayor que `max_body_size` devuelve **413** antes de
leer bytes del cuerpo. Un header inválido, repetido, o combinado con
Transfer-Encoding devuelve **400**. La comparación decimal evita convertir miles
de dígitos controlados por el cliente a un entero. Un Content-Length ausente o
falso no evita el conteo real cuando se lee el cuerpo.

`BodyStream.stream()` comprueba los bytes acumulados antes de entregar cada chunk.
`read()` comprueba además el presupuesto de buffering antes de extender un
bytearray; al terminar cachea un único objeto bytes para repetir la lectura. Ya
no mantiene una lista de todos los chunks. Una lectura fallida consume el flujo
y no deja una caché completa para reproducirlo.

El parser multipart cuenta el flujo completo, incluidos preámbulo y epílogo
descartados, y drena el epílogo tras un delimitador final válido. Limita boundary
a 70 bytes sin CR/LF, procesa los chunks en segmentos de 64 KiB, aplica límites
por archivo/campo/cantidad/encabezados y cuenta strings retenidos mediante
`sys.getsizeof`. Los bytes de archivos todavía en memoria consumen el mismo
presupuesto; los bytes en disco no. La decodificación de content-transfer encoding
de archivos todavía materializa bytes codificados y decodificados, por lo que
requiere un presupuesto adicional de dos veces el tamaño codificado o devuelve
**413**. La sintaxis multipart inválida continúa generando `ValueError`; exceder
recursos genera `PayloadTooLargeException`, ahora también subclase de `ValueError`.

La admisión usa `BoundedSemaphore` seguro entre hilos y ninguna cola de espera de
aplicación. La saturación devuelve **503** con `Retry-After: 1`; `finally` libera
capacidad tras envío correcto, error o cancelación. WebSocket tiene sus propios
límites de admisión. El kernel llama `Request.close()` después del envío HTTP y
las tareas de fondo para cerrar archivos multipart, también ante cancelación.
Copia/guarda los uploads durante la petición si el trabajo continuará después.
Las peticiones y formularios creados manualmente pueden cerrarse explícitamente.

Son presupuestos finitos de entrada y contenido retenido, no una promesa de RSS
absoluta del proceso. El servidor puede entregar un chunk grande antes de que
Python lo rechace; buffers de transporte, capacidad extra del bytearray, objetos
JSON, conversiones temporales, asignaciones de aplicación y respuestas consumen
memoria adicional. La admisión es por instancia de kernel y worker: múltiples
workers multiplican la capacidad. No se drenan los cuerpos ignorados por el
handler solo para medirlos. Configura límites de cuerpo/conexiones/deadlines del
servidor y reverse proxy, cantidad de workers y límite de memoria del SO/contenedor.
Las referencias persistentes a bytes u objetos derivados de peticiones pueden
continuar reteniendo memoria después de la admisión.

## Compatibilidad y verificación

Los valores predeterminados reemplazan deliberadamente el lector prácticamente
ilimitado y los 1000 archivos/1000 campos multipart anteriores. Peticiones que
aceptaban cuerpos grandes en buffer o muchos campos ahora pueden devolver 413;
configura presupuestos finitos mayores cuando se requiera. Construir `BodyStream`
directamente todavía admite un **opt-out explícito** `max_body_size=None` o
`max_buffer_size=None`; `HTTPBodyLimits` de aplicación no acepta estas opciones.
Se conservan las reglas de streaming y reproducción después de `read()` exitoso.
La nueva operación `IRequest.close()` debe implementarse en requests personalizados.

Las regresiones cubren reproducción en el límite exacto, defaults finitos,
desbordamiento real ASGI/RSGI, Content-Length falso/inválido, framing multipart,
memoria retenida, spooling, admisión HTTP compartida, recuperación tras cancelación
y limpieza de uploads. Ejecuta:

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe reactor test --start-dir="tests/http" --verbosity=1
```

Estas pruebas no certifican RSS de producción, throughput, resistencia a clientes
lentos ni coordinación de servidores entre procesos. La certificación y las
mediciones deben declarar servidor real, sistema operativo, workers y tráfico.

# Respuestas predeterminadas: revisión de rendimiento

Revisión del 23 de septiembre de 2026 sobre `responses.py`, con CPython 3.14.3
de 64 bits y Windows 11. La comparación parte de la implementación con el motor
oficial de vistas y los recursos locales, anterior a esta revisión de rendimiento.

## Resultado por impacto

### Crítico

No se identificó un cuello de botella de severidad crítica ni un algoritmo
cuadrático que justifique sustituir el motor de plantillas. El perfil de la
implementación anterior atribuyó aproximadamente el 94% del tiempo de los errores
HTML a Jinja y el 85% del tiempo de las excepciones a Jinja; construir el traceback
representó aproximadamente otro 9% en el caso medido. Estos porcentajes proceden
de cProfile y sirven para localizar costos, no para estimar latencias de producción.

### Alto: duración del servicio y reutilización de salud

**Problema.** El kernel construía `DefaultResponses` nuevamente para cada ruta
predeterminada, aunque ya tenía una instancia creada durante el arranque. Por ello,
las peticiones reales a `/up` no aprovechaban los cuerpos HTML guardados. Cada
petición repetía resolución de dependencias, construcción, renderizado y codificación.

**Implementación.** `KernelHTTP.__callHandler` utiliza su instancia existente
cuando el controlador es exactamente `DefaultResponses`. Los demás controladores
siguen construyéndose por petición. `health` conserva únicamente los bytes de las
dos páginas de estado y crea una respuesta nueva en cada llamada.

**CPU, memoria y tiempo.** Después del primer render, el trabajo de la fábrica de
salud pasa de recorrer y codificar el HTML, O(B) respecto al tamaño de la página,
a una consulta de caché y construcción de encabezados, O(1). Se evitan el servicio
temporal, sus cachés, el contexto, el render y la codificación por petición. Enviar
los B bytes por la red sigue siendo O(B); el benchmark no mide ese envío.

**Trade-off.** El servicio conserva hasta dos cuerpos de salud durante su vida.
Lee nombre e idioma actuales para invalidarlos cuando cambian; mantenimiento se
consulta en cada petición. Un render suspendido solo publica su cuerpo si sus
etiquetas todavía coinciden con las actuales. Esto añade dos lecturas de
configuración a una consulta de caché previamente caliente, pero mantiene los
cambios de configuración visibles después de prolongar la vida del servicio.
No se añade un bloqueo global al camino habitual.

### Alto: consultas de archivos y clasificación MIME

**Problema.** Los archivos existentes pasaban primero por `exists` o `is_file`
y después por la comprobación de `FileResponse`. Además, proporcionar el encabezado
`content-type` no impedía que `FileResponse` dedujera el MIME otra vez.

**Implementación.** `__fileResponse` construye directamente una respuesta con
`media_type` explícito. `FileResponse` consulta los metadatos y verifica que el
archivo sea regular; `OSError` o `ValueError` hacen continuar con el siguiente
candidato o devolver 404. `__publicFile` reúne la selección de favicon, robots y
sitemap y recupera rutas previamente seleccionadas que hayan desaparecido.

**CPU, memoria y tiempo.** Se elimina una comprobación del filesystem para cada
asset válido y cada candidato público encontrado durante la selección inicial.
Se elimina una inferencia MIME por respuesta de archivo, incluyendo sus
transformaciones de rutas y temporales. En Windows, `Path.is_file` puede usar una
implementación nativa distinta de `os.stat`: se cuentan las operaciones observadas,
sin equipararlas a un número exacto de llamadas al kernel del sistema operativo.

**Trade-off.** Las excepciones forman parte del camino de archivos ausentes.
Solo se capturan alrededor de la construcción con argumentos fijos. Los archivos
siguen teniendo una consulta síncrona de metadatos; el beneficio medido con disco
local no predice el de un filesystem remoto. La apertura y lectura ocurren durante
el streaming y todavía pueden fallar si el archivo cambia después de construir
la respuesta.

### Medio: rutas y encabezados reutilizables

**Problema.** Cada asset reconstruía su `Path` y su diccionario de encabezados.
Las otras respuestas también recreaban encabezados constantes. `error` recorría
los encabezados para buscar `cache-control` y luego `Response` volvía a recorrerlos
y normalizarlos; cuando faltaba ese encabezado, se copiaba todo el diccionario.

**Implementación.** Una caché guarda como máximo las seis rutas permitidas de
assets. Los encabezados constantes se definen una vez y `Response` los copia a su
almacenamiento propio. Para encabezados personalizados, `error` consulta
`response.hasHeader` después de la normalización y agrega el valor predeterminado
solo cuando falta.

**CPU, memoria y tiempo.** Se evita un `Path` y un diccionario de entrada por asset
caliente, y un diccionario de encabezados por respuesta con valores predeterminados.
La comprobación adicional de `cache-control` pasa de O(H), con generador y
conversiones a minúsculas, a O(1) sobre la respuesta. Construir sus H encabezados
sigue siendo O(H); el total no se convierte en O(1).

**Trade-off.** Hay un pequeño costo fijo de metadatos y seis rutas como máximo por
instancia. Los diccionarios compartidos son entradas privadas que el servicio no
modifica. No se comparten respuestas, encabezados de salida, flash ni generadores.
No se guardan contenidos o resultados `stat` de archivos. Una ruta permitida
ausente se vuelve a comprobar en la próxima petición.

La selección de un archivo público o su fallback persiste mientras ese archivo
exista. Agregar un candidato de mayor prioridad requiere invalidar la selección
con `del responses["favicon"]`, `del responses["robots_txt"]` o
`del responses["sitemap_xml"]`, o reiniciar el servicio. El tamaño y contenido del
archivo seleccionado siguen reflejando cambios. Esta política de selección ya
existía por instancia y ahora también se aplica entre peticiones del kernel.

### Bajo: contexto, constantes, validación y disposición de instancias

**Problemas.** `__render` recibía un diccionario temporal de argumentos y creaba
otro al combinar el contexto. Cada render reconstruía nombres de plantilla y el
prefijo de assets. Cada excepción recalculaba versiones invariantes y suministraba
`error_context`, que ninguna plantilla utilizaba. JSON repetía la validación del
estado que `Response` realiza antes de serializar. La instancia y su contrato
heredaban almacenamiento mediante `__dict__`.

**Implementación.** Cada render recibe y completa un único diccionario propio;
los nombres de plantilla, prefijo y versiones están predefinidos. Se eliminó
`error_context`. JSON conserva la normalización del enum y delega la validación
del estado en `Response`. HTML y excepciones validan antes de convertir datos o
renderizar. Se añadieron `__slots__` tanto a la implementación como al ABC.

**CPU, memoria y tiempo.** Se evita un diccionario y dos cadenas construidas por
render, además de los temporales de las versiones por excepción y una validación
duplicada por error JSON. La instancia medida ocupa 88 bytes superficiales frente
a 216 bytes de objeto más diccionario en la versión anterior, una diferencia de
128 bytes. Esto no incluye sus dependencias ni cachés. Son mejoras pequeñas frente
al costo del motor y del filesystem, especialmente con un único servicio retenido.

**Trade-offs.** `__render` recibe un diccionario que le pertenece y puede modificar;
no se le debe pasar contexto compartido. Las instancias base con slots no admiten
atributos arbitrarios; una subclase puede declarar los que necesite. Configuración
de entorno, depuración, interfaz y zona horaria siguen leyéndose en cada excepción.
El helper `_status_message` conserva la caché de etiquetas existente y mantiene
la complejidad cognitiva de `error` dentro del límite del analizador.

## Medición

Ejecución controlada en un único CPU lógico, con 21 muestras alternadas. La
calibración ejecutando código idéntico de `FileResponse` mostró una diferencia
del 0,31%. Las cifras siguientes son microsegundos por construcción, no por
petición HTTP completa:

| Escenario | Antes (µs) | Después (µs) | Resultado |
| --- | ---: | ---: | --- |
| Salud HTML: servicio transitorio → retenido | 80,56 | 2,55 | 31,6 veces; −96,8% |
| Asset CSS con ruta caliente | 72,18 | 38,04 | −47,3% |
| robots.txt con selección caliente | 46,74 | 42,18 | −9,7% |
| Error JSON con encabezados personalizados | 5,44 | 4,34 | −20,1% |
| Error JSON sin encabezados personalizados | 3,28 | 2,98 | −9,2% |
| Error HTML | 123,88 | 124,22 | Sin diferencia material |
| Excepción HTML con un frame | 515,96 | 511,69 | Sin diferencia material |
| Salud HTML: ambas instancias ya calientes | 2,06 | 2,35 | +0,29 µs por validar etiquetas |

La primera fila reproduce el cambio de duración del servicio y usa su propia
serie de muestras; la última aísla el costo de comprobar la configuración. No
se debe atribuir a la microoptimización del método la ganancia obtenida al evitar
construcción y renderizado en cada petición.

Picos de memoria trazada sobre el valor inicial de una llamada caliente, medidos
separadamente con el código final:

| Escenario | Antes (bytes) | Después (bytes) |
| --- | ---: | ---: |
| Asset CSS | 4.999 | 3.869 |
| Error JSON | 1.940 | 1.780 |
| Error HTML | 11.683 | 11.139 |
| Excepción HTML | 27.924 | 27.343 |

Son picos de `tracemalloc`, no RSS ni un conteo exacto de asignaciones.

Los resultados finales y el procedimiento reproducible se encuentran en
`storage/framework/default-responses-review/README.md`, `RESULTS.md`,
`focused_comparison.json` y los informes complementarios de ese directorio local
de trabajo. El harness conserva
una copia previa del archivo y compara ambas clases en el mismo proceso usando
`Jinja2Engine` y `ViewEnvironment` reales. Estos artefactos de diagnóstico no forman
parte del paquete distribuido.

Se calienta el motor, se alterna el orden de ambas implementaciones y se informa la
mediana por construcción. Las mediciones de memoria usan `tracemalloc` por separado.
No se incluyen DI, middleware, red ni streaming. No es una prueba de carga HTTP ni
una promesa de throughput; cambios pequeños dentro del ruido no se presentan como
ganancias demostradas.

## Validación y límites

- 25/25 pruebas de respuestas predeterminadas, 52/52 del kernel y 5/5 de convenciones.
- 89/89 pruebas de manejo de fallos.
- Suite HTTP completa: 705/706. El único fallo preexistente es la firma de
  `Router.auth`, distinta de la declarada en `IRouter.auth`, en
  `tests/http/routes/test_router_typing.py:44`; no pertenece a estos cambios.
- Ruff sin incidencias en implementación, contrato, kernel y pruebas revisadas.
- SonarPython 5.31.0.36502: seis archivos, 398 reglas activas, cero incidencias y
  cero Security Hotspots. S100 usa el patrón camelCase del proyecto. Se ejecutó
  el analizador local, no un quality gate remoto de SonarQube.
- Casos nuevos: reutilización en el kernel; nombre e idioma cambiantes; render
  suspendido y finalización fuera de orden; aislamiento de errores y excepciones;
  archivos creados, modificados, eliminados o convertidos en directorios; MIME
  conocido; recuperación de selecciones de archivos desaparecidos.

Los comentarios describen los bloques en inglés. Los métodos usan camelCase y
las funciones de módulo snake_case; se conservan los métodos especiales de Python
y la interfaz pública de caché. No se añade caché de errores o tracebacks por
contenido: su cardinalidad y los datos específicos de petición lo desaconsejan.
No se introducen dataclasses, tipos de respuesta alternativos ni desactivaciones
de reglas para obtener mejoras marginales. Las garantías probadas de concurrencia
corresponden a peticiones asíncronas que comparten un servicio; no se afirma soporte
general para mutar su configuración simultáneamente desde múltiples hilos.

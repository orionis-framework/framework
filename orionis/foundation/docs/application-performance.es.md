# Revisión de rendimiento de Application

> Esta revisión inicial se amplió en [Implementación de rendimiento](application-performance-implemented.es.md).

Archivo revisado: `orionis/foundation/application.py`. Validación realizada con
CPython 3.14.3 de 64 bits sobre Windows. Se revisaron también los contratos de
kernel y proveedores, Container, FreezeThaw, FileBasedCache y sus consumidores.

Los cambios priorizan la memoria bajo concurrencia, la inicialización única y las
lecturas de configuración. Los handlers inmediatos evitan abrir el canal de
vigilancia cuando ya terminaron. Cuando el monitor está activo, la gestión HTTP
corregida termina su limpieza antes de devolver el control, con un coste adicional
que se mide por separado. No se afirma una mejora global de requests/s.

## Hallazgos aplicados, por impacto estimado

### Crítico: acumulación ilimitada del cuerpo ASGI

**Problema.** El dispatcher original utilizaba `asyncio.Queue()` sin límite y
seguía llamando a `receive()` independientemente del consumidor. Un upload podía
quedar completo en memoria. Cuando `receive()` entregaba mensajes inmediatamente,
el bucle tampoco cedía la ejecución durante ese drenaje.

**Implementación.** `Queue(maxsize=8)` y `await queue.put(message)` conservan el
orden y detienen la lectura cuando el consumidor se retrasa. Se entrega también
el mensaje terminal antes de cancelar el kernel, para que un kernel que gestione
la cancelación pueda leer `http.disconnect` durante su limpieza.

**CPU, memoria y tiempo.** La memoria del puente pasa de O(N × S) a O(9 × S), con
N fragmentos y S tamaño máximo de fragmento: ocho mensajes en cola y uno pendiente
en el productor. Con C conexiones, O(C × N × S) pasa a O(C × 9 × S). El kernel y el
servidor pueden tener buffers adicionales; no es un límite del tamaño total del
request. Se reduce el trabajo adelantado y se permite ejecutar otras tareas al
llenarse la cola. El benchmark de 1.000 fragmentos distintos de 64 KiB redujo el
pico de memoria trazada aproximadamente un 99,1 %.

**Trade-off.** Una cola acotada introduce esperas cuando todos los fragmentos ya
están disponibles. Se eligieron ocho posiciones para amortizar ese coste; una
cola de una posición produjo más cambios de tarea en la exploración. La
desconexión no se procesa hasta que pueden entregarse los mensajes anteriores:
no se descarta el cuerpo para buscar una desconexión. La especificación define
ambos eventos sobre el mismo canal `receive`.
[Especificación HTTP de ASGI](https://asgi.readthedocs.io/en/stable/specs/www.html).

**Validación.** Orden de fragmentos, avance de lectura limitado a capacidad + 1,
desconexión y lectura cooperativa del mensaje terminal.

### Alto: inicialización de kernels repetida bajo concurrencia

**Problema.** Comprobar el handler cacheado antes de `await build()/boot()` permitía
que varias primeras peticiones construyeran y arrancaran el mismo kernel. CLI
presentaba el mismo patrón. Podían duplicarse rutas, middleware y otras tareas de
arranque.

**Implementación.** Locks de `asyncio` para HTTP y CLI, con segunda comprobación
dentro del lock. HTTP publica ambos handlers después de completar `boot()`.
Las peticiones siguientes acceden directamente al handler, sin adquirir el lock.
CLI comprueba el resultado de `boot()` con `inspect.isawaitable`, por lo que también
espera wrappers síncronos que devuelven una corrutina.

**CPU, memoria y tiempo.** En una ráfaga de C primeras peticiones, las construcciones
y boots pasan de hasta C a una: O(C × coste_boot) pasa a O(coste_boot + C). Se añaden
dos locks por aplicación; los waiters de arranque se liberan al terminar. La ruta
caliente conserva O(1) de acceso al handler.

**Trade-off.** Las primeras peticiones esperan el mismo arranque. La garantía es
entre tareas de un worker y un event loop; no convierte el singleton ni su
configuración mutable en estructuras seguras entre hilos. Tras un fallo se permite
reintentar; los efectos externos parciales de `boot()` no se revierten.

**Validación.** Ocho primeras peticiones, combinación ASGI/RSGI, publicación tras
boot, error y cancelación durante inicialización, comandos concurrentes y boot CLI
síncrono o awaitable.

### Alto: tareas pendientes, errores de transporte y cancelación externa

**Problema.** Los monitores se cancelaban sin esperarlos; sus errores podían quedar
sin recuperar. Un error de `receive()` podía dejar al handler esperando para
siempre. Ambos protocolos absorbían `CancelledError`, incluyendo cancelaciones
del servidor y timeouts.

**Implementación.** `_await_http_tasks` coordina el handler y el monitor, espera su
limpieza y distingue la desconexión de la cancelación del padre y del propio
kernel. Los monitores cancelan el handler y vuelven a lanzar cuando falla o se
cancela el transporte. ASGI utiliza `queue.get` directamente: se retiraron el
Future de desconexión, dos closures, sus celdas y la corrutina receptora intermedia.
Los monitores comprueban si el kernel ya terminó antes de abrir `receive()` o
`client_disconnect()`: una respuesta inmediata evita crear y cancelar el awaitable
de transporte y su correspondiente espera de limpieza.

**CPU, memoria y tiempo.** Se evita retener tareas y recursos más allá del request,
así como esperas indefinidas ante fallos de transporte. Cada lectura de cuerpo
elimina una corrutina intermedia. El helper compartido añade una corrutina por
request; RSGI añade un wrapper de vigilancia. Esperar la limpieza añade latencia
observable en un kernel sin trabajo: las mediciones aparecen más abajo.

**Trade-off.** Hay más coordinación explícita que en un `cancel()` sin espera.
Se mantienen las dos tareas para aislar la cancelación del handler de la del
servidor. Si el kernel ya terminó, no se consulta un canal de transporte que ya
no necesita supervisión. No se fuerza `eager_start`, aunque se prueba con la factoría
eager de Python. Propagar cancelaciones externas mantiene el funcionamiento de
timeouts y concurrencia estructurada.
[Cancelación en asyncio 3.14](https://docs.python.org/3.14/library/asyncio-task.html#task-cancellation).

**Validación.** Fallos síncronos y asíncronos del transporte, Future cancelado,
autocancelación del kernel, cancelación externa durante limpieza, carreras con
desconexión, ausencia de tareas pendientes y factoría eager.

### Alto: startup concurrente de proveedores incompleto

**Problema.** `popleft()` retiraba el proveedor antes de esperar `boot()`. Otro
startup podía ver la cola vacía mientras ese boot seguía ejecutándose; además,
un fallo o cancelación perdía el proveedor pendiente.

**Implementación.** Un lock coordina el drenaje; se espera `pending[0].boot()` y
solo después se retira el elemento. Se conserva el orden de registro.

**CPU, memoria y tiempo.** Cada proveedor completado arranca una vez y los
consumidores esperan a que sus servicios estén listos. O(P) para P proveedores,
un lock adicional por aplicación y sin copias de la cola. No añade trabajo al
dispatch de cada petición.

**Trade-off.** El startup es secuencial y los boots fallidos quedan pendientes de
reintento. Los proveedores deben tolerar ese reintento si dejaron efectos parciales.

**Validación.** Dos startups concurrentes, orden de boot, fallos y cancelaciones
seguidos de reintento.

### Medio: separación y búsquedas repetidas en config()

**Problema.** Cada lectura repetía `split('.')`, asignaba una lista y los segmentos,
y consultaba cada diccionario con `in` y después `[]`. La escritura creaba además
una sección de la lista de claves.

**Implementación.** Caché por aplicación de hasta 256 tuplas de segmentos. Al
llenarse se vacía antes de guardar una nueva clave. La lectura usa `dict.get` y
la escritura recorre los segmentos con un iterador, sin crear una sección.
Se cachean exclusivamente las rutas; los valores se consultan siempre.

**CPU, memoria y tiempo.** Una lectura caliente elimina `split` y sus asignaciones.
La complejidad sigue siendo O(D), con D niveles de diccionarios; desaparece el
trabajo O(L) de separar una clave de longitud L en cada acceso repetido. La caché
retiene como máximo 256 claves y sus segmentos, no valores de configuración.

**Trade-off.** Las claves nuevas pagan la creación de una tupla y una entrada.
Un flujo con más de 256 claves distintas puede renovar la caché con frecuencia.
El límite es de entradas, no de bytes. No se cachean referencias a subdiccionarios:
se preservan las mutaciones mediante `config()` y `config('seccion')`.

**Validación.** Valores falsy, claves ausentes o vacías, sustitución de padres
escalares, mutación directa, reset y 600 claves distintas.

### Medio en arranque: introspección completa de la pila

**Problema.** `inspect.stack()[1].filename` construía información de todos los
frames y podía buscar contexto de código fuente para obtener un solo filename.

**Implementación.** `sys._getframe(1).f_code.co_filename`; fallback a
`inspect.stack(context=0)` cuando no existe `_getframe`.

**CPU, memoria y tiempo.** De recorrer O(F) frames y crear sus registros a consultar
un frame a profundidad constante, O(1). No se retiene el frame. La mejora pertenece
al arranque; `create()` ya era idempotente y no se ejecuta por request.

**Trade-off.** `_getframe` es específico de implementaciones que lo proporcionen;
el fallback mantiene la alternativa disponible.
[Documentación de sys._getframe](https://docs.python.org/3.14/library/sys.html#sys._getframe).

### Medio en arranque: copia integral antes de persistir

**Problema.** `__persistCompiledState()` hacía `deepcopy` del bootstrap antes de
pasarlo a `FileBasedCache.save()`, que ya lo serializa de forma síncrona y no lo muta.

**Implementación.** Se pasa el bootstrap directamente a `save()`.

**CPU, memoria y tiempo.** Desaparece un recorrido O(N) y un grafo temporal de
tamaño O(N). La serialización y la escritura siguen siendo necesarias; no se
atribuye una aceleración medida al tiempo total de persistencia.

**Trade-off.** Se depende del contrato actual de `FileBasedCache.save`: no mutar
ni retener el dato para serializarlo después. Se conserva el deepcopy de la
configuración personalizada, que sí proporciona aislamiento de hojas arbitrarias.

**Validación.** Persistencia con el driver real y lectura del contenido guardado.

### Bajo: asignaciones y trabajo redundante de bootstrap

- `withConfigPaths()` recorre `CORE_APP_PATHS` directamente: elimina el thaw de un
  mapping de strings, el conjunto duplicado de nombres y un `resolve()` de la raíz
  ya resuelta. Conserva las reglas diferentes de resolución para `str` y `Path`.
- El registro eager actualiza el `OrderedDict` y mueve la entrada al principio sin
  borrarla antes. Se conserva `OrderedDict`: `move_to_end(last=False)` es necesario
  para mantener esa prioridad con coste O(1).
- `routingPaths()` usa pertenencia sobre un literal que CPython compila como
  frozenset constante, eliminando el set temporal de cada llamada.
- `FileBasedCache` crea su directorio; se retira el `exists()/mkdir()` duplicado de
  Application. Se elimina la rama `compiled=False`, que no tenía ningún llamador,
  y el wrapper de registro eager que solo reenviaba una llamada.
- Se corrigen anotaciones de las clases cacheadas de scheduler y exception handler,
  la documentación del descubrimiento de proveedores y el helper de merge.

El impacto individual es pequeño y se concentra en el arranque. Las validaciones
externas se mantienen; las simplificaciones reducen estructuras duplicadas y no
introducen un nuevo modelo de configuración. Las pruebas verifican prioridad de
proveedores, paths, aislamiento de routing y persistencia.

## Decisiones de alcance y compatibilidad

No se añaden slots a Application: Container ya proporciona `__dict__` y se trata
de un singleton por clase. Cambiar toda la jerarquía tiene poco beneficio aquí y
puede romper extensiones. No se sustituye `asdict` por una conversión superficial,
ni se cachean instancias de exception handlers o schedulers que el contenedor debe
construir respetando sus dependencias. `ModuleInspector` ya cachea clases; duplicar
esa caché en todos los accesores añade estado con escaso beneficio demostrado.

Los métodos internos con nombres especiales inventados se renombraron a
`__asgiLifespan`, `__handleHttpAsgi` y `__handleHttpRsgi`. Se conservan `__init__`,
`__call__`, `__rsgi__`, `__rsgi_init__` y `__rsgi_del__` porque son hooks de Python
o del servidor. Renombrarlos rompería el protocolo.

Todas las funciones y métodos del archivo y de los nuevos tests/benchmarks tienen
documentación NumPy. Los comentarios del código describen acciones en inglés.

## Medición y validación

Los scripts reproducibles están en
`tests/foundation/benchmark_application.py` y
`tests/foundation/benchmark_application_async.py`.
El primero compara el algoritmo anterior de lectura con Application actual y
mide la consulta del filename. El segundo extrae por AST las funciones reales de
dispatch de ambos archivos, con kernels ya cacheados y transportes sintéticos.
No incluye red, routing, middleware, base de datos ni arranque del framework.

Baseline HTTP: `application.py` del commit
`3ab30995a86a038a15f24c1f5e636e30e14ed8dd`. Los resultados completos están en
`tests/foundation/benchmark_application_results.json` y
`tests/foundation/benchmark_application_async_results.json`.

| Escenario | Antes | Después | Diferencia observada |
| --- | ---: | ---: | ---: |
| `config('app.debug')` | 496 ns | 397 ns | −20,0 % tiempo |
| Configuración de cuatro niveles | 782 ns | 476 ns | −39,2 % tiempo |
| `config('missing.key')` | 319 ns | 353 ns | +10,9 % tiempo |
| ASGI, kernel inmediato | 21,591 µs/request | 14,339 µs/request | −33,6 % tiempo |
| RSGI, kernel inmediato | 16,928 µs/request | 10,593 µs/request | −37,4 % tiempo |
| ASGI, kernel que suspende una vez | 27,861 µs/request | 32,318 µs/request | +16,0 % tiempo |
| RSGI, kernel que suspende una vez | 21,261 µs/request | 26,878 µs/request | +26,4 % tiempo |
| ASGI, fragmentos disponibles inmediatamente | 1,301 µs/fragmento | 2,494 µs/fragmento | +91,7 % tiempo |
| Pico trazado, upload sin consumidor | 65.754.880 B | 596.841 B | −99,09 % memoria |
| Llamadas receive sin consumidor | 1.001 | 9 | Lectura acotada |
| Obtener filename del caller | 5,951 ms | 64 ns | Operación de arranque aislada |

Configuración: mínimo de cinco repeticiones de 500.000 llamadas por clave;
filename: cinco repeticiones de 100 llamadas. HTTP: medianas de 15 muestras de
20.000 requests por variante/protocolo/escenario, variantes alternadas y GC
pausado durante la medición. El escenario suspendido hace exactamente un
`await asyncio.sleep(0)`; el escenario de cuerpo consume 1.000 mensajes listos.
La memoria usa `tracemalloc` con 1.000 objetos `bytes` distintos de 64 KiB.

El host presentó variabilidad considerable entre muestras, visible en los JSON.
Estas cifras describen microbenchmarks locales, no latencias de producción ni un
ensayo de carga sobre Granian. Las mejoras de memoria y el número de boots tienen
además una justificación estructural. El coste del buffer limitado y de esperar
la limpieza aparece explícitamente: no se ocultan las regresiones de los escenarios
suspendidos, cuerpos ya disponibles o claves ausentes.

Comandos desde la raíz del repositorio, usando las dependencias ya instaladas:

```powershell
$env:PYTHONPATH = (Resolve-Path .venv/Lib/site-packages).Path
$env:PYTHONIOENCODING = 'utf-8'
python -m tests.foundation.benchmark_application
git show 3ab30995a86a038a15f24c1f5e636e30e14ed8dd:orionis/foundation/application.py |
    Set-Content -Encoding utf8 "$env:TEMP/orionis_application_before.py"
python tests/foundation/benchmark_application_async.py --baseline "$env:TEMP/orionis_application_before.py" --samples 15 --requests 20000

python reactor test --start-dir=tests/foundation --verbosity=1
python reactor test --start-dir=tests/http --verbosity=1
python reactor test --start-dir=tests/container --verbosity=1
python reactor test --start-dir=tests/console --verbosity=1
./.venv/Scripts/ruff.exe check orionis/foundation/application.py tests/foundation/test_application*.py tests/foundation/benchmark_application*.py
```

Se usó `C:\Python\Python314\python.exe` porque el ejecutable de `.venv` fallaba
con `uv trampoline failed ... permission denied`. Las dependencias se tomaron
de `.venv/Lib/site-packages`; no se instalaron ni actualizaron paquetes.

**Validación final:** 2.137 pruebas aprobadas: foundation 117/117, HTTP 715/715,
container 231/231 y console 1.074/1.074. Se añadieron 47 pruebas: 28 de HTTP y
lifespan, 12 de configuración/bootstrap y 7 de CLI/proveedores. Ruff no reportó
errores en el código revisado ni en los tests/benchmarks añadidos. Una inspección
AST verificó nombres y secciones NumPy en 195 funciones/métodos de esos archivos.

El entorno no dispone de `sonar-scanner` ni de configuración de análisis SonarQube:
no se afirma haber ejecutado o aprobado ese quality gate. La comprobación de Ruff
es del alcance modificado, no de los cambios ajenos que ya existían en el workspace.

# Implementación de rendimiento de Application

Fecha: 2026-09-28. Python mínimo: 3.14; validación local con CPython 3.14.3 en Windows.

Este documento actualiza el [informe de diagnóstico](application-optimization-decision.es.md)
después de implementar sus hallazgos. Los JSON originales se conservan como
evidencia histórica; los resultados nuevos llevan el sufijo `_after.json`.

Se eliminaron tareas auxiliares del despacho HTTP predeterminado, retención de
controladores en cachés de introspección, contención scoped entre peticiones,
reflexión repetida, imports anticipados y materializaciones evitables. Se conservan
aislamiento por petición, seguridad HTTP y extensiones públicas. No existe una
garantía técnica de «máximo posible» ni de superar cualquier framework/carga.

## Cambios por impacto

| ID / impacto | Problema y cambio aplicado | CPU, memoria y complejidad | Coste de mantenimiento / contrato |
|---|---|---|---|
| C1 / crítico | Las claves de introspección incluían métodos ligados y retenían el controlador. Se normalizan a función y modo de binding. | De un miss por controlador a un miss por función; evita retener hasta 1.024 receptores por caché. Hits O(1) amortizado. | Distinguir instancia, clase, método estático y firmas personalizadas; pruebas de retención y binding. |
| A1 / alto | `Container.invoke/call/build` reconstruían wrappers y revisaban si el callable era async. Usan planes inmutables con slots y parámetros precompilados. | En caliente no hay wrappers de reflexión ni `inspect.iscoroutinefunction`; parámetros en tupla, consumo por índice y sin segunda copia de kwargs. Resolver P parámetros sigue siendo O(P). | Los planes guardan metadatos, no servicios: overrides y scopes se consultan al ejecutar. Mutaciones in-place de firmas/anotaciones requieren invalidación o reinicio; reemplazar métodos/constructores selecciona otro plan. |
| A2 / alto | Dos tareas y una cola por request para vigilancia universal. El modo predeterminado hace `await handler(...)` en la tarea del servidor. | Cero tareas auxiliares, cero cola y cero lectura adelantada en modo directo. Evita coordinación y copia de ContextVars en tareas propias. | La desconexión de un cliente mientras el handler espera otra operación no implica cancelación proactiva. El modo vigilado sigue disponible; cancelación externa del servidor se conserva. |
| A3 / alto condicional | Un lock global por contrato serializaba la construcción en scopes independientes. Los locks scoped pertenecen al scope. | Esperas independientes pueden solaparse: con N scopes y una espera de duración T, de aproximadamente N×T a T, sujeto al servidor/backend. | Una instancia por scope sigue garantizada; los singletons conservan coordinación global. |
| A3 / alto condicional | Un provider diferido con varios contratos podía coordinarse por contrato en vez de por provider. Se coordina por identidad del provider y readiness. | Registro/boot únicos y reutilizables; evita trabajo duplicado y carreras. | Hay estado de registro y boot separado para reintentar tras error/cancelación sin registrar dos veces. |
| A4 / alto según carga | Rutas sin estado pagaban sesión/identidad automáticas. `.public()` y grupos `public=True` permiten omitirlas explícitamente. | Elimina resolución de guard, lectura/escritura de sesión y middleware automático en esas rutas. La ganancia depende especialmente del backend de sesión. | Omite sesión, CSRF e identidad automáticas; no corresponde a formularios autenticados mediante cookies. Conserva middleware explícitos de aplicación/grupo/ruta y controles globales. |
| A4 / alto con almacenamiento remoto | Sesiones limpias se escribían y emitían cookie en cada respuesta; navegación podía ensuciarlas. Se añaden `renewal_interval` y `track_previous_url`. | Con intervalo positivo, una sesión escalar limpia evita escritura/cookie antes de su deadline. Sigue leyendo el store por request. | Opt-in: por defecto intervalo 0 y tracking activado. Mutables, flash, cambios, sesiones nuevas y rotaciones se persisten. TTL/cookie se renuevan juntos por intervalos. |
| M1 / medio | Headers se copiaban/decodificaban/indexaban y luego recorrían otra vez por seguridad. Se construyen y comprueban en un recorrido. | O(H) sigue siendo necesario; se evita lista intermedia de pares decodificados y recorrido extra. Valores simples son strings, con lista solo para duplicados. | El objeto copia la entrada y mantiene orden, duplicados, Latin-1 y validación CR/LF/Host. |
| M2 / medio | `Request` materializaba `BodyStream` y scope de transporte aunque no se usaran. Ahora se crean al primer acceso. | Un GET sin lectura evita el stream; RSGI puede evitar el diccionario completo de scope. | Se mantiene Request y scope DI por petición: son parte del contrato de facades, middleware y servicios scoped. |
| M3 / medio | Una pila vacía o de una capa usaba el pipeline genérico. Se especializan ambos casos. | Vacío: cero objeto pipeline. Una capa: continuación ligera. | Multicapa usa continuación fija por capa para impedir que llamadas concurrentes a `next()` salten middleware suspendido; añade estado frente al algoritmo anterior inseguro. No se promete aceleración multicapa. |
| M4 / medio condicionado | Respuestas constantes repetían validación/codificación. `ResponseTemplate` conserva bytes/headers inmutables y crea una Response independiente. | Codificación del contenido fuera del request y metadatos compartidos. Headers individuales no requieren una lista propia hasta exponerla o duplicarlos. | Cookies, flash, background y headers mutables nunca se comparten entre respuestas. Mutar headers invalida la representación codificada; exponer `getHeader()` desactiva su caché para seguir observando cambios. |
| M5 / alto en arranque y memoria | Importar Application arrastraba subsistemas completos mediante exports y metadatos construidos con imports. Ahora 13 paquetes resuelven exports bajo demanda y la metadata almacena nombres de módulos/clases. | Importar Application pasa de 1.603 a 313 módulos nuevos y de 68,88 a 13,02 MB vivos trazados. `create()`/lifespan aún cargan capacidades que necesitan realmente. | Se conservan import público, identidad, `__all__` y `dir()`. Inspeccionar solo `vars(package)` antes del primer acceso deja de enumerar exports aún no materializados. |
| M6 / medio en primera petición | El kernel HTTP se cargaba después de readiness. Se inicializa durante startup, después de callbacks y antes de confirmar readiness. | Desplaza construcción del kernel/router/middleware al arranque; primeras peticiones concurrentes no duplican el boot. | Lifespan tarda más y comunica errores de configuración antes. Sin lifespan se conserva inicialización lazy con lock y retry. RSGI registra su interfaz correcta. |
| M7 / medio/bajo en arranque | Se descongelaban/copias adicionales de defaults ya nuevos. Se obtiene una configuración anidada nueva y solo se copia su contenedor exterior para merge. | Evita una pasada recursiva sobre defaults y la copia previa a serializar la caché compilada. | Se mantiene separación entre configuración bootstrap inmutable y configuración runtime mutable; reset conserva su contrato. |
| B1 / bajo acumulado | Coroutines de background sin trabajo, accesos repetidos y contenedores temporales. Se eliminan rutas vacías y estructuras redundantes. | Una coroutine menos por respuesta sin background cuando usa la implementación base. | Overrides de `runBackground()` se siguen ejecutando, incluso con `background=None`. |

## Qué se carga una vez y qué se crea por petición

Durante readiness, `__preloadHandlers()` prepara también los planes de funciones,
constructores y métodos ordinarios, estáticos y de clase. No construye controladores
ni resuelve servicios. Descriptores personalizados permanecen lazy para no ejecutar
getters durante el arranque; firmas ordinarias inválidas fallan antes de publicar
las tablas de dispatch. La capacidad LRU limita cuántos planes permanecen calientes.

Se reutilizan la configuración comprometida, registro de providers, singletons,
handlers ASGI/RSGI, router compilado, funciones/clases de handlers, instancias de
middleware y planes de invocación. Las cuatro cachés de metadatos están acotadas
a 1.024 entradas cada una; no conservan métodos ligados a controladores de una
petición. La caché de rutas/configuración también conserva límites explícitos.

Cada petición conserva su scope DI, adapter, Request, estado mutable de respuesta
y controlador transitorio cuando corresponde. Los objetos de cuerpo/scope de
transporte se materializan solamente si un consumidor los solicita. No se cambia
la vida útil de controladores a singleton para mejorar cifras artificialmente.

Los providers con facades síncronas, como Reactor/Schedule/View, conservan su
registro/pinning compatible. Diferirlos sin cambiar la API podría transformar una
llamada síncrona en un awaitable. Los imports diferidos reducen el coste anterior a
`create()`; no equivalen a eliminar esas capacidades durante el arranque completo.

## Política de desconexión

`http.monitor_disconnects` vale `False` por defecto y se captura en `create()`.
Configúralo en la entidad HTTP de la aplicación antes de crearla; por ejemplo,
añade este campo a `BootstrapHTTP` en `config/http.py` para conservar vigilancia:

```python
monitor_disconnects: bool = True
```

Cambiar el diccionario runtime después de `create()` no recompila esta política.
Si se utiliza configuración compilada, hay que regenerarla al cambiar opciones
o actualizar el framework. Los snapshots antiguos sin el campo usan modo directo.

El modo vigilado conserva cola ASGI acotada a ocho mensajes y hasta un mensaje
adicional en el dispatcher. Si el handler no consume cuerpo y la cola se llena,
la detección de desconexión se detiene hasta que vuelva a avanzar la lectura.
No es una garantía absoluta de detectar inmediatamente toda desconexión.

Con el loop nativo sin factory personalizada, el handler vigilado empieza eager:
si termina sin suspenderse, no se abre monitor. Otros loops/factories reciben
`create_task(coroutine)` sin opciones incompatibles. Esto incluye loops cuya API
no admite `eager_start`; se conserva su propia política de scheduling.

## Rutas y sesiones opcionales

La [documentación HTTP](../../http/docs/performance.es.md) contiene ejemplos de
`.public()`, grupos públicos y `ResponseTemplate`. No se marca ninguna ruta de la
aplicación como pública automáticamente.

En la entidad de `config/session.py` pueden declararse, por ejemplo:

```python
track_previous_url: bool = False
renewal_interval: int = 60
```

El intervalo se expresa en segundos; `lifetime` sigue en minutos. El intervalo
debe ser estrictamente menor que la vida de sesión: la igualdad se rechaza porque
programaría la renovación cuando el registro ya expiró. El valor 0 conserva
renovación en cada respuesta.

El ahorro tiene un coste semántico explícito: el tiempo efectivo de inactividad
puede reducirse hasta el intervalo de renovación. `expire_on_close` sigue
omitiendo Max-Age. Una lectura del store por request sigue detectando expiración
y revocación; no se añade una caché local de identidad que sobreviva al logout.
Cuando no hay persistencia tampoco se emite una nueva cookie.

Una sesión con listas/dicts u otros valores mutables conserva persistencia
conservadora: cambios hechos mediante referencias obtenidas por `get()` no
siempre marcan `dirty`. Evitar escrituras en esos casos requeriría snapshots o un
contrato de mutación distinto. No se introdujo ese coste ni esa incompatibilidad.

## Evidencia reproducible

Los archivos de evidencia están en `tests/foundation/benchmark_application_*_after.json`.

Pipeline ASGI precargado, 11 muestras de 10.000 requests por variante. Medianas
en microsegundos por finalización; el rango es mínimo–máximo de las medias de
lote de Orionis directo, no percentiles de latencia:

| Caso | Orionis directo | Rango Orionis | Orionis vigilado | Starlette 1.3.1 | FastAPI 0.139.2 |
|---|---:|---:|---:|---:|---:|
| Función / Response nueva | 11,71 | 9,39–16,29 | 14,86 | 9,57 | 33,57 |
| Controlador transitorio | 13,93 | 12,96–23,52 | 19,70 | 13,70 | 32,59 |
| Función / ResponseTemplate | 10,90 | 9,95–26,12 | 14,17 | 11,57 | 37,52 |

En la fila de template, Orionis usa explícitamente `ResponseTemplate.make()`;
los otros frameworks siguen construyendo Response. La respuesta emitida es
idéntica, pero no se pretende que todos usen la mejor técnica posible para
contenido constante. La dispersión y el cambio de orden entre muestras impiden
atribuir los 0,81 µs entre dos filas exclusivamente a la plantilla.

La función normal sigue por detrás de Starlette y por delante de FastAPI en
este escenario. La diferencia pequeña de la fila de template no prueba una
superioridad general sobre Starlette. El benchmark anterior conservado mostró
variación importante del host, por lo que no se presenta una aceleración causal
de múltiples veces usando cifras históricas frente a estas nuevas.

Orquestación aislada con handlers sintéticos, 11×3.000 requests, concurrencia 1:

| Protocolo / comportamiento | Directo, µs | Vigilado nativo eager, µs |
|---|---:|---:|
| ASGI inmediato | 0,371 | 1,953 |
| ASGI con una suspensión | 2,124 | 7,036 |
| RSGI inmediato | 0,241 | 0,890 |
| RSGI con una suspensión | 2,028 | 5,663 |

Directo crea **0 tareas auxiliares**. Vigilado nativo crea **1** si el handler
termina eager y **2** si se suspende; factories/loops alternativos pueden crear
ambas también en el caso inmediato. Con cuerpo sintético sin consumir, directo
realiza **0 lecturas**, pico trazado **2.144 bytes**; vigilado realiza **9 lecturas**,
pico **597.169 bytes**. Esto mide buffers/tareas de Application, no toda la memoria
del servidor ni del request. El JSON incluye concurrencia 32 y todos los lotes.

DI aislada, 7×5.000: construir controlador e invocarlo registra mediana **2,80 µs**;
invocar función, **1,56 µs**. No son cifras de una petición HTTP completa.

La retención y la concurrencia tienen controles deterministas independientes del
reloj: 1.100 controladores creados, cero vivos tras GC y un miss/1.099 hits del
cache resuelto; dos scopes distintos pueden entrar a construcción antes de que
se libere cualquiera, mientras un scope compartido y un singleton construyen
una sola instancia.

En el experimento de construcción suspendida de 10 ms, ocho scopes completan
en aproximadamente 15,43 ms, frente a 124,06 ms del diagnóstico histórico. Es una
demostración de eliminación de serialización, no una predicción de throughput
para constructores síncronos sin I/O.

El benchmark de imports ejecuta procesos nuevos y mide importación, no proceso
completo, `create()` o readiness. Baseline de esta implementación: mediana
928,58 ms; medición posterior: 118,62 ms. Caches del sistema operativo no se
vacían. Memoria: asignaciones Python trazadas, no RSS.

Los benchmarks HTTP están en memoria, con kernel, container y router reales,
sin servidor/red, sin sesión/autenticación y con respuestas iguales verificadas.
Orionis conserva scope DI y controles globales. Los competidores crean sus
controladores explícitamente y FastAPI devuelve Response sin validación de
modelo. No son cargas equivalentes en capacidades, ni miden p95/p99 o RPS de red.
Las muestras se intercalan entre variantes; no se deben convertir diferencias
con JSON históricos en porcentajes causales porque hubo deriva considerable del
host. Se conservan todas las muestras, versiones y hashes.

## Validación y límites

Se añadieron regresiones para retención de controladores, planes/bindings,
concurrencia scoped y deferred, lifecycle/readiness, dispatch directo y vigilado,
loops/factories alternativos, headers, cuerpo lazy, pipelines concurrentes,
plantillas, background overrides, rutas públicas y renovación de sesiones.

La suite completa pasó **7.730/7.730**. Después del ajuste final de precarga y del
límite estricto de renovación, se verificaron **733/733 HTTP** (incluye cuatro
pruebas nuevas de precarga), **135/135 foundation**, **193/193 Mail**, **9/9 de
renovación** y **39/39 de configuración**. La suite session había pasado **256/256**.
Ruff se ejecutó sobre **todo `orionis` y `tests`**, sin errores. `git diff --check`
también pasó; las advertencias de normalización LF/CRLF no son errores de lint.

Las fixtures de integración de Mail conservan el `PYTHONPATH` heredado en sus
subprocesos. Esto corrigió dos fallos del entorno de pruebas, que descartaba las
dependencias de `.venv`. Se ajustaron inspecciones de exports para `dir/getattr`
y once hallazgos de lint preexistentes en pruebas ajenas al camino HTTP.

`IApplication` y `Application` conservan firmas públicas coherentes. `isBooted`
documenta que significa finalización de `create()` y registro de providers;
readiness HTTP y boot async ocurren en lifespan. Los métodos conservan camelCase
y los hooks de protocolo conservan sus nombres obligatorios. Funciones externas
usan snake_case; documentación NumPy y comentarios de código en inglés.

No hay instalación disponible de SonarScanner/SonarQube en este entorno. Se
ejecutan Ruff y pruebas, pero no se afirma que un Quality Gate remoto no ejecutado
haya aprobado. Tampoco se han medido aún Linux/uvloop, RSGI sobre sockets,
latencias percentiles bajo saturación o cargas con base de datos real.

## Reproducción local

```powershell
$env:PYTHONPATH = (Resolve-Path .venv/Lib/site-packages).Path
$env:PYTHONIOENCODING = 'utf-8'
python -B reactor test --start-dir=tests --verbosity=1
python -m ruff check orionis tests
python -B tests/foundation/benchmark_application_monitor.py --samples 11 --requests 3000 --output tests/foundation/benchmark_application_monitor_after.json
python -B tests/foundation/benchmark_application_stack.py --samples 11 --requests 10000 --profile --output tests/foundation/benchmark_application_stack_after.json
python -B tests/foundation/benchmark_application_di.py --samples 7 --iterations 5000 --output tests/foundation/benchmark_application_di_after.json
python -B tests/foundation/benchmark_application_scoped.py --output tests/foundation/benchmark_application_scoped_after.json
python -B tests/foundation/benchmark_application_imports.py --output tests/foundation/benchmark_application_imports_after.json
```

Ejecutar las mediciones secuencialmente, sin suites de pruebas simultáneas. El
benchmark de stack rota escenarios y variantes entre muestras; el de vigilancia
cuenta tareas sin instalar una task factory que altere la política eager observada.

# Application: análisis y decisiones de rendimiento

> Documento histórico de diagnóstico. Los cambios autorizados posteriormente y
> su validación están en [Implementación de rendimiento](application-performance-implemented.es.md).

Fecha: 2026-09-28. Python mínimo del repositorio: 3.14.

Estado: **diagnóstico para decidir cambios; no se modificó código de producción en esta fase**.
Se añadieron experimentos reproducibles, sus resultados y este informe. Las variantes
sin vigilancia y con ejecución eager existen únicamente dentro de los benchmarks.
El workspace contiene cambios anteriores; esta evaluación toma como referencia su estado actual.

## 1. Conclusión para decidir

Hay margen importante, pero quitar únicamente la tarea de vigilancia no basta para
afirmar que Orionis será más rápido que Starlette o FastAPI. El trabajo prioritario es:

1. Corregir el cacheo de firmas de métodos ligados: repite introspección y retiene
   controladores de peticiones terminadas. Está demostrado mediante contadores y referencias débiles.
2. Preparar planes de invocación por ruta para evitar interpretar dependencias y
   comprobar el tipo de callable en cada petición.
3. Decidir explícitamente qué rutas requieren cancelación proactiva por desconexión.
   La política actual introduce dos tareas adicionales por petición y una cola en ASGI.
4. Permitir perfiles públicos sin sesión ni resolución automática de identidad,
   manteniendo esas prestaciones en las rutas que las necesitan.
5. Evitar que construcciones scoped de peticiones distintas compartan un lock cuando
   pueden suspender. La serialización se confirmó con una construcción instrumentada.

Separar además un proyecto de **arranque y memoria por worker**: importaciones,
providers y servicios CLI cargados durante HTTP. Sus ahorros no se deben presentar
como mejoras directas del throughput de peticiones calientes.

No existe evidencia aquí que permita prometer una ventaja global de requests/s.
Se midió despacho aislado y un pipeline HTTP real ensamblado en memoria; falta la
validación de servidor, red, carga sostenida y prestaciones equivalentes.

## 2. Alcance y fuerza de la evidencia

Se revisaron Application y su contrato, KernelHTTP, Container, introspección,
router, middleware, Request, respuestas, adaptadores ASGI/RSGI, providers,
sesión e identidad. Las líneas citadas corresponden al workspace evaluado.

- **D — demostrado estructuralmente:** conteos de tareas, hits/misses, referencias
  retenidas y coordinación por eventos. No depende de una diferencia pequeña de reloj.
- **M — medido localmente:** medianas y muestras crudas. El equipo Windows presenta
  variación; son observaciones de estos escenarios, no predicciones de producción.
- **H — hipótesis:** cambio concreto sustentado por el código, pendiente de prototipo
  y benchmark. No se asigna un porcentaje de mejora inventado.

Los benchmarks finales se ejecutan secuencialmente para evitar competir entre sí.
Los tiempos de los experimentos preliminares de conversaciones anteriores no se
mezclan con esta nueva tanda. Un `await` puede completarse sin suspender; el caso
`yield_once` fuerza una suspensión mediante `asyncio.sleep(0)` y no simula una base de datos.

## 3. Qué se carga y qué se reutiliza

| Elemento | Vida útil y reutilización actual | Trabajo que queda en cada petición |
|---|---|---|
| Application/Container | Una instancia por clase y proceso; `container.py:65`, `application.py:792` | Lookup de handlers cacheados |
| Bootstrap, configuración y paths | `create()` una vez; `application.py:2652` | `config()` solo cuando un consumidor lo pide |
| Cache compilado de bootstrap | Datos/configuración/metadata; `application.py:1273` | No contiene un kernel ni instancias DI ya construidas |
| Imports Python | `sys.modules` reutiliza módulos | No se reimporta todo el framework por request |
| Providers | Registro en create, boot async durante lifespan; `application.py:1692`, `:1718` | Deferred pendiente solo al resolverlo; hit posterior reutilizado |
| Kernel HTTP y métodos ligados | Primera petición HTTP; `application.py:471` | No se adquiere lock de inicialización en un hit |
| Rutas/callables | Carga, regex e índices durante boot; `http/kernel.py:202`, `:282` | Resolución de ruta y despacho |
| Middleware/adaptadores de respuesta | Construidos durante boot; `http/kernel.py:218`, `:487` | Ejecución y estado del pipeline por request |
| Servicios singleton | Primera resolución/pin; `container.py:918` | Lookup sin lock tras hit |
| Servicios scoped | Una instancia por contrato dentro de cada scope | Un nuevo scope y sus instancias en cada request |
| Firmas DI de funciones estables | LRU de metadata | Todavía wrappers, checks y ensamblaje de argumentos |
| Firmas de controladores transitorios | Cache keyed por método ligado a instancia nueva | Miss repetido y retención: hallazgo C1 |
| Config paths | Hasta 256 claves partidas cacheadas; `application.py:2780` | Navegar la estructura mutable; valores no memoizados |
| Request | Query, cookies, URL y payload diferidos/cacheados por request | Adapter, BodyStream, Request y bindings iniciales |
| Respuesta | Nueva por handler, normalmente | Headers, serialización cuando corresponda y envío |

La reutilización es por worker/proceso; no convierte objetos mutables en seguros
entre hilos o event loops. En particular, middleware compartido debe conservar
sus datos específicos de petición en el request/scope, no en la instancia global.

### Ruta caliente actual

```text
Tarea del servidor
  Application.__call__ / __rsgi__
    handler cacheado
    Task del kernel + Task de vigilancia
    ASGI: Queue(8) + dispatcher dueño del receive
      KernelHTTP
        adapter de request + ScopeManager/ContextVar
        proxies + seguridad + CORS + rate limit si habilitado
        router ya compilado
        BodyStream + Request + binding en scope
        middleware web/API + middleware de ruta
        Container.invoke o build(controlador) + call
        Response + headers + adapter de salida
        cierre del scope
    cancelación y espera de la vigilancia restante
```

Una petición ya llega en una tarea del servidor: Orionis agrega **dos tareas**,
no solamente una. La reutilización de kernel y router no elimina este trabajo.

## 4. Resultados y atribución del coste

Entorno final: CPython **3.14.3**, Windows 11, `ProactorEventLoop`; Orionis
0.756.0 del workspace, Starlette **1.3.1**, FastAPI **0.139.2**, AnyIO 4.15.1 y
Granian 2.8.3 instalado. Granian no se ejecutó como servidor en estas pruebas.
Las versiones y paths de módulos están registrados en el JSON de comparación.

### 4.1. Orquestación aislada: cuatro políticas

11 muestras por caso, ~3.000 peticiones por muestra, orden de variantes alternado,
GC habilitado. Cada celda es la mediana de **µs de tiempo de lote por petición
completada**, no p50 individual ni p99. No incluye DI, router ni I/O real.

| Protocolo / handler / concurrencia | Actual | Solo Task handler | Directo sin monitor | Eager condicionado |
|---|---:|---:|---:|---:|
| ASGI inmediato / 1 | 25,26 | 15,58 | 1,41 | 7,25 |
| ASGI una suspensión / 1 | 61,67 | 26,79 | 9,83 | 30,93 |
| RSGI inmediato / 1 | 32,02 | 28,41 | 1,39 | 6,21 |
| RSGI una suspensión / 1 | 78,57 | 32,00 | 12,09 | 34,20 |
| ASGI inmediato / 32 | 18,88 | 9,29 | 1,49 | 7,96 |
| ASGI una suspensión / 32 | 50,40 | 16,02 | 7,31 | 28,97 |
| RSGI inmediato / 32 | 20,01 | 13,87 | 1,43 | 5,34 |
| RSGI una suspensión / 32 | 42,67 | 16,48 | 6,35 | 23,28 |

Existe dispersión material: ASGI inmediato actual varió 22,95–35,33 µs; RSGI
con suspensión actual, 61,38–99,31 µs. Los grupos de protocolos se ejecutaron en
momentos diferentes: no usar esta tabla para concluir que RSGI es más lento que
ASGI en producción. Los JSON conservan todos los lotes y diferencias pareadas.
La mediana pareada `actual - solo Task` en RSGI fue 6,61 µs inmediato y 37,19 µs
con suspensión; incluye toda la coordinación, no solo asignar la segunda Task.

El conteo independiente del reloj confirma:

| Política | Tasks nuevas por petición inmediata / suspendida | Canceló handler ASGI esperando al recibir disconnect |
|---|---:|---|
| Actual | 2 / 2 | Sí |
| Solo Task handler | 1 / 1 | No |
| Directa | 0 / 0 | No |
| Eager condicionado | 1 / 2 | Sí en el probe; falta la matriz completa de compatibilidad |

Para 1.000 fragmentos ya disponibles, mediana por fragmento: actual **7,69 µs**,
directo **0,83 µs**, solo Task **1,08 µs**, eager **8,15 µs**. Eager no mejoró
esta transferencia; la cola sigue participando. Estos datos no se deben extrapolar
a uploads con latencia de red ni compararse directamente con la tanda histórica.

Con un handler que no consume un cuerpo de 1.000 fragmentos distintos de 64 KiB,
la implementación actual hizo **9 lecturas**, con pico trazado **596.969 B**;
directa hizo **0 lecturas**, con pico **2.080 B** en el harness. Eso mide lectura
anticipada y memoria del puente, no buffers de servidor ni tamaño máximo de request.
Todos los requests/tareas del experimento finalizaron sin tareas pendientes.
[Resultados completos de monitor](../../../tests/foundation/benchmark_application_monitor_results.json).

### 4.2. Pipeline HTTP real precargado frente a competidores

7 muestras × 2.000 requests por combinación. GET estático, handler async inmediato,
Response nueva de 13 bytes, mismos status/body/headers verificados. Se conserva
Container, router, Request, scope y seguridad global de Orionis; se omiten sesión,
auth y bootstrap. FastAPI devuelve Response directamente, sin modelo de salida.
Es una comparación diagnóstica de componentes/configuración; **no equivalencia de
prestaciones ni benchmark de red**. Los controladores en competidores se crean
explícitamente; Orionis pasa por su DI.

| Variante | Función: mediana [mín–máx], µs/request | Controlador: mediana [mín–máx], µs/request |
|---|---:|---:|
| Orionis actual | 127,72 [46,14–200,25] | 355,42 [227,08–458,09] |
| Orionis kernel directo, sin vigilancia | 64,77 [22,53–90,12] | 220,10 [134,67–302,93] |
| Starlette | 36,43 [13,90–68,12] | 46,15 [33,33–64,28] |
| FastAPI | 133,33 [101,88–168,61] | 129,17 [92,63–195,37] |

Quitar la orquestación redujo la mediana local de Orionis, pero su controlador
todavía conserva mucho coste y la función no queda por debajo de Starlette en
esta tanda. La cercanía entre función Orionis actual y FastAPI está dentro de
una dispersión grande: no permite afirmar una victoria de Orionis. Tampoco
demuestra el ranking para JSON validado, rutas numerosas, streaming o red.

El perfil separado del kernel directo, para 2.000 peticiones de función, registró
2.000 llamadas a cada una de estas operaciones: `Container.invoke`,
`ReflectionCallable.getDependencies`, `inspect.iscoroutinefunction`, creación
del adapter, construcción de headers y `Response.getRawHeaders`. Es trabajo que
permanece después de quitar el monitor. Los tiempos de cProfile están
instrumentados y sus acumulados se solapan; se usan para localizar rutas, no para
sumar porcentajes de ahorro.
[Resultados y perfil del pipeline](../../../tests/foundation/benchmark_application_stack_results.json).

### 4.3. DI y retención: evidencia independiente de HTTP

7 muestras × 5.000 operaciones, orden alternado, Container real. Medianas:

| Operación | µs/operación |
|---|---:|
| Reflexión de método ligado a controlador nuevo | 61,10 |
| Reflexión de función estable | 2,78 |
| Reflexión de método sin ligar estable | 3,08 |
| Consulta directa de firma de función ya cacheada | 0,42 |
| Container.build + Container.call | 126,68 |
| Container.call sobre instancia reutilizada | 14,42 |
| Container.invoke de función | 15,12 |
| Crear controlador y llamar directamente | 0,85 |
| Función async directa | 0,35 |

Las llamadas directas omiten prestaciones DI y son referencias inferiores,
no alternativas equivalentes listas para adoptar. Reutilizar una instancia aquí
sirve para aislar metadata; no autoriza a compartir controladores entre usuarios.

**Resultado determinista:** 1.100 instancias nuevas → ambos LRU con 0 hits,
1.100 misses y 1.024 entradas; **1.024 controladores vivos tras `gc.collect()`**.
Sus payloads de prueba retuvieron 4.194.304 B, sin contar overhead. Limpiar solo
el LRU resuelto no los liberó; limpiar ambos dejó cero. Función estable:
1 miss y 1.099 hits en la caché resuelta.
[Resultados DI](../../../tests/foundation/benchmark_application_di_results.json).

### 4.4. Scoped: concurrencia bloqueada por contrato

El experimento usa resolución/scopes reales y reemplaza solo construcción por un
probe que suspende. Antes de liberar la primera construcción, la segunda petición
en otro scope todavía no había iniciado la suya. Cada scope recibió su instancia
correcta, pero el solapamiento máximo fue uno. Los controles de mismo scope y
singleton construyeron correctamente una sola instancia compartida.

Con espera artificial de 10 ms, medianas de tres muestras: **14,85 ms** para un
scope, **30,51 ms** para dos y **124,06 ms** para ocho. La granularidad de timers
Windows explica que no sean exactamente 10/20/80 ms; la causalidad está en los
eventos y en el lock compartido. No es una estimación de todas las rutas reales.
[Resultados scoped](../../../tests/foundation/benchmark_application_scoped_results.json).

### 4.5. Importar Application antes de create()

Cinco procesos nuevos: mediana **1.969,35 ms**, rango **1.441,93–2.246,50 ms**.
El tiempo excluye iniciar el intérprete/script; no se vaciaron cachés del sistema
de archivos. Desde el baseline stdlib del script se agregaron **1.603 módulos**.
Entre las familias cargadas: 89 módulos console, 15 de testing, 37 de view,
129 de SQLAlchemy, 22 de APScheduler, 20 de Jinja2, 54 de Rich y 61 de Redis.

Una corrida separada de `tracemalloc` registró **68.882.780 B vivos** y
68.980.139 B de pico. Son asignaciones Python trazadas, no RSS ni memoria que
pueda eliminarse completamente. No se instanció Application ni se ejecutaron
create/lifespan/requests. Esto justifica revisar el grafo de imports; no atribuir
esos segundos a cada petición.
[Resultados de imports](../../../tests/foundation/benchmark_application_imports_results.json).

### Cómo interpretar la vigilancia

La diferencia `current - handler_task_only` en RSGI aproxima el coste de la
vigilancia completa: coroutine/Task, awaitable del protocolo, planificación,
cancelación y espera de limpieza. **No es el tiempo aislado de `create_task()`.**
En ASGI esa diferencia incluye además la cola y el dispatcher.

La diferencia `handler_task_only - direct_no_monitor` mide el coste de separar el
handler de la tarea llamadora en este harness. La variante directa elimina ambas
tareas adicionales; ASGI también elimina el buffer intermedio y llama a `receive`
cuando el consumidor necesita cuerpo. No equivale a volver a una cola ilimitada.

La variante eager inicia el handler con `eager_start=True` y solo crea el monitor
si el handler continúa pendiente. Reduce de dos a una las tareas adicionales del
caso inmediato; con suspensión siguen siendo dos. ASGI todavía crea su cola antes
del handler. El cambio altera el orden de ejecución y necesita validar task factories,
contextos y loops de despliegue. [Semántica eager de Python 3.14](https://docs.python.org/3.14/library/asyncio-task.html#eager-task-factory).

### Qué garantiza realmente el monitor actual

- RSGI espera `client_disconnect()` y solicita cancelación del handler.
- ASGI debe leer cuerpo y desconexión por un solo canal; el dispatcher entrega
  mensajes al kernel. Si se llena la cola, deja de leer hasta disponer de espacio:
  la detección de una desconexión posterior también se retrasa.
- `Task.cancel()` solicita cancelación cooperativa. El monitor no puede interrumpir
  código Python que bloquea el mismo event loop, ni garantiza revertir efectos externos.
- La limpieza esperada protege la duración de recursos y la propagación de errores.
  Dejar de esperarla sería una regresión de comportamiento, no una optimización equivalente.

ASGI define `http.disconnect` y, desde la subespecificación HTTP 2.4, el error de
`send()` sobre una conexión cerrada; no impone un watcher universal. RSGI exige
finalizar la vigilancia creada al acabar la respuesta porque keep-alive puede
mantener la conexión abierta; eso no obliga a crearla para cada petición.
[ASGI HTTP](https://asgi.readthedocs.io/en/stable/specs/www.html#disconnected-client-send-exception),
[RSGI oficial](https://github.com/emmett-framework/granian/blob/master/docs/spec/RSGI.md).

Starlette 1.3.1 envía una `Response` normal sin un monitor universal. Su
`StreamingResponse` usa error de envío con ASGI HTTP >=2.4; mantiene escucha
concurrente para la rama anterior. Esperar un error de envío no cancela trabajo
costoso mientras el handler no está enviando. [Código de respuestas, tag 1.3.1](https://raw.githubusercontent.com/Kludex/starlette/1.3.1/starlette/responses.py).

## 5. Oportunidades ordenadas por impacto

### Crítico: C1. Eliminar claves de caché ligadas al controlador de cada request

**Problema y evidencia D/M.** `http/kernel.py:654` construye un controlador;
`container.py:1256` obtiene su método ligado y `:1316` inicia reflexión. Los LRU
de `introspection/dependencies/reflection.py:27` y `:178` reciben ese objeto como
clave. Cada instancia nueva causa miss; la clave retiene la instancia.

**Alternativa.** Normalizar metadata de métodos ordinarios a `method.__func__`,
manteniendo por separado el modo de binding. Precompilar el plan de constructor
y acción en el despacho de ruta. La instancia del controlador sigue siendo local
a la petición. La implementación actual ya excluye `self`/`cls` de argumentos DI.

**Impacto.** Sustituye análisis repetido O(p) de la firma por consulta O(1) en hit;
el ensamblaje de p valores sigue siendo O(p). Elimina firmas/Argument temporales
repetidas y referencias globales a instancias. El tamaño del grafo retenido hoy
puede superar mucho el número de entradas si un controlador referencia Request.
Las entradas por instancia también pueden desplazar firmas estables del presupuesto
compartido de 1.024 entradas y reducir su hit ratio.

**Trade-off y pruebas.** Métodos de instancia, clase, estáticos, decoradores,
`__signature__`, reemplazo de funciones y reload requieren tratamiento explícito.
Probar 1.100 instancias con weakrefs, cache hits después del primer acceso,
tipos/defaults/posicionales y ausencia de contaminación entre requests. No usar
controladores singleton como atajo: cambia el aislamiento.

**Decisión recomendada:** ejecutar primero; preserva la intención funcional y
resuelve CPU y memoria. Es retención acotada por entradas LRU, no fuga ilimitada.

### Alto: A1. Eliminar interpretación genérica de dependencias en rutas conocidas

**Problema D/M.** Aunque una función tenga metadata cacheada, `container.py:1316`
crea wrappers y `:1332` comprueba si es async; `:1357` a `:1451` crean estructuras
y recorren la firma. Construir una clase agrega identificación, detección de
ciclos y estado temporal (`:1116`).

**Alternativa.** En boot, preparar por ruta callable, clase/acción, modo async/sync,
metadata del constructor, instrucciones de inyección, convertidores y serializer.
Especializar cero argumentos, parámetros de URL y Request conocido. Conservar el
resolvedor general para casos dinámicos; invalidar el plan cuando cambian bindings.

**Impacto.** Evita ReflectionCallable/ReflectDependencies por invocación, checks
repetidos y parte de los diccionarios/deques de `**kwargs`. Para cero argumentos,
despacho directo O(1); para p argumentos sigue O(p) con menos interpretación.
La diferencia microbench DI/directo es un techo orientativo, no ahorro HTTP prometido.

**Trade-off y pruebas.** Mayor compilador interno, invalidación explícita,
inyecciones scoped resueltas por request, firmas dinámicas y schemas. Probar planes
y fallback con los mismos tests de Container, overrides y llamadas concurrentes.
Los handlers síncronos con I/O bloqueante deben conservar una política explícita
de ejecución: ejecutarlos en el loop para ganar un benchmark perjudica concurrencia.

**Decisión recomendada:** ejecutar después de C1, empezando por el caso sin argumentos.

### Alto: A2. Eliminar vigilancia universal en las rutas que no la necesitan

**Problema D/M.** `application.py:343` a `:348` y `:463` a `:467` agregan tareas
en todas las peticiones. ASGI suma buffer y productor, incluso si el handler no
lee cuerpo. El coste real depende de suspensión y fragmentación.

**Alternativas concretas.**

| Política candidata | Qué elimina | Garantía y coste restante |
|---|---|---|
| Actual: cancelación proactiva universal | Nada | Dos tareas; cola ASGI; cleanup esperado |
| Eager con monitor condicionado | Monitor de respuestas que terminan sin suspender | Una Task de handler; cola ASGI; dos tareas cuando suspende |
| Despacho directo sin monitor | Ambas Tasks; cola/dispatcher ASGI; coordinación de cleanup | Cancelación externa del servidor continúa propagándose; no se detecta abandono mientras se espera otra operación |
| Política compilada por ruta | Coste anterior solo en rutas que lo requieren | Necesita contrato claro para stream, SSE, long-poll y operaciones costosas |

**Impacto.** O(1) de CPU/asignaciones por request y O(k) en transferencias de k
fragmentos. La vía ASGI directa elimina el buffer de Application, pero no limita
por sí sola memoria del servidor ni la que el handler consume/materializa.

**Diseño propuesto.** Mantener una política explícita, inicialmente compatible;
permitir ruta pública directa y ruta con cancelación proactiva. Resolver la
política usando metadata del router/kernel, evitando una segunda resolución en
Application. El monitor y la entrega de cuerpo deben tener un único propietario.
No compartir dos consumidores concurrentes del `receive` ASGI.

**Trade-off y pruebas.** Elegir política cambia semántica, incluso siendo compatible
con ASGI/RSGI. Clientes que abandonan pueden dejar I/O del handler en marcha. Probar
errores de receive/send, cancelación externa, timeout, desconexión durante upload,
cola llena, SSE inactivo, backpressure de salida, cierre de generadores y recursos.
Si se mantiene vigilancia, conservar la espera de limpieza y el límite de cola.

**Decisión recomendada:** prototipo opt-in con medición HTTP real; no eliminar
globalmente el monitor solo para ganar un benchmark. Eager merece un experimento
separado y no resuelve el coste de todas las peticiones que suspenden.

### Alto condicional: A3. Eliminar contención entre scopes independientes

**Problema D.** `container.py:1075` usa un lock por contrato guardado globalmente
en `:138`. Distintos scopes compiten si construir el mismo scoped suspende.
El experimento controla esa suspensión y confirma serialización; no demuestra
que todos los constructores reales la tengan.

**Alternativa.** Alojar el lock `(scope, contrato)` dentro de ScopeManager. Mantener
la coordinación por contrato global para singletons y por identidad para providers.

**Impacto.** Con C peticiones independientes y espera T por construcción, el tramo
serializado puede acercarse a C×T; separado por scope puede solaparse y acercarse a
T más planificación, sujeto a límites de los servicios. No acelera I/O ya serializado
externamente. Se crean locks por servicio usado en cada scope y se liberan al cerrar.

**Trade-off y pruebas.** Dos subtareas del mismo scope todavía deben compartir una
instancia; cancelación/reintento, ciclos, salida del scope y singletons no pueden
romperse. Los controles de identidad del benchmark son un punto de partida.

**Decisión recomendada:** corregir y validar junto con DI; prioridad máxima en cargas
con construcción suspendida confirmada, menor si todo ese trabajo es síncrono.

### Alto según carga: A4. Eliminar sesión/identidad automática de rutas públicas

**Problema D/H.** `http/kernel.py:529` siempre entra al grupo web/API. En web,
`layer/web/start_session.py:133` recuerda la URL anterior y puede iniciar sesión
en un GET público. `session/manager.py:254` puede persistir una sesión restaurada
aunque no cambien datos. En API, `auth/middleware/resolve_identity.py:112` agrega
lock/contexto/guard; un token puede provocar búsqueda de token, identidad y touch
(`auth/guards/token_guard.py:83`). El almacenamiento determina el coste real.

**Alternativa.** Perfiles explícitos público/API autenticada/web con sesión;
resolución diferida de identidad cuando se usa, sesión lazy y tracking de URL
anterior opt-in. Separar persistencia de datos sucios y renovación de expiración.

**Impacto.** Puede eliminar lecturas/escrituras, serialización/cookies y objetos
por request; con store remoto puede dominar microsegundos del monitor. No se
midieron estos backends y no se cuantifica ahorro de red aquí.

**Trade-off y pruebas.** Flash, CSRF, redirects back, login/logout, renovación,
revocación y auditoría de uso. No omitir `save()` por `dirty=False` sin diseñar
renovación. No cachear tokens/identidades entre usuarios sin política de invalidación.

**Decisión recomendada:** decisión de producto por perfil; no cambiar silenciosamente
las garantías de rutas web/API existentes.

### Medio: M1. Fusionar normalización, índice y validación de headers

`adapters/request/asgi.py:137`, `rsgi.py:138`, `payload/estructures/headers.py:25`
y `layer/shared/security.py:151` recorren/transforman headers en varias etapas.
Propuesta: constructor especializado desde el transporte, una pasada para índice,
normalización y señales de validación; decodificación diferida donde sea útil.
Conserva O(h), reduce listas/tuplas/strings y recorridos. Probar duplicados, Host,
Latin-1, orden, CRLF, cookies y `getAll`. No eliminar validación basándose en una
garantía del servidor que no se haya comprobado. Ganancia pendiente de medición.

### Medio: M2. Evitar materialización de Request/BodyStream/scope no utilizados

`http/kernel.py:814` crea BodyStream y Request; `request.py:104` inicializa muchos
slots; RSGI materializa un diccionario de scope (`adapters/request/rsgi.py:318`).
Propuesta: body lazy, scope materializado al pedirlo y, solo cuando el plan de ruta
lo pruebe, evitar Request completo. Mantener valores scoped y mutaciones de params
locales; copy-on-write exige contrato. Ahorra al menos el objeto BodyStream en GET
sin cuerpo y conversiones innecesarias; no todos los slots justifican eliminarlos.
Validar facade Request, middleware, proxies, schemas, errores y cancelación.

### Medio: M3. Compilar el pipeline y especializar cero/una capa

`http/kernel.py:537` crea `_MiddlewarePipeline` incluso para stack vacío; `:593`
crea otra instancia para middleware de ruta. Precalcular stacks y terminales por
ruta, con casos cero/una capa y una sola secuencia cuando lo permita el orden.
Conserva O(m) para m capas, evita wrappers y una parte de los objetos de control.
**No reutilizar el objeto pipeline entre requests:** contiene profundidad, máscara,
request y argumentos mutables. Probar doble next, short-circuit, excepciones web
dentro de sesión, concurrencia y orden antes/después de cada middleware.

### Medio: M4. Respuestas y headers precompilados para contenido constante

`responses.py:100`, `:252` y adaptadores construyen/encodan headers y agregan Server.
Propuesta: representación explícita e inmutable de body+headers estáticos; almacenar
valor único sin lista hasta que existan duplicados. Reusar bytes, no una Response
mutable global. Reduce O(h+b) repetido en respuestas constantes; JSON dinámico
todavía debe serializarse. Probar CORS por origen, Set-Cookie múltiple, background,
HEAD, streams y mutación por middleware. `msgspec.json.encode` ya existe; cambiar
de serializador no es el primer candidato.

### Medio en throughput; alto en arranque/memoria: M5. Cargar solo capacidades usadas

`core_kernels.py:2` importa CLI y HTTP para obtener metadata; `core_providers.py:1`
importa los 17 providers. Solo Cache, Storage y Testing son deferred: diferir boot
no evita esos imports. Reexports de `console/__init__.py`, `console/base/__init__.py`,
`support/facades/__init__.py` y `cache/__init__.py` amplían el grafo aun al importar
un contrato. Startup HTTP también pinnea Reactor/Schedule y construye servicios
de vistas/otras familias que un endpoint mínimo puede no usar.

Propuesta: metadata literal de kernels/scheduler, descriptors de providers por
capacidad HTTP/CLI, exports perezosos y warmup de capacidades activadas. Disminuye
módulos, objetos y memoria por proceso; con W workers el ahorro por worker se
repite, sin asumir memoria física perfectamente aditiva o copy-on-write idéntico.
Mueve fallos de imports: detectarlos durante readiness de cada capacidad.

Antes de diferir más providers, coordinar por **identidad del provider**, no solo
por contrato: `container.py:764` y `:794` cachean servicios individuales, así que
un provider multicontrato puede arrancar más de una vez. Probar lazy imports,
exports públicos, boot concurrente y warmup tras fallo. No prometer RPS a partir
de los tiempos de importación.

### Medio en primera petición: M6. Completar kernel HTTP durante readiness

`Application.__onStartup` arranca providers y hooks; el kernel se carga después,
en la primera petición (`application.py:338`, `:458`). Iniciarlo en lifespan
mueve carga de rutas/middleware fuera de la primera ráfaga. Preservar fallback
bajo lock si el servidor omite lifespan. Reduce latencia inicial, no CPU total
ni tiempo caliente. Probar ambas interfaces, orden de hooks y boot que falla.

Coherencia pendiente del contrato: `contracts/application.py:25` describe
`isBooted` como providers arrancados, pero `create()` pone la bandera antes del
boot async (`application.py:2727`). Documentar estados configurada/ready o exponer
readiness explícita. Este informe lo identifica sin alterar la API.

### Medio/bajo en arranque: M7. Reducir representaciones de configuración

Dataclasses/asdict en `core_config.py:18`, thaw/deepcopy de overrides en
`application.py:2560`, freeze y otro thaw runtime crean varias representaciones.
Propuesta: defaults bajo demanda y snapshot validado con overrides explícitos.
Coste O(n) para n datos de configuración; beneficia arranque/memoria. Mantener
aislamiento de datos del usuario. No cachear indiscriminadamente valores de
`config()`: actualmente admite modificación de mappings anidados y quedarían
resultados obsoletos sin invalidación. Las dataclasses no se recrean por request.

### Bajo: B1. Coroutines vacías, lookups y estructuras pequeñas

Se puede evitar `runBackground()` vacío (`responses.py:630`) mediante metadata
del response; preligar operaciones usadas muchas veces en bucles de cuerpo;
examinar flags constantes. Son reducciones O(1) pequeñas y deben medirse después
de C1/A1/A2. Añadir ramas o bindings también cuesta. El intento previo de usar
`put_nowait()` precedido de `full()` no mostró mejora estable y fue revertido;
no se incluye como candidato demostrado.

## 6. Qué conservar y qué no perseguir primero

| Elemento | Motivo |
|---|---|
| Locks de inicialización HTTP/CLI y singletons | No están en el hit caliente; evitan trabajo duplicado |
| Backpressure mientras exista dispatcher | No regresar a retención ilimitada para reducir esperas |
| Espera de cleanup de tareas creadas | Evita tareas/recursos pendientes y conserva errores/cancelación |
| Contrato IApplication y ABC | No agregan un despacho virtual adicional por request; coste principal en definición/boot |
| Type hints | No validan valores automáticamente por llamada; la reflexión que los consume sí cuesta |
| Slots solo en Application | Una instancia por worker; Container ya tiene `__dict__`; impacto pequeño |
| Cache/import de rutas existente | Ya precompila y reutiliza; primero medir hit ratio/cardinalidad |
| Middleware compartido sin estado de request | Evita reconstrucción; preservar esa propiedad |
| Separación de scopes/ContextVars | Garantiza aislamiento; reducir creación solo cuando el plan pruebe que no es necesaria |
| Caché global de Request, Response mutable o controladores | Riesgo de mezclar datos, cookies, background y usuarios |
| Seguridad/validación retirada solo para una gráfica | Comparación funcionalmente diferente; primero eliminar trabajo redundante |

El router estático ya usa dict y resultados precreados (`route_resolver.py:335`,
`:382`). El dinámico usa índices/regex y caché FIFO de 512 (`:354`, `:386`). La
posible ventaja debe medirse con rutas y URLs diversas; repetición de una única
URL caliente puede ocultar misses y churn. Crecer cachés sin límite no es solución.

## 7. Comparación justa con FastAPI/Starlette

Starlette construye y reutiliza su pila de middleware; FastAPI prepara metadata
de rutas/dependencias y cachea valores DI dentro de cada request. No partir de la
premisa de que esos frameworks repiten toda la introspección. `BaseHTTPMiddleware`
agrega tareas/streams; separarlo de middleware ASGI puro en las comparaciones.
[Starlette application](https://raw.githubusercontent.com/Kludex/starlette/1.3.1/starlette/applications.py),
[Starlette middleware](https://raw.githubusercontent.com/Kludex/starlette/1.3.1/starlette/middleware/base.py),
[FastAPI DI](https://raw.githubusercontent.com/fastapi/fastapi/0.139.2/fastapi/dependencies/utils.py).

FastAPI 0.139.2 tiene una vía de serialización JSON directa mediante Pydantic con
modelo y response class predeterminada. Separar Response(bytes), dict sin esquema
y esquema validado equivalente; quitar el modelo no garantiza menos coste.
[FastAPI routing del tag evaluado](https://raw.githubusercontent.com/fastapi/fastapi/0.139.2/fastapi/routing.py).

Dos preguntas distintas:

1. **Coste del framework:** mismo servidor, ASGI, loop, workers, payload, headers,
   logging, validación, auth/sesión y política de desconexión.
2. **Mejor despliegue de cada stack:** Orionis+RSGI contra FastAPI/Starlette+ASGI.
   Puede ser útil, pero la diferencia pertenece también a protocolo y servidor.

Matriz de aceptación para la siguiente fase:

| Dimensión | Casos mínimos |
|---|---|
| Estado | Import/cold boot, primera petición, warm estable |
| Rutas | 1/100/1.000; primera/media/última; 404/405; estáticas/dinámicas |
| Handler | Async inmediato, await resuelto, I/O controlado, controlador, DI, validación |
| Datos | Sin cuerpo; JSON 1 KiB/64 KiB; upload 4 MiB y fragmentado; consumidor lento |
| Servicios | Público; API con token; web con sesión; lectura y escritura de store |
| Salida | Bytes, JSON sin modelo/con modelo, HEAD, archivo, streaming/SSE |
| Concurrencia | 1/32/128/512 según capacidad; tasa abierta para observar saturación |
| Fallos | Disconnect, timeout, shutdown, receive/send fallidos, excepciones y limpieza |
| Métricas | Throughput, p50/p95/p99, CPU/request, RSS/pico, tareas, errores y recursos retenidos |

Repetir en procesos independientes, alternar orden, conservar versiones y
configuración; ejecutar generador de carga sin convertirse en cuello de botella.
Registrar cuándo el limitante es red, CPU, DB o pool de conexiones. Un ahorro de
10 µs dentro de una petición de 1 ms equivale a ~1% de su tiempo; dentro de 50 µs,
a ~20%. Es aritmética ilustrativa, no resultado de este benchmark.

## 8. Propuesta de ejecución para aprobar por bloques

| Bloque | Incluye | Recomendación | Cambio de semántica | Criterio de aceptación |
|---|---|---|---|---|
| 1 | C1 claves de metadata | Ejecutar primero | No intencional | Hits estables, weakrefs liberadas, misma DI |
| 2 | A1 plan de invocación + A3 scopes | Ejecutar con pruebas de concurrencia | No intencional | Menos CPU; scopes independientes sin serialización artificial |
| 3 | A2 políticas de vigilancia | Prototipo y decisión explícita | Sí en detección de abandono | Latencia/memoria mejores, política documentada y cleanup correcto |
| 4 | A4 perfiles público/auth/web | Decidir producto antes de cambiar defaults | Sí | Mismas garantías en rutas que las activan |
| 5 | M1/M2/M3 headers/request/pipeline | Medir y adoptar individualmente | Evitable con diseño cuidadoso | Menos asignaciones, mismo comportamiento observable |
| 6 | M4 respuesta inmutable opt-in | Evaluar si hay contenido constante | API nueva | Headers/cookies/background aislados |
| 7 | M5/M6/M7 imports/bootstrap/readiness | Proyecto de startup y memoria | Orden de carga/readiness | Menos imports/RSS/cold time; warmup predecible |
| 8 | B1 microajustes | Posponer | Generalmente no | Ganancia repetible mayor que ruido |

Cada bloque debe conservar resultados comparables antes/después. No sumar los
porcentajes de microbenchmarks: sus costes se solapan y parte desaparecerá al
cambiar la arquitectura. Tampoco usar la instancia reutilizada del benchmark DI
como propuesta de compartir controladores entre usuarios.

## 9. Artefactos, reproducción y validación

Los scripts de diagnóstico están en `tests/foundation/`:

- `benchmark_application_monitor.py`: variantes en memoria de orquestación actual,
  directa, una Task y eager; ASGI/RSGI; concurrencia 1/32; cuerpo; conteos y desconexión.
- `benchmark_application_di.py`: Container/reflexión reales, cachés y retención por weakrefs.
- `benchmark_application_scoped.py`: coordinación real de scopes con construcción instrumentada.
- `benchmark_application_stack.py`: core HTTP real precargado y competidores, respuestas verificadas.
- `benchmark_application_imports.py`: procesos nuevos para imports; tracemalloc separado de tiempo.

Cada uno guarda su JSON `benchmark_application_<nombre>_results.json`. Los resultados
de `stack` incluyen perfil acumulado separado del timing; sus tiempos de frames se
solapan y no deben sumarse. El ensamblaje omite bootstrap, sesión y auth, conserva
seguridad global, usa DI real en Orionis y una respuesta bytes nueva en cada handler.
Los controladores de competidores se construyen explícitamente en su endpoint;
no se pretende igualar sus contenedores con el de Orionis.

Ejecutar desde la raíz, con Python 3.14 y dependencias del repositorio:

```powershell
$env:PYTHONPATH = (Resolve-Path .venv/Lib/site-packages).Path
$env:PYTHONIOENCODING = 'utf-8'
python tests/foundation/benchmark_application_monitor.py --samples 11 --requests 3000 --output tests/foundation/benchmark_application_monitor_results.json
python -m tests.foundation.benchmark_application_di --samples 7 --iterations 5000 --output tests/foundation/benchmark_application_di_results.json
python -m tests.foundation.benchmark_application_scoped --output tests/foundation/benchmark_application_scoped_results.json
python tests/foundation/benchmark_application_stack.py --samples 7 --requests 2000 --profile --output tests/foundation/benchmark_application_stack_results.json
python tests/foundation/benchmark_application_imports.py --output tests/foundation/benchmark_application_imports_results.json
```

En este entorno se usa el ejecutable Python del sistema y se prioriza el directorio
de paquetes de `.venv`, porque su launcher uv no puede iniciar el intérprete.
No se instalaron ni actualizaron dependencias. Los scripts que importan dependencias
necesitan ese path; el benchmark de monitor usa solo stdlib y el harness existente.

Validación realizada:

- Los cinco experimentos completaron su ejecución; los JSON incluyen muestras crudas.
- El pipeline verificó status, cuerpo y headers de las ocho combinaciones antes de medir.
- Monitor verificó conteos de tareas, cancelación observable y ausencia de tareas pendientes.
- DI verificó retención/liberación mediante weakrefs; scoped verificó identidad y coordinación.
- Suite `tests/foundation`: **121/121 aprobadas**, sin fallos ni errores, sobre la
  implementación actual. No certifica las variantes especulativas del benchmark.
- **Ruff sin errores** en los cinco scripts nuevos y Application/contrato revisados.
- No está disponible `sonar-scanner`; no se afirma que SonarQube se haya ejecutado
  ni que su quality gate esté aprobado.
- Inspección AST: los cinco scripts compilan; 61 funciones/métodos con documentación
  NumPy, convención de nombres de métodos comprobada; los cinco JSON y enlaces
  locales del informe se pudieron leer y resolver.

El criterio de implementación posterior mantiene métodos camelCase, funciones
externas snake_case, documentación NumPy y comentarios en inglés que describan
el bloque. Ruff debe pasar por cambio; SonarQube requiere ejecutar su analizador
real para afirmar un quality gate aprobado.

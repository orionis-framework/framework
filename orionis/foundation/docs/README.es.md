# Foundation: Revision De Rendimiento

Manual en ingles: [README.md](README.md).
Muestras medidas: [benchmark-results.json](benchmark-results.json).

## Estados Explicitos Y Arranque Sin Servidor

`create()` conserva su comportamiento síncrono de configuración y registro.
Para scripts o workers propios, usar `await app.boot()` antes de consumir
facades. Ejecuta `create()`, espera los providers eager pendientes y devuelve
la aplicación. Las llamadas concurrentes comparten el bloqueo existente;
un fallo o cancelación conserva el provider pendiente para reintentar.
No inicia kernels ni ejecuta hooks del runtime HTTP o CLI.

| Fase | Estado observable | Acceso a servicios |
| --- | --- | --- |
| Construida | `isCreated == False` | Bindings explícitos del container; configurar antes de usar servicios con configuración. |
| Creada | `isCreated == isBooted == True` | Bindings registrados; resolver contratos con `await`. Los efectos del boot eager asíncrono pueden seguir pendientes. |
| Providers iniciados | `areProvidersBooted == True` | Boot eager terminado; los providers deferred siguen resolviéndose bajo demanda. |
| HTTP inicializado | `isHttpReady == True` | Ambos handlers publicados después del boot eager y del kernel. No certifica sockets ni dependencias externas. |
| Scoped | `app.getCurrentScope()` devuelve un scope | Estado aislado por petición, conexión WebSocket o job; no retener servicios scoped en singletons. |
| Facade pinned | El provider esperó `Facade.pin()` | Acceso directo siguiendo la API síncrona/asíncrona del servicio. Antes del pin, el dispatcher requiere `await`, incluso para métodos síncronos. |

Los flags registran etapas de arranque completadas; shutdown no los reinicia
y no representan el estado de salud actual del proceso o sus servicios.
`isBooted` sigue siendo el alias compatible de la fase creada. HTTP lifespan y
Reactor siguen ejecutando sus hooks; los scripts que los necesitan deben usar
el entry point del runtime correspondiente. Resolver un contrato explícito
evita depender del momento de pin de una facade durante el arranque.

## Alcance

Revision de 157 archivos Python y 390 funciones o metodos explicitos de
`orionis/foundation`. Entorno: CPython 3.14.6, Windows 11. La version minima
continua siendo Python 3.14. Se preservaron los cambios previos de colas y sus
validadores compartidos.

No se reprodujo un defecto critico de produccion en las rutas revisadas. Las
mejoras principales afectan importacion, arranque y construccion de servicios.
No se presenta un microbenchmark como una medicion de throughput HTTP.

## Hallazgos Aplicados

### Alto: Esperas Bloqueantes En El Ciclo De Depuracion

**Problema.** Los paneles ejecutaban `time.sleep(0.5)` al arrancar y
`time.sleep(0.1)` al cerrar. Los generadores se avanzan desde el event loop:
esas esperas detenian tambien el progreso de otras tareas del mismo hilo.

**Implementacion.** En `lifespan/startup.py` y `lifespan/shutdown.py`, imprimir
directamente el panel y continuar. Se eliminan los contextos de pantalla
alternativa temporizada y el import de `time` innecesario en startup.

**Impacto.** Se eliminan 500 ms de latencia fija al arrancar y 100 ms al cerrar
en debug fuera de produccion. No se atribuye ahorro de CPU a `sleep`: su coste
principal era la espera y el bloqueo del event loop. No cambia el despacho por
peticion ni el comportamiento silencioso en produccion.

**Trade-off.** El mensaje queda visible en la consola normal durante los hooks,
en lugar de desaparecer tras una pausa decorativa. Se conservan el panel de
disponibilidad, el resumen de uptime y el orden de los generadores.

**Pruebas.** Seis casos nuevos de fases, contenido y politica de visualizacion.

### Medio: Resolucion Repetida De Directorios

**Problema.** `Directory.__init__` llamaba a `app.path(key)` para las 38 rutas:
se repetian validacion, busqueda del bootstrap y despacho de metodo.

**Implementacion.** `dict(app.path())` obtiene el mapa con una llamada y crea
una instantanea propia. Las rutas `Path` son inmutables y se pueden compartir.

**Impacto.** 38 llamadas pasan a una. La copia sigue siendo O(P), con P rutas,
pero se ejecuta a partir del mapa completo. Mediana local: 37.405 a 8.640 us,
4.33x. No se agrega memoria persistente ni trabajo a los accesores.

**Trade-off.** Los dobles o implementaciones de `IApplication` deben soportar
`path()` sin argumentos, como ya exige el contrato. Se conserva la independencia
frente a modificaciones posteriores del mapa original.

**Pruebas.** Accesores, contrato, llamada unica, instantanea independiente y slots:
10/10 casos.

### Medio: Normalizacion Lineal De Enums

**Problema.** `normalize_enum` recorria los miembros, normalizaba cada nombre y
valor y creaba un conjunto temporal por miembro para cada entrada textual.

**Implementacion.** Una tabla `MappingProxyType` indexa nombres y representaciones
normalizadas. `lru_cache(maxsize=64)` conserva revisiones por clase y cantidad
de alias. `setdefault` mantiene la precedencia del primer miembro declarado.
Los enums con valores no escalares conservan el recorrido de sus valores vivos.

**Impacto.** Para enums escalares, O(E) de preparacion una vez y O(1) esperado
por busqueda, ademas del O(L) de normalizar la entrada de longitud L. Se eliminan
hasta E conjuntos y las conversiones repetidas de los miembros por consulta.
Para el ultimo valor de un enum de 33 miembros: 23.658 a 1.357 us, 17.44x local.
La tabla requiere O(E) memoria por revision, con un maximo de 64 revisiones.

**Trade-off.** Se retienen clases y tablas hasta su expulsion. El numero de
alias permite reconocer `_add_alias_`; los valores mutables no se indexan.
No se promete soportar mutaciones de los atributos privados internos de Enum.

**Pruebas.** Seis casos: nombres/valores/alias, precedencia, clases independientes,
alias agregados posteriormente, errores contextualizados y valores mutables.

### Medio: Importacion De Catalogos No Solicitados

**Problema.** Importar solamente `SQLite` ejecutaba los inicializadores que
cargaban tambien los otros motores y todos sus catalogos de enums.

**Implementacion.** Exports PEP 562 mediante el helper existente
`orionis._exports.resolve_export` en `config/database/__init__.py` y
`config/database/enums/__init__.py`. Cada objeto se guarda en el namespace al
resolverlo; los accesos posteriores no pasan por `__getattr__`.

**Impacto.** El import de SQLite carga 7 modulos de configuracion de base de datos
en lugar de 23. Memoria retenida trazada: 4,803,893 a 4,468,062 bytes, unos 336 KB
menos. Mediana de siete procesos: 156.587 a 125.644 ms, con variacion elevada.
Es un beneficio de importacion selectiva, no una mejora prometida al arrancar
una aplicacion que de todas formas necesita todos los motores configurados.

**Trade-off.** Los errores de importacion pueden aparecer en el primer acceso.
Se conserva `__all__`, `dir()`, import directo, wildcard, identidad de clases y
visibilidad para el editor mediante `TYPE_CHECKING`. Las tablas de exports
deben actualizarse al agregar un simbolo publico.

**Pruebas.** Suite de imports frios y contratos de exports: 9/9 casos.

### Medio: Serializacion Innecesaria De Mailers

**Problema.** `Mail.__post_init__` serializaba todos los transportes para
comprobar solamente si el mailer predeterminado estaba declarado. La copia
recursiva no se conservaba ni se necesitaba para validar pertenencia.

**Implementacion.** Consultar nombres mediante `dataclasses.fields` cuando
`mailers` es una entidad. Para mappings se conserva su validacion y copia
profunda, necesarias para aislar datos mutables del llamador.

**Impacto.** La comprobacion deja de recorrer el contenido de cada transporte:
O(F) nombres frente a O(N) valores anidados, sin diccionarios serializados.
Con entidades anidadas ya construidas: 13.944 a 3.139 us, 4.44x local.

**Trade-off.** La pertenencia se define por campos reales de la dataclass,
incluidos los agregados por subclases; no por un `toDict()` personalizado que
invente claves. El chequeo tampoco acepta nombres de metodos como mailers.

**Pruebas.** Una subclase impide serializar y agrega un campo valido; se mantienen
las pruebas de aislamiento y drivers personalizados.

### Bajo: Expulsion Completa Del Cache De Claves

**Problema.** La clave 257 borraba las 256 rutas ya divididas por `config()`.
La alternativa FIFO se descarto tras medir: retenia entradas, pero volvia a
analizar igual cantidad de claves frecuentes en la carga mixta seleccionada.

**Implementacion.** `_parse_config_key` usa un LRU de 256 entradas compartido.
Solo contiene tuplas inmutables de segmentos, nunca valores ni aplicaciones.
Se elimina el diccionario de claves por instancia.

**Impacto.** En 32,500 lecturas, 64 claves frecuentes intercaladas con 500 claves
nuevas: 692 analisis antes/FIFO frente a 564 con LRU, 18.5% menos divisiones,
listas y tuplas de parseo. Un hit evita dividir la cadena; el recorrido de los
diccionarios de configuracion sigue siendo O(D), profundidad de la clave.

**Trade-off.** Las aplicaciones comparten la capacidad del LRU, no sus valores.
Un barrido de claves todas distintas no obtiene hits y paga gestion del LRU.
Las diferencias de tiempo en lecturas calientes se solapan con el ruido: no
se promete un incremento concreto de throughput por este cambio.

**Pruebas.** Se mantienen mutaciones mediante mappings retornados, escrituras,
valores falsy, claves vacias y reset. Se agrego cobertura del limite y retencion
de una clave frecuente.

### Bajo: Metadatos Y Tablas Temporales

**Problema.** El bootstrap usaba un descongelador recursivo para descriptores
planos; ademas creaba una seccion `commands` sin consumidores. `Channels` y
`Disks` reconstruian sus tablas de tipos en cada `__post_init__`.

**Implementacion.** Copias directas de descriptores de cadenas, copia por kernel,
eliminacion de `commands` y tablas de tipos a nivel de modulo. En `Disks`,
conversion de dict o validacion de entidad en ramas excluyentes.

**Impacto.** Bootstrap: 8.357 a 2.172 us, 3.85x local. Un par de validaciones
Channels/Disks deja de crear 7 + 6 tuplas de tablas y 5 tuplas de tipos para
`isinstance`: 18 objetos temporales menos. Se conservan las entidades por
instancia y las copias necesarias; la complejidad sigue siendo lineal.

**Trade-off.** Las copias directas dependen de que esos descriptores sigan
conteniendo solamente cadenas. Si se agregan datos mutables anidados, debe
revisarse la copia. Los snapshots tienen pruebas de independencia.

### Bajo: Validacion Duplicada Y Layout

**Problema.** `IsValidLevel.normalize` primero validaba y despues repetia checks
y `strip().upper()`. Los validadores sin estado mantenian `__dict__`.

**Implementacion.** `normalize` valida y convierte una vez. `__call__` delega y
continua retornando `None`. Los conjuntos de niveles son `frozenset`; ambos
validadores usan slots vacios. `IApplication` declara tambien slots vacios.

**Impacto.** Normalizar `" warning "`: 1.863 a 1.110 us, 1.68x local. Los
validadores no tienen diccionario por instancia. No se atribuye este ahorro a
`Application`, que sigue heredando almacenamiento dinamico de `Container`.

**Trade-off.** No se pueden agregar atributos dinamicos a los validadores
privados. No se cambian firmas, mensajes ni el retorno de validacion-only.

**Pruebas.** Representaciones validas, tipos invalidos, retorno y layout: 5/5.

## Politica De Inicializacion

### Archivos `__init__.py`

| Grupo | Decision | Motivo |
| --- | --- | --- |
| `config/database/__init__.py` | Diferido. | Seleccionar una entidad no carga todos los motores. |
| `config/database/enums/__init__.py` | Diferido. | Evitar catalogos ajenos incluso al importar un modulo hoja. |
| Los 20 inicializadores vacios | Conservar vacios. | No necesitan imports ni dispatchers. |
| Los otros 25 agregadores | Conservar eager. | Exports pequenos/cohesivos; no introducir tablas sin beneficio demostrado. |

Los vacios comprenden las raices foundation/config, namespaces de entidades,
contratos, lifespan y helpers de sesion. Los eager comprenden las demas raices
de configuracion, sus paquetes pequenos de enums no vacios, los validadores de
logging y los enums de runtime/lifespan. Ningun initializer construye entidades
de configuracion para anticipar lecturas del entorno.

### Constructores

| Constructor O Carga | Decision |
| --- | --- |
| `Application.__init__` | Estado, validacion base y locks eager; servicios/kernels y copia runtime diferidos. |
| `Directory.__init__` | Instantanea eager; accesores sin resolucion dinamica. |
| Dataclasses / `__post_init__` | Validacion eager al construir; lecturas Env mediante factories. |
| `Configuration` | Construir las secciones solicitadas; no esconder validacion en el primer acceso. |
| Defaults y providers core | Importar al solicitarlos; no cachear instancias dependientes de Env. |
| Modulos de paneles HTTP | Cargar durante lifespan, no por peticion ni por despacho CLI ordinario. |

No se aplico `slots=True` indiscriminadamente a dataclasses publicas: cambiaria
`__dict__`, referencias debiles y comportamiento de subclases para objetos
principalmente de arranque. Las anotaciones requeridas por DI, como
`Directory(app: IApplication)`, conservan el tipo real importado en runtime.

## Comportamiento Conservado

`Application` es singleton por clase. `create()` registra configuracion y
servicios; la disponibilidad HTTP se completa durante lifespan. Los locks de
primera carga y arranque de providers se mantienen, incluidos reintentos tras
fallo y cancelacion. No se agregaron locks ni tareas al despacho HTTP caliente.

El orden de configuracion sigue siendo defaults, setters fluidos y dataclasses
descubiertas. La configuracion compilada evita repetir esa carga; cambiar
metadatos del framework sigue exigiendo invalidar su cache de bootstrap.

`config()` expone mapas mutables vivos. Los lectores deben observar sus cambios:
por eso no se cachean valores ni getters ligados a un diccionario padre.
`resetRuntimeConfig()` restaura la instantanea congelada. Flags debug/produccion
y politica de monitorizacion siguen fijados en el arranque.

El polling de mantenimiento conserva su ventana de 100 ms y su lectura periodica
de filesystem. Cambiarlo por tareas de fondo o por otra semantica de frescura
requeriria un contrato operativo distinto. La configuracion mutable no adquiere
garantias de escrituras simultaneas entre hilos por tener metadatos cacheados.

Se documentaron los cinco metodos que carecian de una seccion de resultado y se
corrigio el resumen no imperativo de Mail. Las 390 definiciones tienen anotaciones
y resultados NumPy, sin seccion Examples. Los nombres de metodos son camelCase;
funciones fuera de clases son snake_case; protocolos Python/Granian se preservan.

## Verificacion Y Limites

Las pruebas usan el runner reactor y el venv del repositorio. El resumen Rich
puede ocultar subtests fallidos: se inspeccionaron tambien `testsRun`, `failures`
y `errors` del resultado de `TestRunner.run()`, sin modificar el runner.

Resultados de las regresiones ejecutadas:

| Suite | Resultado |
| --- | --- |
| Container | 243/243. |
| View | 205/205. |
| Mail | 193/193. |
| Logging | 176/176. |
| Storage | 242/242. |
| Foundation | 146/153; 7 tests con 31 fallos y 6 errores de subtests previos. |
| HTTP | 738 ejecutados; 1 test de paridad de stub con 1 fallo y 1 error previos. |
| Database | 238 ejecutados; 1 error previo del test de mass assignment de User. |

Se agregaron 24 pruebas. El fallo previo de autocancelacion HTTP si se corrigio
en su fixture: ahora el
kernel espera que el monitor entre antes de cancelarse. Mantiene la asercion de
limpieza y las 28 pruebas de transporte pasan. No se cambio el despacho real.

Los siete tests de configuracion restantes tratan diferencias de defaults,
declaraciones de opciones en plantillas, nulabilidad Oracle y precedencia Env de
logging. El stub del router difiere en `group` y carece de `export`. El test SQL
espera rechazar `active`, pero el modelo lo incluye en `fillable`. No se modifican
esas superficies para hacer aparecer una suite verde.

Ruff se comprueba sobre todo foundation y sus tests. SonarQube IDE se ejecuto
sobre los archivos modificados; no sustituye un Quality Gate remoto ni una
certificacion de Security Hotspots.

Los benchmarks usan siete rondas intercaladas, 10,000 construcciones o 100,000
normalizaciones por ronda, y procesos independientes para imports. El JSON
registra muestras y commit base. La memoria de imports es `tracemalloc`, no RSS.
Hubo variacion considerable de carga del equipo. No se midieron throughput HTTP,
p99, Python free-threaded, otros sistemas operativos ni servicios externos.

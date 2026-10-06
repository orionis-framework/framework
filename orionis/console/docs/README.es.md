# orionis.console

> Descubre y ejecuta comandos CLI, imprime salida, genera archivos y declara tareas programadas.

Versión en inglés: [README.md](README.md).

## Tabla de contenidos

- [Requisitos](#requisitos)
- [Descripción funcional](#descripción-funcional)
- [Estructura del módulo](#estructura-del-módulo)
- [Referencia de API](#referencia-de-api)
- [Ejemplos de uso](#ejemplos-de-uso)
- [Características de diseño](#características-de-diseño)
- [Rendimiento y concurrencia](#rendimiento-y-concurrencia)
- [Notas de compatibilidad](#notas-de-compatibilidad)
- [Verificación y limitaciones](#verificación-y-limitaciones)

## Requisitos

Python `>=3.14` y las restricciones de dependencias provienen de
[../../../pyproject.toml](../../../pyproject.toml). El CLI usa la aplicación
y contenedor del framework; importar una fachada no inicializa su servicio.
El launcher [../../../reactor](../../../reactor) carga el bootstrap de la
aplicación y llama a `Application.handleCommand` mediante `Loop.run`.
Los ejemplos sin servidor crean aplicaciones temporales aisladas. Evidencia:
[../../foundation/application.py](../../foundation/application.py),
`Application.boot` y `handleCommand`.

La preparación adicional depende de la operación:

- El descubrimiento necesita `app_console_commands` y rutas console
  configuradas. `Loader` importa módulos Python; sus cuerpos pueden ejecutarse.
  La metadata compilada usa `app.compiledPath` y rutas monitoreadas.
- El scheduler usa `config("scheduler")`, normalizada por `ScheduleStore`
  a la entidad externa. Memory no requiere servicios; Redis exige un servidor
  accesible. El job store database necesita el driver síncrono de una conexión
  configurada, no solo su driver async.
- `serve` necesita una entrada de aplicación válida y Granian; puede reemplazar
  el proceso Unix o lanzar un subprocess o servidor embebido en Windows.
- `install` exige `pyproject.toml` de aplicación y `uv` en PATH para instalar.
  Cambia los paquetes del intérprete, no el manifiesto o lockfile. Listar no
  instala.
- Los comandos de base de datos, colas, MCP y caché de aplicación necesitan
  servicios, configuración y recursos o datos autorizados reales. Los helpers
  interactivos necesitan stdin; los secretos se leen mediante `getpass`.

Fuentes: [../core/loader.py](../core/loader.py), `Loader`;
[../tasks/store.py](../tasks/store.py), `ScheduleStore`;
[../commands/serve/serve.py](../commands/serve/serve.py), `ServerCommand`;
[../commands/support/install.py](../commands/support/install.py), `InstallCommand`;
[../output/console.py](../output/console.py), `Console`. Esta tarea documental
no incluye instalación global de dependencias ni limpieza del checkout.

## Descripción funcional

El módulo define argumentos, descubrimiento, despacho, salida, plantillas de
generación y scheduling. `KernelCLI` selecciona una firma; `Reactor` resuelve
metadata mediante `Loader`, parsea argumentos, construye el handler con el
contenedor y reporta su resultado. `Schedule` registra declaraciones de tareas
fluidas con APScheduler, mientras los helpers de salida sirven al CLI y a
diagnósticos HTTP.

### Límites de ejecución

`KernelCLI.boot(application)` resuelve `IReactor`; `handle` requiere ese
reactor guardado. Acepta una lista o `None`, rechaza otros tipos con
`TypeError`, elimina un primer token que contenga `"reactor"`, retira tokens
iniciales de `IGNORE_FLAGS` y despacha `list` ante entrada vacía o help.
Muta la lista suministrada al retirar tokens. Evidencia:
[../kernel.py](../kernel.py), `KernelCLI.handle`.

`Reactor.call` entra en un scope, fija `kernel=CONSOLE` e inicia un contador
compartido antes de su `try` de ejecución. Valida la firma, resuelve metadata,
parsea argumentos, construye la clase y llama a su método declarado.
Las instancias `IBaseCommand` reciben valores parseados con `setArguments`;
los otros handlers reciben kwargs directamente. Un resultado entero se
retorna sin cambios, incluidos bool de Python; otros resultados se vuelven `0`.

Las `Exception` de ejecución se registran, cronometran, imprimen como FAIL
si corresponde y se entregan a `ICatch.exception`; luego se convierten a `1`
si el reporte tiene éxito. Los fallos de infraestructura fuera del try o
dentro del reporte pueden propagarse. `SystemExit`, cancelación y otras
subclases de `BaseException` no se convierten mediante ese manejador.
Help y errores de parser imprimen ayuda Rich y salen con `sys.exit`.
`clear:logs` exitoso omite deliberadamente el log de finalización. Evidencia:
[../core/reactor.py](../core/reactor.py), `Reactor.call` y
`Reactor.__parseCommandArgs`.

**Discrepancia de docstring:** `Reactor.call` lista `ValueError` por comando
ausente en Raises, pero la implementación normal lo reporta y retorna `1`.
Sus límites de scope, contador y reporte definen el comportamiento, no una
promesa absoluta de que no escape ningún error. Se comprobaron tres casos
locales de control de flujo.

## Estructura del módulo

Se inspeccionaron los 140 archivos Python y las 24 plantillas `.stub`.
El apéndice de declaraciones enlaza cada archivo Python, incluidos
inicializadores vacíos; el catálogo de plantillas enlaza todos los recursos
de ejecución no Python.

| Área | Responsabilidad |
| --- | --- |
| Raíz y `base/` | Exportaciones diferidas, `KernelCLI`, providers y bases de comandos, scheduler y listeners. |
| `args/`, `entities/`, `enums/` | Dataclass Argument, payloads de comandos, tareas y eventos, y enums de acciones, estados, eventos y ANSI. |
| `core/` | Registro de comandos, loader, reactor y contratos. |
| `fluent/`, `tasks/` | Builders de comandos y tareas, servicio scheduler, factory de job stores y contratos. |
| `output/`, `debug/`, `dynamic/` | Consola, executor, parser de ayuda, printer HTTP, dumper, helpers que terminan el proceso y barra de progreso. |
| `commands/` | Clases de comandos integrados y helpers de base de datos, generación, señales y limpieza. |
| `templates/` | `Stub` y 24 plantillas fuente. |
| `stdio.py` | Reserva contextual de stdout de protocolo MCP y redirección de diagnósticos. |

### Catálogo de plantillas

`Stub` carga estos archivos relativos a su módulo, sustituye placeholders
admitidos y crea el destino. Son recursos de generación, no scripts
ejecutables directamente ni exportaciones Python adicionales.

| Recurso | Plantilla empaquetada |
| --- | --- |
| [orionis/console/templates/console_command.stub](../templates/console_command.stub) | `console_command` |
| [orionis/console/templates/console_listener.stub](../templates/console_listener.stub) | `console_listener` |
| [orionis/console/templates/contract.stub](../templates/contract.stub) | `contract` |
| [orionis/console/templates/database_migration.stub](../templates/database_migration.stub) | `database_migration` |
| [orionis/console/templates/database_schema.stub](../templates/database_schema.stub) | `database_schema` |
| [orionis/console/templates/database_seeder.stub](../templates/database_seeder.stub) | `database_seeder` |
| [orionis/console/templates/facade.stub](../templates/facade.stub) | `facade` |
| [orionis/console/templates/facade_interface.stub](../templates/facade_interface.stub) | `facade_interface` |
| [orionis/console/templates/factory.stub](../templates/factory.stub) | `factory` |
| [orionis/console/templates/http_controller.stub](../templates/http_controller.stub) | `http_controller` |
| [orionis/console/templates/http_middleware.stub](../templates/http_middleware.stub) | `http_middleware` |
| [orionis/console/templates/http_schema.stub](../templates/http_schema.stub) | `http_schema` |
| [orionis/console/templates/http_schema_rule.stub](../templates/http_schema_rule.stub) | `http_schema_rule` |
| [orionis/console/templates/job.stub](../templates/job.stub) | `job` |
| [orionis/console/templates/mail.stub](../templates/mail.stub) | `mail` |
| [orionis/console/templates/mcp_prompt.stub](../templates/mcp_prompt.stub) | `mcp_prompt` |
| [orionis/console/templates/mcp_resource.stub](../templates/mcp_resource.stub) | `mcp_resource` |
| [orionis/console/templates/mcp_server.stub](../templates/mcp_server.stub) | `mcp_server` |
| [orionis/console/templates/mcp_tool.stub](../templates/mcp_tool.stub) | `mcp_tool` |
| [orionis/console/templates/model.stub](../templates/model.stub) | `model` |
| [orionis/console/templates/provider_deferred.stub](../templates/provider_deferred.stub) | `provider_deferred` |
| [orionis/console/templates/provider_eager.stub](../templates/provider_eager.stub) | `provider_eager` |
| [orionis/console/templates/service.stub](../templates/service.stub) | `service` |
| [orionis/console/templates/test.stub](../templates/test.stub) | `test` |

## Referencia de API

La sección de [declaraciones literales](#declaraciones-literales) copia
declaraciones públicas con decoradores, anotaciones, predeterminados y campos.
Los fragmentos de cabecera son referencia, no ejemplos ejecutables. Los grupos
de comportamiento siguientes explican parámetros, resultados, efectos y
límites de excepciones. Se identifica el comportamiento heredado en vez de
copiarlo como métodos recién declarados.

### Imports y nombres coincidentes

La raíz [../__init__.py](../__init__.py) exporta de forma diferida `Argument`,
`Console`, `Dumper` y `ProgressBar`. Solicitar un nombre declarado importa y
guarda su objeto; las exportaciones desconocidas lanzan `AttributeError`.
`__dir__` lista nombres cargados y exportaciones sin resolverlas todas.
El mismo patrón se usa en [../base/__init__.py](../base/__init__.py) para
`BaseCommand`, `BaseScheduler`, `BaseTaskListener`, y en
[../contracts/__init__.py](../contracts/__init__.py) para `ISchedule`.

Otras reexportaciones son explícitas en
[../entities/__init__.py](../entities/__init__.py),
[../enums/__init__.py](../enums/__init__.py) y
[../fluent/__init__.py](../fluent/__init__.py). Los inicializadores vacíos no
reexportan las clases vecinas. Las fachadas `Reactor` y `Schedule` pertenecen
a `orionis.support.facades`, no a la raíz console.

Distingue nombres cortos idénticos: entidad `Command` frente a `Command`
fluido; entidad `Task` frente a `Task` fluido; flags enum de eventos frente
a payloads dataclass; `HelpCommand` de salida frente al comando `list`.
Cada entrada literal identifica su ruta. Imports de clases Rich, helpers
de typing como `T` y tablas privadas no son API adicionales de consola.

### Argument y declaraciones de comandos

`Argument` ([../args/argument.py](../args/argument.py)) se genera mediante
`@dataclass(kw_only=True, frozen=True, slots=True)`; su constructor se deriva
de los campos literales, no de un `__init__` explícito. `name_or_flags` es
obligatorio y se normaliza a tupla. Los defaults de `const` y `default` son
el centinela real `MISSING`, no `None`; los demás campos y defaults se copian
en el apéndice. `extra` tiene una factory de diccionario nuevo, pero sigue
siendo mutable dentro del objeto frozen.

La validación rechaza colecciones de flags vacías, elementos no string,
`-h`/`--help`, tipos incorrectos de action/nargs/type/choices/required/help/
metavar/dest/version/extra, nargs string incompatible y texto de versión
ausente para la acción version. `type_` no puede acompañar las cuatro acciones
constantes o bool. No valida anticipadamente toda combinación argparse,
spelling de acción, rango de nargs entero o duración de generadores.
Se comprueba iterabilidad de `choices` sin materializarlo.
`addToParser(parser)` siempre reenvía `default`, pasa campos presentes,
aplica `required` solo a flags opcionales y permite que `extra` sobrescriba
kwargs construidos. Se propagan errores de definición o conversión del
parser. El reactor elimina únicamente valores idénticos a `MISSING`.

`BaseCommand` ([../base/command.py](../base/command.py)) hereda `Console`.
`handle` lanza `NotImplementedError` hasta sobrescribirlo. `getArgument`
exige clave string y distingue ausencia de `None` almacenado.
`setArguments` exige diccionario y fusiona estado, no lo reemplaza;
`getArguments` retorna una copia superficial. `signature`, `description`,
`timestamps` y `arguments` son declaraciones consumidas por el loader,
no argumentos de constructor. No se copian las listas mutables de clase.

`Command` fluido ([../fluent/command.py](../fluent/command.py)) captura firma,
referencia concreta callable y método, por defecto `"handle"`. Comprueba
callability, tipo del método y presencia del atributo callable; no aplica
el regex de firmas de comandos base. `timestamp`, `description` y `arguments`
validan sus inputs inmediatos, mutan el builder y retornan `Self`.
Las listas se retienen, no se clonan. `get()` retorna
`(signature, CommandEntity)` con referencias a esas declaraciones. Reactor
normaliza un handler no-lista a `[handler, "__call__"]` antes de registrarlo.

### Estado del loader y reactor

`Loader` ([../core/loader.py](../core/loader.py)) necesita `compiled`, rutas,
routing y base path de aplicación. Solo crea persistencia en modo compilado.
`load` retorna `None`; `get(signature)` devuelve entidad o `None`; `all()`
retorna su diccionario vivo de comandos. Construye metadata, entidades y
parsers, no instancias de handlers. Las fuentes posteriores reemplazan firmas
previas: core, clases de aplicación definidas en su módulo descubierto y
luego rutas fluidas.

Las firmas base se recortan y validan con el regex completo
`[a-z][a-z0-9]*(?::[a-z][a-z0-9]*(?:-[a-z0-9]+)*)?`.
Firmas ausentes, vacías o inválidas lanzan `ValueError`; tipos incorrectos,
`TypeError`. Una descripción ausente o `None` tiene default; una descripción
declarada vacía o no string falla. Los argumentos deben ser una lista de
`Argument`. El guard de handler fluido comprueba callable con `__name__`,
aunque su descripción diga clase. El builder valida después el método.

El descubrimiento frío importa rutas console; metadata compilada puede
omitirlo. La caché monitorea rutas configuradas más `core/commands.py`, no
hashea automáticamente todos los cuerpos de comandos del framework.
La metadata guarda rutas de tipos, marcadores `"__MISSING__"` y choices
materializados; reconstruirla importa tipos y restaura `None` si no resuelve.
Un literal que coincida con el marcador no se escapa independientemente.
Los choices generadores pueden consumirse al serializar metadata. Los
parsers desactivan abreviación de opciones y existen incluso sin argumentos
personalizados. Registrar después de cargar cachés no tiene invalidación
pública aquí.

`Reactor` ([../core/reactor.py](../core/reactor.py)) requiere aplicación,
loader, executor, logger, catch y contador declarados. `command` es síncrono
y retorna el builder. `hasCommand` solicita una entidad al loader. `info`
guarda y retorna la misma lista ordenada de diccionarios con timestamps/
signature/description/arguments/object/method, excluyendo firmas con dobles
guiones bajos a ambos lados. Mutar esa lista afecta a llamadores posteriores.
`call` y sus fallos se describen en [Límites de ejecución](#límites-de-ejecución);
las excepciones arbitrarias de handlers y reporte no son exhaustivamente
enumerables.

### Consola y recursos de salida

`Console` ([../output/console.py](../output/console.py)) no tiene constructor
explícito. Los mensajes retornan `None`; banners añaden opcionalmente
timestamps DateTime y ANSI crudo; los textos añaden color o bold. `write`
reenvía kwargs de print; `writeLine`, `line`, `clearLine` y `newLine` escriben
stdout, y `newLine` rechaza cantidades no positivas. `clear` solo emite su
secuencia de terminal cuando stdout es TTY.

Los inputs son síncronos: `ask` retorna input; `confirm` convierte a mayúsculas
y acepta `Y`/`YES`, usando default solo ante entrada vacía; `secret` usa
getpass. `anticipate` retorna la primera coincidencia de prefijo o fallback;
`choice` valida lista no vacía e índice default y repite hasta un número
válido. Pueden propagarse errores EOF, input, output y conversión.
`table` rechaza headers o filas vacíos, dibuja bordes manuales y usa zip
normal, no validación estricta de anchura de filas. `exception` exige una
`Exception` y muestra traceback Rich. No promete layouts exactos de terminal.

`progressBar` es de solo lectura y crea una `ProgressBar` cada vez.
`sleep(seconds)` espera asyncio sleep. `exitSuccess`/`exitError` llaman a
sys.exit y capturan su `SystemExit` antes de llamar a os._exit: el uso normal
termina el proceso sin la limpieza ordinaria. No se ejecutan en el host de
validación. `dump` configura un `VarDumper` nuevo; sus defaults difieren de
los defaults estáticos de `Dumper`.

`ProgressBar` ([../dynamic/progress_bar.py](../dynamic/progress_bar.py)) captura
write y flush de stdout en el constructor. Su estado público es `total`,
`bar_width` y `progress`; no añade validación de positividad o tipo.
`start` reinicia, `advance` limita solo por encima del total, y `finish`
completa y escribe newline. Total cero puede dividir por cero al dibujar;
no se limita progreso negativo. Mezclar writers puede intercalar el display.

`Executor` ([../output/executor.py](../output/executor.py)) imprime líneas
RUNNING/DONE/FAIL con timestamps; las cadenas `program` y `time` afectan al
relleno. `HelpCommand` de salida
([../output/help_command.py](../output/help_command.py)) parsea acciones
argparse a help/positionals/optionals/subcommands y las imprime; lee
recursivamente internals del parser y no invoca comandos.

`VarDumper` ([../output/var_dumper.py](../output/var_dumper.py)) retiene una
lista con copias profundas de los valores. Las opciones booleanas exigen
bool; depth/module/line validan sus tipos inmediatos y retornan la instancia.
`values(*args)` añade cada argumento; `value` añade uno. Print reutiliza
valores retenidos y avanza índices; resolver caller y grabar Rich son estado
de instancia. `toHtml` omite el header, llama a `print`, restaura el flag y
exporta HTML grabado: también escribe en consola. Se propagan errores de
deepcopy, Rich y output. `forceExit` puede terminar con código 1; redirection
cambia temporalmente stdout/stderr del proceso. Los estáticos `Dumper.dump`
y `Dumper.dd` ([../debug/dumper.py](../debug/dumper.py)) construyen esas cadenas;
dd activa salida forzada, no un retorno del dato mostrado.

### Printer HTTP y stdio de protocolo

`HTTPRequestPrinter` ([../output/http_request.py](../output/http_request.py))
captura ancho de terminal, callbacks stdout y un timestamp inicial compartido.
`setEnabled` activa output; `startTimer` retorna perf-counter o `None` si está
desactivado. `printRequest(adapter, response)` necesita printer y timer,
omite rutas `/.well-known/`, formatea método, ruta, estado y duración y encola
o escribe directamente. Sus diccionarios públicos de color y
`HTTP_MIN_STATUS_CODE=100` configuran el formato. No tiene timer por request.

`start` crea una cola de 1.000 entradas y worker; no protege un start repetido.
Si se llena, descarta líneas silenciosamente. `stop` espera terminar la cola,
cancela y espera el worker y limpia referencias. Los errores de output del
worker no se capturan alrededor de task_done; no se declara garantía general
de drain/stop ante fallo del writer. Sin start, stdout I/O es síncrono.

`protocol_stdio(arguments)` ([../stdio.py](../stdio.py)) es un contextmanager
síncrono generado desde una función con yield. Reconoce `mcp:start` en índice
cero o después de una primera ruta cuyo stem sea `reactor`; no retira todos
los flags de intérprete como KernelCLI. Guarda stdout binario original en
ContextVar, redirige stdout textual a stderr y restaura ambos al salir.
Los contextos anidados reutilizan un writer existente. `protocol_stdout()`
retorna ese writer o `None`; stdout sin `buffer` puede dar `None`.
La selección contextual no vuelve thread-safe la redirección global.

### Scheduling y comportamiento de listeners

`ScheduleStore` ([../tasks/store.py](../tasks/store.py)) captura una entidad
desde `app.config("scheduler")` y un connection manager. `store` y `config`
de solo lectura exponen la entidad. `redis()` construye RedisJobStore con
host/port/db/password/key configurados. `database()` construye
SQLAlchemyJobStore síncrono con config de conexión y tabla; los imports
de driver ausentes se traducen mediante el helper de dependencias database.
Config de store ausente lanza `RuntimeError`; otros errores pueden propagarse.
Este servicio no declara close.

`Schedule` ([../tasks/schedule.py](../tasks/schedule.py)) comienza STOPPED.
`command` valida firma y lista de argumentos, crea `ITask` y reemplaza una
declaración de igual firma; construir purpose no equivale a validar con su
setter. `on` acepta un evento enum y callable, uno por evento. Ambos rechazan
registro fuera de STOPPED. No existe mutador público `Schedule.store(...)`;
la elección del job store se captura de configuración.

`info` carga y guarda firmas reactor disponibles, valida disponibilidad de
tareas y triggers y retorna una nueva lista de diccionarios. `boot` materializa
jobs, añade memory y almacenamiento persistente configurado, registra
máscaras, añade jobs con `replace_existing` de configuración, desactiva tres
loggers APScheduler globalmente, fija RUNNING e inicia el scheduler. No
protege boot repetido y fija RUNNING antes de confirmar éxito de start.

El callable de job es `_execute_scheduled_command` a nivel de módulo y
despacha mediante la fachada externa Reactor. El nombre privado compatible
`_executeScheduledCommand` sigue como alias para jobs persistidos previos;
no es nueva API pública. Los kwargs de tareas aparecen en entity/info, pero
este callable registrado de signature/args no los pasa.

Los listeners por tarea pasan a diccionario por evento; duplicados reemplazan
el anterior con un warning. Callbacks sync se ejecutan directamente; funciones
corrutina reconocidas usan tareas gestionadas. Un callable sync que retorne
awaitable no se espera después por estos dispatchers. Las `Exception` de
listeners van a ICatch con logging; fallos al reportarlas aún pueden importar.
Los hooks de BaseScheduler son integración de declaración o ciclo de vida,
no salida console; `BaseTaskListener` hereda Console y da hooks sin operación.

Los controles pausan, reanudan o eliminan jobs y estado, retornando bool
exitoso. Errores previos al arranque o de estado son RuntimeError; jobs
ausentes de APScheduler pueden lanzar ValueError; errores capturados de
backend se envuelven en RuntimeError. `shutdown(wait)` valida un int opcional
no negativo excluyendo bool y crea una tarea gestionada de limpieza.
La espera default retenida es 0.5 segundos; `wait()` espera el evento fijado
solo después del trabajo. La limpieza espera una instantánea de listeners
pendientes y hace shutdown en executor. No reinicia estado a STOPPED ni
limpia el evento para reutilizarlo. Un fallo previo a event.set puede dejar
wait pendiente.

### Triggers Task y payloads

`Task` fluido ([../fluent/task.py](../fluent/task.py)) retiene signature, args,
kwargs, purpose y timezone de DateTime. `entity` exige firma truthy y trigger
configurado; retorna un dataclass nuevo con referencias compartidas de args,
kwargs, listeners y trigger. Las opciones explícitas ganan con `is not None`,
incluido coalesce falso o delay cero.

Los métodos de configuración retornan Self; los triggers retornan bool,
normalmente True, y sobrescriben trigger. No encadenes un setter desde el
retorno de un trigger. Intervalos positivos usan IntervalTrigger; variantes
At, CronTrigger; fechas únicas, DateTrigger. Los límites y defaults exactos
se declaran en el apéndice. Rangos de minuto/segundo/hora son 0-59, 0-59,
0-23; datetime también exige calendario válido. Algunos setters validan
tipos de forma distinta y ciertos checks int aceptan bool; anotar no convierte.

`randomDelay(max_seconds=10)` elige un entero de 0 a max_seconds, exige int
de 0 a 120 y modifica jitter del trigger existente si está presente.
Jitter positivo se rechaza al configurar seconds o onceAt; configurar delay
después usa otra ruta. Start/end guardan límites para construir triggers
posteriores, no parchean todos los campos ya existentes.
`everyMinutesAt`, `everyHoursAt`, `everyDaysAt` significan campos de calendario
con pasos, no intervalos móviles arbitrarios. Weekly usa domingo a medianoche.
`cron` exige al menos un campo no None y delega validación a APScheduler.
Se propagan errores de fecha o trigger que no se manejen explícitamente.

Las entidades ([../entities/__init__.py](../entities/__init__.py)) son
dataclasses mutables keyword-only que heredan helpers BaseEntity. Los campos
literales documentan constructores generados; sus decoradores no son frozen
ni slots. Command args puede ser lista Argument o parser. Los listeners Task
se anotan como lista callable, pero el builder guarda tuplas `(event, callback)`.
Event __post_init__ reemplaza description desde code, incluido el fallback
desconocido. Los enums y sus miembros se copian en el apéndice; flags de
eventos son máscaras IntEnum, no payloads.

### Generadores y API auxiliares

`Stub` ([../templates/stub.py](../templates/stub.py)) retiene template/name/
prefix/postfix/replacements y deriva nombres de forma diferida. `create`
normaliza extensión, valida nombres con patrones de módulo minúsculo,
carga UTF-8, sustituye strings, crea directorios y abre el destino exclusivamente.
El destino existente lanza FileExistsError; plantilla ausente FileNotFoundError;
nombres/extensión/resultado relativo inválidos ValueError; tipos incorrectos
de reemplazo o extensión TypeError. Se propagan otros errores I/O. La
contención relativa se comprueba después de escribir y no deshace el archivo.
Prefix afecta a la clase, pero no se antepone al filename. No necesariamente
se eliminan placeholders desconocidos.

`MakeStubCommand` y sus sobrescrituras públicas retornan diccionarios de
reemplazos, nombres de plantilla, cadenas de ruta o tuplas `(label, path)`
como se declara. Handle async usa to_thread para renderizar y escribir,
y captura OSError/TypeError/ValueError seleccionados para reportarlos.
Estos fallos reportados no tienen por qué producir retorno no cero. No se
revierte generación parcial de varios archivos. El catálogo identifica
firmas, argumentos y rol de ruta de cada subclase.

`DatabaseInspector` en el módulo privado
[../commands/db/_inspection.py](../commands/db/_inspection.py) se documenta
como clase auxiliar nombrada, no fachada raíz. Expone connection/config/driver/
name y consulta metadata por dialecto. Quoting escapa delimitadores; falla con
componentes vacíos. List retorna nombres; count/size, ints o None donde se
soporten; tableDetails retorna name/rows/size/columns/indexes/foreign_keys,
validando una tabla resuelta unívocamente. Resultados y permisos dependen de
la conexión. `format_bytes` en db.show muestra None como N/A y unidades binarias.

`DatabaseWiper.wipe` retorna el `WipeResult(tables, views, types)` generado
tras DDL destructivo por dialecto, orden de dependencias y manejo seleccionado
de transacciones o foreign keys. No es universalmente reversible.
`WorkerSignals` registra stop handlers solo en el hilo principal y los restaura.
`clear_files` recorre sufijos y retorna `(removed_count, errors)`; es helper
de módulo privado, no API segura de limpieza global del repo. Sus declaraciones
y puntos de uso se enlazan en el apéndice.

### Catálogo de comandos integrados

`CORE_COMMANDS` y `get_core_commands_mapping` se definen en
[../core/commands.py](../core/commands.py). Se verificaron **58** firmas core
únicas. Atributos de subclase y argumentos heredados definen su CLI; los
métodos pueden tener parámetros DI que no son flags. El catálogo se obtiene
de clases y `Argument` reales, no de documentación anterior.

| Firma | Clase y fuente | Argumentos CLI | Operación declarada |
| --- | --- | --- | --- |
| `about` | [VersionCommand](../commands/support/about.py) | `None` | Displays the Orionis framework version and metadata. |
| `clear:cache` | [ClearCacheCommand](../commands/support/clear_cache.py) | `None` | Clear entries from the default application cache store. |
| `clear:logs` | [ClearLogsCommand](../commands/support/clear_logs.py) | `None` | Clear framework log files. |
| `clear:testing` | [ClearTestingCommand](../commands/support/clear_testing.py) | `None` | Clear cached test-run results. |
| `clear:views` | [ClearViewsCommand](../commands/support/clear_views.py) | `None` | Clear compiled view templates. |
| `db:seed` | [DbSeedCommand](../commands/db/seed.py) | `--database / -d` | Runs all pending database seeders. |
| `db:show` | [DbShowCommand](../commands/db/show.py) | `--database / -d; --counts; --views` | Shows database information and table summaries. |
| `db:table` | [DbTableCommand](../commands/db/table.py) | `table; --database / -d` | Shows columns, indexes and keys for a database table. |
| `db:wipe` | [DbWipeCommand](../commands/db/wipe.py) | `--database / -d; --force` | Drop all user tables, views, and types in a database. |
| `down` | [DownCommand](../commands/support/down.py) | `None` | Put the application into maintenance mode. |
| `env` | [EnvironmentCommand](../commands/support/environment.py) | `None` | Display the current application environment. |
| `install` | [InstallCommand](../commands/support/install.py) | `options; --list; --yes / -y` | Install optional dependencies and dependency groups. |
| `key:generate` | [KeyGenerateCommand](../commands/support/key_generate.py) | `--force` | Generate the application encryption key. |
| `list` | [HelpCommand](../commands/support/list.py) | `None` | Show available commands and usage. |
| `make:console-command` | [MakeConsoleCommand](../commands/make/console.py) | `name; --signature / -s; --description / -d` | Creates a new custom console command. |
| `make:console-listener` | [MakeConsoleListener](../commands/make/console_listener.py) | `name` | Creates a new console task listener class. |
| `make:contract` | [MakeContract](../commands/make/contract.py) | `name` | Creates a new contract class. |
| `make:database-migration` | [MakeDatabaseMigration](../commands/make/database_migration.py) | `name` | Creates a timestamped database migration. |
| `make:database-schema` | [MakeDatabaseSchema](../commands/make/database_schema.py) | `name` | Creates a reusable database table schema. |
| `make:database-seeder` | [MakeDatabaseSeeder](../commands/make/database_seeder.py) | `name` | Creates a database seeder. |
| `make:facade` | [MakeFacade](../commands/make/facade.py) | `name; --accessor / -a` | Creates a new facade class and interface. |
| `make:factory` | [MakeFactory](../commands/make/factory.py) | `name; --model / -m` | Creates a model factory in the database directory. |
| `make:http-controller` | [MakeHttpController](../commands/make/http_controller.py) | `name; --invoke; --api` | Creates an invokable or resource HTTP controller. |
| `make:http-middleware` | [MakeHttpMiddleware](../commands/make/http_middleware.py) | `name` | Creates a new HTTP middleware class. |
| `make:http-schema` | [MakeHttpSchema](../commands/make/http_schema.py) | `name` | Creates a custom HTTP validation schema. |
| `make:http-schema-rule` | [MakeHttpSchemaRule](../commands/make/http_schema_rule.py) | `name` | Creates a custom validation rule. |
| `make:job` | [MakeJob](../commands/make/job.py) | `name` | Create an asynchronous queue job. |
| `make:mail` | [MakeMail](../commands/make/mail.py) | `name` | Creates a reusable mail notification class. |
| `make:mcp-prompt` | [MakeMcpPrompt](../commands/make/mcp.py) | `name` | Create a new MCP prompt. |
| `make:mcp-resource` | [MakeMcpResource](../commands/make/mcp.py) | `name` | Create a new MCP resource. |
| `make:mcp-server` | [MakeMcpServer](../commands/make/mcp.py) | `name` | Create a new MCP server. |
| `make:mcp-tool` | [MakeMcpTool](../commands/make/mcp.py) | `name` | Create a new MCP tool. |
| `make:model` | [MakeModel](../commands/make/model.py) | `name` | Creates a new ORM model class. |
| `make:provider` | [MakeProvider](../commands/make/provider.py) | `name; --deferred` | Creates a new provider class file. |
| `make:service` | [MakeService](../commands/make/service.py) | `name` | Creates a new service class. |
| `make:test` | [MakeTest](../commands/make/test.py) | `name` | Creates a new application test case. |
| `mcp:list` | [McpListCommand](../commands/mcp/list.py) | `None` | List registered HTTP and local MCP servers. |
| `mcp:start` | [McpStartCommand](../commands/mcp/start.py) | `name` | Start a registered MCP 2026-07-28 server over STDIO. |
| `migrate` | [MigrateCommand](../commands/migrate/migrate.py) | `--database / -d; --seed` | Runs all pending database migrations. |
| `migrate:fresh` | [MigrateFreshCommand](../commands/migrate/fresh.py) | `--database / -d` | Clears migration and seeder history, then migrates. |
| `migrate:refresh` | [MigrateRefreshCommand](../commands/migrate/refresh.py) | `--database / -d; --step / -s` | Rolls back and re-applies database migrations. |
| `migrate:reset` | [MigrateResetCommand](../commands/migrate/reset.py) | `--database / -d` | Reverts every applied database migration. |
| `migrate:rollback` | [MigrateRollbackCommand](../commands/migrate/rollback.py) | `--database / -d; --step / -s` | Reverts the last batch(es) of database migrations. |
| `migrate:status` | [MigrateStatusCommand](../commands/migrate/status.py) | `--database / -d` | Shows the status of every discovered migration. |
| `optimize` | [OptimizeCommand](../commands/support/optimize.py) | `None` | Compile application Python files to optimized bytecode. |
| `optimize:clear` | [OptimizeClearCommand](../commands/support/optimize_clear.py) | `None` | Removes compiled configuration, route, and command caches, Python bytecode, and build artifacts. |
| `queue:clear` | [QueueClearCommand](../commands/queue/clear.py) | `connection; --queue` | Delete ready, delayed, and reserved jobs from a queue. |
| `queue:failed` | [QueueFailedCommand](../commands/queue/failed.py) | `None` | List failed queue jobs. |
| `queue:forget` | [QueueForgetCommand](../commands/queue/forget.py) | `id` | Delete a failed job by its identifier. |
| `queue:retry` | [QueueRetryCommand](../commands/queue/retry.py) | `id` | Retry a failed job by its identifier. |
| `queue:work` | [QueueWorkCommand](../commands/queue/work.py) | `connection; --queue; --concurrency; --max-jobs; --stop-when-empty` | Consume queued jobs with retries and graceful shutdown. |
| `route:list` | [RouteListCommand](../commands/route/list.py) | `None` | List the application's registered HTTP routes. |
| `schedule:list` | [ScheduleListCommand](../commands/schedule/list.py) | `None` | Lists all scheduled jobs defined in the application. |
| `schedule:work` | [ScheduleWorkCommand](../commands/schedule/work.py) | `None` | Run the scheduled tasks defined by the application. |
| `seed` | [SeedCommand](../commands/seed/seed.py) | `--database / -d` | Runs all pending database seeders. |
| `serve` | [ServerCommand](../commands/serve/serve.py) | `--interface / -i; --port / -p; --log; --export` | Initializes the Orionis server with Granian (The Rust HTTP server for Python). |
| `test` | [TestCommand](../commands/test/test.py) | `--verbosity / -v; --fail-fast / -f; --start-dir / -s; --file-pattern; --method-pattern; --panel; --no-panel` | Executes test cases defined in the project. |
| `up` | [UpCommand](../commands/support/up.py) | `None` | Bring the application out of maintenance mode. |

Entradas support, install, serve, scheduling, queue, MCP, database, migrate,
seed y make pueden tener efectos sustanciales. `install --list` solo lista;
selección y confirmación pueden instalar en el entorno de sys.executable con
`uv pip install --python ... -- ...`. Se expanden includes; ciclos y selecciones
ambiguas fallan; cancelar termina y espera el child. Los códigos distinguen
inputs inválidos, fallos e interrupción 130.

`db:wipe` elimina objetos y necesita --force sin terminal; migrate y seed
delegan en database. queue work y scheduler work pueden permanecer activos;
mcp:start sirve STDIO registrado; serve lanza Granian. clear:* elimina sus
datos/logs/cachés reales; down/up escribe mantenimiento. optimize escribe
bytecode; optimize:clear elimina archivos compilados conocidos, bytecode y
artefactos de build omitiendo carpetas de entorno. Test retorna 1 para
FAILED/ERRORED. Son comportamientos de entradas, no autorización para
ejecutarlos en este checkout.

### Declaraciones literales

Cada entrada da la ruta de propietario relativa al repositorio y declaración
original. Los campos dataclass explican constructores generados; se incluyen
constantes, miembros enum, atributos de comandos, exports y propiedades.
Los cuerpos abstractos suelen tener solo docstring, pero IBaseScheduler.tasks
lanza explícitamente NotImplementedError. Las ABC rechazan instanciación
incompleta sin exigir firmas runtime de sobrescritura. Se excluyen helpers
privados o imports del listado exhaustivo salvo los auxiliares necesarios
para explicar comportamiento.

#### __init__.py

Fuente: [orionis/console/__init__.py](../__init__.py).

`__all__`

```python
__all__ = [
    "Argument",
    "Console",
    "Dumper",
    "ProgressBar",
]
```

`__getattr__`

```python
def __getattr__(name: str) -> object:
```

`__dir__`

```python
def __dir__() -> list[str]:
```

#### args/__init__.py

Fuente: [orionis/console/args/__init__.py](../args/__init__.py).

Sin API pública declarada directamente; inicializador o soporte privado de integración.

#### args/argument.py

Fuente: [orionis/console/args/argument.py](../args/argument.py).

`Argument`

```python
@dataclass(kw_only=True, frozen=True, slots=True)
class Argument(BaseEntity):
```

`Argument fields`

```python
name_or_flags: str | Iterable[str]
action: str | ArgumentAction | None = None
nargs: int | str | None = None
const: Any = MISSING
default: Any = MISSING
type_: Callable[[str], Any] | None = None
choices: Iterable[Any] | None = None
required: bool = False
help: str | None = None
metavar: str | tuple[str, ...] | None = None
dest: str | None = None
version: str | None = None
extra: dict[str, Any] = field(default_factory=dict)
```

`Argument.__post_init__`

```python
def __post_init__(self) -> None: # NOSONAR
```

`Argument.addToParser`

```python
def addToParser(self, parser: argparse.ArgumentParser) -> None: # NOSONAR
```

#### base/__init__.py

Fuente: [orionis/console/base/__init__.py](../base/__init__.py).

`__all__`

```python
__all__ = [
    "BaseCommand",
    "BaseScheduler",
    "BaseTaskListener",
]
```

`__getattr__`

```python
def __getattr__(name: str) -> object:
```

`__dir__`

```python
def __dir__() -> list[str]:
```

#### base/command.py

Fuente: [orionis/console/base/command.py](../base/command.py).

`BaseCommand`

```python
class BaseCommand(Console, IBaseCommand):
```

`BaseCommand fields`

```python
timestamps: bool = True
signature: str
description: str
arguments: ClassVar[list[Argument]] = []
```

`BaseCommand.__init__`

```python
def __init__(self) -> None:
```

`BaseCommand.handle`

```python
async def handle(self) -> None:
```

`BaseCommand.getArgument`

```python
def getArgument(self, key: str, default: Any | None = None) -> Any | None:
```

`BaseCommand.getArguments`

```python
def getArguments(self) -> dict[str, Any]:
```

`BaseCommand.setArguments`

```python
def setArguments(self, args: dict[str, Any]) -> None:
```

#### base/contracts/__init__.py

Fuente: [orionis/console/base/contracts/__init__.py](../base/contracts/__init__.py).

Sin API pública declarada directamente; inicializador o soporte privado de integración.

#### base/contracts/command.py

Fuente: [orionis/console/base/contracts/command.py](../base/contracts/command.py).

`IBaseCommand`

```python
class IBaseCommand(ABC):
```

`IBaseCommand fields`

```python
timestamps: ClassVar[bool] = True
signature: ClassVar[str]
description: ClassVar[str]
arguments: ClassVar[list[Argument]] = []
```

`IBaseCommand.handle`

```python
@abstractmethod
async def handle(self) -> None:
```

`IBaseCommand.getArgument`

```python
@abstractmethod
def getArgument(self, key: str, default: Any = None) -> Any:
```

`IBaseCommand.getArguments`

```python
@abstractmethod
def getArguments(self) -> dict[str, Any]:
```

`IBaseCommand.setArguments`

```python
@abstractmethod
def setArguments(self, args: dict[str, Any]) -> None:
```

#### base/contracts/listener.py

Fuente: [orionis/console/base/contracts/listener.py](../base/contracts/listener.py).

`IBaseTaskListener`

```python
class IBaseTaskListener(ABC):
```

`IBaseTaskListener.onTaskAdded`

```python
@abstractmethod
async def onTaskAdded(self, event: TaskEvent) -> None:
```

`IBaseTaskListener.onTaskRemoved`

```python
@abstractmethod
async def onTaskRemoved(self, event: TaskEvent) -> None:
```

`IBaseTaskListener.onTaskExecuted`

```python
@abstractmethod
async def onTaskExecuted(self, event: TaskEvent) -> None:
```

`IBaseTaskListener.onTaskError`

```python
@abstractmethod
async def onTaskError(self, event: TaskEvent) -> None:
```

`IBaseTaskListener.onTaskMissed`

```python
@abstractmethod
async def onTaskMissed(self, event: TaskEvent) -> None:
```

`IBaseTaskListener.onTaskSubmitted`

```python
@abstractmethod
async def onTaskSubmitted(self, event: TaskEvent) -> None:
```

`IBaseTaskListener.onTaskMaxInstances`

```python
@abstractmethod
async def onTaskMaxInstances(self, event: TaskEvent) -> None:
```

#### base/contracts/scheduler.py

Fuente: [orionis/console/base/contracts/scheduler.py](../base/contracts/scheduler.py).

`IBaseScheduler`

```python
class IBaseScheduler(ABC):
```

`IBaseScheduler.tasks`

```python
@abstractmethod
async def tasks(self, schedule: ISchedule) -> None:
```

`IBaseScheduler.onStarted`

```python
@abstractmethod
async def onStarted(self, event: SchedulerEvent) -> None:
```

`IBaseScheduler.onPaused`

```python
@abstractmethod
async def onPaused(self, event: SchedulerEvent) -> None:
```

`IBaseScheduler.onResumed`

```python
@abstractmethod
async def onResumed(self, event: SchedulerEvent) -> None:
```

`IBaseScheduler.onShutdown`

```python
@abstractmethod
async def onShutdown(self, event: SchedulerEvent) -> None:
```

#### base/listener.py

Fuente: [orionis/console/base/listener.py](../base/listener.py).

`BaseTaskListener`

```python
class BaseTaskListener(Console, IBaseTaskListener):
```

`BaseTaskListener.onTaskAdded`

```python
async def onTaskAdded(self, event: TaskEvent) -> None:
```

`BaseTaskListener.onTaskRemoved`

```python
async def onTaskRemoved(self, event: TaskEvent) -> None:
```

`BaseTaskListener.onTaskExecuted`

```python
async def onTaskExecuted(self, event: TaskEvent) -> None:
```

`BaseTaskListener.onTaskError`

```python
async def onTaskError(self, event: TaskEvent) -> None:
```

`BaseTaskListener.onTaskMissed`

```python
async def onTaskMissed(self, event: TaskEvent) -> None:
```

`BaseTaskListener.onTaskSubmitted`

```python
async def onTaskSubmitted(self, event: TaskEvent) -> None:
```

`BaseTaskListener.onTaskMaxInstances`

```python
async def onTaskMaxInstances(self, event: TaskEvent) -> None:
```

#### base/scheduler.py

Fuente: [orionis/console/base/scheduler.py](../base/scheduler.py).

`BaseScheduler`

```python
class BaseScheduler(IBaseScheduler):
```

`BaseScheduler.tasks`

```python
async def tasks(self, schedule: ISchedule) -> None:
```

`BaseScheduler.onStarted`

```python
async def onStarted(self, event: SchedulerEvent) -> None:
```

`BaseScheduler.onPaused`

```python
async def onPaused(self, event: SchedulerEvent) -> None:
```

`BaseScheduler.onResumed`

```python
async def onResumed(self, event: SchedulerEvent) -> None:
```

`BaseScheduler.onShutdown`

```python
async def onShutdown(self, event: SchedulerEvent) -> None:
```

#### commands/__init__.py

Fuente: [orionis/console/commands/__init__.py](../commands/__init__.py).

Sin API pública declarada directamente; inicializador o soporte privado de integración.

#### commands/db/__init__.py

Fuente: [orionis/console/commands/db/__init__.py](../commands/db/__init__.py).

Sin API pública declarada directamente; inicializador o soporte privado de integración.

#### commands/db/_inspection.py

Fuente: [orionis/console/commands/db/_inspection.py](../commands/db/_inspection.py).

`DatabaseInspector`

```python
class DatabaseInspector:
```

`DatabaseInspector fields`

```python
__slots__ = ("config", "connection", "driver", "name")
```

`DatabaseInspector.__init__`

```python
def __init__(
    self,
    manager: IConnectionManager,
    name: str | None = None,
) -> None:
```

`DatabaseInspector.quoteIdentifier`

```python
def quoteIdentifier(self, name: str, *, qualified: bool = True) -> str:
```

`DatabaseInspector.listTables`

```python
async def listTables(self) -> list[str]:
```

`DatabaseInspector.listViews`

```python
async def listViews(self) -> list[str]:
```

`DatabaseInspector.listMaterializedViews`

```python
async def listMaterializedViews(self) -> list[str]:
```

`DatabaseInspector.viewCounts`

```python
async def viewCounts(self) -> tuple[int, int]:
```

`DatabaseInspector.listTypes`

```python
async def listTypes(self) -> list[str]:
```

`DatabaseInspector.listDomains`

```python
async def listDomains(self) -> list[str]:
```

`DatabaseInspector.databaseSize`

```python
async def databaseSize(self) -> int | None:
```

`DatabaseInspector.connectionCount`

```python
async def connectionCount(self) -> int | None:
```

`DatabaseInspector.rowCount`

```python
async def rowCount(self, name: str) -> int:
```

`DatabaseInspector.tableSize`

```python
async def tableSize(self, name: str) -> int | None:
```

`DatabaseInspector.tableSizes`

```python
async def tableSizes(self, tables: list[str]) -> dict[str, int]:
```

`DatabaseInspector.tableDetails`

```python
async def tableDetails(self, name: str) -> dict[str, Any]:
```

#### commands/db/seed.py

Fuente: [orionis/console/commands/db/seed.py](../commands/db/seed.py).

`DbSeedCommand`

```python
class DbSeedCommand(SeedCommand):
```

`DbSeedCommand fields`

```python
signature: str = "db:seed"
description: str = "Runs all pending database seeders."
```

#### commands/db/show.py

Fuente: [orionis/console/commands/db/show.py](../commands/db/show.py).

`format_bytes`

```python
def format_bytes(size: int | None) -> str:
```

`DbShowCommand`

```python
class DbShowCommand(MigrationCommand):
```

`DbShowCommand fields`

```python
timestamps: bool = False
signature: str = "db:show"
description: str = "Shows database information and table summaries."
arguments: ClassVar[list[Argument]] = [
        *MigrationCommand.arguments,
        Argument(
            name_or_flags="--counts",
            action="store_true",
            help="Count table rows (may be slow on large databases).",
            dest="counts",
        ),
        Argument(
            name_or_flags="--views",
            action="store_true",
            help="Include views in the output.",
            dest="views",
        ),
    ]
```

`DbShowCommand.handle`

```python
async def handle(self, conn_manager: IConnectionManager) -> None: # NOSONAR
```

#### commands/db/table.py

Fuente: [orionis/console/commands/db/table.py](../commands/db/table.py).

`DbTableCommand`

```python
class DbTableCommand(MigrationCommand):
```

`DbTableCommand fields`

```python
timestamps: bool = False
signature: str = "db:table"
description: str = "Shows columns, indexes and keys for a database table."
arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags="table",
            type_=str,
            help="Table name to inspect.",
        ),
        *MigrationCommand.arguments,
    ]
```

`DbTableCommand.handle`

```python
async def handle(self, conn_manager: IConnectionManager) -> int:
```

#### commands/db/wipe.py

Fuente: [orionis/console/commands/db/wipe.py](../commands/db/wipe.py).

`WipeResult`

```python
@dataclass(frozen=True, slots=True)
class WipeResult:
```

`WipeResult fields`

```python
tables: int
views: int
types: int
```

`DatabaseWiper`

```python
class DatabaseWiper:
```

`DatabaseWiper fields`

```python
__slots__ = ("_inspector",)
```

`DatabaseWiper.__init__`

```python
def __init__(self, inspector: DatabaseInspector) -> None:
```

`DatabaseWiper.wipe`

```python
async def wipe(self) -> WipeResult:
```

`DbWipeCommand`

```python
class DbWipeCommand(BaseCommand):
```

`DbWipeCommand fields`

```python
signature: str = "db:wipe"
description: str = "Drop all user tables, views, and types in a database."
arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags=["--database", "-d"],
            type_=str,
            required=False,
            help="Named connection to wipe; defaults to the default one.",
            dest="database",
        ),
        Argument(
            name_or_flags="--force",
            action=ArgumentAction.STORE_TRUE,
            default=False,
            help="Wipe without an interactive confirmation.",
        ),
    ]
```

`DbWipeCommand.handle`

```python
async def handle(self, conn_manager: IConnectionManager) -> int:
```

#### commands/make/__init__.py

Fuente: [orionis/console/commands/make/__init__.py](../commands/make/__init__.py).

Sin API pública declarada directamente; inicializador o soporte privado de integración.

#### commands/make/_base.py

Fuente: [orionis/console/commands/make/_base.py](../commands/make/_base.py).

`MakeStubCommand`

```python
class MakeStubCommand(BaseCommand):
```

`MakeStubCommand fields`

```python
template_name: ClassVar[str]
path_key: ClassVar[str]
success_label: ClassVar[str]
prefix: ClassVar[str | None] = None
postfix: ClassVar[str | None] = None
replacement_arguments: ClassVar[dict[str, str]] = {}
arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags="name",
            type_=str,
            required=True,
            help="The file and class name for the generated file.",
        ),
    ]
```

`MakeStubCommand.getTemplateName`

```python
def getTemplateName(self) -> str:
```

`MakeStubCommand.getReplacements`

```python
def getReplacements(self) -> dict[str, str]:
```

`MakeStubCommand.createFile`

```python
def createFile(
    self,
    app: IApplication,
    name: str,
    *,
    template_name: str | None = None,
    extension: str = "py",
    replacements: dict[str, str] | None = None,
) -> str:
```

`MakeStubCommand.createFiles`

```python
def createFiles(
    self,
    app: IApplication,
    name: str,
) -> tuple[tuple[str, str], ...]:
```

`MakeStubCommand.handle`

```python
async def handle(self, app: IApplication) -> None:
```

#### commands/make/console.py

Fuente: [orionis/console/commands/make/console.py](../commands/make/console.py).

`MakeConsoleCommand`

```python
class MakeConsoleCommand(MakeStubCommand):
```

`MakeConsoleCommand fields`

```python
timestamps: bool = False
signature: str = "make:console-command"
description: str = "Creates a new custom console command."
template_name: str = "console_command"
path_key: str = "app_console_commands"
success_label: str = "Console command"
postfix: str | None = "Command"
replacement_arguments: ClassVar[dict[str, str]] = {
        "signature": "signature",
        "description": "description",
    }
arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags="name",
            type_=str,
            required=True,
            help="The file and class name for the new console command.",
        ),
        Argument(
            name_or_flags=["--signature", "-s"],
            type_=str,
            required=True,
            help="The unique signature registered for the command.",
        ),
        Argument(
            name_or_flags=["--description", "-d"],
            type_=str,
            required=False,
            help="A short description shown in command help.",
        ),
    ]
```

`MakeConsoleCommand.getReplacements`

```python
def getReplacements(self) -> dict[str, str]:
```

`MakeConsoleCommand.handle`

```python
async def handle(
    self,
    app: IApplication,
    reactor: IReactor,
) -> None:
```

#### commands/make/console_listener.py

Fuente: [orionis/console/commands/make/console_listener.py](../commands/make/console_listener.py).

`MakeConsoleListener`

```python
class MakeConsoleListener(MakeStubCommand):
```

`MakeConsoleListener fields`

```python
timestamps: bool = False
signature: str = "make:console-listener"
description: str = "Creates a new console task listener class."
template_name: str = "console_listener"
path_key: str = "app_console_listeners"
success_label: str = "Console task listener"
postfix: str | None = "Listener"
```

#### commands/make/contract.py

Fuente: [orionis/console/commands/make/contract.py](../commands/make/contract.py).

`MakeContract`

```python
class MakeContract(MakeStubCommand):
```

`MakeContract fields`

```python
timestamps: bool = False
signature: str = "make:contract"
description: str = "Creates a new contract class."
template_name: str = "contract"
path_key: str = "app_contracts"
success_label: str = "Contract"
prefix: str | None = "I"
```

#### commands/make/database_migration.py

Fuente: [orionis/console/commands/make/database_migration.py](../commands/make/database_migration.py).

`MakeDatabaseMigration`

```python
class MakeDatabaseMigration(MakeStubCommand):
```

`MakeDatabaseMigration fields`

```python
timestamps: bool = False
signature: str = "make:database-migration"
description: str = "Creates a timestamped database migration."
template_name: str = "database_migration"
path_key: str = "database_migrations"
success_label: str = "Database migration"
```

`MakeDatabaseMigration.createFiles`

```python
def createFiles(
    self,
    app: IApplication,
    name: str,
) -> tuple[tuple[str, str], ...]:
```

#### commands/make/database_schema.py

Fuente: [orionis/console/commands/make/database_schema.py](../commands/make/database_schema.py).

`MakeDatabaseSchema`

```python
class MakeDatabaseSchema(MakeStubCommand):
```

`MakeDatabaseSchema fields`

```python
timestamps: bool = False
signature: str = "make:database-schema"
description: str = "Creates a reusable database table schema."
template_name: str = "database_schema"
path_key: str = "database_schemas"
success_label: str = "Database schema"
postfix: str | None = "Schema"
```

#### commands/make/database_seeder.py

Fuente: [orionis/console/commands/make/database_seeder.py](../commands/make/database_seeder.py).

`MakeDatabaseSeeder`

```python
class MakeDatabaseSeeder(MakeStubCommand):
```

`MakeDatabaseSeeder fields`

```python
timestamps: bool = False
signature: str = "make:database-seeder"
description: str = "Creates a database seeder."
template_name: str = "database_seeder"
path_key: str = "database_seeders"
success_label: str = "Database seeder"
postfix: str | None = "Seeder"
```

#### commands/make/facade.py

Fuente: [orionis/console/commands/make/facade.py](../commands/make/facade.py).

`MakeFacade`

```python
class MakeFacade(MakeStubCommand):
```

`MakeFacade fields`

```python
timestamps: bool = False
signature: str = "make:facade"
description: str = "Creates a new facade class and interface."
template_name: str = "facade"
path_key: str = "app_facades"
success_label: str = "Facade"
arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags="name",
            type_=str,
            required=True,
            help="The file and class name for the new facade.",
        ),
        Argument(
            name_or_flags=["--accessor", "-a"],
            type_=str,
            required=True,
            help="The service identifier in the application container.",
        ),
    ]
```

`MakeFacade.getReplacements`

```python
def getReplacements(self) -> dict[str, str]:
```

`MakeFacade.createFiles`

```python
def createFiles(
    self,
    app: IApplication,
    name: str,
) -> tuple[tuple[str, str], ...]:
```

#### commands/make/factory.py

Fuente: [orionis/console/commands/make/factory.py](../commands/make/factory.py).

`MakeFactory`

```python
class MakeFactory(MakeStubCommand):
```

`MakeFactory fields`

```python
__slots__ = ()
timestamps: bool = False
signature: str = "make:factory"
description: str = "Creates a model factory in the database directory."
template_name: str = "factory"
path_key: str = "database_factories"
success_label: str = "Model factory"
postfix: str | None = "Factory"
arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags="name",
            type_=str,
            required=True,
            help="The factory class or file name, for example UserFactory.",
        ),
        Argument(
            name_or_flags=["--model", "-m"],
            type_=str,
            required=False,
            help="Model name below app/models, for example User or sales/Order.",
        ),
    ]
```

`MakeFactory.createFiles`

```python
def createFiles(
    self,
    app: IApplication,
    name: str,
) -> tuple[tuple[str, str], ...]:
```

#### commands/make/http_controller.py

Fuente: [orionis/console/commands/make/http_controller.py](../commands/make/http_controller.py).

`MakeHttpController`

```python
class MakeHttpController(MakeStubCommand):
```

`MakeHttpController fields`

```python
timestamps: bool = False
signature: str = "make:http-controller"
description: str = "Creates an invokable or resource HTTP controller."
template_name: str = "http_controller"
path_key: str = "app_http_controllers"
success_label: str = "HTTP controller"
postfix: str | None = "Controller"
arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags="name",
            type_=str,
            required=True,
            help="The file and class name for the new controller.",
        ),
        Argument(
            name_or_flags="--invoke",
            default=False,
            help="Generate a single invokable __call__ action.",
            action="store_true",
        ),
        Argument(
            name_or_flags="--api",
            default=False,
            help="Annotate generated actions with JSONResponse.",
            action="store_true",
        ),
    ]
```

`MakeHttpController.getControllerMethods`

```python
def getControllerMethods(self) -> str:
```

`MakeHttpController.getReplacements`

```python
def getReplacements(self) -> dict[str, str]:
```

#### commands/make/http_middleware.py

Fuente: [orionis/console/commands/make/http_middleware.py](../commands/make/http_middleware.py).

`MakeHttpMiddleware`

```python
class MakeHttpMiddleware(MakeStubCommand):
```

`MakeHttpMiddleware fields`

```python
timestamps: bool = False
signature: str = "make:http-middleware"
description: str = "Creates a new HTTP middleware class."
template_name: str = "http_middleware"
path_key: str = "app_http_middleware"
success_label: str = "HTTP middleware"
postfix: str | None = "Middleware"
```

#### commands/make/http_schema.py

Fuente: [orionis/console/commands/make/http_schema.py](../commands/make/http_schema.py).

`MakeHttpSchema`

```python
class MakeHttpSchema(MakeStubCommand):
```

`MakeHttpSchema fields`

```python
timestamps: bool = False
signature: str = "make:http-schema"
description: str = "Creates a custom HTTP validation schema."
template_name: str = "http_schema"
path_key: str = "app_http_schemas"
success_label: str = "HTTP schema"
postfix: str | None = "Schema"
```

#### commands/make/http_schema_rule.py

Fuente: [orionis/console/commands/make/http_schema_rule.py](../commands/make/http_schema_rule.py).

`MakeHttpSchemaRule`

```python
class MakeHttpSchemaRule(MakeStubCommand):
```

`MakeHttpSchemaRule fields`

```python
timestamps: bool = False
signature: str = "make:http-schema-rule"
description: str = "Creates a custom validation rule."
template_name: str = "http_schema_rule"
path_key: str = "app_http_schemas_rules"
success_label: str = "HTTP schema rule"
postfix: str | None = "Rule"
```

#### commands/make/job.py

Fuente: [orionis/console/commands/make/job.py](../commands/make/job.py).

`MakeJob`

```python
class MakeJob(MakeStubCommand):
```

`MakeJob fields`

```python
__slots__ = ()
timestamps: bool = False
signature: str = "make:job"
description: str = "Create an asynchronous queue job."
template_name: str = "job"
path_key: str = "app_jobs"
success_label: str = "Job"
postfix: str | None = "Job"
```

#### commands/make/mail.py

Fuente: [orionis/console/commands/make/mail.py](../commands/make/mail.py).

`MakeMail`

```python
class MakeMail(MakeStubCommand):
```

`MakeMail fields`

```python
timestamps: bool = False
signature: str = "make:mail"
description: str = "Creates a reusable mail notification class."
template_name: str = "mail"
path_key: str = "app_notifications"
success_label: str = "Mail"
postfix: str | None = "Mail"
```

#### commands/make/mcp.py

Fuente: [orionis/console/commands/make/mcp.py](../commands/make/mcp.py).

`MakeMcpServer`

```python
class MakeMcpServer(MakeStubCommand):
```

`MakeMcpServer fields`

```python
timestamps = False
signature = "make:mcp-server"
description = "Create a new MCP server."
template_name = "mcp_server"
path_key = "app_mcp_servers"
success_label = "MCP server"
postfix = "Server"
```

`MakeMcpTool`

```python
class MakeMcpTool(MakeStubCommand):
```

`MakeMcpTool fields`

```python
timestamps = False
signature = "make:mcp-tool"
description = "Create a new MCP tool."
template_name = "mcp_tool"
path_key = "app_mcp_tools"
success_label = "MCP tool"
postfix = "Tool"
```

`MakeMcpResource`

```python
class MakeMcpResource(MakeStubCommand):
```

`MakeMcpResource fields`

```python
timestamps = False
signature = "make:mcp-resource"
description = "Create a new MCP resource."
template_name = "mcp_resource"
path_key = "app_mcp_resources"
success_label = "MCP resource"
postfix = "Resource"
```

`MakeMcpPrompt`

```python
class MakeMcpPrompt(MakeStubCommand):
```

`MakeMcpPrompt fields`

```python
timestamps = False
signature = "make:mcp-prompt"
description = "Create a new MCP prompt."
template_name = "mcp_prompt"
path_key = "app_mcp_prompts"
success_label = "MCP prompt"
postfix = "Prompt"
```

#### commands/make/model.py

Fuente: [orionis/console/commands/make/model.py](../commands/make/model.py).

`MakeModel`

```python
class MakeModel(MakeStubCommand):
```

`MakeModel fields`

```python
timestamps: bool = False
signature: str = "make:model"
description: str = "Creates a new ORM model class."
template_name: str = "model"
path_key: str = "app_models"
success_label: str = "Model"
```

#### commands/make/provider.py

Fuente: [orionis/console/commands/make/provider.py](../commands/make/provider.py).

`MakeProvider`

```python
class MakeProvider(MakeStubCommand):
```

`MakeProvider fields`

```python
timestamps: bool = False
signature: str = "make:provider"
description: str = "Creates a new provider class file."
template_name: str = "provider_eager"
path_key: str = "app_providers"
success_label: str = "Provider"
postfix: str | None = "Provider"
arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags="name",
            type_=str,
            required=True,
            help="The file and class name for the new provider.",
        ),
        Argument(
            name_or_flags="--deferred",
            default=False,
            help="Load the provider only when one of its services is needed.",
            action="store_true",
        ),
    ]
```

`MakeProvider.getTemplateName`

```python
def getTemplateName(self) -> str:
```

#### commands/make/service.py

Fuente: [orionis/console/commands/make/service.py](../commands/make/service.py).

`MakeService`

```python
class MakeService(MakeStubCommand):
```

`MakeService fields`

```python
timestamps: bool = False
signature: str = "make:service"
description: str = "Creates a new service class."
template_name: str = "service"
path_key: str = "app_services"
success_label: str = "Service"
```

#### commands/make/test.py

Fuente: [orionis/console/commands/make/test.py](../commands/make/test.py).

`MakeTest`

```python
class MakeTest(MakeStubCommand):
```

`MakeTest fields`

```python
timestamps: bool = False
signature: str = "make:test"
description: str = "Creates a new application test case."
template_name: str = "test"
path_key: str = "tests"
success_label: str = "Test"
```

`MakeTest.createFiles`

```python
def createFiles(
    self,
    app: IApplication,
    name: str,
) -> tuple[tuple[str, str], ...]:
```

#### commands/mcp/__init__.py

Fuente: [orionis/console/commands/mcp/__init__.py](../commands/mcp/__init__.py).

Sin API pública declarada directamente; inicializador o soporte privado de integración.

#### commands/mcp/list.py

Fuente: [orionis/console/commands/mcp/list.py](../commands/mcp/list.py).

`McpListCommand`

```python
class McpListCommand(BaseCommand):
```

`McpListCommand fields`

```python
timestamps = False
signature = "mcp:list"
description = "List registered HTTP and local MCP servers."
```

`McpListCommand.handle`

```python
async def handle(self, manager: IMcpManager) -> None:
```

#### commands/mcp/start.py

Fuente: [orionis/console/commands/mcp/start.py](../commands/mcp/start.py).

`McpStartCommand`

```python
class McpStartCommand(BaseCommand):
```

`McpStartCommand fields`

```python
timestamps = False
signature = "mcp:start"
description = "Start a registered MCP 2026-07-28 server over STDIO."
arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags="name", type_=str, required=True,
            help="Local server handle.",
        ),
    ]
```

`McpStartCommand.handle`

```python
async def handle(self, manager: IMcpManager) -> int:
```

#### commands/migrate/__init__.py

Fuente: [orionis/console/commands/migrate/__init__.py](../commands/migrate/__init__.py).

Sin API pública declarada directamente; inicializador o soporte privado de integración.

#### commands/migrate/base.py

Fuente: [orionis/console/commands/migrate/base.py](../commands/migrate/base.py).

`MigrationCommand`

```python
class MigrationCommand(BaseCommand):
```

`MigrationCommand fields`

```python
timestamps: bool = True
arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags=["--database", "-d"],
            type_=str,
            required=False,
            help="Named connection to run against; defaults to the default one.",
            dest="database",
        ),
    ]
```

`MigrationCommand.targetConnection`

```python
def targetConnection(self) -> str | None:
```

`MigrationCommand.progressEvents`

```python
def progressEvents(self) -> MigrationEvents:
```

`MigrationCommand.reportEmpty`

```python
def reportEmpty(self, message: str) -> None:
```

#### commands/migrate/fresh.py

Fuente: [orionis/console/commands/migrate/fresh.py](../commands/migrate/fresh.py).

`MigrateFreshCommand`

```python
class MigrateFreshCommand(MigrationCommand):
```

`MigrateFreshCommand fields`

```python
signature: str = "migrate:fresh"
description: str = "Clears migration and seeder history, then migrates."
```

`MigrateFreshCommand.handle`

```python
async def handle(self, migrator: Migrator) -> None:
```

#### commands/migrate/migrate.py

Fuente: [orionis/console/commands/migrate/migrate.py](../commands/migrate/migrate.py).

`MigrateCommand`

```python
class MigrateCommand(MigrationCommand):
```

`MigrateCommand fields`

```python
signature: str = "migrate"
description: str = "Runs all pending database migrations."
arguments: ClassVar[list[Argument]] = [
        *MigrationCommand.arguments,
        Argument(
            name_or_flags="--seed",
            action="store_true",
            default=False,
            help="Run pending database seeders after successful migrations.",
            dest="seed",
        ),
    ]
```

`MigrateCommand.handle`

```python
async def handle(
    self,
    migrator: Migrator,
    seeder_runner: SeederRunner,
) -> None:
```

#### commands/migrate/refresh.py

Fuente: [orionis/console/commands/migrate/refresh.py](../commands/migrate/refresh.py).

`MigrateRefreshCommand`

```python
class MigrateRefreshCommand(MigrationCommand):
```

`MigrateRefreshCommand fields`

```python
signature: str = "migrate:refresh"
description: str = "Rolls back and re-applies database migrations."
arguments: ClassVar[list[Argument]] = [
        *MigrationCommand.arguments,
        Argument(
            name_or_flags=["--step", "-s"],
            type_=int,
            required=False,
            help=(
                "Number of migration batches to roll back before migrating "
                "again. Defaults to every applied migration."
            ),
            dest="step",
        ),
    ]
```

`MigrateRefreshCommand.handle`

```python
async def handle(self, migrator: Migrator) -> None:
```

#### commands/migrate/reset.py

Fuente: [orionis/console/commands/migrate/reset.py](../commands/migrate/reset.py).

`MigrateResetCommand`

```python
class MigrateResetCommand(MigrationCommand):
```

`MigrateResetCommand fields`

```python
signature: str = "migrate:reset"
description: str = "Reverts every applied database migration."
```

`MigrateResetCommand.handle`

```python
async def handle(self, migrator: Migrator) -> None:
```

#### commands/migrate/rollback.py

Fuente: [orionis/console/commands/migrate/rollback.py](../commands/migrate/rollback.py).

`MigrateRollbackCommand`

```python
class MigrateRollbackCommand(MigrationCommand):
```

`MigrateRollbackCommand fields`

```python
signature: str = "migrate:rollback"
description: str = "Reverts the last batch(es) of database migrations."
arguments: ClassVar[list[Argument]] = [
        *MigrationCommand.arguments,
        Argument(
            name_or_flags=["--step", "-s"],
            type_=int,
            required=False,
            help=(
                "Number of migration batches to roll back. Defaults to 1 "
                "(the most recent batch)."
            ),
            dest="step",
        ),
    ]
```

`MigrateRollbackCommand.handle`

```python
async def handle(self, migrator: Migrator) -> None:
```

#### commands/migrate/status.py

Fuente: [orionis/console/commands/migrate/status.py](../commands/migrate/status.py).

`MigrateStatusCommand`

```python
class MigrateStatusCommand(MigrationCommand):
```

`MigrateStatusCommand fields`

```python
signature: str = "migrate:status"
description: str = "Shows the status of every discovered migration."
```

`MigrateStatusCommand.handle`

```python
async def handle(self, migrator: Migrator) -> None:
```

#### commands/queue/__init__.py

Fuente: [orionis/console/commands/queue/__init__.py](../commands/queue/__init__.py).

Sin API pública declarada directamente; inicializador o soporte privado de integración.

#### commands/queue/_signals.py

Fuente: [orionis/console/commands/queue/_signals.py](../commands/queue/_signals.py).

`WorkerSignals`

```python
class WorkerSignals:
```

`WorkerSignals fields`

```python
__slots__ = ("_handlers", "_loop", "_worker")
```

`WorkerSignals.__init__`

```python
def __init__(self, worker: IWorker) -> None:
```

`WorkerSignals.__enter__`

```python
def __enter__(self) -> None:
```

`WorkerSignals.__exit__`

```python
def __exit__(self, *_exception: object) -> None:
```

#### commands/queue/clear.py

Fuente: [orionis/console/commands/queue/clear.py](../commands/queue/clear.py).

`QueueClearCommand`

```python
class QueueClearCommand(BaseCommand):
```

`QueueClearCommand fields`

```python
__slots__ = ()
timestamps: bool = False
signature: str = "queue:clear"
description: str = "Delete ready, delayed, and reserved jobs from a queue."
arguments: ClassVar[list[Argument]] = [
        Argument(name_or_flags="connection", type_=str, nargs="?", default=None),
        Argument(name_or_flags="--queue", type_=str, default="default"),
    ]
```

`QueueClearCommand.handle`

```python
async def handle(self, manager: IQueueManager) -> int:
```

#### commands/queue/failed.py

Fuente: [orionis/console/commands/queue/failed.py](../commands/queue/failed.py).

`QueueFailedCommand`

```python
class QueueFailedCommand(BaseCommand):
```

`QueueFailedCommand fields`

```python
__slots__ = ()
timestamps: bool = False
signature: str = "queue:failed"
description: str = "List failed queue jobs."
```

`QueueFailedCommand.handle`

```python
async def handle(self, manager: IQueueManager) -> int:
```

#### commands/queue/forget.py

Fuente: [orionis/console/commands/queue/forget.py](../commands/queue/forget.py).

`QueueForgetCommand`

```python
class QueueForgetCommand(BaseCommand):
```

`QueueForgetCommand fields`

```python
__slots__ = ()
timestamps: bool = False
signature: str = "queue:forget"
description: str = "Delete a failed job by its identifier."
arguments: ClassVar[list[Argument]] = [
        Argument(name_or_flags="id", type_=str, help="Failed job identifier."),
    ]
```

`QueueForgetCommand.handle`

```python
async def handle(self, manager: IQueueManager) -> int:
```

#### commands/queue/retry.py

Fuente: [orionis/console/commands/queue/retry.py](../commands/queue/retry.py).

`QueueRetryCommand`

```python
class QueueRetryCommand(BaseCommand):
```

`QueueRetryCommand fields`

```python
__slots__ = ()
timestamps: bool = False
signature: str = "queue:retry"
description: str = "Retry a failed job by its identifier."
arguments: ClassVar[list[Argument]] = [
        Argument(name_or_flags="id", type_=str, help="Failed job identifier."),
    ]
```

`QueueRetryCommand.handle`

```python
async def handle(self, manager: IQueueManager) -> int:
```

#### commands/queue/work.py

Fuente: [orionis/console/commands/queue/work.py](../commands/queue/work.py).

`QueueWorkCommand`

```python
class QueueWorkCommand(BaseCommand):
```

`QueueWorkCommand fields`

```python
__slots__ = ()
timestamps: bool = False
signature: str = "queue:work"
description: str = "Consume queued jobs with retries and graceful shutdown."
arguments: ClassVar[list[Argument]] = [
        Argument(name_or_flags="connection", type_=str, nargs="?", default=None),
        Argument(name_or_flags="--queue", type_=str, default=None),
        Argument(name_or_flags="--concurrency", type_=int, default=None),
        Argument(name_or_flags="--max-jobs", type_=int, default=None, dest="max_jobs"),
        Argument(
            name_or_flags="--stop-when-empty",
            action=ArgumentAction.STORE_TRUE,
            default=False,
            dest="stop_when_empty",
        ),
    ]
```

`QueueWorkCommand.handle`

```python
async def handle(self, manager: IQueueManager) -> int:
```

#### commands/route/__init__.py

Fuente: [orionis/console/commands/route/__init__.py](../commands/route/__init__.py).

Sin API pública declarada directamente; inicializador o soporte privado de integración.

#### commands/route/list.py

Fuente: [orionis/console/commands/route/list.py](../commands/route/list.py).

`RouteListCommand`

```python
class RouteListCommand(BaseCommand):
```

`RouteListCommand fields`

```python
timestamps: bool = False
signature: str = "route:list"
description: str = "List the application's registered HTTP routes."
```

`RouteListCommand.handle`

```python
async def handle(
    self,
    route_loader: RouteLoader,
    console: Console,
) -> int:
```

#### commands/schedule/__init__.py

Fuente: [orionis/console/commands/schedule/__init__.py](../commands/schedule/__init__.py).

Sin API pública declarada directamente; inicializador o soporte privado de integración.

#### commands/schedule/list.py

Fuente: [orionis/console/commands/schedule/list.py](../commands/schedule/list.py).

`ScheduleListCommand`

```python
class ScheduleListCommand(BaseCommand):
```

`ScheduleListCommand fields`

```python
timestamps: bool = False
signature: str = "schedule:list"
description: str = "Lists all scheduled jobs defined in the application."
```

`ScheduleListCommand.handle`

```python
async def handle(
    self,
    app: IApplication,
    console: Console,
) -> None:
```

#### commands/schedule/work.py

Fuente: [orionis/console/commands/schedule/work.py](../commands/schedule/work.py).

`ScheduleWorkCommand`

```python
class ScheduleWorkCommand(BaseCommand):
```

`ScheduleWorkCommand fields`

```python
timestamps: bool = False
signature: str = "schedule:work"
description: str = "Run the scheduled tasks defined by the application."
```

`ScheduleWorkCommand.handle`

```python
async def handle(
    self,
    app: IApplication,
    console: Console,
) -> int | None:
```

#### commands/seed/__init__.py

Fuente: [orionis/console/commands/seed/__init__.py](../commands/seed/__init__.py).

Sin API pública declarada directamente; inicializador o soporte privado de integración.

#### commands/seed/seed.py

Fuente: [orionis/console/commands/seed/seed.py](../commands/seed/seed.py).

`SeedCommand`

```python
class SeedCommand(MigrationCommand):
```

`SeedCommand fields`

```python
signature: str = "seed"
description: str = "Runs all pending database seeders."
```

`SeedCommand.handle`

```python
async def handle(self, seeder_runner: SeederRunner) -> None:
```

#### commands/serve/__init__.py

Fuente: [orionis/console/commands/serve/__init__.py](../commands/serve/__init__.py).

Sin API pública declarada directamente; inicializador o soporte privado de integración.

#### commands/serve/serve.py

Fuente: [orionis/console/commands/serve/serve.py](../commands/serve/serve.py).

`ServerCommand`

```python
class ServerCommand(BaseCommand):
```

`ServerCommand fields`

```python
timestamps = False
signature = "serve"
description = (
        "Initializes the Orionis server with Granian "
        "(The Rust HTTP server for Python)."
    )
arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags=["--interface", "-i"],
            type_=str,
            help="Interface type to use (ASGI or RSGI).",
            choices=["rsgi", "asgi"],
            dest="interface",
            default=MISSING,
            required=False,
        ),
        Argument(
            name_or_flags=["--port", "-p"],
            type_=int,
            help="Port number to bind the server to.",
            dest="port",
            default=MISSING,
            required=False,
        ),
        Argument(
            name_or_flags=["--log"],
            help="Enable logging in production mode.",
            action="store_true",
            dest="log_enabled",
            default=False,
            required=False,
        ),
        Argument(
            name_or_flags=["--export"],
            help="Export the resolved Granian command in console.",
            action="store_true",
            dest="export",
            default=False,
            required=False,
        ),
    ]
```

`ServerCommand.__init__`

```python
def __init__(self) -> None:
```

`ServerCommand.handle`

```python
async def handle(self, app: IApplication) -> None:
```

#### commands/support/__init__.py

Fuente: [orionis/console/commands/support/__init__.py](../commands/support/__init__.py).

Sin API pública declarada directamente; inicializador o soporte privado de integración.

#### commands/support/_clear.py

Fuente: [orionis/console/commands/support/_clear.py](../commands/support/_clear.py).

`clear_files`

```python
def clear_files(
    directory: Path,
    suffix: str | tuple[str, ...],
) -> tuple[int, list[str]]:
```

#### commands/support/about.py

Fuente: [orionis/console/commands/support/about.py](../commands/support/about.py).

`VersionCommand`

```python
class VersionCommand(BaseCommand):
```

`VersionCommand fields`

```python
timestamps: bool = False
signature: str = "about"
description: str = "Displays the Orionis framework version and metadata."
```

`VersionCommand.handle`

```python
def handle(
    self,
    console: Console,
) -> None:
```

#### commands/support/clear_cache.py

Fuente: [orionis/console/commands/support/clear_cache.py](../commands/support/clear_cache.py).

`ClearCacheCommand`

```python
class ClearCacheCommand(BaseCommand):
```

`ClearCacheCommand fields`

```python
timestamps: bool = False
signature: str = "clear:cache"
description: str = "Clear entries from the default application cache store."
```

`ClearCacheCommand.handle`

```python
async def handle(self, cache: ICacheManager, console: Console) -> int:
```

#### commands/support/clear_logs.py

Fuente: [orionis/console/commands/support/clear_logs.py](../commands/support/clear_logs.py).

`ClearLogsCommand`

```python
class ClearLogsCommand(BaseCommand):
```

`ClearLogsCommand fields`

```python
timestamps: bool = False
signature: str = "clear:logs"
description: str = "Clear framework log files."
```

`ClearLogsCommand.handle`

```python
def handle( # NOSONAR
    self,
    app: IApplication,
    console: Console,
    logger: ILogger,
) -> int:
```

#### commands/support/clear_testing.py

Fuente: [orionis/console/commands/support/clear_testing.py](../commands/support/clear_testing.py).

`ClearTestingCommand`

```python
class ClearTestingCommand(BaseCommand):
```

`ClearTestingCommand fields`

```python
timestamps: bool = False
signature: str = "clear:testing"
description: str = "Clear cached test-run results."
```

`ClearTestingCommand.handle`

```python
def handle(self, app: IApplication, console: Console) -> int:
```

#### commands/support/clear_views.py

Fuente: [orionis/console/commands/support/clear_views.py](../commands/support/clear_views.py).

`ClearViewsCommand`

```python
class ClearViewsCommand(BaseCommand):
```

`ClearViewsCommand fields`

```python
timestamps: bool = False
signature: str = "clear:views"
description: str = "Clear compiled view templates."
```

`ClearViewsCommand.handle`

```python
def handle(self, app: IApplication, console: Console) -> int:
```

#### commands/support/down.py

Fuente: [orionis/console/commands/support/down.py](../commands/support/down.py).

`DownCommand`

```python
class DownCommand(MaintenanceModeCommand):
```

`DownCommand fields`

```python
signature: str = "down"
description: str = "Put the application into maintenance mode."
state: str = "down"
status_message: str = "The application is now in maintenance mode."
```

#### commands/support/environment.py

Fuente: [orionis/console/commands/support/environment.py](../commands/support/environment.py).

`EnvironmentCommand`

```python
class EnvironmentCommand(BaseCommand):
```

`EnvironmentCommand fields`

```python
timestamps: bool = False
signature: str = "env"
description: str = "Display the current application environment."
```

`EnvironmentCommand.handle`

```python
def handle(self, app: IApplication, console: Console) -> None:
```

#### commands/support/install.py

Fuente: [orionis/console/commands/support/install.py](../commands/support/install.py).

`InstallCommand`

```python
class InstallCommand(BaseCommand):
```

`InstallCommand fields`

```python
__slots__ = ("_console",)
timestamps: bool = False
signature: str = "install"
description: str = "Install optional dependencies and dependency groups."
arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags="options",
            nargs="*",
            default=[],
            type_=str,
            help="Names or numbers to install; use extra:NAME or group:NAME.",
        ),
        Argument(
            name_or_flags="--list",
            action=ArgumentAction.STORE_TRUE,
            default=False,
            help="List installation options without installing packages.",
        ),
        Argument(
            name_or_flags=("--yes", "-y"),
            action=ArgumentAction.STORE_TRUE,
            default=False,
            help="Install the selected options without asking for confirmation.",
        ),
    ]
```

`InstallCommand.__init__`

```python
def __init__(self) -> None:
```

`InstallCommand.handle`

```python
async def handle(self, app: IApplication) -> int:
```

#### commands/support/key_generate.py

Fuente: [orionis/console/commands/support/key_generate.py](../commands/support/key_generate.py).

`KeyGenerateCommand`

```python
class KeyGenerateCommand(BaseCommand):
```

`KeyGenerateCommand fields`

```python
timestamps: bool = False
signature: str = "key:generate"
description: str = "Generate the application encryption key."
arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags="--force",
            action=ArgumentAction.STORE_TRUE,
            default=False,
            help="Replace the existing application key.",
        ),
    ]
```

`KeyGenerateCommand.handle`

```python
def handle(
    self,
    app: IApplication,
    console: Console,
) -> int:
```

#### commands/support/list.py

Fuente: [orionis/console/commands/support/list.py](../commands/support/list.py).

`HelpCommand`

```python
class HelpCommand(BaseCommand):
```

`HelpCommand fields`

```python
timestamps: bool = False
signature: str = "list"
description: str = "Show available commands and usage."
```

`HelpCommand.handle`

```python
async def handle(
    self,
    reactor: IReactor,
    console: Console,
) -> None:
```

#### commands/support/maintenance.py

Fuente: [orionis/console/commands/support/maintenance.py](../commands/support/maintenance.py).

`MaintenanceModeCommand`

```python
class MaintenanceModeCommand(BaseCommand):
```

`MaintenanceModeCommand fields`

```python
timestamps: bool = False
state: ClassVar[str]
status_message: ClassVar[str]
```

`MaintenanceModeCommand.handle`

```python
def handle(self, app: IApplication, console: Console) -> int:
```

#### commands/support/optimize.py

Fuente: [orionis/console/commands/support/optimize.py](../commands/support/optimize.py).

`OptimizeCommand`

```python
class OptimizeCommand(BaseCommand):
```

`OptimizeCommand fields`

```python
timestamps: bool = True
signature: str = "optimize"
description: str = "Compile application Python files to optimized bytecode."
```

`OptimizeCommand.handle`

```python
def handle(self, app: IApplication, console: Console) -> int: # NOSONAR
```

#### commands/support/optimize_clear.py

Fuente: [orionis/console/commands/support/optimize_clear.py](../commands/support/optimize_clear.py).

`OptimizeClearCommand`

```python
class OptimizeClearCommand(BaseCommand):
```

`OptimizeClearCommand fields`

```python
timestamps: bool = True
signature: str = "optimize:clear"
description: str = (
        "Removes compiled configuration, route, and command caches, "
        "Python bytecode, and build artifacts."
    )
```

`OptimizeClearCommand.handle`

```python
def handle(
    self,
    app: IApplication,
    console: Console,
) -> int:
```

#### commands/support/up.py

Fuente: [orionis/console/commands/support/up.py](../commands/support/up.py).

`UpCommand`

```python
class UpCommand(MaintenanceModeCommand):
```

`UpCommand fields`

```python
signature: str = "up"
description: str = "Bring the application out of maintenance mode."
state: str = "up"
status_message: str = "The application is now available."
```

#### commands/test/__init__.py

Fuente: [orionis/console/commands/test/__init__.py](../commands/test/__init__.py).

Sin API pública declarada directamente; inicializador o soporte privado de integración.

#### commands/test/test.py

Fuente: [orionis/console/commands/test/test.py](../commands/test/test.py).

`TestCommand`

```python
class TestCommand(BaseCommand):
```

`TestCommand fields`

```python
timestamps: bool = False
signature: str = "test"
description: str = "Executes test cases defined in the project."
arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags=["--verbosity", "-v"],
            type_=int,
            required=False,
            help=(
                "Level of detail in test output. 0: silent, 1: standard, "
                "2: detailed. Defaults to 2 (detailed)."
            ),
            dest="verbosity",
        ),
        Argument(
            name_or_flags=["--fail-fast", "-f"],
            type_=int,
            required=False,
            help=(
                "1: Stop on first failure. 0: Continue running all tests. "
                "Defaults to 0 (continue)."
            ),
            dest="fail_fast",
        ),
        Argument(
            name_or_flags=["--start-dir", "-s"],
            type_=str,
            required=False,
            help=(
                "Directory to search for tests. Defaults to 'tests'."
            ),
            dest="start_dir",
        ),
        Argument(
            name_or_flags=["--file-pattern"],
            type_=str,
            required=False,
            help=(
                "Filename pattern to identify test files. Defaults to 'test_*.py'."
            ),
            dest="file_pattern",
        ),
        Argument(
            name_or_flags=["--method-pattern"],
            type_=str,
            required=False,
            help=(
                "Pattern to filter specific test methods. Defaults to 'test*'."
            ),
            dest="method_pattern",
        ),
        Argument(
            name_or_flags=["--panel"],
            action=ArgumentAction.STORE_TRUE,
            default=True,
            help="Show Rich panels for test execution (default).",
            dest="with_panel",
        ),
        Argument(
            name_or_flags=["--no-panel"],
            action=ArgumentAction.STORE_FALSE,
            help="Disable Rich panels for test execution.",
            dest="with_panel",
        ),
    ]
```

`TestCommand.handle`

```python
async def handle(
    self,
    app: IApplication,
    test_engine: ITestingEngine,
) -> int:
```

#### contracts/__init__.py

Fuente: [orionis/console/contracts/__init__.py](../contracts/__init__.py).

`__all__`

```python
__all__ = [
    "ISchedule",
]
```

`__getattr__`

```python
def __getattr__(name: str) -> object:
```

`__dir__`

```python
def __dir__() -> list[str]:
```

#### contracts/kernel.py

Fuente: [orionis/console/contracts/kernel.py](../contracts/kernel.py).

`IKernelCLI`

```python
class IKernelCLI(ABC):
```

`IKernelCLI fields`

```python
__slots__ = ()
```

`IKernelCLI.boot`

```python
@abstractmethod
async def boot(
    self,
    application: IApplication,
) -> None:
```

`IKernelCLI.handle`

```python
@abstractmethod
async def handle(self, args: list[str] | None = None) -> int:
```

#### contracts/schedule.py

Fuente: [orionis/console/contracts/schedule.py](../contracts/schedule.py).

`ISchedule`

```python
class ISchedule(ABC):
```

`ISchedule.info`

```python
@abstractmethod
async def info(self) -> list[dict]:
```

`ISchedule.boot`

```python
@abstractmethod
async def boot(self) -> None:
```

`ISchedule.on`

```python
@abstractmethod
def on(
    self,
    event: SchedulerEvent,
    listener: Callable,
) -> Self:
```

`ISchedule.state`

```python
@abstractmethod
def state(self) -> str:
```

`ISchedule.isRunning`

```python
@abstractmethod
def isRunning(self) -> bool:
```

`ISchedule.isPaused`

```python
@abstractmethod
def isPaused(self) -> bool:
```

`ISchedule.isStopped`

```python
@abstractmethod
def isStopped(self) -> bool:
```

`ISchedule.command`

```python
@abstractmethod
def command(
    self,
    signature: str,
    args: list[str] | None = None,
    purpose: str | None = None,
) -> ITask:
```

`ISchedule.pauseTask`

```python
@abstractmethod
def pauseTask(
    self,
    signature: str,
) -> bool:
```

`ISchedule.resumeTask`

```python
@abstractmethod
def resumeTask(
    self,
    signature: str,
) -> bool:
```

`ISchedule.removeTask`

```python
@abstractmethod
def removeTask(
    self,
    signature: str,
) -> bool:
```

`ISchedule.removeAllTasks`

```python
@abstractmethod
def removeAllTasks(self) -> bool:
```

`ISchedule.pause`

```python
@abstractmethod
def pause(self) -> bool:
```

`ISchedule.resume`

```python
@abstractmethod
def resume(self) -> bool:
```

`ISchedule.shutdown`

```python
@abstractmethod
def shutdown(self, wait: int | None = None) -> None:
```

`ISchedule.wait`

```python
@abstractmethod
async def wait(self) -> None:
```

#### contracts/store.py

Fuente: [orionis/console/contracts/store.py](../contracts/store.py).

`IScheduleStore`

```python
class IScheduleStore(ABC):
```

`IScheduleStore.store`

```python
@property
@abstractmethod
def store(self) -> str:
```

`IScheduleStore.config`

```python
@property
@abstractmethod
def config(self) -> ConfigScheduler:
```

`IScheduleStore.redis`

```python
@abstractmethod
def redis(self) -> RedisJobStore:
```

`IScheduleStore.database`

```python
@abstractmethod
def database(self) -> SQLAlchemyJobStore:
```

#### core/__init__.py

Fuente: [orionis/console/core/__init__.py](../core/__init__.py).

Sin API pública declarada directamente; inicializador o soporte privado de integración.

#### core/commands.py

Fuente: [orionis/console/core/commands.py](../core/commands.py).

`get_core_commands_mapping`

```python
def get_core_commands_mapping() -> tuple:
```

`CORE_COMMANDS`

```python
CORE_COMMANDS: tuple = get_core_commands_mapping()
```

#### core/contracts/__init__.py

Fuente: [orionis/console/core/contracts/__init__.py](../core/contracts/__init__.py).

Sin API pública declarada directamente; inicializador o soporte privado de integración.

#### core/contracts/loader.py

Fuente: [orionis/console/core/contracts/loader.py](../core/contracts/loader.py).

`ILoader`

```python
class ILoader(ABC):
```

`ILoader.get`

```python
@abstractmethod
async def get(self, signature: str) -> Command | None:
```

`ILoader.all`

```python
@abstractmethod
async def all(self) -> dict[str, Command]:
```

`ILoader.addFluentCommand`

```python
@abstractmethod
def addFluentCommand(
    self,
    signature: str,
    handler: list[type[Any], str | None],
) -> ICommand:
```

`ILoader.load`

```python
@abstractmethod
async def load(self) -> None:
```

#### core/contracts/reactor.py

Fuente: [orionis/console/core/contracts/reactor.py](../core/contracts/reactor.py).

`IReactor`

```python
class IReactor(ABC):
```

`IReactor.command`

```python
@abstractmethod
def command(
    self,
    signature: str,
    handler: list[type[Any] | str | None] | str,
) -> ICommand:
```

`IReactor.hasCommand`

```python
@abstractmethod
async def hasCommand(self, signature: str) -> bool:
```

`IReactor.info`

```python
@abstractmethod
async def info(self) -> list[dict]:
```

`IReactor.call`

```python
@abstractmethod
async def call(
    self,
    signature: str,
    args: list[str] | None = None,
) -> int:
```

#### core/loader.py

Fuente: [orionis/console/core/loader.py](../core/loader.py).

`Loader`

```python
class Loader(ILoader):
```

`Loader.__init__`

```python
def __init__(self, app: IApplication) -> None:
```

`Loader.get`

```python
async def get(self, signature: str) -> Command | None:
```

`Loader.all`

```python
async def all(self) -> dict[str, Command]:
```

`Loader.load`

```python
async def load(self) -> None:
```

`Loader.addFluentCommand`

```python
def addFluentCommand(
    self,
    signature: str,
    handler: list[type[Any], str | None],
) -> ICommand:
```

#### core/reactor.py

Fuente: [orionis/console/core/reactor.py](../core/reactor.py).

`Reactor`

```python
class Reactor(IReactor):
```

`Reactor.__init__`

```python
def __init__(
    self,
    app: IApplication,
    loader: Loader,
    executer: Executor,
    logger: ILogger,
    catch: ICatch,
    performance_counter: PerformanceCounter,
) -> None:
```

`Reactor.command`

```python
def command(
    self,
    signature: str,
    handler: list[type[Any] | str | None] | str,
) -> ICommand:
```

`Reactor.hasCommand`

```python
async def hasCommand(self, signature: str) -> bool:
```

`Reactor.info`

```python
async def info(self) -> list[dict]:
```

`Reactor.call`

```python
async def call( # NOSONAR
    self,
    signature: str,
    args: list[str] | None = None,
) -> int:
```

#### debug/__init__.py

Fuente: [orionis/console/debug/__init__.py](../debug/__init__.py).

Sin API pública declarada directamente; inicializador o soporte privado de integración.

#### debug/contracts/__init__.py

Fuente: [orionis/console/debug/contracts/__init__.py](../debug/contracts/__init__.py).

Sin API pública declarada directamente; inicializador o soporte privado de integración.

#### debug/contracts/dumper.py

Fuente: [orionis/console/debug/contracts/dumper.py](../debug/contracts/dumper.py).

`IDumper`

```python
class IDumper(ABC):
```

`IDumper.dd`

```python
@staticmethod
@abstractmethod
def dd(
    *args: tuple[Any],
    show_types: bool = False,
    show_index: bool = False,
    expand_all: bool = True,
    max_depth: int | None = None,
    module_path: str | None = None,
    line_number: int | None = None,
    redirect_output: bool = False,
    insert_line: bool = False,
) -> None:
```

`IDumper.dump`

```python
@staticmethod
@abstractmethod
def dump(
    *args: tuple[Any],
    show_types: bool = False,
    show_index: bool = False,
    expand_all: bool = True,
    max_depth: int | None = None,
    module_path: str | None = None,
    line_number: int | None = None,
    redirect_output: bool = False,
    insert_line: bool = False,
) -> None:
```

#### debug/dumper.py

Fuente: [orionis/console/debug/dumper.py](../debug/dumper.py).

`Dumper`

```python
class Dumper(IDumper):
```

`Dumper.dd`

```python
@staticmethod
def dd(
    *args: tuple[Any],
    show_types: bool = False,
    show_index: bool = False,
    expand_all: bool = True,
    max_depth: int | None = None,
    module_path: str | None = None,
    line_number: int | None = None,
    redirect_output: bool = False,
    insert_line: bool = False,
) -> None:
```

`Dumper.dump`

```python
@staticmethod
def dump(
    *args: tuple[Any],
    show_types: bool = False,
    show_index: bool = False,
    expand_all: bool = True,
    max_depth: int | None = None,
    module_path: str | None = None,
    line_number: int | None = None,
    redirect_output: bool = False,
    insert_line: bool = False,
) -> None:
```

#### dynamic/__init__.py

Fuente: [orionis/console/dynamic/__init__.py](../dynamic/__init__.py).

Sin API pública declarada directamente; inicializador o soporte privado de integración.

#### dynamic/contracts/__init__.py

Fuente: [orionis/console/dynamic/contracts/__init__.py](../dynamic/contracts/__init__.py).

Sin API pública declarada directamente; inicializador o soporte privado de integración.

#### dynamic/contracts/progress_bar.py

Fuente: [orionis/console/dynamic/contracts/progress_bar.py](../dynamic/contracts/progress_bar.py).

`IProgressBar`

```python
class IProgressBar(ABC):
```

`IProgressBar.start`

```python
@abstractmethod
def start(self) -> None:
```

`IProgressBar.advance`

```python
@abstractmethod
def advance(
    self,
    increment: int = 1,
) -> None:
```

`IProgressBar.finish`

```python
@abstractmethod
def finish(self) -> None:
```

#### dynamic/progress_bar.py

Fuente: [orionis/console/dynamic/progress_bar.py](../dynamic/progress_bar.py).

`ProgressBar`

```python
class ProgressBar(IProgressBar):
```

`ProgressBar.__init__`

```python
def __init__(self, total: int = 100, width: int = 50) -> None:
```

`ProgressBar.start`

```python
def start(self) -> None:
```

`ProgressBar.advance`

```python
def advance(self, increment: int = 1) -> None:
```

`ProgressBar.finish`

```python
def finish(self) -> None:
```

#### entities/__init__.py

Fuente: [orionis/console/entities/__init__.py](../entities/__init__.py).

`__all__`

```python
__all__ = ["Command", "SchedulerEvent", "Task", "TaskEvent"]
```

#### entities/command.py

Fuente: [orionis/console/entities/command.py](../entities/command.py).

`Command`

```python
@dataclass(kw_only=True)
class Command(BaseEntity):
```

`Command fields`

```python
obj: type
method: str = "handle"
timestamps: bool = True
signature: str
description: str
args: list[Argument] | argparse.ArgumentParser | None = None
```

#### entities/scheduler_event.py

Fuente: [orionis/console/entities/scheduler_event.py](../entities/scheduler_event.py).

`SchedulerEvent`

```python
@dataclass(kw_only=True)
class SchedulerEvent(BaseEntity):
```

`SchedulerEvent fields`

```python
code: int
description: str = field(default="")
jobstore: str = field(default="memory")
```

`SchedulerEvent.__post_init__`

```python
def __post_init__(self) -> None:
```

#### entities/task.py

Fuente: [orionis/console/entities/task.py](../entities/task.py).

`Task`

```python
@dataclass(kw_only=True)
class Task(BaseEntity):
```

`Task fields`

```python
signature: str
args: list[str] | None = field(
        default_factory=list,
    )
kwargs: dict | None = field(
        default_factory=dict,
    )
purpose: str | None = None
random_delay: int | None = None
start_date: datetime | None = None
end_date: datetime | None = None
trigger: CronTrigger | DateTrigger | IntervalTrigger | None = None
details: str | None = None
max_instances: int | None = 1
misfire_grace_time: int | None = None
coalesce: bool | None = True
listeners: list[Callable[..., None]] = field(
        default_factory=list,
    )
```

#### entities/task_event.py

Fuente: [orionis/console/entities/task_event.py](../entities/task_event.py).

`TaskEvent`

```python
@dataclass(kw_only=True)
class TaskEvent(BaseEntity):
```

`TaskEvent fields`

```python
code: int
description: str = field(
        default="",
    )
signature: str
jobstore: str = field(
        default="memory",
    )
scheduled_run_times: Any | None = field(
        default=None,
    )
scheduled_run_time: Any | None = field(
        default=None,
    )
retval: Any | None = field(
        default=None,
    )
exception: Any | None = field(
        default=None,
    )
traceback: Any | None = field(
        default=None,
    )
```

`TaskEvent.__post_init__`

```python
def __post_init__(self) -> None:
```

#### enums/__init__.py

Fuente: [orionis/console/enums/__init__.py](../enums/__init__.py).

`__all__`

```python
__all__ = [
    "ANSIColors",
    "ArgumentAction",
    "ScheduleStates",
    "SchedulerEvent",
    "TaskEvent",
]
```

#### enums/actions.py

Fuente: [orionis/console/enums/actions.py](../enums/actions.py).

`ArgumentAction`

```python
class ArgumentAction(Enum):
```

`ArgumentAction fields`

```python
STORE = "store"
STORE_CONST = "store_const"
STORE_TRUE = "store_true"
STORE_FALSE = "store_false"
APPEND = "append"
APPEND_CONST = "append_const"
COUNT = "count"
HELP = "help"
VERSION = "version"
```

#### enums/events.py

Fuente: [orionis/console/enums/events.py](../enums/events.py).

`TaskEvent`

```python
class TaskEvent(IntEnum):
```

`TaskEvent fields`

```python
ADDED = 2**9
REMOVED = 2**10
MODIFIED = 2**11
EXECUTED = 2**12
ERROR = 2**13
MISSED = 2**14
SUBMITTED = 2**15
MAX_INSTANCES = 2**16
```

`SchedulerEvent`

```python
class SchedulerEvent(IntEnum):
```

`SchedulerEvent fields`

```python
STARTED = 2**0
SHUTDOWN = 2**1
PAUSED = 2**2
RESUMED = 2**3
```

#### enums/states.py

Fuente: [orionis/console/enums/states.py](../enums/states.py).

`ScheduleStates`

```python
class ScheduleStates(Enum):
```

`ScheduleStates fields`

```python
STOPPED = "STOPPED"
RUNNING = "RUNNING"
PAUSED = "PAUSED"
```

#### enums/styles.py

Fuente: [orionis/console/enums/styles.py](../enums/styles.py).

`ANSIColors`

```python
class ANSIColors(Enum):
```

`ANSIColors fields`

```python
DEFAULT = "\033[0m"
BG_INFO = "\033[44m"
BG_ERROR = "\033[41m"
BG_FAIL = "\033[48;5;166m"
BG_WARNING = "\033[43m"
BG_SUCCESS = "\033[42m"
TEXT_INFO = "\033[34m"
TEXT_ERROR = "\033[91m"
TEXT_WARNING = "\033[33m"
TEXT_SUCCESS = "\033[32m"
TEXT_WHITE = "\033[97m"
TEXT_MUTED = "\033[90m"
TEXT_BOLD_INFO = "\033[1;34m"
TEXT_BOLD_ERROR = "\033[1;91m"
TEXT_BOLD_WARNING = "\033[1;33m"
TEXT_BOLD_SUCCESS = "\033[1;32m"
TEXT_BOLD_WHITE = "\033[1;97m"
TEXT_BOLD_MUTED = "\033[1;90m"
TEXT_BOLD = "\033[1m"
TEXT_STYLE_UNDERLINE = "\033[4m"
CYAN = "\033[36m"
DIM = "\033[2m"
MAGENTA = "\033[35m"
ITALIC = "\033[3m"
```

#### fluent/__init__.py

Fuente: [orionis/console/fluent/__init__.py](../fluent/__init__.py).

`__all__`

```python
__all__ = ["Command", "Task"]
```

#### fluent/command.py

Fuente: [orionis/console/fluent/command.py](../fluent/command.py).

`Command`

```python
class Command(ICommand):
```

`Command.__init__`

```python
def __init__(
    self,
    signature: str,
    concrete: Callable[..., Any],
    method: str = "handle",
) -> None:
```

`Command.timestamp`

```python
def timestamp(self, *, enabled: bool = True) -> Self:
```

`Command.description`

```python
def description(self, desc: str) -> Self:
```

`Command.arguments`

```python
def arguments(self, args: list[Argument]) -> Self:
```

`Command.get`

```python
def get(self) -> tuple[str, CommandEntity]:
```

#### fluent/contracts/__init__.py

Fuente: [orionis/console/fluent/contracts/__init__.py](../fluent/contracts/__init__.py).

Sin API pública declarada directamente; inicializador o soporte privado de integración.

#### fluent/contracts/command.py

Fuente: [orionis/console/fluent/contracts/command.py](../fluent/contracts/command.py).

`ICommand`

```python
class ICommand(ABC):
```

`ICommand.timestamp`

```python
@abstractmethod
def timestamp(self, *, enabled: bool = True) -> ICommand:
```

`ICommand.description`

```python
@abstractmethod
def description(self, desc: str) -> ICommand:
```

`ICommand.arguments`

```python
@abstractmethod
def arguments(self, args: list) -> ICommand:
```

`ICommand.get`

```python
@abstractmethod
def get(self) -> tuple[str, CommandEntity]:
```

#### fluent/contracts/task.py

Fuente: [orionis/console/fluent/contracts/task.py](../fluent/contracts/task.py).

`ITask`

```python
class ITask(ABC):
```

`ITask.entity`

```python
@abstractmethod
def entity(
    self,
    random_delay: int | None = 0,
    max_instances: int | None = 1,
    misfire_grace_time: int | None = 0,
    *,
    coalesce: bool | None = True,
) -> TaskEntity:
```

`ITask.coalesce`

```python
@abstractmethod
def coalesce(
    self,
    *,
    coalesce: bool = True,
) -> ITask:
```

`ITask.misfireGraceTime`

```python
@abstractmethod
def misfireGraceTime(
    self,
    seconds: int = 60,
) -> ITask:
```

`ITask.purpose`

```python
@abstractmethod
def purpose(
    self,
    purpose: str,
) -> ITask:
```

`ITask.startDate`

```python
@abstractmethod
def startDate(
    self,
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
) -> ITask:
```

`ITask.endDate`

```python
@abstractmethod
def endDate(
    self,
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
) -> ITask:
```

`ITask.randomDelay`

```python
@abstractmethod
def randomDelay(
    self,
    max_seconds: int = 10,
) -> ITask:
```

`ITask.maxInstances`

```python
@abstractmethod
def maxInstances(
    self,
    max_instances: int,
) -> ITask:
```

`ITask.on`

```python
@abstractmethod
def on(
    self,
    event: TaskEventListener,
    callback: Callable,
) -> ITask:
```

`ITask.registerListener`

```python
@abstractmethod
def registerListener(
    self,
    listener: IBaseTaskListener,
) -> ITask:
```

`ITask.onceAt`

```python
@abstractmethod
def onceAt(
    self,
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`ITask.everySeconds`

```python
@abstractmethod
def everySeconds(
    self,
    seconds: int,
) -> bool:
```

`ITask.everyFiveSeconds`

```python
@abstractmethod
def everyFiveSeconds(
    self,
) -> bool:
```

`ITask.everyTenSeconds`

```python
@abstractmethod
def everyTenSeconds(
    self,
) -> bool:
```

`ITask.everyFifteenSeconds`

```python
@abstractmethod
def everyFifteenSeconds(
    self,
) -> bool:
```

`ITask.everyTwentySeconds`

```python
@abstractmethod
def everyTwentySeconds(
    self,
) -> bool:
```

`ITask.everyTwentyFiveSeconds`

```python
@abstractmethod
def everyTwentyFiveSeconds(
    self,
) -> bool:
```

`ITask.everyThirtySeconds`

```python
@abstractmethod
def everyThirtySeconds(
    self,
) -> bool:
```

`ITask.everyThirtyFiveSeconds`

```python
@abstractmethod
def everyThirtyFiveSeconds(
    self,
) -> bool:
```

`ITask.everyFortySeconds`

```python
@abstractmethod
def everyFortySeconds(
    self,
) -> bool:
```

`ITask.everyFortyFiveSeconds`

```python
@abstractmethod
def everyFortyFiveSeconds(
    self,
) -> bool:
```

`ITask.everyFiftySeconds`

```python
@abstractmethod
def everyFiftySeconds(
    self,
) -> bool:
```

`ITask.everyFiftyFiveSeconds`

```python
@abstractmethod
def everyFiftyFiveSeconds(
    self,
) -> bool:
```

`ITask.everyMinutes`

```python
@abstractmethod
def everyMinutes(
    self,
    minutes: int,
) -> bool:
```

`ITask.everyMinuteAt`

```python
@abstractmethod
def everyMinuteAt(
    self,
    seconds: int,
) -> bool:
```

`ITask.everyMinutesAt`

```python
@abstractmethod
def everyMinutesAt(
    self,
    minutes: int,
    seconds: int,
) -> bool:
```

`ITask.everyFiveMinutes`

```python
@abstractmethod
def everyFiveMinutes(
    self,
) -> bool:
```

`ITask.everyFiveMinutesAt`

```python
@abstractmethod
def everyFiveMinutesAt(
    self,
    seconds: int,
) -> bool:
```

`ITask.everyTenMinutes`

```python
@abstractmethod
def everyTenMinutes(
    self,
) -> bool:
```

`ITask.everyTenMinutesAt`

```python
@abstractmethod
def everyTenMinutesAt(
    self,
    seconds: int,
) -> bool:
```

`ITask.everyFifteenMinutes`

```python
@abstractmethod
def everyFifteenMinutes(
    self,
) -> bool:
```

`ITask.everyFifteenMinutesAt`

```python
@abstractmethod
def everyFifteenMinutesAt(
    self,
    seconds: int,
) -> bool:
```

`ITask.everyTwentyMinutes`

```python
@abstractmethod
def everyTwentyMinutes(
    self,
) -> bool:
```

`ITask.everyTwentyMinutesAt`

```python
@abstractmethod
def everyTwentyMinutesAt(
    self,
    seconds: int,
) -> bool:
```

`ITask.everyTwentyFiveMinutes`

```python
@abstractmethod
def everyTwentyFiveMinutes(
    self,
) -> bool:
```

`ITask.everyTwentyFiveMinutesAt`

```python
@abstractmethod
def everyTwentyFiveMinutesAt(
    self,
    seconds: int,
) -> bool:
```

`ITask.everyThirtyMinutes`

```python
@abstractmethod
def everyThirtyMinutes(
    self,
) -> bool:
```

`ITask.everyThirtyMinutesAt`

```python
@abstractmethod
def everyThirtyMinutesAt(
    self,
    seconds: int,
) -> bool:
```

`ITask.everyThirtyFiveMinutes`

```python
@abstractmethod
def everyThirtyFiveMinutes(
    self,
) -> bool:
```

`ITask.everyThirtyFiveMinutesAt`

```python
@abstractmethod
def everyThirtyFiveMinutesAt(
    self,
    seconds: int,
) -> bool:
```

`ITask.everyFortyMinutes`

```python
@abstractmethod
def everyFortyMinutes(
    self,
) -> bool:
```

`ITask.everyFortyMinutesAt`

```python
@abstractmethod
def everyFortyMinutesAt(
    self,
    seconds: int,
) -> bool:
```

`ITask.everyFortyFiveMinutes`

```python
@abstractmethod
def everyFortyFiveMinutes(
    self,
) -> bool:
```

`ITask.everyFortyFiveMinutesAt`

```python
@abstractmethod
def everyFortyFiveMinutesAt(
    self,
    seconds: int,
) -> bool:
```

`ITask.everyFiftyMinutes`

```python
@abstractmethod
def everyFiftyMinutes(
    self,
) -> bool:
```

`ITask.everyFiftyMinutesAt`

```python
@abstractmethod
def everyFiftyMinutesAt(
    self,
    seconds: int,
) -> bool:
```

`ITask.everyFiftyFiveMinutes`

```python
@abstractmethod
def everyFiftyFiveMinutes(
    self,
) -> bool:
```

`ITask.everyFiftyFiveMinutesAt`

```python
@abstractmethod
def everyFiftyFiveMinutesAt(
    self,
    seconds: int,
) -> bool:
```

`ITask.hourly`

```python
@abstractmethod
def hourly(
    self,
) -> bool:
```

`ITask.hourlyAt`

```python
@abstractmethod
def hourlyAt(
    self,
    minute: int,
    second: int = 0,
) -> bool:
```

`ITask.everyOddHours`

```python
@abstractmethod
def everyOddHours(
    self,
) -> bool:
```

`ITask.everyEvenHours`

```python
@abstractmethod
def everyEvenHours(
    self,
) -> bool:
```

`ITask.everyHours`

```python
@abstractmethod
def everyHours(
    self,
    hours: int,
) -> bool:
```

`ITask.everyHoursAt`

```python
@abstractmethod
def everyHoursAt(
    self,
    hours: int,
    minute: int,
    second: int = 0,
) -> bool:
```

`ITask.everyTwoHours`

```python
@abstractmethod
def everyTwoHours(
    self,
) -> bool:
```

`ITask.everyTwoHoursAt`

```python
@abstractmethod
def everyTwoHoursAt(
    self,
    minute: int,
    second: int = 0,
) -> bool:
```

`ITask.everyThreeHours`

```python
@abstractmethod
def everyThreeHours(
    self,
) -> bool:
```

`ITask.everyThreeHoursAt`

```python
@abstractmethod
def everyThreeHoursAt(
    self,
    minute: int,
    second: int = 0,
) -> bool:
```

`ITask.everyFourHours`

```python
@abstractmethod
def everyFourHours(
    self,
) -> bool:
```

`ITask.everyFourHoursAt`

```python
@abstractmethod
def everyFourHoursAt(
    self,
    minute: int,
    second: int = 0,
) -> bool:
```

`ITask.everyFiveHours`

```python
@abstractmethod
def everyFiveHours(
    self,
) -> bool:
```

`ITask.everyFiveHoursAt`

```python
@abstractmethod
def everyFiveHoursAt(
    self,
    minute: int,
    second: int = 0,
) -> bool:
```

`ITask.everySixHours`

```python
@abstractmethod
def everySixHours(
    self,
) -> bool:
```

`ITask.everySixHoursAt`

```python
@abstractmethod
def everySixHoursAt(
    self,
    minute: int,
    second: int = 0,
) -> bool:
```

`ITask.everySevenHours`

```python
@abstractmethod
def everySevenHours(
    self,
) -> bool:
```

`ITask.everySevenHoursAt`

```python
@abstractmethod
def everySevenHoursAt(
    self,
    minute: int,
    second: int = 0,
) -> bool:
```

`ITask.everyEightHours`

```python
@abstractmethod
def everyEightHours(
    self,
) -> bool:
```

`ITask.everyEightHoursAt`

```python
@abstractmethod
def everyEightHoursAt(
    self,
    minute: int,
    second: int = 0,
) -> bool:
```

`ITask.everyNineHours`

```python
@abstractmethod
def everyNineHours(
    self,
) -> bool:
```

`ITask.everyNineHoursAt`

```python
@abstractmethod
def everyNineHoursAt(
    self,
    minute: int,
    second: int = 0,
) -> bool:
```

`ITask.everyTenHours`

```python
@abstractmethod
def everyTenHours(
    self,
) -> bool:
```

`ITask.everyTenHoursAt`

```python
@abstractmethod
def everyTenHoursAt(
    self,
    minute: int,
    second: int = 0,
) -> bool:
```

`ITask.everyElevenHours`

```python
@abstractmethod
def everyElevenHours(
    self,
) -> bool:
```

`ITask.everyElevenHoursAt`

```python
@abstractmethod
def everyElevenHoursAt(
    self,
    minute: int,
    second: int = 0,
) -> bool:
```

`ITask.everyTwelveHours`

```python
@abstractmethod
def everyTwelveHours(
    self,
) -> bool:
```

`ITask.everyTwelveHoursAt`

```python
@abstractmethod
def everyTwelveHoursAt(
    self,
    minute: int,
    second: int = 0,
) -> bool:
```

`ITask.daily`

```python
@abstractmethod
def daily(
    self,
) -> bool:
```

`ITask.dailyAt`

```python
@abstractmethod
def dailyAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`ITask.everyDays`

```python
@abstractmethod
def everyDays(
    self,
    days: int,
) -> bool:
```

`ITask.everyDaysAt`

```python
@abstractmethod
def everyDaysAt(
    self,
    days: int,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`ITask.everyTwoDays`

```python
@abstractmethod
def everyTwoDays(
    self,
) -> bool:
```

`ITask.everyTwoDaysAt`

```python
@abstractmethod
def everyTwoDaysAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`ITask.everyThreeDays`

```python
@abstractmethod
def everyThreeDays(
    self,
) -> bool:
```

`ITask.everyThreeDaysAt`

```python
@abstractmethod
def everyThreeDaysAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`ITask.everyFourDays`

```python
@abstractmethod
def everyFourDays(
    self,
) -> bool:
```

`ITask.everyFourDaysAt`

```python
@abstractmethod
def everyFourDaysAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`ITask.everyFiveDays`

```python
@abstractmethod
def everyFiveDays(
    self,
) -> bool:
```

`ITask.everyFiveDaysAt`

```python
@abstractmethod
def everyFiveDaysAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`ITask.everySixDays`

```python
@abstractmethod
def everySixDays(
    self,
) -> bool:
```

`ITask.everySixDaysAt`

```python
@abstractmethod
def everySixDaysAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`ITask.everySevenDays`

```python
@abstractmethod
def everySevenDays(
    self,
) -> bool:
```

`ITask.everySevenDaysAt`

```python
@abstractmethod
def everySevenDaysAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`ITask.everyMondayAt`

```python
@abstractmethod
def everyMondayAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`ITask.everyTuesdayAt`

```python
@abstractmethod
def everyTuesdayAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`ITask.everyWednesdayAt`

```python
@abstractmethod
def everyWednesdayAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`ITask.everyThursdayAt`

```python
@abstractmethod
def everyThursdayAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`ITask.everyFridayAt`

```python
@abstractmethod
def everyFridayAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`ITask.everySaturdayAt`

```python
@abstractmethod
def everySaturdayAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`ITask.everySundayAt`

```python
@abstractmethod
def everySundayAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`ITask.weekly`

```python
@abstractmethod
def weekly(
    self,
) -> bool:
```

`ITask.everyWeeks`

```python
@abstractmethod
def everyWeeks(
    self,
    weeks: int,
) -> bool:
```

`ITask.every`

```python
@abstractmethod
def every(
    self,
    weeks: int = 0,
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
) -> bool:
```

`ITask.cron`

```python
@abstractmethod
def cron(
    self,
    year: str | None = None,
    month: str | None = None,
    day: str | None = None,
    week: str | None = None,
    day_of_week: str | None = None,
    hour: str | None = None,
    minute: str | None = None,
    second: str | None = None,
) -> bool:
```

#### fluent/task.py

Fuente: [orionis/console/fluent/task.py](../fluent/task.py).

`Task`

```python
class Task(ITask):
```

`Task.__init__`

```python
def __init__(
    self,
    signature: str,
    args: list[str] | None,
    kwargs: dict | None = None,
    purpose: str | None = None,
) -> None:
```

`Task.entity`

```python
def entity(
    self,
    random_delay: int | None = 0,
    max_instances: int | None = 1,
    misfire_grace_time: int | None = 0,
    *,
    coalesce: bool | None = True,
) -> TaskEntity:
```

`Task.coalesce`

```python
def coalesce(
    self,
    *,
    coalesce: bool = True,
) -> Self:
```

`Task.misfireGraceTime`

```python
def misfireGraceTime(
    self,
    seconds: int = 60,
) -> Self:
```

`Task.purpose`

```python
def purpose(
    self,
    purpose: str,
) -> Self:
```

`Task.startDate`

```python
def startDate(
    self,
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
) -> Self:
```

`Task.endDate`

```python
def endDate(
    self,
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
) -> Self:
```

`Task.randomDelay`

```python
def randomDelay(
    self,
    max_seconds: int = 10,
) -> Self:
```

`Task.maxInstances`

```python
def maxInstances(
    self,
    max_instances: int,
) -> Self:
```

`Task.on`

```python
def on(
    self,
    event: TaskEvent,
    callback: Callable,
) -> Self:
```

`Task.registerListener`

```python
def registerListener(
    self,
    listener: BaseTaskListener,
) -> Self:
```

`Task.onceAt`

```python
def onceAt(
    self,
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`Task.everySeconds`

```python
def everySeconds(
    self,
    seconds: int,
) -> bool:
```

`Task.everyFiveSeconds`

```python
def everyFiveSeconds(
    self,
) -> bool:
```

`Task.everyTenSeconds`

```python
def everyTenSeconds(
    self,
) -> bool:
```

`Task.everyFifteenSeconds`

```python
def everyFifteenSeconds(
    self,
) -> bool:
```

`Task.everyTwentySeconds`

```python
def everyTwentySeconds(
    self,
) -> bool:
```

`Task.everyTwentyFiveSeconds`

```python
def everyTwentyFiveSeconds(
    self,
) -> bool:
```

`Task.everyThirtySeconds`

```python
def everyThirtySeconds(
    self,
) -> bool:
```

`Task.everyThirtyFiveSeconds`

```python
def everyThirtyFiveSeconds(
    self,
) -> bool:
```

`Task.everyFortySeconds`

```python
def everyFortySeconds(
    self,
) -> bool:
```

`Task.everyFortyFiveSeconds`

```python
def everyFortyFiveSeconds(
    self,
) -> bool:
```

`Task.everyFiftySeconds`

```python
def everyFiftySeconds(
    self,
) -> bool:
```

`Task.everyFiftyFiveSeconds`

```python
def everyFiftyFiveSeconds(
    self,
) -> bool:
```

`Task.everyMinutes`

```python
def everyMinutes(
    self,
    minutes: int,
) -> bool:
```

`Task.everyMinuteAt`

```python
def everyMinuteAt(
    self,
    seconds: int,
) -> bool:
```

`Task.everyMinutesAt`

```python
def everyMinutesAt(
    self,
    minutes: int,
    seconds: int,
) -> bool:
```

`Task.everyFiveMinutes`

```python
def everyFiveMinutes(
    self,
) -> bool:
```

`Task.everyFiveMinutesAt`

```python
def everyFiveMinutesAt(
    self,
    seconds: int,
) -> bool:
```

`Task.everyTenMinutes`

```python
def everyTenMinutes(
    self,
) -> bool:
```

`Task.everyTenMinutesAt`

```python
def everyTenMinutesAt(
    self,
    seconds: int,
) -> bool:
```

`Task.everyFifteenMinutes`

```python
def everyFifteenMinutes(
    self,
) -> bool:
```

`Task.everyFifteenMinutesAt`

```python
def everyFifteenMinutesAt(
    self,
    seconds: int,
) -> bool:
```

`Task.everyTwentyMinutes`

```python
def everyTwentyMinutes(
    self,
) -> bool:
```

`Task.everyTwentyMinutesAt`

```python
def everyTwentyMinutesAt(
    self,
    seconds: int,
) -> bool:
```

`Task.everyTwentyFiveMinutes`

```python
def everyTwentyFiveMinutes(
    self,
) -> bool:
```

`Task.everyTwentyFiveMinutesAt`

```python
def everyTwentyFiveMinutesAt(
    self,
    seconds: int,
) -> bool:
```

`Task.everyThirtyMinutes`

```python
def everyThirtyMinutes(
    self,
) -> bool:
```

`Task.everyThirtyMinutesAt`

```python
def everyThirtyMinutesAt(
    self,
    seconds: int,
) -> bool:
```

`Task.everyThirtyFiveMinutes`

```python
def everyThirtyFiveMinutes(
    self,
) -> bool:
```

`Task.everyThirtyFiveMinutesAt`

```python
def everyThirtyFiveMinutesAt(
    self,
    seconds: int,
) -> bool:
```

`Task.everyFortyMinutes`

```python
def everyFortyMinutes(
    self,
) -> bool:
```

`Task.everyFortyMinutesAt`

```python
def everyFortyMinutesAt(
    self,
    seconds: int,
) -> bool:
```

`Task.everyFortyFiveMinutes`

```python
def everyFortyFiveMinutes(
    self,
) -> bool:
```

`Task.everyFortyFiveMinutesAt`

```python
def everyFortyFiveMinutesAt(
    self,
    seconds: int,
) -> bool:
```

`Task.everyFiftyMinutes`

```python
def everyFiftyMinutes(
    self,
) -> bool:
```

`Task.everyFiftyMinutesAt`

```python
def everyFiftyMinutesAt(
    self,
    seconds: int,
) -> bool:
```

`Task.everyFiftyFiveMinutes`

```python
def everyFiftyFiveMinutes(
    self,
) -> bool:
```

`Task.everyFiftyFiveMinutesAt`

```python
def everyFiftyFiveMinutesAt(
    self,
    seconds: int,
) -> bool:
```

`Task.hourly`

```python
def hourly(
    self,
) -> bool:
```

`Task.hourlyAt`

```python
def hourlyAt(
    self,
    minute: int,
    second: int = 0,
) -> bool:
```

`Task.everyOddHours`

```python
def everyOddHours(
    self,
) -> bool:
```

`Task.everyEvenHours`

```python
def everyEvenHours(
    self,
) -> bool:
```

`Task.everyHours`

```python
def everyHours(
    self,
    hours: int,
) -> bool:
```

`Task.everyHoursAt`

```python
def everyHoursAt(
    self,
    hours: int,
    minute: int,
    second: int = 0,
) -> bool:
```

`Task.everyTwoHours`

```python
def everyTwoHours(
    self,
) -> bool:
```

`Task.everyTwoHoursAt`

```python
def everyTwoHoursAt(
    self,
    minute: int,
    second: int = 0,
) -> bool:
```

`Task.everyThreeHours`

```python
def everyThreeHours(
    self,
) -> bool:
```

`Task.everyThreeHoursAt`

```python
def everyThreeHoursAt(
    self,
    minute: int,
    second: int = 0,
) -> bool:
```

`Task.everyFourHours`

```python
def everyFourHours(
    self,
) -> bool:
```

`Task.everyFourHoursAt`

```python
def everyFourHoursAt(
    self,
    minute: int,
    second: int = 0,
) -> bool:
```

`Task.everyFiveHours`

```python
def everyFiveHours(
    self,
) -> bool:
```

`Task.everyFiveHoursAt`

```python
def everyFiveHoursAt(
    self,
    minute: int,
    second: int = 0,
) -> bool:
```

`Task.everySixHours`

```python
def everySixHours(
    self,
) -> bool:
```

`Task.everySixHoursAt`

```python
def everySixHoursAt(
    self,
    minute: int,
    second: int = 0,
) -> bool:
```

`Task.everySevenHours`

```python
def everySevenHours(
    self,
) -> bool:
```

`Task.everySevenHoursAt`

```python
def everySevenHoursAt(
    self,
    minute: int,
    second: int = 0,
) -> bool:
```

`Task.everyEightHours`

```python
def everyEightHours(
    self,
) -> bool:
```

`Task.everyEightHoursAt`

```python
def everyEightHoursAt(
    self,
    minute: int,
    second: int = 0,
) -> bool:
```

`Task.everyNineHours`

```python
def everyNineHours(
    self,
) -> bool:
```

`Task.everyNineHoursAt`

```python
def everyNineHoursAt(
    self,
    minute: int,
    second: int = 0,
) -> bool:
```

`Task.everyTenHours`

```python
def everyTenHours(
    self,
) -> bool:
```

`Task.everyTenHoursAt`

```python
def everyTenHoursAt(
    self,
    minute: int,
    second: int = 0,
) -> bool:
```

`Task.everyElevenHours`

```python
def everyElevenHours(
    self,
) -> bool:
```

`Task.everyElevenHoursAt`

```python
def everyElevenHoursAt(
    self,
    minute: int,
    second: int = 0,
) -> bool:
```

`Task.everyTwelveHours`

```python
def everyTwelveHours(
    self,
) -> bool:
```

`Task.everyTwelveHoursAt`

```python
def everyTwelveHoursAt(
    self,
    minute: int,
    second: int = 0,
) -> bool:
```

`Task.daily`

```python
def daily(
    self,
) -> bool:
```

`Task.dailyAt`

```python
def dailyAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`Task.everyDays`

```python
def everyDays(
    self,
    days: int,
) -> bool:
```

`Task.everyDaysAt`

```python
def everyDaysAt(
    self,
    days: int,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`Task.everyTwoDays`

```python
def everyTwoDays(
    self,
) -> bool:
```

`Task.everyTwoDaysAt`

```python
def everyTwoDaysAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`Task.everyThreeDays`

```python
def everyThreeDays(
    self,
) -> bool:
```

`Task.everyThreeDaysAt`

```python
def everyThreeDaysAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`Task.everyFourDays`

```python
def everyFourDays(
    self,
) -> bool:
```

`Task.everyFourDaysAt`

```python
def everyFourDaysAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`Task.everyFiveDays`

```python
def everyFiveDays(
    self,
) -> bool:
```

`Task.everyFiveDaysAt`

```python
def everyFiveDaysAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`Task.everySixDays`

```python
def everySixDays(
    self,
) -> bool:
```

`Task.everySixDaysAt`

```python
def everySixDaysAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`Task.everySevenDays`

```python
def everySevenDays(
    self,
) -> bool:
```

`Task.everySevenDaysAt`

```python
def everySevenDaysAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`Task.everyMondayAt`

```python
def everyMondayAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`Task.everyTuesdayAt`

```python
def everyTuesdayAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`Task.everyWednesdayAt`

```python
def everyWednesdayAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`Task.everyThursdayAt`

```python
def everyThursdayAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`Task.everyFridayAt`

```python
def everyFridayAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`Task.everySaturdayAt`

```python
def everySaturdayAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`Task.everySundayAt`

```python
def everySundayAt(
    self,
    hour: int,
    minute: int = 0,
    second: int = 0,
) -> bool:
```

`Task.weekly`

```python
def weekly(
    self,
) -> bool:
```

`Task.everyWeeks`

```python
def everyWeeks(
    self,
    weeks: int,
) -> bool:
```

`Task.every`

```python
def every(
    self,
    weeks: int = 0,
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
) -> bool:
```

`Task.cron`

```python
def cron(
    self,
    year: str | None = None,
    month: str | None = None,
    day: str | None = None,
    week: str | None = None,
    day_of_week: str | None = None,
    hour: str | None = None,
    minute: str | None = None,
    second: str | None = None,
) -> bool:
```

#### kernel.py

Fuente: [orionis/console/kernel.py](../kernel.py).

`KernelCLI`

```python
class KernelCLI(IKernelCLI):
```

`KernelCLI fields`

```python
__slots__ = ("__reactor",)
IGNORE_FLAGS: ClassVar[frozenset[str]] = frozenset({
        "reactor", "-c", "-m", "-", "-i", "-q", "-B", "-O", "-OO", "-v",
        "-vv", "-d", "-x", "-E", "-s", "-S", "-u", "-I", "-W",
    })
```

`KernelCLI.boot`

```python
async def boot(
    self,
    application: IApplication,
) -> None:
```

`KernelCLI.handle`

```python
async def handle(self, args: list[str] | None = None) -> int:
```

#### output/__init__.py

Fuente: [orionis/console/output/__init__.py](../output/__init__.py).

Sin API pública declarada directamente; inicializador o soporte privado de integración.

#### output/console.py

Fuente: [orionis/console/output/console.py](../output/console.py).

`Console`

```python
class Console(IConsole):
```

`Console.progressBar`

```python
@property
def progressBar(self) -> IProgressBar:
```

`Console.success`

```python
def success(self, message: str, *, timestamp: bool = True) -> None:
```

`Console.textSuccess`

```python
def textSuccess(self, message: str) -> None:
```

`Console.textSuccessBold`

```python
def textSuccessBold(self, message: str) -> None:
```

`Console.info`

```python
def info(self, message: str, *, timestamp: bool = True) -> None:
```

`Console.textInfo`

```python
def textInfo(self, message: str) -> None:
```

`Console.textInfoBold`

```python
def textInfoBold(self, message: str) -> None:
```

`Console.warning`

```python
def warning(self, message: str, *, timestamp: bool = True) -> None:
```

`Console.textWarning`

```python
def textWarning(self, message: str) -> None:
```

`Console.textWarningBold`

```python
def textWarningBold(self, message: str) -> None:
```

`Console.fail`

```python
def fail(self, message: str, *, timestamp: bool = True) -> None:
```

`Console.error`

```python
def error(self, message: str, *, timestamp: bool = True) -> None:
```

`Console.textError`

```python
def textError(self, message: str) -> None:
```

`Console.textErrorBold`

```python
def textErrorBold(self, message: str) -> None:
```

`Console.textMuted`

```python
def textMuted(self, message: str) -> None:
```

`Console.textMutedBold`

```python
def textMutedBold(self, message: str) -> None:
```

`Console.textUnderline`

```python
def textUnderline(self, message: str) -> None:
```

`Console.clear`

```python
def clear(self) -> None:
```

`Console.clearLine`

```python
def clearLine(self) -> None:
```

`Console.line`

```python
def line(self) -> None:
```

`Console.newLine`

```python
def newLine(self, count: int = 1) -> None:
```

`Console.write`

```python
def write(
    self,
    *values: object,
    sep: str | None = " ",
    end: str | None = "\n",
    file: SupportsWrite[str] | None = None,
    flush: bool = False,
) -> None:
```

`Console.writeLine`

```python
def writeLine(self, message: str) -> None:
```

`Console.ask`

```python
def ask(self, question: str) -> str:
```

`Console.confirm`

```python
def confirm(self, question: str, *, default: bool = False) -> bool:
```

`Console.secret`

```python
def secret(self, question: str) -> str:
```

`Console.table`

```python
def table(self, headers: list, rows: list) -> None:
```

`Console.anticipate`

```python
def anticipate(self, question: str, options: list, default: None = None) -> str:
```

`Console.choice`

```python
def choice(self, question: str, choices: list, default_index: int = 0) -> str:
```

`Console.exception`

```python
def exception(self, exception: Exception) -> None:
```

`Console.exitSuccess`

```python
def exitSuccess(self, message: str | None = None) -> None:
```

`Console.exitError`

```python
def exitError(self, message: str| None = None) -> None:
```

`Console.dump`

```python
def dump(
    self,
    *args: type[Any],
    show_types: bool = True,
    show_index: bool = False,
    expand_all: bool = True,
    max_depth: int | None = None,
    module_path: str | None = None,
    line_number: int | None = None,
    force_exit: bool = False,
    redirect_output: bool = False,
    insert_line: bool = False,
) -> None:
```

`Console.sleep`

```python
async def sleep(self, seconds: float) -> None:
```

#### output/contracts/__init__.py

Fuente: [orionis/console/output/contracts/__init__.py](../output/contracts/__init__.py).

Sin API pública declarada directamente; inicializador o soporte privado de integración.

#### output/contracts/console.py

Fuente: [orionis/console/output/contracts/console.py](../output/contracts/console.py).

`IConsole`

```python
class IConsole(ABC):
```

`IConsole.progressBar`

```python
@property
@abstractmethod
def progressBar(self) -> IProgressBar:
```

`IConsole.success`

```python
@abstractmethod
def success(self, message: str, *, timestamp: bool = True) -> None:
```

`IConsole.textSuccess`

```python
@abstractmethod
def textSuccess(self, message: str) -> None:
```

`IConsole.textSuccessBold`

```python
@abstractmethod
def textSuccessBold(self, message: str) -> None:
```

`IConsole.info`

```python
@abstractmethod
def info(self, message: str, *, timestamp: bool = True) -> None:
```

`IConsole.textInfo`

```python
@abstractmethod
def textInfo(self, message: str) -> None:
```

`IConsole.textInfoBold`

```python
@abstractmethod
def textInfoBold(self, message: str) -> None:
```

`IConsole.warning`

```python
@abstractmethod
def warning(self, message: str, *, timestamp: bool = True) -> None:
```

`IConsole.textWarning`

```python
@abstractmethod
def textWarning(self, message: str) -> None:
```

`IConsole.textWarningBold`

```python
@abstractmethod
def textWarningBold(self, message: str) -> None:
```

`IConsole.fail`

```python
@abstractmethod
def fail(self, message: str, *, timestamp: bool = True) -> None:
```

`IConsole.error`

```python
@abstractmethod
def error(self, message: str, *, timestamp: bool = True) -> None:
```

`IConsole.textError`

```python
@abstractmethod
def textError(self, message: str) -> None:
```

`IConsole.textErrorBold`

```python
@abstractmethod
def textErrorBold(self, message: str) -> None:
```

`IConsole.textMuted`

```python
@abstractmethod
def textMuted(self, message: str) -> None:
```

`IConsole.textMutedBold`

```python
@abstractmethod
def textMutedBold(self, message: str) -> None:
```

`IConsole.textUnderline`

```python
@abstractmethod
def textUnderline(self, message: str) -> None:
```

`IConsole.clear`

```python
@abstractmethod
def clear(self) -> None:
```

`IConsole.clearLine`

```python
@abstractmethod
def clearLine(self) -> None:
```

`IConsole.line`

```python
@abstractmethod
def line(self) -> None:
```

`IConsole.newLine`

```python
@abstractmethod
def newLine(self, count: int = 1) -> None:
```

`IConsole.write`

```python
@abstractmethod
def write(
    self,
    *values: object,
    sep: str | None = " ",
    end: str | None = "\n",
    file: SupportsWrite[str] | None = None,
    flush: bool = False,
) -> None:
```

`IConsole.writeLine`

```python
@abstractmethod
def writeLine(self, message: str) -> None:
```

`IConsole.ask`

```python
@abstractmethod
def ask(self, question: str) -> str:
```

`IConsole.confirm`

```python
@abstractmethod
def confirm(self, question: str, *, default: bool = False) -> bool:
```

`IConsole.secret`

```python
@abstractmethod
def secret(self, question: str) -> str:
```

`IConsole.table`

```python
@abstractmethod
def table(self, headers: list, rows: list) -> None:
```

`IConsole.anticipate`

```python
@abstractmethod
def anticipate(self, question: str, options: list, default: None = None) -> str:
```

`IConsole.choice`

```python
@abstractmethod
def choice(self, question: str, choices: list, default_index: int = 0) -> str:
```

`IConsole.exception`

```python
@abstractmethod
def exception(self, exception: Exception) -> None:
```

`IConsole.exitSuccess`

```python
@abstractmethod
def exitSuccess(self, message: str | None = None) -> None:
```

`IConsole.exitError`

```python
@abstractmethod
def exitError(self, message: str| None = None) -> None:
```

`IConsole.dump`

```python
@abstractmethod
def dump(
    self,
    *args: type[Any],
    show_types: bool = True,
    show_index: bool = False,
    expand_all: bool = True,
    max_depth: int | None = None,
    module_path: str | None = None,
    line_number: int | None = None,
    force_exit: bool = False,
    redirect_output: bool = False,
    insert_line: bool = False,
) -> None:
```

`IConsole.sleep`

```python
@abstractmethod
async def sleep(self, seconds: float) -> None:
```

#### output/contracts/executor.py

Fuente: [orionis/console/output/contracts/executor.py](../output/contracts/executor.py).

`IExecutor`

```python
class IExecutor(ABC):
```

`IExecutor.running`

```python
@abstractmethod
def running(self, program: str, time: str = "") -> None:
```

`IExecutor.done`

```python
@abstractmethod
def done(self, program: str, time: str = "") -> None:
```

`IExecutor.fail`

```python
@abstractmethod
def fail(self, program: str, time: str = "") -> None:
```

#### output/contracts/help_command.py

Fuente: [orionis/console/output/contracts/help_command.py](../output/contracts/help_command.py).

`IHelpCommand`

```python
class IHelpCommand(ABC):
```

`IHelpCommand.parseActions`

```python
@staticmethod
@abstractmethod
def parseActions(
    actions: list[argparse.Action],
) -> dict[str, Any]:
```

`IHelpCommand.printActions`

```python
@staticmethod
@abstractmethod
def printActions(
    command_name: str,
    actions: list[argparse.Action],
    *,
    is_error: bool = False,
) -> None:
```

#### output/contracts/http_request.py

Fuente: [orionis/console/output/contracts/http_request.py](../output/contracts/http_request.py).

`IHTTPRequestPrinter`

```python
class IHTTPRequestPrinter(ABC):
```

`IHTTPRequestPrinter.setEnabled`

```python
@abstractmethod
def setEnabled(self, *, enabled: bool) -> None:
```

`IHTTPRequestPrinter.start`

```python
@abstractmethod
async def start(self) -> None:
```

`IHTTPRequestPrinter.stop`

```python
@abstractmethod
async def stop(self) -> None:
```

`IHTTPRequestPrinter.startTimer`

```python
@abstractmethod
def startTimer(self) -> float | None:
```

`IHTTPRequestPrinter.printRequest`

```python
@abstractmethod
def printRequest(
    self,
    adapter: TransportAdapter,
    response: Response,
) -> None:
```

#### output/contracts/var_dumper.py

Fuente: [orionis/console/output/contracts/var_dumper.py](../output/contracts/var_dumper.py).

`IVarDumper`

```python
class IVarDumper(ABC):
```

`IVarDumper.showTypes`

```python
@abstractmethod
def showTypes(self, *, show: bool = True) -> IVarDumper:
```

`IVarDumper.showIndex`

```python
@abstractmethod
def showIndex(self, *, show: bool = True) -> IVarDumper:
```

`IVarDumper.expandAll`

```python
@abstractmethod
def expandAll(self, *, expand: bool = True) -> IVarDumper:
```

`IVarDumper.maxDepth`

```python
@abstractmethod
def maxDepth(self, depth: int | None) -> IVarDumper:
```

`IVarDumper.modulePath`

```python
@abstractmethod
def modulePath(self, path: str | None) -> IVarDumper:
```

`IVarDumper.lineNumber`

```python
@abstractmethod
def lineNumber(self, number: int | None) -> IVarDumper:
```

`IVarDumper.forceExit`

```python
@abstractmethod
def forceExit(self, *, force: bool = True) -> IVarDumper:
```

`IVarDumper.redirectOutput`

```python
@abstractmethod
def redirectOutput(self, *, redirect: bool = True) -> IVarDumper:
```

`IVarDumper.values`

```python
@abstractmethod
def values(self, *args: tuple | list) -> IVarDumper:
```

`IVarDumper.value`

```python
@abstractmethod
def value(self, value: type[T]) -> IVarDumper:
```

`IVarDumper.print`

```python
@abstractmethod
def print(self, *, insert_line: bool = False) -> None:
```

`IVarDumper.toHtml`

```python
@abstractmethod
def toHtml(self, *, insert_line: bool = False) -> str:
```

#### output/executor.py

Fuente: [orionis/console/output/executor.py](../output/executor.py).

`Executor`

```python
class Executor(IExecutor):
```

`Executor.running`

```python
def running(self, program: str, time: str = "") -> None:
```

`Executor.done`

```python
def done(self, program: str, time: str = "") -> None:
```

`Executor.fail`

```python
def fail(self, program: str, time: str = "") -> None:
```

#### output/help_command.py

Fuente: [orionis/console/output/help_command.py](../output/help_command.py).

`HelpCommand`

```python
class HelpCommand(IHelpCommand):
```

`HelpCommand.parseActions`

```python
@staticmethod
def parseActions(
    actions: list[argparse.Action],
) -> dict[str, Any]:
```

`HelpCommand.printActions`

```python
@staticmethod
def printActions( # NOSONAR
    command_name: str,
    actions: list[argparse.Action],
    *,
    is_error: bool = False,
) -> None:
```

#### output/http_request.py

Fuente: [orionis/console/output/http_request.py](../output/http_request.py).

`HTTPRequestPrinter`

```python
class HTTPRequestPrinter(IHTTPRequestPrinter):
```

`HTTPRequestPrinter fields`

```python
HTTP_MIN_STATUS_CODE: ClassVar[int] = 100
HTTP_COLORS: ClassVar[dict] = {
        "GET":     (_BG_GREEN,   _FG_BLACK),
        "POST":    (_BG_BLUE,    _FG_WHITE),
        "PUT":     (_BG_YELLOW,  _FG_BLACK),
        "PATCH":   (_BG_MAGENTA, _FG_WHITE),
        "DELETE":  (_BG_RED,     _FG_WHITE),
        "OPTIONS": (_BG_CYAN,    _FG_BLACK),
        "HEAD":    (_BG_WHITE,   _FG_BLACK),
        "TRACE":   (_BG_GREY70,  _FG_BLACK),
        "CONNECT": (_BG_BRIGHT,  _FG_WHITE),
        "QUERY":   (_BG_GREY37,  _FG_WHITE),
        "default": (_BG_GREY37,  _FG_WHITE),
    }
STATUS_COLORS: ClassVar[dict] = {
        "1xx": (_BG_CYAN,    _FG_BLACK),
        "2xx": (_BG_GREEN,   _FG_WHITE),
        "3xx": (_BG_YELLOW,  _FG_BLACK),
        "4xx": (_BG_MAGENTA, _FG_WHITE),
        "5xx": (_BG_RED,     _FG_WHITE),
        "default": (_BG_GREY50, _FG_WHITE),
    }
```

`HTTPRequestPrinter.__init__`

```python
def __init__(self) -> None:
```

`HTTPRequestPrinter.setEnabled`

```python
def setEnabled(self, *, enabled: bool) -> None:
```

`HTTPRequestPrinter.start`

```python
async def start(self) -> None:
```

`HTTPRequestPrinter.stop`

```python
async def stop(self) -> None:
```

`HTTPRequestPrinter.startTimer`

```python
def startTimer(self) -> float | None:
```

`HTTPRequestPrinter.printRequest`

```python
def printRequest(
    self,
    adapter: TransportAdapter,
    response: Response,
) -> None:
```

#### output/var_dumper.py

Fuente: [orionis/console/output/var_dumper.py](../output/var_dumper.py).

`VarDumper`

```python
class VarDumper(IVarDumper):
```

`VarDumper.__init__`

```python
def __init__(self) -> None:
```

`VarDumper.showTypes`

```python
def showTypes(self, *, show: bool = True) -> VarDumper:
```

`VarDumper.showIndex`

```python
def showIndex(self, *, show: bool = True) -> VarDumper:
```

`VarDumper.expandAll`

```python
def expandAll(self, *, expand: bool = True) -> VarDumper:
```

`VarDumper.maxDepth`

```python
def maxDepth(self, depth: int | None) -> VarDumper:
```

`VarDumper.modulePath`

```python
def modulePath(self, path: str | None) -> VarDumper:
```

`VarDumper.lineNumber`

```python
def lineNumber(self, number: int | None) -> VarDumper:
```

`VarDumper.forceExit`

```python
def forceExit(self, *, force: bool = True) -> VarDumper:
```

`VarDumper.redirectOutput`

```python
def redirectOutput(self, *, redirect: bool = True) -> VarDumper:
```

`VarDumper.values`

```python
def values(self, *args: tuple | list) -> VarDumper:
```

`VarDumper.value`

```python
def value(self, value: type[T]) -> VarDumper:
```

`VarDumper.print`

```python
def print(self, *, insert_line: bool = False) -> None:
```

`VarDumper.toHtml`

```python
def toHtml(self, *, insert_line: bool = False) -> str:
```

#### reactor_provider.py

Fuente: [orionis/console/reactor_provider.py](../reactor_provider.py).

`ReactorProvider`

```python
class ReactorProvider(ServiceProvider):
```

`ReactorProvider.register`

```python
def register(self) -> None:
```

`ReactorProvider.boot`

```python
async def boot(self) -> None:
```

#### scheduler_provider.py

Fuente: [orionis/console/scheduler_provider.py](../scheduler_provider.py).

`ScheduleProvider`

```python
class ScheduleProvider(ServiceProvider):
```

`ScheduleProvider.register`

```python
def register(self) -> None:
```

`ScheduleProvider.boot`

```python
async def boot(self) -> None:
```

#### stdio.py

Fuente: [orionis/console/stdio.py](../stdio.py).

`protocol_stdout`

```python
def protocol_stdout() -> BinaryIO | None:
```

`protocol_stdio`

```python
@contextmanager
def protocol_stdio(arguments: Sequence[str] | None) -> Generator[None]:
```

#### tasks/__init__.py

Fuente: [orionis/console/tasks/__init__.py](../tasks/__init__.py).

Sin API pública declarada directamente; inicializador o soporte privado de integración.

#### tasks/schedule.py

Fuente: [orionis/console/tasks/schedule.py](../tasks/schedule.py).

`Schedule`

```python
class Schedule(ISchedule):
```

`Schedule.__init__`

```python
def __init__(
    self,
    reactor: IReactor,
    exception_handler: ICatch,
    stores: IScheduleStore,
) -> None:
```

`Schedule.info`

```python
async def info(self) -> list[dict]:
```

`Schedule.boot`

```python
async def boot(self) -> None:
```

`Schedule.on`

```python
def on(
    self,
    event: SchedulerEvent,
    listener: Callable,
) -> Self:
```

`Schedule.state`

```python
def state(self) -> str:
```

`Schedule.isRunning`

```python
def isRunning(self) -> bool:
```

`Schedule.isPaused`

```python
def isPaused(self) -> bool:
```

`Schedule.isStopped`

```python
def isStopped(self) -> bool:
```

`Schedule.command`

```python
def command(
    self,
    signature: str,
    args: list[str] | None = None,
    purpose: str | None = None,
) -> ITask:
```

`Schedule.pauseTask`

```python
def pauseTask(
    self,
    signature: str,
) -> bool:
```

`Schedule.resumeTask`

```python
def resumeTask(
    self,
    signature: str,
) -> bool:
```

`Schedule.removeTask`

```python
def removeTask(
    self,
    signature: str,
) -> bool:
```

`Schedule.removeAllTasks`

```python
def removeAllTasks(self) -> bool:
```

`Schedule.pause`

```python
def pause(self) -> bool:
```

`Schedule.resume`

```python
def resume(self) -> bool:
```

`Schedule.shutdown`

```python
def shutdown(self, wait: int | None = None) -> None:
```

`Schedule.wait`

```python
async def wait(self) -> None:
```

#### tasks/store.py

Fuente: [orionis/console/tasks/store.py](../tasks/store.py).

`ScheduleStore`

```python
class ScheduleStore(IScheduleStore):
```

`ScheduleStore.__init__`

```python
def __init__(
    self,
    app: IApplication,
    db_manager: IConnectionManager,
) -> None:
```

`ScheduleStore.store`

```python
@property
def store(self) -> str:
```

`ScheduleStore.config`

```python
@property
def config(self) -> ConfigScheduler:
```

`ScheduleStore.redis`

```python
def redis(self) -> RedisJobStore:
```

`ScheduleStore.database`

```python
def database(self) -> SQLAlchemyJobStore:
```

#### templates/__init__.py

Fuente: [orionis/console/templates/__init__.py](../templates/__init__.py).

Sin API pública declarada directamente; inicializador o soporte privado de integración.

#### templates/stub.py

Fuente: [orionis/console/templates/stub.py](../templates/stub.py).

`Stub`

```python
class Stub:
```

`Stub fields`

```python
__slots__ = (
        "_class_name",
        "_classname",
        "_directory_parts",
        "_filename",
        "_postfix",
        "_prefix",
        "_replacements",
        "_template_name",
    )
```

`Stub.__init__`

```python
def __init__(
    self,
    template_name: str,
    class_name: str,
    prefix: str | None = None,
    postfix: str | None = None,
    replacements: dict[str, str] | None = None,
) -> None:
```

`Stub.create`

```python
def create(
    self,
    directory: Path,
    relative_to: Path | None = None,
    extension: str = "py",
) -> str:
```

## Ejemplos de uso

Cada bloque es un script independiente para Python 3.14+. Los recursos están
en memoria o temporales fuera del checkout. Ninguno inicia servidor real,
contacta Redis o servicios externos, instala en el venv del repo ni limpia
almacenamiento compartido. No se afirma estabilidad del texto exacto ANSI,
layout, tiempos o PID.

### 1. Parsear argumentos y manejar un error real de definición

```python
import argparse
from orionis.console import Argument
from orionis.console.enums import ArgumentAction
from orionis.support.types.sentinel import MISSING

parser = argparse.ArgumentParser(prog="example:report", add_help=False)
Argument(name_or_flags="name", type_=str).addToParser(parser)
Argument(name_or_flags=("--count", "-c"), type_=int, default=2).addToParser(parser)
Argument(
    name_or_flags="--verbose", action=ArgumentAction.STORE_TRUE,
).addToParser(parser)
parsed = vars(parser.parse_args(["Ada", "--count=3"]))
assert parsed["name"] == "Ada" and parsed["count"] == 3
assert parsed["verbose"] is MISSING
filtered = {key: value for key, value in parsed.items() if value is not MISSING}
assert "verbose" not in filtered
try:
    Argument(name_or_flags="-h")
except ValueError:
    pass
else:
    error_msg = "Expected reserved-help validation"
    raise AssertionError(error_msg)
```

### 2. Reutilizar argumentos e inspeccionar una declaración fluida

```python
import asyncio
from orionis.console import Argument
from orionis.console.base import BaseCommand
from orionis.console.fluent.command import Command

class TotalCommand(BaseCommand):
    """Return a total from parsed command arguments."""

    signature = "example:total"
    description = "Compute a local total."

    async def handle(self) -> int:
        """Return twice the requested amount."""
        return self.getArgument("amount", 1) * 2

async def main() -> None:
    """Exercise base state and fluent metadata without discovery."""
    command = TotalCommand()
    command.setArguments({"amount": 3, "nullable": None})
    command.setArguments({"other": True})
    assert await command.handle() == 6
    assert command.getArgument("nullable", "fallback") is None
    copy = command.getArguments()
    copy.clear()
    assert command.getArgument("amount") == 3
    builder = Command("example:total", TotalCommand).timestamp(enabled=False)
    builder.description("Local total").arguments([
        Argument(name_or_flags="--amount", type_=int),
    ])
    signature, entity = builder.get()
    assert signature == "example:total" and entity.method == "handle"
    assert not entity.timestamps and len(entity.args) == 1

asyncio.run(main())
```

### 3. Capturar salida, progreso y HTML sin terminar el proceso

```python
from contextlib import redirect_stdout
from io import StringIO
from orionis.console import Console, ProgressBar
from orionis.console.output.var_dumper import VarDumper

captured = StringIO()
with redirect_stdout(captured):
    console = Console()
    console.info("ready", timestamp=False)
    console.table(["Name", "State"], [["worker", "local"]])
    assert console.progressBar is not console.progressBar
    progress = ProgressBar(total=2, width=4)
    progress.start()
    progress.advance()
    progress.finish()
    assert progress.progress == 2
    dumper = VarDumper().showIndex(show=False).value({"value": 7})
    html = dumper.toHtml()
assert "ready" in captured.getvalue() and "worker" in captured.getvalue()
assert "<pre" in html and "value" in html
```

### 4. Inspeccionar e iniciar un schedule memory futuro

```python
import asyncio
from types import SimpleNamespace
from orionis.console.tasks.schedule import Schedule

class Commands:
    """Supply available signatures for schedule validation."""

    async def info(self) -> list[dict]:
        """Return the one declared local signature."""
        return [{"signature": "example:future"}]

    async def call(self, signature: str, args: list[str]) -> int:
        """Return success for a local signature."""
        assert signature == "example:future"
        return 0

class Catch:
    """Expose the scheduler's exception collaborator."""

    async def exception(self, error: Exception) -> None:
        """Reject unexpected callback errors in this example."""
        raise error

async def main() -> None:
    """Start and stop a memory scheduler without executing future work."""
    config = SimpleNamespace(
        store="memory", jitter=0, max_instances=1,
        misfire_grace_time=30, coalesce=True, replace_existing=True,
    )
    stores = SimpleNamespace(config=config, store="memory")
    schedule = Schedule(Commands(), Catch(), stores)
    task = schedule.command("example:future", purpose="Future local job")
    task.maxInstances(2).coalesce(coalesce=False).randomDelay(0)
    assert task.onceAt(2099, 1, 1) is True
    rows = await schedule.info()
    assert rows[0]["coalesce"] is False
    assert schedule.state() == "STOPPED"
    await schedule.boot()
    try:
        assert schedule.isRunning()
        assert schedule.pause()
        assert schedule.isPaused()
        assert schedule.resume()
        assert schedule.removeAllTasks()
    finally:
        schedule.shutdown(wait=0)
        await asyncio.wait_for(schedule.wait(), timeout=5)

asyncio.run(main())
```

Se ejercita el ciclo real del scheduler con una fecha posterior a la de
validación y se eliminan jobs antes de shutdown. No prueba serialización
persistente ni ejecución mediante la fachada Reactor.

### 5. Generar y compilar un comando temporal

```python
import ast
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.console.templates.stub import Stub

with TemporaryDirectory(prefix="orionis-console-stub-") as directory:
    root = Path(directory)
    generator = Stub(
        "console_command", "reports/daily", postfix="Command",
        replacements={
            "signature_literal": repr("example:daily"),
            "description_literal": repr("Generate a local report."),
        },
    )
    relative = generator.create(root, relative_to=root)
    target = root / relative
    source = target.read_text(encoding="utf-8")
    ast.parse(source)
    assert "class DailyCommand" in source and "example:daily" in source
    try:
        generator.create(root)
    except FileExistsError:
        pass
    else:
        error_msg = "Expected exclusive file creation"
        raise AssertionError(error_msg)
```

El handle generado queda intencionadamente sin implementar por su plantilla;
el script valida generación y sintaxis, no un resultado de comando ficticio.

### 6. Separar texto diagnóstico MCP de stdout binario

```python
import sys
from contextlib import redirect_stderr, redirect_stdout
from io import BytesIO, StringIO, TextIOWrapper
from orionis.console.stdio import protocol_stdio, protocol_stdout

binary = BytesIO()
writer = TextIOWrapper(binary, encoding="utf-8")
diagnostics = StringIO()
with redirect_stdout(writer), redirect_stderr(diagnostics):
    assert protocol_stdout() is None
    with protocol_stdio(["reactor", "mcp:start", "example"]):
        assert protocol_stdout() is binary
        print("diagnostic")
        protocol_stdout().write(b"protocol\n")
        with protocol_stdio(["mcp:start", "example"]):
            assert protocol_stdout() is binary
    assert sys.stdout is writer and protocol_stdout() is None
writer.flush()
assert binary.getvalue() == b"protocol\n"
assert diagnostics.getvalue() == "diagnostic\n"
writer.detach()
```

### 7. Despachar un comando fluido con la aplicación real

```python
import asyncio
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

route_source = '\n'.join([
    'from orionis.console import Argument',
    'from orionis.support.facades.reactor import Reactor',
    'class Handler:',
    '    def run(self, amount: int = 1) -> int:',
    '        return amount * 2',
    'Reactor.command("example:double", [Handler, "run"])'
    '.timestamp(enabled=False).arguments(['
    'Argument(name_or_flags="--amount", type_=int, default=1)])',
    '',
])
with TemporaryDirectory(prefix="orionis-console-application-") as directory:
    root = Path(directory)
    (root / "app/console/commands").mkdir(parents=True)
    (root / "routes").mkdir()
    (root / "routes/__init__.py").write_text("", encoding="utf-8")
    (root / "routes/console.py").write_text(route_source, encoding="utf-8")
    original_cwd = Path.cwd()
    os.chdir(root)
    sys.path.insert(0, str(root))
    try:
        from orionis import Application
        from orionis.console.core.contracts.reactor import IReactor

        app = Application(base_path=root).withRouting(console="routes/console.py")

        async def main() -> None:
            """Boot providers and dispatch one isolated fluent command."""
            await app.boot()
            reactor = await app.make(IReactor)
            assert await reactor.hasCommand("example:double")
            result = await app.handleCommand([
                "reactor", "example:double", "--amount=3",
            ])
            assert result == 6
            assert await reactor.call("example:missing") == 1

        asyncio.run(main())
    finally:
        import logging
        logging.shutdown()
        sys.path.remove(str(root))
        os.chdir(original_cwd)
```

Esto cubre providers, import de ruta, argparse, DI y KernelCLI con estado
temporal. El catch real reporta el comando ausente deliberado; no se presume
un traceback de texto exacto.

## Características de diseño

- Exports diferidos conviven con imports eager de `core.commands`. Guardar
  metadata no implica que los demás módulos core permanezcan sin importar.
- Los bindings son singletons eager; `ReactorProvider` fija su fachada;
  `ScheduleProvider` registra store antes de scheduler y luego fija Schedule.
- KernelCLI declara slots y su contrato slots vacíos. La mayoría de servicios
  y ABC no usan slots; no deduzcas ausencia global de diccionarios.
  Argument tiene slots de dataclass y Stub los declara.
- Builders mutables y metadata/listings guardados retienen referencias.
  Los payloads dataclass son keyword-only, con factories mutables declaradas.
- Los jobs usan callable de módulo para no serializar la instancia Schedule
  al guardarlos.

Fuentes: grupos enlazados, [../reactor_provider.py](../reactor_provider.py),
[../scheduler_provider.py](../scheduler_provider.py) y campos literales.

## Rendimiento y concurrencia

Registros y cachés de loader/reactor no tienen sincronización aquí.
El reactor singleton comparte contador mutable entre llamadas; abrir scopes
no lo serializa ni vuelve thread-safe todos los colaboradores. Las cachés
info pueden quedar desactualizadas; los objetos vivos retornados no son
copias salvo indicación. Resolver parsers o tipos puede importar módulos.

Input/output console, I/O de artefactos, plantillas, filesystem de support
y construcción SQL job store incluyen trabajo síncrono. Declarar async
no garantiza que no bloquee. Make delega archivos a workers; cancelar no
revierte escrituras iniciadas. Serve tiene lock asyncio por instancia y
reconstruye estado por llamada, no un singleton global. No asumas seguridad
al mutar argumentos concurrentemente en instancias con estado.

La cola HTTP descarta overflow y comparte timer. Progreso captura stdout,
pero diagnóstico o redirección pueden cambiar streams globales. Schedule usa
tareas de listeners gestionadas, sets mutables, comportamiento de leases y
clientes job store, y cambios globales de logging. Shutdown no es un reset
general de reutilización. No se realizaron benchmarks.

> ⚠️ No especificado en el código fuente: un contrato global de seguridad de
> despacho concurrente o entre hilos, scheduling persistente exactly-once,
> rollback completo de archivos generados o printing diagnóstico HTTP sin pérdidas.

## Notas de compatibilidad

El mínimo declarado es Python `>=3.14`; se ejecutó con **CPython 3.14.6 en
Windows** desde el venv del repo. Las fuentes usan `typing.Self`, uniones,
slots y keyword-only dataclass y `Path.walk`. Las anotaciones diferidas,
string o bajo TYPE_CHECKING pueden necesitar nombres no disponibles para
evaluación runtime irrestricta. Los tipos DI se verifican desde fuentes reales,
no se adivinan.

| Dependencia | Rango declarado | Lockfile | Entorno de validación |
| --- | --- | --- | --- |
| `apscheduler` | `>=3.11.3,<4.0` | `3.11.3` | `3.11.3` |
| `rich` | `>=15.0.0,<16.0` | `15.0.0` | `15.0.0` |
| `granian` | `>=2.8.3,<3.0` | `2.8.4` | `2.8.4` |
| `sqlalchemy` | `>=2.0.54,<3.0` | `2.1.1` | `2.1.1` |
| `redis` | `>=8.1.0` | `8.1.0` | `8.1.0` |
| `msgspec` | `>=0.21.1` | `0.22.0` | `0.22.0` |
| `pendulum` | `>=3.2.0,<4.0` | `3.2.0` | `3.2.0` |
| `psutil` | `>=7.2.2,<8.0` | `7.2.2` | `7.2.2` |
| `ruff` | `>=0.16.8` | `0.16.9` | `0.16.9` |

Rangos declarados: [../../../pyproject.toml](../../../pyproject.toml);
versiones resueltas: [../../../uv.lock](../../../uv.lock), que no son mínimos
soportados. Scheduling Redis/database y servidores o red necesitan sus
despliegues y drivers. Exec Unix y subprocess/embedded Windows son rutas
distintas; esta tarea no certifica tráfico real.

## Verificación y limitaciones

### Cobertura y ejecución

El inventario cubre cada fuente y plantilla, clases, métodos, propiedades,
funciones, campos de constructores dataclass, enums, constantes, exports,
firmas core y auxiliares públicos. Estado y helpers privados, librerías
importadas y typing `T` quedan explícitamente fuera de la API independiente.
Se contrastaron descripciones con los cuerpos invocados, no se asumieron
como autoridad automática.

TestingEngine y TestRunner nativos ejecutaron 1.247 pruebas con **1.247
correctas**, sin fallos o errores crudos ni omisiones, en aplicación aislada
iniciada. El primer run con TEMP largo anidado tuvo una aserción fallida:
el catálogo install trunca intencionadamente el path a 120 columnas y el test
esperaba la ruta completa. El caso aislado y la suite pasaron con TEMP externo
normal y raíz corta. Se conservó el resultado inicial; no se ocultó ni se
cambió fuente o test.

La integración offline de install usó wheels locales y venvs pip-free nuevos
temporales; no cambió el entorno existente. No se ejecutaron operaciones
reales clear/install/serve/migrate/queue-worker del checkout.

### Resultados de ejemplos

| Ejemplo | Sintaxis | Imports locales | Ejecución |
| --- | --- | --- | --- |
| 1 | Correcta | Correctos | Ejecutado correctamente. |
| 2 | Correcta | Correctos | Ejecutado correctamente. |
| 3 | Correcta | Correctos | Ejecutado correctamente. |
| 4 | Correcta | Correctos | Ejecutado correctamente. |
| 5 | Correcta | Correctos | Ejecutado correctamente. |
| 6 | Correcta | Correctos | Ejecutado correctamente. |
| 7 | Correcta | Correctos | Ejecutado correctamente. |

La referencia final contiene 644 declaraciones literales y 88 bloques de
campos/exports, cubriendo 140 fuentes Python, 58 comandos core y 24 plantillas.
Ambos manuales tienen 173 encabezados equivalentes y 739 bloques idénticos;
se comprobaron 274 enlaces relativos/anclas por manual y 22 del skill. Los
siete ejemplos de cada idioma pasaron sintaxis, imports locales y ejecución
independiente. El YAML contiene solo name y description, con nombre
orionis-console. Ruff acotado a orionis/console y tests/console pasó sin
fixes/caché; el editor no informa errores en los tres entregables.

La instantánea completa inicial incluye archivos ocultos, ignorados y no
versionados. El delta del estado versionado son estos dos manuales y el nuevo
SKILL.md bajo console/docs; se conservan índice Git, HEAD y cambios versionados
previos. La comparación completa también encontró contenido cambiado en tres
cachés bootstrap existentes (commands, config, routes) y storage/logs/stack.log,
además de solo mtime en la ruta vacía routes/ai.py. Su origen no quedó
establecido, por lo que se conservaron sin revertirlos ni eliminarlos. No puede
certificarse la integridad exclusiva del alcance. Scripts e informes quedan
fuera del repositorio; docs contiene exactamente estos tres archivos.

### Límites restantes

Las diferencias observadas incluyen conversión de errores de reactor,
cantidad de comandos, estado por instancia de serve, ausencia de
Schedule.store, retornos bool de triggers, referencias compartidas de tareas
y printing en toHtml. Las excepciones de dependencias o callbacks no forman
una lista exhaustiva. Flags de intérprete, terminal interactiva, buffering de
protocolo y servicios externos requieren su propio contexto de uso.

> ⚠️ No ejecutado en este entorno: tráfico real de Granian, Redis vivo o
> job stores remotos persistentes, workers queue/MCP desplegados, prompts
> de secretos interactivos, comandos destructivos del checkout, ejecución
> Linux/macOS/free-threaded y versiones distintas de Python 3.14.6.

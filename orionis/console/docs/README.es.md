# `orionis.console`

> Entorno de ejecución por línea de comandos de Orionis: descubre comandos, analiza sus argumentos, los ejecuta a través del contenedor, imprime su salida y los programa en el tiempo.

## Tabla de contenidos

- [Descripción funcional](#descripción-funcional)
  - [Dónde encaja en el framework](#dónde-encaja-en-el-framework)
  - [Flujo de un comando](#flujo-de-un-comando)
  - [Mapa de archivos](#mapa-de-archivos)
  - [Decisiones de diseño](#decisiones-de-diseño)
- [Referencia de API](#referencia-de-api)
  - [`KernelCLI`](#kernelcli)
  - [`Reactor`](#reactor)
  - [`Loader`](#loader)
  - [`BaseCommand`](#basecommand)
  - [`Argument`](#argument)
  - [`Console`](#console)
  - [`ProgressBar`](#progressbar)
  - [`Dumper`](#dumper)
  - [`VarDumper`](#vardumper)
  - [`Executor`](#executor)
  - [`HelpCommand`](#helpcommand)
  - [`HTTPRequestPrinter`](#httprequestprinter)
  - [`Command` (constructor fluido)](#command-constructor-fluido)
  - [`Schedule`](#schedule)
  - [`Task` (constructor fluido)](#task-constructor-fluido)
  - [`ScheduleStore`](#schedulestore)
  - [`BaseScheduler` y `BaseTaskListener`](#basescheduler-y-basetasklistener)
  - [Entidades](#entidades)
  - [Enumeraciones](#enumeraciones)
  - [Comandos integrados](#comandos-integrados)
  - [Proveedores de servicios](#proveedores-de-servicios)
- [Ejemplos de uso](#ejemplos-de-uso)
  - [Declarar un comando propio](#declarar-un-comando-propio)
  - [Declarar argumentos](#declarar-argumentos)
  - [Registrar un comando fluido](#registrar-un-comando-fluido)
  - [Invocar el reactor desde código](#invocar-el-reactor-desde-código)
  - [Reportar un comando que falla](#reportar-un-comando-que-falla)
  - [Escribir en la consola](#escribir-en-la-consola)
  - [Volcar valores durante la depuración](#volcar-valores-durante-la-depuración)
  - [Programar tareas](#programar-tareas)
- [Consideraciones de rendimiento y concurrencia](#consideraciones-de-rendimiento-y-concurrencia)
- [Notas de compatibilidad](#notas-de-compatibilidad)

## Descripción funcional

### Dónde encaja en el framework

`orionis.console` es la contraparte CLI de `orionis.http`: el mismo contenedor
`Application` sirve a los dos entornos, pero el lado de consola se entra por el
script `reactor` de la raíz del proyecto, que llama a
`Application.handleCommand(sys.argv)`.

El módulo cubre cuatro responsabilidades:

1. **Descubrimiento** — `Loader` reúne los comandos del framework, los comandos de
   la aplicación bajo `app/console/commands/` y los comandos fluidos declarados en
   `routes/console.py`.
2. **Ejecución** — `Reactor` analiza los argumentos con `argparse`, construye la
   clase del comando a través del contenedor, la invoca y convierte el resultado
   en un código de salida del proceso.
3. **Salida** — `Console`, `Executor`, `ProgressBar`, `VarDumper` y `Dumper`
   dibujan todo lo que imprime la CLI.
4. **Programación** — `Schedule` y el constructor fluido `Task` registran firmas
   de comandos en un `AsyncIOScheduler` de APScheduler.

Dependencias directas con otros módulos de Orionis: `orionis.container`
(proveedores, fachadas, resolución con ámbito), `orionis.foundation`
(`IApplication`, kernels y proveedores núcleo), `orionis.logging` (`ILogger`),
`orionis.failure` (`ICatch`, `KernelContext`), `orionis.cache` (`FileBasedCache`
para la caché de metadatos de comandos), `orionis.introspection` (descubrimiento
de módulos), `orionis.support` (`PerformanceCounter`, `MISSING`, `DateTime`,
fachadas), `orionis.database` (`IConnectionManager`, usado por el almacén de
trabajos del planificador) y `orionis.test` (`ITestingEngine`, usado por el
comando `test`).

### Flujo de un comando

```text
reactor (script)
  └─ Application.handleCommand(sys.argv)
       └─ KernelCLI.handle(args)            strips interpreter flags, routes "list"
            └─ Reactor.call(signature, args)
                 ├─ Application.beginScope()            scope["kernel"] = CONSOLE
                 ├─ PerformanceCounter.astart()
                 ├─ Loader.get(signature)               metadata → Command entity
                 ├─ Executor.running(signature)         "… RUNNING" line
                 ├─ ArgumentParser.parse_args(args)     MISSING values are dropped
                 ├─ Application.build(command.obj)      constructor injection
                 ├─ Application.call(instance, method)  method injection
                 ├─ Executor.done(signature, time)      "… DONE" line
                 └─ ILogger.info(...) / ICatch.exception(...) on failure
```

### Mapa de archivos

| Ruta | Contenido |
|---|---|
| `__init__.py` | Reexporta `Argument`, `Console`, `Dumper`, `ProgressBar`. |
| `kernel.py` | `KernelCLI`, el punto de entrada CLI registrado en `CORE_KERNELS`. |
| `reactor_provider.py` | `ReactorProvider`: vincula `IReactor` y fija la fachada `Reactor`. |
| `scheduler_provider.py` | `ScheduleProvider`: vincula `IScheduleStore` e `ISchedule`, fija la fachada `Schedule`. |
| `args/argument.py` | `Argument`, la definición declarativa de un argumento de `argparse`. |
| `base/` | `BaseCommand`, `BaseScheduler`, `BaseTaskListener` y sus contratos. |
| `commands/` | Los 17 comandos integrados (`make:*`, `migrate:*`, `schedule:*`, `serve`, `test`, `about`, `list`, `optimize*`). |
| `contracts/` | `IKernelCLI`, `ISchedule`, `IScheduleStore`. |
| `core/commands.py` | `CORE_COMMANDS`, la tupla inmutable de clases de comandos integrados. |
| `core/loader.py` | `Loader`: descubrimiento, caché de metadatos y construcción del `ArgumentParser`. |
| `core/reactor.py` | `Reactor`: despacho, medición de tiempo, registro y manejo de errores. |
| `debug/dumper.py` | `Dumper.dd()` / `Dumper.dump()`. |
| `dynamic/progress_bar.py` | `ProgressBar`. |
| `entities/` | Entidades de datos `Command`, `Task`, `SchedulerEvent`, `TaskEvent`. |
| `enums/` | `ArgumentAction`, `ScheduleStates`, `SchedulerEvent`, `TaskEvent`, `ANSIColors`. |
| `fluent/command.py` | `Command`, el constructor fluido que usa `Reactor.command()`. |
| `fluent/task.py` | `Task`, el constructor tipo cron que usa `Schedule.command()`. |
| `output/` | `Console`, `Executor`, `HelpCommand`, `HTTPRequestPrinter`, `VarDumper`. |
| `stubs/` | Plantillas `.stub` que usan los comandos `make:*`. |
| `tasks/schedule.py` | `Schedule` junto con la función de módulo `_executeScheduledCommand`. |
| `tasks/store.py` | `ScheduleStore`: construye los almacenes de trabajos Redis / SQLAlchemy. |

### Decisiones de diseño

- **Primero el contrato.** Cada pieza pública tiene una ABC en un paquete
  hermano `contracts/` (`IReactor`, `ILoader`, `IKernelCLI`, `ISchedule`,
  `IScheduleStore`, `IConsole`, `IBaseCommand`, …). Los proveedores vinculan la
  interfaz, así que quien la consume puede anotar el contrato y dejar que el
  contenedor inyecte la implementación.
- **Metadatos, no instancias.** `Loader` guarda diccionarios planos (ruta del
  módulo, nombre de clase, argumentos serializados) e importa la clase del
  comando solo cuando se ejecuta de verdad. Eso mantiene `list` barato y hace que
  la caché sea serializable.
- **`MISSING` en lugar de `None`.** `Argument.const` y `Argument.default` valen
  por defecto el centinela `orionis.support.types.sentinel.MISSING`, para poder
  distinguir un flag ausente de un `None` explícito; `Reactor` elimina esas
  claves antes de invocar el comando.
- **`Argument` inmutable y con slots.** `Argument` es un
  `@dataclass(kw_only=True, frozen=True, slots=True)` que se valida a sí mismo en
  `__post_init__`, de modo que una definición inválida falla al importar la
  clase, no al ejecutar el comando.
- **Los comandos heredan la consola.** `BaseCommand` extiende `Console`, por lo
  que `self.info(...)`, `self.table(...)` o `self.progressBar` están disponibles
  dentro de `handle()` sin cableado adicional.
- **Callable de módulo en el planificador.** Los trabajos de APScheduler se
  registran con la función de módulo `_executeScheduledCommand`, nunca con un
  método ligado, para que un almacén persistente pueda serializar el trabajo como
  una referencia `module:function`.
- **Comando de servidor de un solo proceso.** `ServerCommand` implementa
  `__new__` con un `RLock` a nivel de clase, así que `serve` es un singleton
  dentro del proceso.

## Referencia de API

### `KernelCLI`

`orionis.console.kernel.KernelCLI`, implementa `IKernelCLI`. Está registrado en
`orionis/foundation/core_kernels.py` bajo la clave `"KernelCLI"`.

```python
IGNORE_FLAGS: ClassVar[frozenset[str]] = frozenset({
    "reactor", "-c", "-m", "-", "-i", "-q", "-B", "-O", "-OO", "-v",
    "-vv", "-d", "-x", "-E", "-s", "-S", "-u", "-I", "-W",
})

_HELP_FLAGS: ClassVar[frozenset[str]] = frozenset({"help", "--help", "-h"})

__slots__ = ("__reactor",)

async def boot(self, application: IApplication) -> None: ...

async def handle(self, args: list[str] | None = None) -> int: ...
```

- `boot(application)` resuelve `IReactor` desde el contenedor y lo guarda. Debe
  ejecutarse antes que `handle()`; `Application.handleCommand` lo hace una sola
  vez y cachea el método `handle` ligado.
- `handle(args)` normaliza la lista de argumentos y despacha:
  - lanza `TypeError` con `"Arguments must be provided as a list."` cuando `args`
    no es ni `None` ni una `list`;
  - descarta el primer elemento cuando *contiene* la subcadena `"reactor"` (así
    también se elimina una ruta absoluta como `/usr/local/bin/reactor`);
  - elimina la serie inicial de elementos presentes en `IGNORE_FLAGS`;
  - llama a `reactor.call("list")` cuando no queda nada o cuando el primer
    elemento está en `_HELP_FLAGS`;
  - en cualquier otro caso devuelve `await reactor.call(args[0], args[1:])`.
- Efecto secundario: la lista recibida se modifica en el sitio (`del args[0]`,
  `del args[:i]`). El punto de entrada pasa `sys.argv`, que se consume a
  propósito.
- La clase declara `__slots__`, así que una instancia solo guarda la referencia
  al reactor y no arrastra diccionario de instancia.

### `Reactor`

`orionis.console.core.reactor.Reactor`, implementa `IReactor`. Se vincula como
singleton con el alias `"x-orionis-IReactor"`; se accede a él por la fachada
`orionis.support.facades.reactor.Reactor`.

```python
def __init__(
    self,
    app: IApplication,
    loader: Loader,
    executer: Executor,
    logger: ILogger,
    catch: ICatch,
    performance_counter: PerformanceCounter,
) -> None: ...

def command(
    self,
    signature: str,
    handler: list[type[Any] | str | None] | str,
) -> ICommand: ...

async def info(self) -> list[dict]: ...

async def call(self, signature: str, args: list[str] | None = None) -> int: ...
```

- `command(signature, handler)` registra un comando fluido y devuelve el
  constructor. Una clase suelta se normaliza a `[handler, "__call__"]`; una lista
  puede llevar el nombre del método como segundo elemento. Todos los argumentos
  del constructor los inyecta el contenedor.
- `info()` devuelve un diccionario por comando registrado con las claves
  `timestamps`, `signature`, `description`, `arguments` (el
  `argparse.ArgumentParser` o `None`), `object` y `method`, ordenados por firma.
  Las firmas envueltas en dobles guiones bajos se omiten. El resultado se memoiza
  durante la vida de la instancia.
- `call(signature, args)` devuelve el código de salida:
  - abre un ámbito del contenedor y fija `scope["kernel"] = KernelContext.CONSOLE`;
  - mide la ejecución con `PerformanceCounter` e imprime las líneas `RUNNING` /
    `DONE` a través de `Executor` cuando `command.timestamps` es verdadero y no
    aparece ni `-h` ni `--help`;
  - devuelve el valor producido por el comando cuando es `int`, y `0` en caso
    contrario;
  - captura toda `Exception`, la registra con `ILogger.error`, imprime la línea
    `FAIL`, antepone `[<Clase>.<método>]` al mensaje, la delega en
    `ICatch.exception` y devuelve `1`. Los fallos nunca se propagan a quien llama.
- El `SystemExit` que lanza `argparse` no se captura: un flag inválido imprime la
  ayuda del comando y termina el proceso con el código de argparse; `-h` imprime
  la ayuda y sale con `0`.

### `Loader`

`orionis.console.core.loader.Loader`, implementa `ILoader`. Lo construye el
contenedor como dependencia del constructor de `Reactor`.

```python
def __init__(self, app: IApplication) -> None: ...

async def get(self, signature: str) -> Command | None: ...

async def all(self) -> dict[str, Command]: ...

async def load(self) -> None: ...

def addFluentCommand(
    self,
    signature: str,
    handler: list[type[Any], str | None],
) -> ICommand: ...
```

- Orden de descubrimiento: `CORE_COMMANDS` → clases bajo
  `app/console/commands/` que heredan de `BaseCommand` → comandos fluidos
  importados desde los archivos de rutas de consola. Una fuente posterior
  sobrescribe a la anterior cuando la firma coincide.
- Caché de metadatos: cuando `IApplication.compiled` es verdadero, el loader
  escribe el diccionario de metadatos en un `FileBasedCache` llamado `commands`
  dentro de `IApplication.compiledPath`, invalidado por las rutas monitorizadas
  configuradas. Cuando es falso, el descubrimiento se repite en cada arranque.
- `get(signature)` importa y construye solo el comando solicitado; `all()`
  construye todos los comandos descubiertos.
- `addFluentCommand` lanza `ValueError` cuando `handler` no es una lista con al
  menos un elemento, y `TypeError` cuando el primer elemento no es una clase. El
  nombre del método vale `"__call__"` por defecto.
- Detalles de serialización: `Argument.type_` se guarda como
  `"<módulo>.<qualname>"` y se restaura importándolo; `MISSING` se guarda como la
  cadena `"__MISSING__"`; un metavar de tipo `tuple` se guarda como lista. Un
  tipo que ya no se puede importar se restaura como `None`.

### `BaseCommand`

`orionis.console.base.command.BaseCommand`, extiende `Console` e implementa
`IBaseCommand`. Se importa con `from orionis.console.base import BaseCommand`.

```python
timestamps: bool = True
signature: str
description: str
arguments: ClassVar[list[Argument]] = []

def __init__(self) -> None: ...

async def handle(self) -> None: ...

def getArgument(self, key: str, default: Any | None = None) -> Any | None: ...

def getArguments(self) -> dict[str, Any]: ...

def setArguments(self, args: dict[str, Any]) -> None: ...
```

- `signature` es obligatoria y la valida el loader: debe ser una cadena no vacía
  que cumpla `^[a-zA-Z][a-zA-Z0-9_:]*[a-zA-Z0-9]$|^[a-zA-Z]$`.
- `handle()` es el punto de entrada; las subclases pueden declarar parámetros
  adicionales, que resuelve el contenedor. La implementación heredada lanza
  `NotImplementedError`.
- `getArgument(key, default)` lanza `TypeError` cuando `key` no es una cadena y
  devuelve `default` cuando la clave no existe — incluidos los flags cuyo valor
  quedó en `MISSING` y que por eso el reactor eliminó.
- `getArguments()` devuelve una copia superficial; `setArguments()` mezcla el
  diccionario recibido con el interno y lanza `TypeError` cuando no es un dict.
- Todos los métodos de `Console` están disponibles en `self`.

### `Argument`

`orionis.console.args.argument.Argument`, un
`@dataclass(kw_only=True, frozen=True, slots=True)` que extiende `BaseEntity`.
Se importa con `from orionis.console import Argument`.

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

def addToParser(self, parser: argparse.ArgumentParser) -> None: ...
```

Validaciones realizadas en `__post_init__`:

| Condición | Excepción |
|---|---|
| `name_or_flags` vacío | `ValueError` |
| Un flag que no es cadena | `TypeError` |
| `-h` o `--help` entre los flags | `ValueError` |
| `action` que no es `str`, `ArgumentAction` ni `None` | `TypeError` |
| `nargs` que no es `int`, `str` ni `None` | `TypeError` |
| `nargs` de tipo cadena fuera de `{"?", "*", "+"}` | `ValueError` |
| `type_` no invocable | `TypeError` |
| `type_` combinado con `store_true`, `store_false`, `store_const` o `append_const` | `TypeError` |
| `choices` dado como cadena, o no iterable | `TypeError` |
| `required` que no es `bool` | `TypeError` |

`name_or_flags` se normaliza a `tuple[str, ...]`. `addToParser` reenvía los
campos informados a `parser.add_argument`, junto con todo lo que haya en `extra`.

### `Console`

`orionis.console.output.console.Console`, implementa `IConsole`. Es la clase base
de `BaseCommand` y `BaseTaskListener`, y también se puede instanciar
directamente. Se importa con `from orionis.console import Console`.

| Grupo | Métodos |
|---|---|
| Mensajes con banner (prefijo + marca de tiempo) | `success(message, *, timestamp=True)`, `info(...)`, `warning(...)`, `fail(...)`, `error(...)` |
| Texto plano con color | `textSuccess`, `textSuccessBold`, `textInfo`, `textInfoBold`, `textWarning`, `textWarningBold`, `textError`, `textErrorBold`, `textMuted`, `textMutedBold`, `textUnderline` |
| Disposición | `clear()`, `clearLine()`, `line()`, `newLine(count=1)`, `write(*values, sep=' ', end='\n', file=None, flush=False)`, `writeLine(message)` |
| Entrada | `ask(question)`, `confirm(question, *, default=False)`, `secret(question)`, `anticipate(question, options, default=None)`, `choice(question, choices, default_index=0)` |
| Salida enriquecida | `table(headers, rows)`, `exception(exception)`, `dump(*args, ...)` |
| Control del proceso | `exitSuccess(message=None)`, `exitError(message=None)` |
| Varios | `progressBar` (propiedad), `sleep(seconds)` (asíncrono) |

- `progressBar` devuelve una `ProgressBar()` **nueva** en cada acceso, construida
  con los valores por defecto `total=100, width=50`.
- `exitSuccess` / `exitError` llaman a `sys.exit(0)` / `sys.exit(1)` y recurren a
  `os._exit` con el mismo código si el `SystemExit` es absorbido.
- `exception(exception)` dibuja un `rich.traceback.Traceback`.
- `dump(...)` usa `VarDumper` con `show_types=True` por defecto, a diferencia de
  `Dumper.dump(...)`, cuyo valor por defecto es `False`.
- `sleep(seconds)` espera en `asyncio.sleep`; es la única corrutina de la clase.

### `ProgressBar`

`orionis.console.dynamic.progress_bar.ProgressBar`, implementa `IProgressBar`.
Se importa con `from orionis.console import ProgressBar`.

```python
def __init__(self, total: int = 100, width: int = 50) -> None: ...

def start(self) -> None: ...

def advance(self, increment: int = 1) -> None: ...

def finish(self) -> None: ...
```

La barra se dibuja con `\r` sobre una sola línea usando los caracteres de bloque
`█` y `░`, escribiendo directamente en `sys.stdout`. `finish()` completa la barra
y emite un salto de línea.

### `Dumper`

`orionis.console.debug.dumper.Dumper`, implementa `IDumper`; ambos miembros son
`@staticmethod`. Se importa con `from orionis.console import Dumper`.

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
) -> None: ...

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
) -> None: ...
```

Ambos arman una cadena `VarDumper` con las mismas opciones; la única diferencia
es `forceExit`: `dd` lo pone en `True` (el proceso se detiene tras imprimir) y
`dump` en `False`. Cuando se omiten `module_path` / `line_number`, la cabecera
muestra la ubicación dentro del propio `orionis.console.debug.dumper`.

### `VarDumper`

`orionis.console.output.var_dumper.VarDumper`, implementa `IVarDumper`. Objeto
fluido que hay detrás de `Dumper` y de `Console.dump`.

```python
def showTypes(self, *, show: bool = True) -> VarDumper: ...
def showIndex(self, *, show: bool = True) -> VarDumper: ...
def expandAll(self, *, expand: bool = True) -> VarDumper: ...
def maxDepth(self, depth: int | None) -> VarDumper: ...
def modulePath(self, path: str | None) -> VarDumper: ...
def lineNumber(self, number: int | None) -> VarDumper: ...
def forceExit(self, *, force: bool = True) -> VarDumper: ...
def redirectOutput(self, *, redirect: bool = True) -> VarDumper: ...
def values(self, *args: tuple | list) -> VarDumper: ...
def value(self, value: type[T]) -> VarDumper: ...
def print(self, *, insert_line: bool = False) -> None: ...
def toHtml(self, *, insert_line: bool = False) -> str: ...
```

`print()` escribe el panel de Rich; `toHtml()` devuelve ese mismo dibujo como una
cadena HTML en lugar de imprimirlo.

### `Executor`

`orionis.console.output.executor.Executor`, implementa `IExecutor`. Sin estado;
se inyecta en `Reactor` y lo reutilizan los comandos de migración.

```python
def running(self, program: str, time: str = "") -> None: ...
def done(self, program: str, time: str = "") -> None: ...
def fail(self, program: str, time: str = "") -> None: ...
```

Cada llamada imprime una línea con la forma
`<marca de tiempo> | <programa> ...... ~ <tiempo> <ESTADO>`, rellenada con
puntos.

### `HelpCommand`

`orionis.console.output.help_command.HelpCommand`, implementa `IHelpCommand`;
ambos miembros son `@staticmethod`.

```python
@staticmethod
def parseActions(actions: list[argparse.Action]) -> dict[str, Any]: ...

@staticmethod
def printActions(
    command_name: str,
    actions: list[argparse.Action],
    *,
    is_error: bool = False,
) -> None: ...
```

`Reactor` llama a `printActions` cuando `argparse` lanza `SystemExit`, de manera
que un flag incorrecto y `--help` comparten el mismo dibujo; `is_error` cambia el
estilo.

### `HTTPRequestPrinter`

`orionis.console.output.http_request.HTTPRequestPrinter`, implementa
`IHTTPRequestPrinter`. Lo usa el entorno HTTP, no el flujo de comandos.

```python
def setEnabled(self, *, enabled: bool) -> None: ...
async def start(self) -> None: ...
async def stop(self) -> None: ...
def startTimer(self) -> float | None: ...
def printRequest(self, adapter: TransportAdapter, response: Response) -> None: ...
```

`start()` lanza una corrutina trabajadora interna que vacía la cola de impresión,
así que el registro de peticiones nunca bloquea la ruta de la respuesta;
`stop()` la detiene.

### `Command` (constructor fluido)

`orionis.console.fluent.command.Command`, implementa `ICommand`. Lo devuelve
`Reactor.command(...)`; no está pensado para instanciarse a mano.

```python
def __init__(
    self,
    signature: str,
    concrete: Callable[..., Any],
    method: str = "handle",
) -> None: ...

def timestamp(self, *, enabled: bool = True) -> Self: ...
def description(self, desc: str) -> Self: ...
def arguments(self, args: list[Argument]) -> Self: ...
def get(self) -> tuple[str, CommandEntity]: ...
```

El constructor lanza `TypeError` cuando `concrete` no es invocable o `method` no
es una cadena, y `AttributeError` cuando `concrete` no tiene un atributo
invocable con ese nombre. Valores por defecto: marcas de tiempo activadas,
descripción `"No description provided."` y lista de argumentos vacía. `get()`
devuelve el par `(signature, Command)` que consume el loader.

### `Schedule`

`orionis.console.tasks.schedule.Schedule`, implementa `ISchedule`. Se vincula
como singleton a `ISchedule` y se accede a él por la fachada
`orionis.support.facades.schedule.Schedule`. Envuelve un `AsyncIOScheduler` de
APScheduler.

```python
def __init__(
    self,
    reactor: IReactor,
    exception_handler: ICatch,
    stores: IScheduleStore,
) -> None: ...

def command(
    self,
    signature: str,
    args: list[str] | None = None,
    purpose: str | None = None,
) -> ITask: ...

def on(self, event: SchedulerEvent, listener: Callable) -> Self: ...
async def info(self) -> list[dict]: ...
async def boot(self) -> None: ...
def state(self) -> str: ...
def isRunning(self) -> bool: ...
def isPaused(self) -> bool: ...
def isStopped(self) -> bool: ...
def pauseTask(self, signature: str) -> bool: ...
def resumeTask(self, signature: str) -> bool: ...
def removeTask(self, signature: str) -> bool: ...
def removeAllTasks(self) -> bool: ...
def pause(self) -> bool: ...
def resume(self) -> bool: ...
def shutdown(self, wait: int | None = None) -> None: ...
async def wait(self) -> None: ...
```

- `command(...)` y `on(...)` son **solo de tiempo de declaración**: ambos lanzan
  `RuntimeError` en cuanto el planificador sale del estado `STOPPED`. `command`
  lanza `TypeError` cuando la firma no es una cadena no vacía o cuando `args` no
  es una lista de cadenas.
- `info()` valida las tareas declaradas contra las firmas que conoce el reactor y
  lanza `ValueError` ante una desconocida. Cada entrada lleva `signature`,
  `args`, `kwargs`, `purpose`, `random_delay`, `coalesce`, `max_instances`,
  `misfire_grace_time`, `start_date`, `end_date` y `details`.
- `boot()` registra todos los trabajos **antes** de llamar a
  `AsyncIOScheduler.start()`, añade el almacén `memory` más el configurado,
  suscribe los oyentes de planificador y de tareas, silencia los loggers de
  APScheduler y pasa el estado a `RUNNING`. Los trabajos se añaden con
  `replace_existing` tomado de `scheduler.replace_existing` en la configuración.
- Los métodos de control de tareas lanzan `RuntimeError` cuando el planificador
  no ha arrancado (`"The Orionis task scheduler has not been started."`) o cuando
  la tarea no está en el estado esperado, y `ValueError` cuando el trabajo no
  existe.
- `shutdown(wait)` programa un apagado ordenado como tarea gestionada: espera
  `wait` segundos (por defecto `0.5`), aguarda las tareas de oyentes en vuelo,
  apaga el planificador en un executor y activa el evento interno. `wait` debe
  ser un `int` no negativo que no sea `bool`; en caso contrario se lanza
  `TypeError`. Pasar `None` conserva el valor actual.
- `wait()` bloquea hasta que ese evento de apagado se activa.
- El callable del trabajo es la corrutina de módulo
  `_executeScheduledCommand(signature, args)`, que despacha a través de la
  fachada `Reactor`.

### `Task` (constructor fluido)

`orionis.console.fluent.task.Task`, implementa `ITask`. Lo devuelve
`Schedule.command(...)`.

Los métodos de configuración devuelven `Self` para encadenar:

| Método | Efecto |
|---|---|
| `purpose(purpose)` | Nombre legible que reporta `schedule:list`. |
| `coalesce(*, coalesce=True)` | Fusiona en una sola las ejecuciones perdidas. |
| `misfireGraceTime(seconds=60)` | Segundos de tolerancia para una ejecución tardía. |
| `maxInstances(max_instances)` | Ejecuciones concurrentes permitidas para el trabajo. |
| `randomDelay(max_seconds=10)` | Jitter; parchea el trigger en el sitio si ya existe uno. |
| `startDate(year, month, day, hour=0, minute=0, second=0)` | Límite inferior de la ventana de programación. |
| `endDate(year, month, day, hour=0, minute=0, second=0)` | Límite superior de la ventana de programación. |
| `on(event, callback)` | Registra un callback para un `TaskEvent`. |
| `registerListener(listener)` | Registra todos los métodos `onTask*` de un `BaseTaskListener`. |

Los métodos de trigger devuelven `bool` y **reemplazan** cualquier trigger
configurado antes:

| Familia | Miembros |
|---|---|
| Una sola vez | `onceAt(year, month, day, hour=0, minute=0, second=0)` |
| Segundos | `everySeconds(seconds)`, `everyFiveSeconds()` … `everyFiftyFiveSeconds()` |
| Minutos | `everyMinutes(minutes)`, `everyMinuteAt(seconds)`, `everyMinutesAt(minutes, seconds)`, `everyFiveMinutes()` … `everyFiftyFiveMinutes()` y sus variantes `…At(seconds)` |
| Horas | `hourly()`, `hourlyAt(minute, second=0)`, `everyOddHours()`, `everyEvenHours()`, `everyHours(hours)`, `everyHoursAt(hours, minute, second=0)`, `everyTwoHours()` … `everyTwelveHours()` y sus variantes `…At(minute, second=0)` |
| Días | `daily()`, `dailyAt(hour, minute=0, second=0)`, `everyDays(days)`, `everyDaysAt(days, hour, minute=0, second=0)`, `everyTwoDays()` … `everySevenDays()` y sus variantes `…At(...)` |
| Días de la semana | `everyMondayAt(hour, minute=0, second=0)` … `everySundayAt(...)` |
| Semanas | `weekly()`, `everyWeeks(weeks)` |
| Genéricos | `every(weeks=0, days=0, hours=0, minutes=0, seconds=0)`, `cron(year=None, month=None, day=None, week=None, day_of_week=None, hour=None, minute=None, second=None)` |

Los valores fuera de rango lanzan `ValueError` con los mensajes
`"Interval value must be a positive integer."`, `"Minute must be between 0 and
59."`, `"Second must be between 0 and 59."` o `"Hour must be between 0 and
23."`.

```python
def entity(
    self,
    random_delay: int | None = 0,
    max_instances: int | None = 1,
    misfire_grace_time: int | None = 0,
    *,
    coalesce: bool | None = True,
) -> TaskEntity: ...
```

`entity(...)` materializa la entidad `Task` que consume `Schedule.boot()`. Los
valores configurados en la tarea ganan sobre los argumentos, que llevan los
valores por defecto globales de la sección de configuración `scheduler`.

### `ScheduleStore`

`orionis.console.tasks.store.ScheduleStore`, implementa `IScheduleStore`. Se
vincula como singleton a `IScheduleStore` para poder inyectarlo en `Schedule`.

```python
def __init__(self, app: IApplication, db_manager: IConnectionManager) -> None: ...

@property
def store(self) -> str: ...

@property
def config(self) -> ConfigScheduler: ...

def redis(self) -> RedisJobStore: ...

def database(self) -> SQLAlchemyJobStore: ...
```

El constructor materializa `Scheduler(**app.config("scheduler"))`. `store`
devuelve el nombre del driver configurado; `config` expone la entidad completa
(`jitter`, `max_instances`, `misfire_grace_time`, `coalesce`,
`replace_existing`, …). `redis()` y `database()` lanzan `RuntimeError` cuando la
sección `scheduler.stores.*` correspondiente nunca se configuró; `database()`
construye una URL de motor SQLAlchemy síncrona, así que debe estar instalado el
driver síncrono de la conexión elegida.

### `BaseScheduler` y `BaseTaskListener`

```python
class BaseScheduler(IBaseScheduler):
    async def tasks(self, schedule: ISchedule) -> None: ...
    async def onStarted(self, event: SchedulerEvent) -> None: ...
    async def onPaused(self, event: SchedulerEvent) -> None: ...
    async def onResumed(self, event: SchedulerEvent) -> None: ...
    async def onShutdown(self, event: SchedulerEvent) -> None: ...

class BaseTaskListener(Console, IBaseTaskListener):
    async def onTaskAdded(self, event: TaskEvent) -> None: ...
    async def onTaskRemoved(self, event: TaskEvent) -> None: ...
    async def onTaskExecuted(self, event: TaskEvent) -> None: ...
    async def onTaskError(self, event: TaskEvent) -> None: ...
    async def onTaskMissed(self, event: TaskEvent) -> None: ...
    async def onTaskSubmitted(self, event: TaskEvent) -> None: ...
    async def onTaskMaxInstances(self, event: TaskEvent) -> None: ...
```

`BaseScheduler` es la clase base de `app/console/scheduler.py`: `tasks()` es el
punto donde se declaran las tareas y los métodos `on*` son ganchos de ciclo de
vida. **No** extiende `Console`. `BaseTaskListener` sí, de modo que un oyente
puede imprimir directamente. Ambos pueden implementarse con métodos síncronos:
el despachador acepta las dos formas. Las dependencias del constructor de ambas
clases las inyecta el contenedor.

### Entidades

Todas extienden `BaseEntity` (`toDict()`, `getFields()`).

```python
@dataclass(kw_only=True)
class Command(BaseEntity):
    obj: type
    method: str = "handle"
    timestamps: bool = True
    signature: str
    description: str
    args: list[Argument] | argparse.ArgumentParser | None = None

@dataclass(kw_only=True)
class Task(BaseEntity):
    signature: str
    args: list[str] | None = field(default_factory=list)
    kwargs: dict | None = field(default_factory=dict)
    purpose: str | None = None
    random_delay: int | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    trigger: CronTrigger | DateTrigger | IntervalTrigger | None = None
    details: str | None = None
    max_instances: int | None = 1
    misfire_grace_time: int | None = None
    coalesce: bool | None = True
    listeners: list[Callable[..., None]] = field(default_factory=list)

@dataclass(kw_only=True)
class SchedulerEvent(BaseEntity):
    code: int
    description: str = field(default="")
    jobstore: str = field(default="memory")

@dataclass(kw_only=True)
class TaskEvent(BaseEntity):
    code: int
    description: str = field(default="")
    signature: str
    jobstore: str = field(default="memory")
    scheduled_run_times: Any | None = field(default=None)
    scheduled_run_time: Any | None = field(default=None)
    retval: Any | None = field(default=None)
    exception: Any | None = field(default=None)
    traceback: Any | None = field(default=None)
```

`Command.args` lleva la lista declarativa `list[Argument]` mientras el
constructor fluido define el comando, y el `argparse.ArgumentParser` que `Loader`
arma a partir de esa lista cuando el comando se materializa —que es la forma que
lee `Reactor`—. `SchedulerEvent.__post_init__` y `TaskEvent.__post_init__`
rellenan `description` a partir de `code`.

### Enumeraciones

| Enum | Miembros |
|---|---|
| `ArgumentAction(Enum)` | `STORE`, `STORE_CONST`, `STORE_TRUE`, `STORE_FALSE`, `APPEND`, `APPEND_CONST`, `COUNT`, `HELP`, `VERSION` |
| `ScheduleStates(Enum)` | `STOPPED`, `RUNNING`, `PAUSED` |
| `SchedulerEvent(IntEnum)` | `STARTED = 2**0`, `SHUTDOWN = 2**1`, `PAUSED = 2**2`, `RESUMED = 2**3` |
| `TaskEvent(IntEnum)` | `ADDED = 2**9`, `REMOVED = 2**10`, `MODIFIED = 2**11`, `EXECUTED = 2**12`, `ERROR = 2**13`, `MISSED = 2**14`, `SUBMITTED = 2**15`, `MAX_INSTANCES = 2**16` |
| `ANSIColors(Enum)` | 24 secuencias de escape que usa `Console` (`TEXT_INFO`, `BG_SUCCESS`, `TEXT_BOLD_ERROR`, …) |

Las enumeraciones de eventos son `IntEnum` con potencias de dos porque
APScheduler se suscribe con una máscara de bits; `orionis.console.enums` exporta
los flags y `orionis.console.entities` exporta las cargas útiles de los eventos
con los mismos nombres.

### Comandos integrados

`CORE_COMMANDS` (`orionis/console/core/commands.py`) es una tupla de 17 clases:

| Firma | Clase | Notas |
|---|---|---|
| `about` | `VersionCommand` | Panel con los metadatos del framework. |
| `list` | `HelpCommand` | Destino por defecto cuando no se indica comando. |
| `make:command` | `MakeCommand` | `name`, `--signature/-s`, `--description/-d`. |
| `make:provider` | `MakeProvider` | `name`, `--deferred`. |
| `make:task:listener` | `MakeTaskListener` | `name`. |
| `migrate` | `MigrateCommand` | `--database/-d`. |
| `migrate:fresh` | `MigrateFreshCommand` | Elimina y vuelve a ejecutar todo. |
| `migrate:refresh` | `MigrateRefreshCommand` | `--step/-s`. |
| `migrate:reset` | `MigrateResetCommand` | Revierte todas las migraciones. |
| `migrate:rollback` | `MigrateRollbackCommand` | `--step/-s`, por defecto el último lote. |
| `migrate:status` | `MigrateStatusCommand` | Tabla de estado. |
| `optimize` | `OptimizeCommand` | `compileall` con nivel de optimización 2. |
| `optimize:clear` | `OptimizeClearCommand` | Borra cachés, bytecode y artefactos de compilación. |
| `schedule:list` | `ScheduleListCommand` | Tabla de las tareas declaradas. |
| `schedule:work` | `ScheduleWorkCommand` | Ejecuta el planificador hasta que se interrumpe. |
| `serve` | `ServerCommand` | `--interface/-i`, `--port/-p`, `--log`, `--export`. |
| `test` | `TestCommand` | `--verbosity/-v`, `--fail-fast/-f`, `--start-dir/-s`, `--file-pattern`, `--method-pattern`, `--panel`, `--no-panel`. |

`MigrationCommand` (`commands/migrate/base_command.py`) es la base común de la
familia `migrate:*`: expone `targetConnection()`, `progressEvents()` y
`reportEmpty(message)`, y aporta el argumento `--database/-d`.

`test` devuelve un código de salida distinto de cero cuando algún resultado es
`FAILED` o `ERRORED`, de modo que puede cortar una tubería de CI.

### Proveedores de servicios

```python
class ReactorProvider(ServiceProvider):
    def register(self) -> None: ...
    async def boot(self) -> None: ...

class ScheduleProvider(ServiceProvider):
    def register(self) -> None: ...
    async def boot(self) -> None: ...
```

Ambos figuran en `CORE_PROVIDERS` y ninguno es diferido.

- `ReactorProvider.register()` vincula `IReactor → Reactor` como singleton con el
  alias `"x-orionis-IReactor"`, que es exactamente el accesor que devuelve la
  fachada `Reactor`. `boot()` fija esa fachada.
- `ScheduleProvider.register()` vincula `IScheduleStore → ScheduleStore`
  **antes** que `ISchedule → Schedule`, porque `Schedule` declara
  `IScheduleStore` como dependencia de su constructor y una interfaz solo se
  autorresuelve cuando tiene un binding explícito. `boot()` fija la fachada
  `Schedule`.

## Ejemplos de uso

### Declarar un comando propio

Cualquier subclase de `BaseCommand` colocada bajo `app/console/commands/` se
descubre automáticamente.

```python
# app/console/commands/greet_command.py
from orionis.console import Argument
from orionis.console.base import BaseCommand


class GreetCommand(BaseCommand):

    signature: str = "app:greet"

    description: str = "Greets a user from the console."

    arguments = [
        Argument(
            name_or_flags=["--name", "-n"],
            type_=str,
            required=False,
            help="Name to greet. Defaults to 'world'.",
        ),
        Argument(
            name_or_flags=["--shout"],
            action="store_true",
            help="Print the greeting in upper case.",
        ),
    ]

    async def handle(self) -> None:
        """
        Print the greeting requested through the command line.

        Returns
        -------
        None
            The greeting is written to the console.
        """
        name: str = self.getArgument("name", "world")
        message = f"Hello, {name}!"
        if self.getArgument("shout", default=False):
            message = message.upper()
        self.success(message)
```

```text
$ python reactor app:greet --name Ada

2026-09-01 19:12:50 | app:greet ............................................  RUNNING
 SUCCESS  2026-09-01 19:12:50 Hello, Ada!
2026-09-01 19:12:50 | app:greet .......................................  ~ 0.04s DONE

$ python reactor app:greet --shout

2026-09-01 19:12:56 | app:greet ............................................  RUNNING
 SUCCESS  2026-09-01 19:12:56 HELLO, WORLD!
2026-09-01 19:12:56 | app:greet .......................................  ~ 0.02s DONE
```

### Declarar argumentos

`Argument` es una descripción plana de un argumento de `argparse`, así que
también se puede usar fuera de un comando.

```python
import argparse

from orionis.console import Argument
from orionis.console.enums.actions import ArgumentAction

parser = argparse.ArgumentParser(prog="app:report", add_help=False)

Argument(
    name_or_flags="name",
    type_=str,
    required=True,
    help="Report owner.",
).addToParser(parser)

Argument(
    name_or_flags=["--format", "-f"],
    type_=str,
    choices=["csv", "json"],
    default="json",
    help="Output format.",
).addToParser(parser)

Argument(
    name_or_flags=["--verbose"],
    action=ArgumentAction.STORE_TRUE,
    help="Print every processed row.",
).addToParser(parser)

print(vars(parser.parse_args(["Ada", "-f", "csv", "--verbose"])))
print(vars(parser.parse_args(["Ada"])))

try:
    Argument(name_or_flags=["--flag"], action="store_true", type_=int)
except TypeError as exc:
    print(f"TypeError: {str(exc).split('.')[0]}.")

try:
    Argument(name_or_flags=["-h"])
except ValueError as exc:
    print(f"ValueError: {exc}")
```

```text
{'name': 'Ada', 'format': 'csv', 'verbose': True}
{'name': 'Ada', 'format': 'json', 'verbose': <MISSING>}
TypeError: 'type_' is not compatible with action='store_true'.
ValueError: Custom help flags '-h' and '--help' are not allowed.
```

La segunda línea muestra el centinela `MISSING` que deja un flag que no se pasó.
`Reactor` elimina esas claves antes de invocar el comando, y por eso
`getArgument("verbose", default=False)` devuelve `False` en vez del centinela.

### Registrar un comando fluido

Cualquier clase puede convertirse en comando sin heredar de `BaseCommand`.

```python
# routes/console.py
from app.services.welcome_service import WelcomeService
from orionis.console.args.argument import Argument
from orionis.support.facades.reactor import Reactor

Reactor.command("app:test", [WelcomeService, "greetUser"])\
       .timestamp()\
       .description("Command Test Defined as Route")\
       .arguments([
            Argument(
                name_or_flags=["--name", "-n"],
                type_=str,
                required=False,
            ),
       ])
```

```text
$ python reactor app:test --name Ada

2026-09-01 19:13:07 | app:test .............................................  RUNNING
Hello, Ada! Welcome to Orionis Framework.
2026-09-01 19:13:08 | app:test .........................................  ~ 1.3s DONE
```

### Invocar el reactor desde código

El reactor es un servicio normal del contenedor, así que se puede resolver y
manejar desde cualquier script.

```python
import asyncio

from bootstrap.app import app
from orionis.console.core.contracts.reactor import IReactor
from orionis.support.facades.reactor import Reactor


async def main() -> None:
    await Reactor.pin()
    reactor: IReactor = await app.make(IReactor)

    signatures = [command["signature"] for command in await reactor.info()]
    print(len(signatures), "commands")
    print(signatures)


asyncio.run(main())
```

```text
19 commands
['about', 'app:inspire', 'app:test', 'list', 'make:command', 'make:provider', 'make:task:listener', 'migrate', 'migrate:fresh', 'migrate:refresh', 'migrate:reset', 'migrate:rollback', 'migrate:status', 'optimize', 'optimize:clear', 'schedule:list', 'schedule:work', 'serve', 'test']
```

Las 19 firmas son los 17 comandos integrados más los dos que declara este
proyecto (`app:inspire` como clase, `app:test` como ruta fluida).

`await Reactor.pin()` hace falta en un script suelto: los proveedores eager solo
arrancan bajo el entorno CLI o HTTP, así que la fachada aún no está fijada y
`routes/console.py` —que se importa durante el descubrimiento— fallaría con
`AttributeError: '_FacadeDispatch' object has no attribute 'timestamp'`. El
error solo aparece cuando la caché de metadatos de comandos está fría, porque
una caché caliente ni siquiera importa los archivos de rutas.

### Reportar un comando que falla

`Reactor.call` nunca deja escapar una excepción: se la entrega a `ICatch`, que
imprime el traceback, y devuelve `1`.

```python
import asyncio

from bootstrap.app import app
from orionis.console.core.contracts.reactor import IReactor
from orionis.support.facades.reactor import Reactor


async def main() -> None:
    await Reactor.pin()
    reactor: IReactor = await app.make(IReactor)

    exit_code = await reactor.call("does:not:exist")
    print("missing command exit code:", exit_code)


asyncio.run(main())
```

Final de la salida; el traceback de Rich que dibuja `ICatch` se imprime encima
de estas dos líneas y aquí se omite porque contiene rutas absolutas:

```text
ValueError: Command 'does:not:exist' not found.
missing command exit code: 1
```

### Escribir en la consola

`Console` se puede instanciar directamente; dentro de un comando esos mismos
métodos están disponibles en `self`.

```python
from orionis.console import Console

console = Console()
console.textInfoBold("Deploying release 2.7.0")
console.textMuted("target: production")
console.textSuccess("done")
console.line()

console.table(
    ["Service", "Status"],
    [["api", "running"], ["worker", "stopped"]],
)
```

```text
Deploying release 2.7.0
target: production
done

┌─────────┬─────────┐
│ Service │ Status  │
├─────────┼─────────┤
│ api     │ running │
│ worker  │ stopped │
└─────────┴─────────┘
```

### Volcar valores durante la depuración

```python
from orionis.console import Dumper

Dumper.dump({"user": "ada", "roles": ["admin", "dev"]}, show_types=True)
```

```text
🐞 Module(orionis.console.debug.dumper) #111
╭─ dict ──────────────────────────────────────────────────────────╮
│                                                                 │
│ {                                                               │
│ │ 'user': 'ada',                                                │
│ │ 'roles': [                                                    │
│ │ │ 'admin',                                                    │
│ │ │ 'dev'                                                       │
│ │ ]                                                             │
│ }                                                               │
╰─────────────────────────────────────────────────────────────────╯
```

Cambia `dump` por `dd` para detener el proceso justo después de imprimir. El
panel lo dibuja Rich, así que su ancho sigue al del terminal.

### Programar tareas

Las tareas de la aplicación se declaran en `app/console/scheduler.py`, dentro del
gancho `tasks` de una subclase de `BaseScheduler`:

```python
# app/console/scheduler.py
from orionis.console.base import BaseScheduler
from orionis.console.contracts import ISchedule


class Scheduler(BaseScheduler):

    def tasks(self, schedule: ISchedule) -> None:
        """
        Declare the scheduled commands of the application.

        Parameters
        ----------
        schedule : ISchedule
            Scheduler injected by the framework.

        Returns
        -------
        None
            Tasks are registered as a side effect.
        """
        schedule.command("app:inspire", purpose="Daily quote").dailyAt(7, 30)
        schedule.command("app:test", ["--name", "Ada"]).everyFiveSeconds()
```

La misma API funciona desde un script, lo que resulta útil para inspeccionar qué
se registraría antes de ejecutar `schedule:work`:

```python
import asyncio

from bootstrap.app import app
from orionis.console.contracts import ISchedule
from orionis.support.facades.reactor import Reactor


async def main() -> None:
    await Reactor.pin()
    schedule: ISchedule = await app.make(ISchedule)

    schedule.command("app:inspire", purpose="Daily quote").dailyAt(7, 30)
    schedule.command("app:test", ["--name", "Ada"]).everyFiveSeconds()

    print("state:", schedule.state())
    for task in await schedule.info():
        print(task)

    try:
        schedule.command("app:missing").hourly()
        await schedule.info()
    except ValueError as exc:
        print(f"ValueError: {exc}")


asyncio.run(main())
```

```text
state: STOPPED
{'signature': 'app:inspire', 'args': [], 'kwargs': {}, 'purpose': 'Daily quote', 'random_delay': 0, 'coalesce': True, 'max_instances': 1, 'misfire_grace_time': 30, 'start_date': None, 'end_date': None, 'details': 'Every day at 07:30:00'}
{'signature': 'app:test', 'args': ['--name', 'Ada'], 'kwargs': {}, 'purpose': None, 'random_delay': 0, 'coalesce': True, 'max_instances': 1, 'misfire_grace_time': 30, 'start_date': None, 'end_date': None, 'details': 'Every 5 seconds'}
ValueError: Task signature 'app:missing' is not available in the reactor.
```

`random_delay`, `coalesce`, `max_instances` y `misfire_grace_time` vienen de la
sección de configuración `scheduler` salvo que la tarea los sobrescriba.

## Consideraciones de rendimiento y concurrencia

- **Todo es `asyncio`.** `handle()` puede declararse `async def` o `def`; el
  contenedor espera el resultado cuando es una corrutina. `Reactor.call` corre
  dentro del bucle que crea `Loop.run(...)` en el script `reactor`.
- **Importaciones perezosas.** `Loader` guarda solo metadatos e importa el módulo
  de un comando la primera vez que se ejecuta, cacheando el módulo importado en
  un diccionario. Un proceso que ejecuta un comando nunca importa los otros
  dieciséis.
- **Caché de metadatos.** Con `compiled=True` el resultado del descubrimiento se
  escribe en `storage/framework/bootstrap` (una entrada de `FileBasedCache`
  llamada `commands`). La caché se invalida por las rutas monitorizadas
  configuradas en la aplicación; los cambios dentro de `orionis/` no se
  monitorizan, así que editar el framework obliga a borrar esa carpeta (o a
  ejecutar `optimize:clear`).
- **Listados memoizados.** `Reactor.info()` cachea su resultado por instancia y
  `Schedule` cachea el conjunto de firmas disponibles tras la primera consulta.
- **Resolución con ámbito.** Cada `Reactor.call` abre su propio ámbito del
  contenedor; los servicios con ámbito no se filtran entre dos comandos
  ejecutados en el mismo proceso.
- **Concurrencia del planificador.** `AsyncIOScheduler` ejecuta los trabajos en
  el mismo bucle de eventos. `max_instances` (por defecto `1`) acota las
  ejecuciones concurrentes de una firma y `coalesce` fusiona las perdidas. Los
  callbacks de los oyentes se envuelven en objetos `asyncio.Task` gestionados,
  registrados en un conjunto y esperados durante `shutdown()`;
  `Schedule.__gracefulShutdown` ejecuta el apagado bloqueante de APScheduler en
  un executor para no dejar el bucle sin respuesta.
- **Sin locks en la ruta de comandos.** Ni `Loader` ni `Reactor` declaran ninguna
  primitiva de sincronización: los dos asumen un comando por proceso, que es como
  los usa el punto de entrada CLI. El único lock del módulo es el `RLock` de
  clase que protege `ServerCommand.__new__`.
- **Escrituras directas en stdout.** `ProgressBar` cachea `sys.stdout.write` /
  `sys.stdout.flush` y repinta una sola línea con `\r`; mezclarlo con otra salida
  en la misma línea estropea el dibujo.
- **Logging de APScheduler.** `Schedule.boot()` desactiva los loggers
  `apscheduler`, `apscheduler.executors` y `apscheduler.scheduler`, de modo que
  sus registros nunca llegan a los canales de logging de la aplicación.

## Notas de compatibilidad

- Python `>= 3.14` (`requires-python` en `pyproject.toml`). El módulo se apoya en
  las uniones de PEP 604, `typing.Self` y las anotaciones diferidas de PEP 649.
- Dependencias base ya instaladas con el framework: `apscheduler~=3.11`
  (planificador y almacenes de trabajos), `rich~=15.0` (tablas, paneles,
  tracebacks), `granian[dotenv,pname,reload,uvloop,winloop]~=2.7` (lo usa
  `serve`), `sqlalchemy[asyncio]~=2.0` (almacén de trabajos en base de datos). No
  hace falta instalar nada más para usar este módulo.
- `serve` se comporta distinto según la plataforma: en Unix reemplaza la imagen
  del proceso con `execvpe`, y en Windows lanza un subproceso o sirve dentro del
  propio proceso.
- El almacén `redis` necesita además un servidor Redis alcanzable y la sección
  `scheduler.stores.redis`; el almacén `database` necesita el driver
  **síncrono** de la conexión elegida, porque APScheduler crea su motor de
  inmediato.
- Añadir o quitar un comando o proveedor del núcleo no invalida la caché
  compilada de arranque. Borra `storage/framework/bootstrap` después de cambiar
  cualquier cosa bajo `orionis/`.
- Los colores de la consola se emiten como secuencias de escape ANSI crudas
  tomadas de `ANSIColors`; un terminal sin soporte ANSI muestra los códigos tal
  cual.

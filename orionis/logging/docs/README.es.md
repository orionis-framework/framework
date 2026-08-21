# orionis.logging

> Registro de la aplicación: un único logger de la biblioteca estándar gobernado por canales con nombre, con rotación de archivos por tiempo y por tamaño.

## Tabla de contenidos

- [Descripción funcional](#descripción-funcional)
  - [Dónde encaja en el framework](#dónde-encaja-en-el-framework)
  - [Cadena de resolución](#cadena-de-resolución)
  - [Mapa de archivos](#mapa-de-archivos)
  - [Decisiones de diseño](#decisiones-de-diseño)
- [Referencia de API](#referencia-de-api)
  - [Fachada `Log`](#fachada-log)
  - [`ILogger`](#ilogger)
  - [`Logger`](#logger)
  - [`SuffixResolver`](#suffixresolver)
  - [Resolvedores de sufijo](#resolvedores-de-sufijo)
  - [`AdvancedRotatingFileHandler`](#advancedrotatingfilehandler)
  - [`RotatingHandlerFactory`](#rotatinghandlerfactory)
  - [`LoggerProvider`](#loggerprovider)
  - [Entidades de configuración](#entidades-de-configuración)
- [Ejemplos de uso](#ejemplos-de-uso)
  - [1. Registrar desde un controlador](#1-registrar-desde-un-controlador)
  - [2. Resolver el servicio con el contenedor](#2-resolver-el-servicio-con-el-contenedor)
  - [3. `Logger` autónomo sin el contenedor](#3-logger-autónomo-sin-el-contenedor)
  - [4. Cambiar de canal y manejar errores](#4-cambiar-de-canal-y-manejar-errores)
  - [5. `SuffixResolver` propio](#5-suffixresolver-propio)
  - [6. Construir un handler con la fábrica](#6-construir-un-handler-con-la-fábrica)
- [Rendimiento y concurrencia](#rendimiento-y-concurrencia)
- [Notas de compatibilidad](#notas-de-compatibilidad)

## Descripción funcional

`orionis.logging` escribe las líneas de registro de la aplicación en archivos.
Envuelve un único `logging.Logger` de la biblioteca estándar llamado
`__orionis__` y lo configura a partir de la sección `logging` de la
configuración de la aplicación, que declara **canales** (`stack`, `hourly`,
`daily`, `weekly`, `monthly`, `chunked`). Solo hay un canal conectado a la vez;
`switchChannel()` lo intercambia en tiempo de ejecución.

La rotación no se delega en `logging.handlers`: el módulo trae su propio
`AdvancedRotatingFileHandler`, parametrizado por una estrategia `SuffixResolver`
que decide el sufijo del nombre de archivo (`daily_2026-08-21.log`,
`hourly_2026-08-21_14.log`, …) y que, para el canal `chunked`, produce un sufijo
único en cada rotación, de modo que la rotación pasa a estar gobernada por el
tamaño del archivo en lugar del tiempo.

### Dónde encaja en el framework

| Pieza | Valor |
|---|---|
| Contrato | `orionis.logging.contracts.logger.ILogger` |
| Implementación | `orionis.logging.logger.Logger` |
| Binding del contenedor | `singleton(ILogger, Logger, alias="x-orionis-ILogger")` |
| Provider | `orionis.logging.provider.LoggerProvider` (listado en `CORE_PROVIDERS`, eager — no diferido) |
| Fachada | `orionis.support.facades.logger.Log` (accessor `"x-orionis-ILogger"`) |
| Configuración | Entidades de `orionis.foundation.config.logging`, publicadas por `config/logging.py` |

El provider registra el binding en `register()` y fija (pin) la fachada en
`boot()`. Los providers eager los arranca `Application.__onStartup()`, es decir,
cuando arranca el runtime HTTP o CLI. Antes de ese momento la fachada **no**
está fijada y cualquier acceso a atributo devuelve un `_FacadeDispatch` que hay
que esperar (`await Log.getAvailableChannels()`); tras el pin, las llamadas son
directas (`Log.info("...")`, sin `await`). El código del framework que corre
durante el propio arranque —o los scripts sueltos— deben inyectar `ILogger` o
llamar explícitamente a `await Log.pin()`.

Otros módulos del framework consumen el servicio directamente: el `Reactor` de
consola reporta los fallos de comandos a través de `ILogger`, y el planificador
avisa mediante la fachada `Log` cuando se sobrescribe un listener de una tarea.

### Cadena de resolución

```text
Log (fachada) ─┐
               ├─► ILogger ──► Logger ──► logging.Logger("__orionis__")
DI: ILogger   ─┘                 │
                                 ├─ canal "stack"    ──► logging.FileHandler
                                 └─ resto de canales ──► RotatingHandlerFactory
                                                              │
                                                              ├─ HourlySuffixResolver
                                                              ├─ DailySuffixResolver   ─┐
                                                              ├─ WeeklySuffixResolver   ├─► AdvancedRotatingFileHandler
                                                              ├─ MonthlySuffixResolver ─┘
                                                              └─ ChunkedSuffixResolver
```

La creación del handler es **perezosa**: `Logger.__init__` solo toma una
instantánea de `app.config("logging")`. El logger estándar y su handler se
construyen en la primera llamada a
`info()`/`error()`/`warning()`/`debug()`/`critical()`/`getLogger()`/`switchChannel()`,
bajo un `threading.Lock` con doble comprobación. Hasta entonces
`getActiveChannels()` devuelve `[]`.

### Mapa de archivos

| Archivo | Contenido |
|---|---|
| `__init__.py` | Reexporta `Logger` (`__all__ = ["Logger"]`) |
| `logger.py` | `Logger`, el único servicio público del módulo |
| `provider.py` | `LoggerProvider` (binding + pin de la fachada) |
| `contracts/logger.py` | `ILogger` (ABC) |
| `contracts/suffix_resolver.py` | `SuffixResolver` (ABC, `__slots__ = ()`) |
| `handlers/advanced_rotating_file_handler.py` | `AdvancedRotatingFileHandler` |
| `handlers/rotating_handler_factory.py` | `RotatingHandlerFactory` + los seis constructores privados `_create_*` |
| `handlers/hourly_suffix_resolver.py` | `HourlySuffixResolver` |
| `handlers/daily_suffix_resolver.py` | `DailySuffixResolver` |
| `handlers/weekly_suffix_resolver.py` | `WeeklySuffixResolver` |
| `handlers/monthly_suffix_resolver.py` | `MonthlySuffixResolver` |
| `handlers/chunked_suffix_resolver.py` | `ChunkedSuffixResolver` |
| `handlers/__init__.py` | Vacío (los handlers se importan por ruta completa) |

El módulo **no define excepciones propias**: los fallos se reportan como
`RuntimeError`, como valor booleano de retorno (`switchChannel`) o se ignoran
(rutas de limpieza y compresión).

### Decisiones de diseño

- **Patrón Strategy para la rotación.** `AdvancedRotatingFileHandler` sabe
  escribir, rotar, comprimir y purgar; *cuándo* rotar se delega en un
  `SuffixResolver`. Añadir una política de rotación implica escribir una clase,
  no un handler.
- **Un solo canal activo.** La caché de handlers guarda como máximo una entrada
  (o la clave `"fallback"`), así que `getActiveChannel()` tiene sentido y
  cambiar de canal es un reemplazo completo, no una suma.
- **Caché de formatters a nivel de clase.** `Logger._formatter_cache` lo
  comparten todas las instancias del proceso y se indexa por `format|datefmt`,
  de modo que inicializaciones repetidas reutilizan el mismo
  `logging.Formatter`.
- **`name` como `ClassVar`.** `Logger.name` es un atributo de clase plano que
  eclipsa, vía MRO, la propiedad abstracta declarada por `ILogger`, evitando la
  llamada al descriptor de propiedad en cada acceso.
- **`__slots__` en los resolvedores.** Los cinco resolvedores y el ABC
  `SuffixResolver` declaran `__slots__`, así que sus instancias no llevan
  `__dict__`. `Logger` y `AdvancedRotatingFileHandler` no declaran `__slots__`.
- **Sin `from __future__ import annotations` en `logger.py`.** La clase la
  construye el contenedor DI, que resuelve las dependencias del constructor por
  reflexión; las anotaciones como cadena romperían esa resolución. El resto de
  archivos del módulo sí usa el future import.

## Referencia de API

### Fachada `Log`

`orionis.support.facades.logger.Log`

```python
class Log(Facade):
    @classmethod
    def getFacadeAccessor(cls) -> str: ...
```

Devuelve la cadena `"x-orionis-ILogger"`, el alias con el que `LoggerProvider`
registra el servicio. La fachada no declara ningún método de registro propio:
todos los métodos de `ILogger` los expone dinámicamente `FacadeMeta`. Existe un
stub paralelo `logger.pyi` solo para el autocompletado del editor, que nunca se
ejecuta.

El estado importa:

| Estado de la fachada | Comportamiento |
|---|---|
| Sin pin (antes del arranque del runtime) | `Log.loquesea` devuelve un `_FacadeDispatch`; hay que esperarlo: `await Log.getAvailableChannels()` |
| Con pin (`LoggerProvider.boot()` o `await Log.pin()` explícito) | Paso directo: `Log.info("...")`, `Log.getActiveChannel()` |

### `ILogger`

`orionis.logging.contracts.logger.ILogger` — `abc.ABC`. **No** declara
`__slots__ = ()`, así que las implementaciones conservan `__dict__`.

| Miembro | Firma |
|---|---|
| `name` | `@property def name(self) -> str` |
| `info` | `def info(self, message: str) -> None` |
| `error` | `def error(self, message: str) -> None` |
| `warning` | `def warning(self, message: str) -> None` |
| `debug` | `def debug(self, message: str) -> None` |
| `critical` | `def critical(self, message: str) -> None` |
| `getLogger` | `def getLogger(self) -> logging.Logger` |
| `reloadConfiguration` | `def reloadConfiguration(self) -> None` |
| `switchChannel` | `def switchChannel(self, channel_name: str) -> bool` |
| `close` | `def close(self) -> None` |
| `getActiveChannels` | `def getActiveChannels(self) -> list[str]` |
| `getActiveChannel` | `def getActiveChannel(self) -> str \| None` |
| `getAvailableChannels` | `def getAvailableChannels(self) -> list[str]` |

Todos los métodos abstractos tienen el cuerpo vacío: el contrato no se puede
invocar mediante `super()`.

### `Logger`

`orionis.logging.logger.Logger(ILogger)`

```python
def __init__(self, app: IApplication) -> None: ...
```

**Parámetros**

- `app` (`IApplication`) — instancia de la aplicación. Solo se usan dos puntos
  de enganche: `app.config("logging")` (se lee una vez en el constructor, y de
  nuevo en `reloadConfiguration()`) y `app.path("root")` (se lee al construir un
  handler).

**Efectos secundarios del constructor:** ninguno sobre el sistema de archivos.
Guarda la instantánea de configuración e inicializa el estado interno; no crea
ningún directorio ni abre ningún archivo.

**Atributos de clase**

| Atributo | Valor |
|---|---|
| `name` | `ClassVar[str] = "__orionis__"` |
| `_formatter_cache` | `dict[str, logging.Formatter]`, a nivel de clase, indexado por `f"{log_format}\|{date_format}"` |

**Ajustes fijos, asignados en `__init__` y no configurables**

| Ajuste | Valor |
|---|---|
| Formato del mensaje | `"%(asctime)s [%(levelname)s]: %(message)s"` |
| Formato de fecha | `"%Y-%m-%d %H:%M:%S"` |
| Nombre del logger estándar | `"__orionis__"` |
| Nivel del logger | `logging.DEBUG` |

El nivel del logger es `DEBUG` y `propagate` se fija en `False`; el filtrado
efectivo lo hace el nivel del **handler**, que proviene de la configuración del
canal.

**Métodos**

| Método | Devuelve | Comportamiento |
|---|---|---|
| `info(message: str)` | `None` | Garantiza la inicialización y llama a `logging.Logger.info(message)` |
| `error(message: str)` | `None` | Igual, nivel `error` |
| `warning(message: str)` | `None` | Igual, nivel `warning` |
| `debug(message: str)` | `None` | Igual, nivel `debug` |
| `critical(message: str)` | `None` | Igual, nivel `critical` |
| `getLogger()` | `logging.Logger` | Garantiza la inicialización y devuelve el logger estándar subyacente |
| `reloadConfiguration()` | `None` | Cierra handlers, limpia cachés, relee `app.config("logging")`, reinicializa y registra `"Logger configuration reloaded successfully"` |
| `switchChannel(channel_name: str)` | `bool` | Reemplaza el handler activo por el que declara `channel_name` |
| `close()` | `None` | Cierra y elimina todos los handlers, limpia la caché y suelta la referencia al logger |
| `getActiveChannels()` | `list[str]` | Claves presentes en la caché de handlers |
| `getActiveChannel()` | `str \| None` | Primera clave de la caché, o `None` |
| `getAvailableChannels()` | `list[str]` | Claves de `channels` en la instantánea de configuración de la instancia |
| `__del__()` | `None` | Llama a `close()` suprimiendo cualquier excepción |

**Excepciones**

- `RuntimeError` — desde `getLogger()` y desde cualquier método de registro
  cuando la inicialización falla; la excepción original queda encadenada
  (`"Failed to initialize logger: …"`). `reloadConfiguration()` lanza
  `RuntimeError("Failed to reload logger configuration: …")` ante cualquier
  fallo.
- `switchChannel()` nunca lanza: devuelve `False` para un canal desconocido,
  para un canal que la fábrica no puede construir, y cuando captura `OSError`,
  `RuntimeError` o `ValueError`.
- `close()` suprime `OSError`, `RuntimeError` y `ValueError`.

**Algoritmo de inicialización** (privado `__initializeLogger`)

1. `logging.getLogger("__orionis__")`; si ya tiene handlers, se limpian.
2. `setLevel(logging.DEBUG)`, `propagate = False`.
3. Lee `default` y `channels` de la instantánea, más `app.path("root")`.
4. Si `default` está presente en `channels`, la configuración se normaliza y:
   - canal `"stack"` → se crea directamente un
     `logging.FileHandler(f"{root}/{path}", encoding="utf-8")` (el directorio
     padre se crea con `mkdir(parents=True, exist_ok=True)`); `path` toma por
     defecto `storage/logs/stack.log`;
   - cualquier otro canal → `RotatingHandlerFactory.createHandler(...)`.
   El handler recibe el formatter cacheado y
   `setLevel(channel_config.get("level", logging.INFO))`, y se guarda en caché
   bajo el nombre del canal.
5. Si `default` **no** está en `channels`, se crea un `logging.FileHandler`
   de respaldo en `f"{root}/storage/logs/default.log"` y se cachea bajo la clave
   `"fallback"`. A ese handler no se le aplica ningún nivel, así que queda en
   `NOTSET` y manda el nivel `DEBUG` del logger.

**Normalización de nivel** (privado `__normalizeChannelConfig`) copia el dict
del canal y reescribe `level`:

| Entrada | Resultado |
|---|---|
| Enum `Level` (o cualquier objeto con `.value`) | `level.value` |
| `str` | `getattr(logging, value.upper(), logging.INFO)` — sin distinguir mayúsculas; los nombres desconocidos caen a `INFO` |
| `None` | `logging.INFO` |
| `int` | se deja tal cual |

**Detalles de `switchChannel`.** El nombre del canal se comprueba contra la
configuración *antes* de inicializar nada, así que un nombre inválido nunca
fuerza la inicialización. La inicialización ocurre después y **fuera** del lock
(`__init_lock` es un `threading.Lock` no reentrante); a continuación se cierran
y eliminan los handlers actuales, se limpia la caché y se construye el nuevo
handler mediante la fábrica — también para `"stack"`, que por tanto acaba siendo
el `FileHandler(delay=True)` de la fábrica en lugar del handler abierto de forma
anticipada durante la inicialización. Si tiene éxito se escribe la línea
informativa `"Successfully switched to channel: <nombre>"` a través del nuevo
handler.

### `SuffixResolver`

`orionis.logging.contracts.suffix_resolver.SuffixResolver` — `abc.ABC` con
`__slots__ = ()`.

```python
def getSuffix(self, dt: datetime | None = None) -> str: ...
def getNextRotationTime(self, current_time: datetime) -> datetime: ...
```

`getSuffix` devuelve la cadena que sustituye al marcador `{suffix}` de una
plantilla de ruta; `None` significa «usa la hora actual».
`getNextRotationTime` forma parte del contrato y lo implementan los cinco
resolvedores, pero `AdvancedRotatingFileHandler` no lo llama: la rotación se
decide comparando sufijos y con `max_bytes`.

### Resolvedores de sufijo

Los cinco viven en `orionis.logging.handlers`, implementan `SuffixResolver`,
declaran `__slots__` y capturan `self.tz = DateTime.getZoneInfo()` en su
constructor — es decir, la zona horaria de la aplicación configurada en ese
momento (`config app.timezone`, cargada por `Application.create()` antes de que
arranquen los providers).

| Clase | Constructor | Formato de `getSuffix` | Ejemplo |
|---|---|---|---|
| `HourlySuffixResolver` | `()` | `%Y-%m-%d_%H` | `2026-08-21_14` |
| `DailySuffixResolver` | `(at_time: time \| None = None)` | `%Y-%m-%d` | `2026-08-21` |
| `WeeklySuffixResolver` | `(at_time: time \| None = None)` | `{año_iso}-week{semana_iso:02d}` | `2026-week34` |
| `MonthlySuffixResolver` | `(at_time: time \| None = None)` | `%Y-%m` | `2026-08` |
| `ChunkedSuffixResolver` | `()` | `%Y%m%d_%H%M%S_{counter:04d}` | `20260821_143705_0001` |

`at_time` vale `time(0, 0, 0)` (medianoche) por defecto y solo afecta a
`getNextRotationTime`, nunca al sufijo.

`getNextRotationTime` por clase, evaluado para `2026-08-21 14:37:05+00:00`:

| Clase | Regla | Resultado |
|---|---|---|
| `HourlySuffixResolver` | Trunca a la hora (reemplazando `tzinfo` por la zona del resolvedor) y suma una hora | `2026-08-21 15:00:00+00:00` |
| `DailySuffixResolver` | Hoy a `at_time`; suma un día si eso no está en el futuro | `2026-08-22 00:00:00+00:00` |
| `WeeklySuffixResolver` | Próximo lunes a `at_time`; suma siete días si eso no está en el futuro | `2026-08-24 00:00:00+00:00` |
| `MonthlySuffixResolver` | Primer día del mes siguiente a `at_time` | `2026-09-01 00:00:00+00:00` |
| `ChunkedSuffixResolver` | `current_time + timedelta(hours=1)` (la rotación por tamaño lo ignora) | `2026-08-21 15:37:05+00:00` |

`ChunkedSuffixResolver` es el único resolvedor con estado: mantiene un contador
que incrementa bajo un `threading.Lock`, de modo que **cada llamada a
`getSuffix()` devuelve un valor distinto**. Eso es lo que convierte a
`AdvancedRotatingFileHandler` en un rotador por tamaño — el sufijo siempre
difiere del actual, así que la rotación la decide de hecho la comprobación de
`max_bytes` que se hace antes de consumir el sufijo.

### `AdvancedRotatingFileHandler`

`orionis.logging.handlers.advanced_rotating_file_handler.AdvancedRotatingFileHandler`,
subclase de `logging.Handler`.

```python
def __init__(
    self,
    path_template: str,
    suffix_resolver: SuffixResolver,
    max_bytes: int | None = None,
    backup_count: int = 5,
    encoding: str = "utf-8",
    *,
    delay: bool = True,
    compress_rotated: bool = False,
    app_root: str = ".",
) -> None: ...
```

**Parámetros**

| Parámetro | Tipo | Significado |
|---|---|---|
| `path_template` | `str` | Ruta relativa a `app_root`, con `{suffix}` |
| `suffix_resolver` | `SuffixResolver` | Estrategia que decide el sufijo |
| `max_bytes` | `int \| None` | Umbral de tamaño; `None` desactiva la rotación por tamaño |
| `backup_count` | `int` | Número de archivos rotados que se conservan, además del que se está escribiendo |
| `encoding` | `str` | Codificación con la que se abre el archivo |
| `delay` | `bool` (solo por nombre) | `True` (por defecto) pospone la apertura hasta el primer registro; `False` la abre en el constructor |
| `compress_rotated` | `bool` (solo por nombre) | Comprime con gzip el archivo anterior al rotar |
| `app_root` | `str` (solo por nombre) | Directorio base que se antepone a `path_template` |

**Atributos públicos:** `path_template`, `suffix_resolver`, `max_bytes`,
`backup_count`, `encoding`, `delay`, `compress_rotated`, `app_root` (un `Path`),
más el estado mutable `stream` (`None` hasta la primera escritura),
`current_path`, `current_suffix` y `file_size`.

**Métodos públicos**

| Método | Comportamiento |
|---|---|
| `emit(record: LogRecord) -> None` | Formatea el registro **fuera** del lock y, ya con `self._lock`, garantiza el stream, escribe `msg + "\n"` y suma `len(msg) + 1` a `file_size`. Solo captura `OSError` y lo reporta con `Handler.handleError(record)` |
| `close() -> None` | Cierra el stream bajo el lock y llama a `logging.Handler.close()` |

**Algoritmo de rotación** (`_ensureStream` → `_shouldRotate` → `_rotateFile`)

1. `current_suffix = suffix_resolver.getSuffix()`.
2. Rota cuando el sufijo difiere del activo, **o** cuando
   `max_bytes is not None and file_size >= max_bytes`.
3. Rotar cierra el stream, comprime con gzip el archivo anterior si
   `compress_rotated` está activo (`<archivo>.gz`, se borra el original; si la
   compresión falla se elimina el `.gz` parcial), purga archivos viejos y
   reinicia `current_path`, `current_suffix` y `file_size`.
4. La nueva ruta se resuelve y se abre en modo append con `buffering=1` (línea a
   línea). `file_size` se siembra con `stat().st_size` si el archivo ya existe.

**Resolución de ruta** (`_resolvePath`) sustituye `{suffix}`, une el resultado
con `app_root`, crea el directorio padre (`mkdir(parents=True, exist_ok=True)`)
y cachea la cadena durante 300 segundos usando `time.monotonic()`. La caché se
vacía en cuanto supera las 50 entradas, lo que la acota para la rotación
chunked (un sufijo único por fragmento).

**Purga** (`_cleanupOldFiles`) lista el directorio del archivo actual, se queda
con los nombres que casan con una expresión regular precompilada en el
constructor (el nombre base de la plantilla con `{suffix}` sustituido por `.*`),
los ordena por fecha de modificación de más nuevo a más viejo y borra todo lo
que exceda `backup_count`, junto con su `.gz` correspondiente si existe. Todos
los `OSError` se ignoran para que la purga nunca rompa el registro. El efecto
neto es como máximo `backup_count` archivos rotados más el archivo que se está
escribiendo.

### `RotatingHandlerFactory`

`orionis.logging.handlers.rotating_handler_factory.RotatingHandlerFactory`

```python
@staticmethod
def createHandler(
    channel_name: str,
    channel_config: dict,
    app_root: str,
) -> Handler | None: ...
```

Lee `channel_config["path"]` (por defecto `"storage/logs/default.log"`) y
`channel_config["level"]` (por defecto `20`, es decir `INFO`), y despacha
mediante el dict de nivel de módulo `_CHANNEL_CREATORS`. **Devuelve `None` para
un nombre de canal desconocido** — no lanza excepción. Todos los constructores
llaman a `handler.setLevel(level)` antes de devolver.

| `channel_name` | Handler | Resolvedor | Claves de config leídas | Valores por defecto |
|---|---|---|---|---|
| `stack` | `logging.FileHandler(delay=True)` | — | — | El directorio padre se crea de inmediato |
| `hourly` | `AdvancedRotatingFileHandler` | `HourlySuffixResolver()` | `retention_hours` → `backup_count` | `24` |
| `daily` | `AdvancedRotatingFileHandler` | `DailySuffixResolver(at)` | `at`, `retention_days` → `backup_count` | `at=None` → medianoche, `7` |
| `weekly` | `AdvancedRotatingFileHandler` | `WeeklySuffixResolver(at)` | `at`, `retention_weeks` → `backup_count` | `at=None` → medianoche, `4` |
| `monthly` | `AdvancedRotatingFileHandler` | `MonthlySuffixResolver(at)` | `at`, `retention_months` → `backup_count` | `at=None` → medianoche, `4` |
| `chunked` | `AdvancedRotatingFileHandler` | `ChunkedSuffixResolver()` | `mb_size` → `max_bytes = mb_size * 1024 * 1024`, `files` → `backup_count` | `10` MB, `5` archivos; `compress_rotated=True` |

`chunked` es el único canal que se construye con `compress_rotated=True`, así
que sus archivos rotados terminan en `.log.gz`.

Los constructores de `weekly` y `monthly` leen `channel_config.get("at")`, pero
las entidades de configuración correspondientes (`Weekly`, `Monthly`) no
declaran el campo `at` — solo `Daily` lo hace. Con las entidades del framework
esos dos canales reciben siempre `None` y sus resolvedores caen a medianoche;
una configuración escrita a mano como `dict` sí puede suministrar `at`.

### `LoggerProvider`

`orionis.logging.provider.LoggerProvider(ServiceProvider)`

```python
def register(self) -> None: ...
async def boot(self) -> None: ...
```

- `register()` — `self.app.singleton(ILogger, Logger, alias="x-orionis-ILogger")`.
  Se comparte una única instancia de `Logger` por proceso; resolver `ILogger` o
  el alias devuelve el mismo objeto.
- `boot()` — `await LoggerFacade.pin()`, que convierte a `Log` en un paso
  directo. El provider **no** es diferido, así que arranca durante el inicio de
  la aplicación junto con el resto de providers del núcleo.

### Entidades de configuración

Declaradas en `orionis.foundation.config.logging`, publicadas por el
`config/logging.py` de la aplicación (clase `BootstrapLogging`).
`app.config("logging")` devuelve un `dict` plano
(`{"default": ..., "channels": {...}}`); ahí los niveles ya son enteros,
mientras que `Daily.at` sigue siendo un `datetime.time`.

| Entidad | Campos | Valores por defecto |
|---|---|---|
| `Logging` | `default: str`, `channels: Channels \| dict` | `Env.get("LOG_CHANNEL", "stack")`, `Channels()` |
| `Channels` | `stack`, `hourly`, `daily`, `weekly`, `monthly`, `chunked` | Una entidad por canal |
| `Stack` | `path`, `level` | `storage/logs/stack.log`, `INFO` |
| `Hourly` | `path`, `level`, `retention_hours` | `storage/logs/hourly_{suffix}.log`, `INFO`, `24` |
| `Daily` | `path`, `level`, `retention_days`, `at` | `storage/logs/daily_{suffix}.log`, `INFO`, `7`, `time(0, 0)` |
| `Weekly` | `path`, `level`, `retention_weeks` | `storage/logs/weekly_{suffix}.log`, `INFO`, `4` |
| `Monthly` | `path`, `level`, `retention_months` | `storage/logs/monthly_{suffix}.log`, `INFO`, `4` |
| `Chunked` | `path`, `level`, `mb_size`, `files` | `storage/logs/chunked_{suffix}.log`, `INFO`, `10`, `5` |

Todas son `@dataclass(frozen=True, kw_only=True)` que extienden `BaseEntity` y
validan en `__post_init__`:

- `IsValidPath` — `path` debe ser una cadena no vacía terminada en `.log`; todos
  los canales salvo `stack` exigen además el literal `{suffix}` en la ruta.
- `IsValidLevel` — `level` acepta un enum `Level`, uno de los enteros
  `10/20/30/40/50`, o un nombre de nivel sin distinguir mayúsculas; se normaliza
  a su valor entero.
- Rangos: `retention_hours` 1–168, `retention_days` 1–90, `retention_weeks`
  1–12, `retention_months` 1–12, `mb_size` 1–1000 MB, `files` ≥ 1.
- `Logging.default` debe nombrar uno de los seis campos de `Channels`; en caso
  contrario se lanza `ValueError` al construir la configuración.
- `Daily.at` acepta un `datetime.time` o una cadena ISO `HH:MM:SS`, que se
  convierte; cualquier otra cosa lanza.

`Level` (`orionis.foundation.config.logging.enums.levels.Level`) es un `Enum`
que refleja los valores de la biblioteca estándar: `DEBUG=10`, `INFO=20`,
`WARNING=30`, `ERROR=40`, `CRITICAL=50`.

## Ejemplos de uso

### 1. Registrar desde un controlador

Dentro de una aplicación arrancada la fachada está fijada, así que las llamadas
son síncronas. El contrato también se puede inyectar como parámetro y lo
resuelve el contenedor.

```python
from orionis.http import HttpResponse, response
from orionis.logging.contracts.logger import ILogger
from orionis.support.facades.logger import Log


class ReportController:
    """Emit application log lines while serving a request."""

    async def index(self, logger: ILogger) -> HttpResponse:
        logger.info("report requested")
        return response.json({"status": "ok"})

    async def store(self) -> HttpResponse:
        Log.warning("disk usage above 80%")
        return response.noContent()
```

### 2. Resolver el servicio con el contenedor

La inyección de dependencias funciona sin importar el estado de la fachada, lo
que la convierte en la opción segura en scripts y durante el arranque.

```python
from bootstrap.app import app
from orionis.aio.loop import Loop
from orionis.logging.contracts.logger import ILogger
from orionis.support.facades.logger import Log


async def main() -> None:
    logger = await app.make(ILogger)
    logger.info("resolved through the container")
    print("active channel:", logger.getActiveChannel())

    # The facade is pinned by LoggerProvider.boot() during runtime startup;
    # a standalone script has to request the pin explicitly.
    await Log.pin()
    Log.warning("disk usage above 80%")
    print("available channels:", Log.getAvailableChannels())
    print("same instance:", Log.getLogger() is logger.getLogger())


Loop.run(main())
```

Salida con la configuración por defecto:

```text
active channel: stack
available channels: ['stack', 'hourly', 'daily', 'weekly', 'monthly', 'chunked']
same instance: True
```

### 3. `Logger` autónomo sin el contenedor

`Logger` solo necesita un objeto que exponga `config(key)` y `path(name)`, lo
que permite usarlo en scripts aislados y en pruebas.

```python
import logging
import tempfile
from pathlib import Path

from orionis.logging import Logger


class MiniApp:
    """Minimal stand-in exposing the two hooks Logger consumes."""

    def __init__(self, root: str) -> None:
        self._root = root

    def config(self, key: str) -> dict:
        return {
            "default": "daily",
            "channels": {
                "daily": {
                    "path": "logs/app_{suffix}.log",
                    "level": logging.DEBUG,
                    "retention_days": 3,
                },
            },
        }

    def path(self, name: str) -> str:
        return self._root


with tempfile.TemporaryDirectory() as root:
    logger = Logger(MiniApp(root))
    logger.info("service started")
    logger.debug("cache warm-up finished")
    print("active:", logger.getActiveChannels())
    print("files:", sorted(p.name for p in (Path(root) / "logs").iterdir()))
    logger.close()
    print("after close:", logger.getActiveChannels())
```

Salida (ejecutado el 2026-08-21):

```text
active: ['daily']
files: ['app_2026-08-21.log']
after close: []
```

### 4. Cambiar de canal y manejar errores

`switchChannel` señala el fallo con `False`; `reloadConfiguration` es el único
método que lanza si algo falla.

```python
import logging
import tempfile

from orionis.logging import Logger


class MiniApp:
    """Minimal stand-in exposing the two hooks Logger consumes."""

    def __init__(self, root: str) -> None:
        self._root = root

    def config(self, key: str) -> dict:
        return {
            "default": "daily",
            "channels": {
                "daily": {
                    "path": "logs/app_{suffix}.log",
                    "level": logging.DEBUG,
                    "retention_days": 3,
                },
            },
        }

    def path(self, name: str) -> str:
        return self._root


with tempfile.TemporaryDirectory() as root:
    logger = Logger(MiniApp(root))
    logger.info("written to the default channel")

    if not logger.switchChannel("hourly"):
        print("channel 'hourly' is not declared; staying on the current one")

    print("available:", logger.getAvailableChannels())
    print("active:", logger.getActiveChannel())

    try:
        logger.reloadConfiguration()
    except RuntimeError as exc:
        print("reload failed:", exc)
    else:
        print("reloaded, active:", logger.getActiveChannel())

    logger.close()
```

Salida:

```text
channel 'hourly' is not declared; staying on the current one
available: ['daily']
active: daily
reloaded, active: daily
```

### 5. `SuffixResolver` propio

Implementar el contrato basta para enchufar una política de rotación nueva en
`AdvancedRotatingFileHandler`.

```python
import logging
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from orionis.logging.contracts.suffix_resolver import SuffixResolver
from orionis.logging.handlers.advanced_rotating_file_handler import (
    AdvancedRotatingFileHandler,
)


class ShiftSuffixResolver(SuffixResolver):
    """Rotate twice a day: one file for the morning, one for the afternoon."""

    __slots__ = ()

    def getSuffix(self, dt: datetime | None = None) -> str:
        moment = dt or datetime.now()
        half = "am" if moment.hour < 12 else "pm"
        return f"{moment:%Y-%m-%d}-{half}"

    def getNextRotationTime(self, current_time: datetime) -> datetime:
        if current_time.hour < 12:
            return current_time.replace(hour=12, minute=0, second=0, microsecond=0)
        midnight = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight + timedelta(days=1)


with tempfile.TemporaryDirectory() as root:
    handler = AdvancedRotatingFileHandler(
        path_template="logs/shift_{suffix}.log",
        suffix_resolver=ShiftSuffixResolver(),
        backup_count=4,
        app_root=root,
    )
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))

    native = logging.getLogger("shift-demo")
    native.setLevel(logging.INFO)
    native.addHandler(handler)
    native.info("payment accepted")
    native.handlers.clear()
    handler.close()

    print("files:", sorted(p.name for p in (Path(root) / "logs").iterdir()))
```

Salida (ejecutado a las 18:57 hora local):

```text
files: ['shift_2026-08-21-pm.log']
```

### 6. Construir un handler con la fábrica

Útil para conectar un handler rotativo de Orionis a un logger de terceros, y
para ver cómo se traducen las opciones del canal a parámetros del handler.

```python
import logging
import tempfile

from orionis.logging.handlers.rotating_handler_factory import RotatingHandlerFactory

with tempfile.TemporaryDirectory() as root:
    built = RotatingHandlerFactory.createHandler(
        channel_name="chunked",
        channel_config={
            "path": "logs/audit_{suffix}.log",
            "level": logging.INFO,
            "mb_size": 1,
            "files": 3,
        },
        app_root=root,
    )
    print("handler:", type(built).__name__)
    print("max_bytes:", built.max_bytes, "backup_count:", built.backup_count)
    print("compress_rotated:", built.compress_rotated)

    unknown = RotatingHandlerFactory.createHandler(
        channel_name="syslog",
        channel_config={"path": "logs/syslog.log", "level": logging.INFO},
        app_root=root,
    )
    print("unsupported channel ->", unknown)
    built.close()
```

Salida:

```text
handler: AdvancedRotatingFileHandler
max_bytes: 1048576 backup_count: 3
compress_rotated: True
unsupported channel -> None
```

## Rendimiento y concurrencia

- **Inicialización perezosa.** Construir el logger no cuesta nada hasta el
  primer mensaje. `__ensureLoggerReady()` usa doble comprobación sobre un
  `threading.Lock`, así que la ruta rápida es un único `is not None`.
- **Guarda en línea en la ruta caliente.** Cada método de registro repite la
  comprobación `if self.__logger is None` en línea en lugar de llamar siempre al
  ayudante, y llama directamente al método de nivel de la biblioteca estándar en
  vez de a `log(level, …)`.
- **Caché de formatters.** `Logger._formatter_cache` es un `dict` de clase
  plano, sin lock. Fallos de caché concurrentes pueden construir el mismo
  formatter dos veces; como el valor es función pura de la clave, la entrada que
  sobrevive es equivalente.
- **Seguridad de hilos en el handler.** `AdvancedRotatingFileHandler` protege
  `_ensureStream()` y la escritura con su propio `threading.Lock`, y formatea el
  registro *antes* de tomarlo. `logging.Logger` añade además su propio bloqueo
  por registro.
- **Resolvedores.** `ChunkedSuffixResolver` incrementa su contador bajo un lock
  y se puede compartir. Los otros cuatro son inmutables en la práctica tras la
  construcción (solo guardan `tz` y `at_time`) y no mantienen estado por
  llamada.
- **Caché de rutas.** Los resultados de resolución se cachean por instancia de
  handler durante 300 segundos y solo se leen dentro de `_ensureStream()`, es
  decir, siempre bajo el lock del handler. El tope de 50 entradas evita el
  crecimiento sin límite cuando cada rotación produce un sufijo único.
- **La E/S es síncrona.** El módulo no expone API asíncrona: una llamada de
  registro hace una escritura con búfer sobre un archivo abierto y, como el
  stream se abre con `buffering=1`, vuelca una línea por registro. Dentro de una
  corrutina eso bloquea el bucle de eventos mientras dura la escritura; además,
  rotar cuesta `stat`, `mkdir`, listar el directorio y —para `chunked`—
  comprimir con gzip el archivo anterior.
- **Alcance de proceso.** El logger estándar `"__orionis__"` es global al
  proceso, así que cualquier instancia de `Logger` construida sobre él comparte
  sus handlers; de todos modos el contenedor registra una sola instancia. **No**
  hay bloqueo entre procesos: varios procesos que escriban en el mismo archivo
  dependen de la semántica de append del sistema operativo, y la rotación o la
  purga concurrentes entre procesos no están coordinadas.
- **Coste de la purga.** `_cleanupOldFiles()` se ejecuta en cada rotación y hace
  un `glob("*")` completo del directorio de logs más un `stat()` por archivo que
  case, así que su coste es proporcional al número de archivos que haya en ese
  directorio.

## Notas de compatibilidad

- **Python.** Requiere Python ≥ 3.14, en línea con el `requires-python` del
  proyecto. Las anotaciones usan uniones PEP 604 (`int | None`) y evaluación
  diferida PEP 649.
- **Dependencias.** Solo biblioteca estándar (`logging`, `gzip`, `shutil`, `re`,
  `threading`, `pathlib`, `time`, `datetime`), más
  `orionis.support.facades.datetime.DateTime` — la única fuente de verdad de la
  zona horaria en el framework, que envuelve `pendulum`. No hace falta instalar
  nada aparte del propio framework.
- **`from __future__ import annotations`.** Lo usan el provider, los contratos,
  los handlers y los resolvedores; **no** se usa a propósito en `logger.py`,
  porque el contenedor DI resuelve `Logger.__init__` por reflexión y las
  anotaciones como cadena se interpretarían como referencias adelantadas
  literales.
- **Windows.** Los archivos de log se abren en modo texto, así que `\n` se
  escribe como `\r\n`. `file_size` se lleva como `len(msg) + 1` por registro, de
  modo que el contador queda por debajo del tamaño real y la rotación por tamaño
  se dispara algo más tarde de lo que sugiere el `max_bytes` configurado.
- **Separadores de ruta.** `path_template` se parte con `rsplit("/", 1)` al
  construir la expresión regular de purga, así que las plantillas deben usar
  barras normales incluso en Windows; la ruta resuelta en sí se construye con
  `pathlib`.
- **Zona horaria.** Los resolvedores capturan `DateTime.getZoneInfo()` en el
  momento de la construcción. Como `Application.create()` configura la zona
  horaria antes de que arranquen los providers, los handlers construidos durante
  el arranque ya usan la zona de la aplicación; un resolvedor instanciado antes
  de esa configuración conservaría el valor por defecto (`UTC`).

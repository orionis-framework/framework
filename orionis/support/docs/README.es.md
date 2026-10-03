# Orionis Support

> Tipos de utilidad, patrones, entidades, formateadores y fachadas compartidos por los módulos de Orionis.

## Tabla de contenidos

- [Descripción funcional](#descripción-funcional)
- [Referencia de API](#referencia-de-api)
  - [BaseEntity](#baseentity)
  - [Fachadas](#fachadas)
  - [DateTime](#datetime)
  - [Formatter](#formatter)
  - [Inspirational](#inspirational)
  - [Patterns](#patterns)
  - [Performance](#performance)
  - [Structures](#structures)
  - [System](#system)
  - [Types](#types)
- [Ejemplos de uso](#ejemplos-de-uso)
- [Consideraciones de rendimiento y concurrencia](#consideraciones-de-rendimiento-y-concurrencia)
- [Notas de compatibilidad](#notas-de-compatibilidad)

## Descripción funcional

`orionis.support` es un espacio de nombres para utilidades reutilizables del framework; su `__init__.py` raíz está vacío y no exporta una API consolidada. Importa cada símbolo desde el subpaquete propietario. Estas utilidades dan soporte, entre otros, a la configuración de `orionis.foundation`, los resultados de `orionis.orm`, el formateo de errores de `orionis.http`, la medición de `orionis.console` y el acceso a servicios mediante las fachadas del contenedor.

| Subpaquete | API principal | Función |
|---|---|---|
| `entities` | `BaseEntity` | Serialización de dataclasses y metadatos de campos. |
| `facades` | `Application`, `Auth`, `Cache`, `Catch`, `Crypt`, `DateTime`, `DB`, `Hash`, `Lang`, `Log`, `Mail`, `Queue`, `Reactor`, `Route`, `Schedule`, `Schema`, `Session`, `Storage`, `Test`, `View` | Exports perezosos de servicios del contenedor y utilidades de fecha/hora. |
| `formatter` | `Parser`, `ExceptionParser`, `IExceptionParser` | Convierte detalles de excepciones y frames de pila en diccionarios. Consulta la [referencia de Formatter](../formatter/docs/README.es.md). |
| `inspirational` | `Inspire`, `IInspire`, `INSPIRATIONAL_QUOTES` | Selecciona una cita de la colección incluida. Consulta la [referencia de Inspirational](../inspirational/docs/README.es.md). |
| `patterns` | `Final`, `Singleton` | Metaclases para clases no heredables y construcción singleton. Consulta la [referencia de Patterns](../patterns/docs/README.es.md). |
| `performance` | `PerformanceCounter`, `IPerformanceCounter` | Mide el tiempo transcurrido. Consulta la [referencia de Performance](../performance/docs/README.es.md). |
| `structures` | `FreezeThaw` | Convierte estructuras anidadas entre formas mutables e inmutables. Consulta la [referencia de Structures](../structures/docs/README.es.md). |
| `system` | `Workers`, `IWorkers` | Calcula una cantidad de workers a partir de CPU y memoria. Consulta la [referencia de System](../system/docs/README.es.md). |
| `types` | `Collection`, `DotDict`, `MISSING`, `StdClass`, `Stringable`, `ICollection`, `IStdClass` | Helpers para colecciones, mappings, centinelas, objetos dinámicos y cadenas. Consulta la [referencia de Types](../types/docs/README.es.md). |

Los manuales de cada subpaquete contienen tablas de métodos y ejemplos para sus APIs. Las secciones siguientes cubren el comportamiento del paquete raíz, la entidad auxiliar, los exports de fachadas y la API de fecha/hora, que no tiene aquí un manual separado.

## Referencia de API

### BaseEntity

Importa con `from orionis.support.entities import BaseEntity`. `BaseEntity` es un mixin con slots, no una dataclass. Sus subclases necesitan campos de dataclass para que funcionen `dataclasses.fields()` y `dataclasses.asdict()`.

```python
class BaseEntity:
    def __post_init__(self) -> None: ...
    def toDict(self) -> dict[str, Any]: ...
    def getFields(self) -> list[dict[str, Any]]: ...
```

- `__post_init__(self) -> None` es un hook sin operación disponible para las subclases dataclass.
- `toDict(self) -> dict[str, Any]` convierte recursivamente los campos de la dataclass a un diccionario y serializa los miembros de enum como su `.value`.
- `getFields(self) -> list[dict[str, Any]]` devuelve nombres de campos, nombres de tipo normalizados, valores por defecto y metadatos. Al construir el resultado, invoca las fábricas de valores por defecto y los valores callable de metadatos.
- El método privado `_cachedFieldMetadata(cls) -> tuple[tuple[Field[Any], tuple[str, ...]], ...]` cachea los metadatos de campos y tipos por clase de entidad; es un detalle interno utilizado por `getFields()`.

### Fachadas

Importa desde `orionis.support.facades`; el paquete resuelve estos nombres de forma perezosa mediante `__getattr__(name: str) -> object` y enumera los nombres cargados y declarados con `__dir__() -> list[str]`. El `__all__` del paquete contiene los 20 nombres siguientes. Diecinueve son fachadas de servicio; `DateTime` es una utilidad de métodos de clase, no una subclase de `Facade`.

| Export | Módulo de definición | Base en runtime | Firma y destino de `getFacadeAccessor` |
|---|---|---|---|
| `Application` | `facades/application.py` | `Facade` | `getFacadeAccessor(cls) -> str`; devuelve `"x-orionis-IApplication"`. |
| `Auth` | `facades/auth.py` | `Facade` | `getFacadeAccessor(cls) -> type`; devuelve `IAuthManager`. |
| `Cache` | `facades/cache.py` | `Facade` | `getFacadeAccessor(cls) -> type`; devuelve `ICacheManager`. |
| `Catch` | `facades/catch.py` | `Facade` | `getFacadeAccessor(cls) -> str`; devuelve `"x-orionis-ICatch"`. |
| `Crypt` | `facades/encrypter.py` | `Facade` | `getFacadeAccessor(cls) -> type`; devuelve `IEncrypter`. |
| `DB` | `facades/db.py` | `Facade` | `getFacadeAccessor(cls) -> type`; devuelve `IQueryBuilder`. |
| `Hash` | `facades/hash.py` | `Facade` | `getFacadeAccessor(cls) -> type`; devuelve `IHashManager`. |
| `Lang` | `facades/lang.py` | `Facade` | `getFacadeAccessor(cls) -> type`; devuelve `ITranslator`. |
| `Log` | `facades/logger.py` | `Facade` | `getFacadeAccessor(cls) -> str`; devuelve `"x-orionis-ILogger"`. |
| `Mail` | `facades/mail.py` | `Facade` | `getFacadeAccessor(cls) -> type[IMailManager]`; devuelve `IMailManager`. |
| `Queue` | `facades/queue.py` | `Facade` | `getFacadeAccessor(cls) -> type[IQueueManager]`; devuelve `IQueueManager`. |
| `Reactor` | `facades/reactor.py` | `Facade` | `getFacadeAccessor(cls) -> str`; devuelve `"x-orionis-IReactor"`. |
| `Route` | `facades/router.py` | `Facade` | `getFacadeAccessor(cls) -> str`; devuelve `"x-orionis-IRouter"`. |
| `Schedule` | `facades/schedule.py` | `Facade` | `getFacadeAccessor(cls) -> type`; devuelve `ISchedule`. |
| `Schema` | `facades/schema.py` | `Facade` | `getFacadeAccessor(cls) -> type[ISchema]`; devuelve `ISchema`. |
| `Session` | `facades/session.py` | `ScopedFacade` | `getFacadeAccessor(cls) -> type[ISession]`; devuelve `ISession`. |
| `Storage` | `facades/storage.py` | `Facade` | `getFacadeAccessor(cls) -> type`; devuelve `IStorageManager`. |
| `Test` | `facades/testing.py` | `Facade` | `getFacadeAccessor(cls) -> type`; devuelve `ITestingEngine`. |
| `View` | `facades/view.py` | `Facade` | `getFacadeAccessor(cls) -> type`; devuelve `IViewFactory`. |

Cada accessor tiene en el código la firma `@classmethod def getFacadeAccessor(cls) -> ...`. Estas clases de fachada no declaran otros métodos de runtime; las operaciones del servicio se exponen dinámicamente por la clase base y pertenecen al contrato/servicio devuelto. Su disponibilidad depende del binding y del ciclo de vida de esa fachada. Los archivos `.pyi` asociados proporcionan declaraciones estáticas para el editor y el verificador de tipos, pero no son implementaciones de runtime.

### DateTime

Importa con `from orionis.support.facades import DateTime` o directamente desde `orionis.support.facades.datetime`. `DateTime` no es una fachada del contenedor: sus métodos son métodos de clase respaldados por `pendulum`. El estado de clase predeterminado comienza con la zona horaria `"UTC"` y el locale `"en"`; la inicialización de la aplicación puede cargar valores mediante el hook privado `_loadConfig(...)`.

La API pública devuelve valores de Pendulum, salvo cuando se indica otro tipo:

| Métodos | Forma de firma y comportamiento |
|---|---|
| `getTimezone`, `getLocale`, `getZoneInfo` | `getTimezone(cls) -> str`, `getLocale(cls) -> str`, `getZoneInfo(cls) -> ZoneInfo`; leen la zona horaria/locale configurados y un `ZoneInfo` cacheado. |
| `now`, `today`, `tomorrow`, `yesterday` | Aceptan `tz: str \| None = None`; `now` devuelve `pendulum.DateTime` y los otros tres devuelven `pendulum.Date`. |
| `parse` | `parse(cls, date_string: str, tz: str \| None = None, *, strict: bool = True) -> pendulum.DateTime`. |
| `fromFormat` | `fromFormat(cls, date_string: str, fmt: str, tz: str \| None = None, locale: str \| None = None) -> pendulum.DateTime`. |
| `local`, `naive`, `datetime` | Construyen valores de fecha/hora desde componentes enteros; `datetime` también acepta `tz: str \| None = None`. Consulta las firmas del código para los valores predeterminados posicionales. |
| `fromTimestamp` | `fromTimestamp(cls, timestamp: float, tz: str \| None = None) -> pendulum.DateTime`. |
| `fromDatetime` | `fromDatetime(cls, dt: datetime \| pendulum.DateTime, tz: str \| None = None) -> pendulum.DateTime`; los valores no admitidos producen `TypeError`. |
| `duration`, `interval` | Construyen `pendulum.Duration` y `pendulum.Interval`; `duration` recibe unidades solo por nombre e `interval` recibe `start`, `end` y `absolute=False` solo por nombre. |
| `startOf`, `endOf` | `(..., unit: str, dt: pendulum.DateTime \| None = None, tz: str \| None = None) -> pendulum.DateTime`; delegan en Pendulum los límites de la unidad. |
| `startOfDay`, `endOfDay`, `startOfWeek`, `endOfWeek`, `startOfMonth`, `endOfMonth`, `startOfYear`, `endOfYear` | Aceptan `dt` y `tz` opcionales y devuelven el límite correspondiente como `pendulum.DateTime`. |
| `convertToLocal`, `formatLocal` | Convierten entradas string/datetime a la zona configurada o formatean un valor como `str`. Las entradas no admitidas de `convertToLocal` producen `TypeError`. |
| `addDays`, `addHours`, `addMinutes` | Suman una cantidad entera a un `pendulum.DateTime` recibido y devuelven un nuevo datetime Pendulum. |
| `diffInDays`, `diffInHours` | Comparan dos datetimes Pendulum y devuelven como `int` la cantidad absoluta de días u horas completos. |
| `isWeekend`, `isToday`, `isFuture`, `isPast`, `isLeapYear`, `isBirthday` | Predicados de fecha que devuelven `bool`; las fechas opcionales usan la hora actual en la zona configurada cuando así lo indica la firma. |
| `closest`, `farthest` | Comparan un `pendulum.DateTime` de referencia con `*others` y devuelven un `pendulum.DateTime`. |
| `add`, `subtract` | Aplican unidades de año/mes/semana/día/hora/minuto/segundo/microsegundo, recibidas solo por nombre, a un datetime. |
| `diff`, `diffForHumans` | Devuelven `pendulum.Interval` o `str` localizado legible; el segundo datetime opcional usa la hora actual por defecto. |
| `next`, `previous` | Buscan una ocurrencia de día de la semana; aceptan `day_of_week` opcional y `keep_time=False` solo por nombre. |
| `average` | Devuelve el punto medio entre un datetime y otro opcional. |
| `firstOf`, `lastOf`, `nthOf` | Buscan un límite u ocurrencia de día de semana en un mes, trimestre o año. |

Las firmas de los métodos públicos se muestran a continuación según sus declaraciones en el código. Todos son métodos de clase.

```text
def getTimezone(cls) -> str
def getLocale(cls) -> str
def getZoneInfo(cls) -> ZoneInfo
def now(cls, tz: str | None = None) -> pendulum.DateTime
def today(cls, tz: str | None = None) -> pendulum.Date
def tomorrow(cls, tz: str | None = None) -> pendulum.Date
def yesterday(cls, tz: str | None = None) -> pendulum.Date
def parse(cls, date_string: str, tz: str | None = None, *, strict: bool = True) -> pendulum.DateTime
def fromFormat(cls, date_string: str, fmt: str, tz: str | None = None, locale: str | None = None) -> pendulum.DateTime
def local(cls, year: int, month: int = 1, day: int = 1, hour: int = 0, minute: int = 0, second: int = 0, microsecond: int = 0) -> pendulum.DateTime
def naive(cls, year: int, month: int = 1, day: int = 1, hour: int = 0, minute: int = 0, second: int = 0, microsecond: int = 0) -> pendulum.DateTime
def fromTimestamp(cls, timestamp: float, tz: str | None = None) -> pendulum.DateTime
def fromDatetime(cls, dt: stdlib_datetime | pendulum.DateTime, tz: str | None = None) -> pendulum.DateTime
def datetime(cls, year: int, month: int = 1, day: int = 1, hour: int = 0, minute: int = 0, second: int = 0, microsecond: int = 0, tz: str | None = None) -> pendulum.DateTime
def duration(cls, *, days: float = 0, seconds: float = 0, microseconds: float = 0, milliseconds: float = 0, minutes: float = 0, hours: float = 0, weeks: float = 0, years: float = 0, months: float = 0) -> pendulum.Duration
def interval(cls, start: pendulum.DateTime, end: pendulum.DateTime, *, absolute: bool = False) -> pendulum.Interval
def startOf(cls, unit: str, dt: pendulum.DateTime | None = None, tz: str | None = None) -> pendulum.DateTime
def endOf(cls, unit: str, dt: pendulum.DateTime | None = None, tz: str | None = None) -> pendulum.DateTime
def startOfDay(cls, dt: pendulum.DateTime | None = None, tz: str | None = None) -> pendulum.DateTime
def endOfDay(cls, dt: pendulum.DateTime | None = None, tz: str | None = None) -> pendulum.DateTime
def convertToLocal(cls, dt: str | stdlib_datetime | pendulum.DateTime) -> pendulum.DateTime
def formatLocal(cls, dt: pendulum.DateTime | None = None, format_string: str = "YYYY-MM-DD HH:mm:ss") -> str
def startOfWeek(cls, dt: pendulum.DateTime | None = None, tz: str | None = None) -> pendulum.DateTime
def endOfWeek(cls, dt: pendulum.DateTime | None = None, tz: str | None = None) -> pendulum.DateTime
def startOfMonth(cls, dt: pendulum.DateTime | None = None, tz: str | None = None) -> pendulum.DateTime
def endOfMonth(cls, dt: pendulum.DateTime | None = None, tz: str | None = None) -> pendulum.DateTime
def startOfYear(cls, dt: pendulum.DateTime | None = None, tz: str | None = None) -> pendulum.DateTime
def endOfYear(cls, dt: pendulum.DateTime | None = None, tz: str | None = None) -> pendulum.DateTime
def addDays(cls, dt: pendulum.DateTime, days: int) -> pendulum.DateTime
def addHours(cls, dt: pendulum.DateTime, hours: int) -> pendulum.DateTime
def addMinutes(cls, dt: pendulum.DateTime, minutes: int) -> pendulum.DateTime
def diffInDays(cls, dt1: pendulum.DateTime, dt2: pendulum.DateTime) -> int
def diffInHours(cls, dt1: pendulum.DateTime, dt2: pendulum.DateTime) -> int
def isWeekend(cls, dt: pendulum.DateTime | None = None) -> bool
def isToday(cls, dt: pendulum.DateTime) -> bool
def isFuture(cls, dt: pendulum.DateTime) -> bool
def isPast(cls, dt: pendulum.DateTime) -> bool
def isLeapYear(cls, dt: pendulum.DateTime | None = None) -> bool
def isBirthday(cls, dt: pendulum.DateTime, other: pendulum.DateTime | None = None) -> bool
def closest(cls, dt: pendulum.DateTime, *others: pendulum.DateTime) -> pendulum.DateTime
def farthest(cls, dt: pendulum.DateTime, *others: pendulum.DateTime) -> pendulum.DateTime
def add(cls, dt: pendulum.DateTime, *, years: int = 0, months: int = 0, weeks: int = 0, days: int = 0, hours: int = 0, minutes: int = 0, seconds: float = 0, microseconds: int = 0) -> pendulum.DateTime
def subtract(cls, dt: pendulum.DateTime, *, years: int = 0, months: int = 0, weeks: int = 0, days: int = 0, hours: int = 0, minutes: int = 0, seconds: float = 0, microseconds: int = 0) -> pendulum.DateTime
def diff(cls, dt1: pendulum.DateTime, dt2: pendulum.DateTime | None = None, *, absolute: bool = True) -> pendulum.Interval
def diffForHumans(cls, dt: pendulum.DateTime, other: pendulum.DateTime | None = None, *, absolute: bool = False, locale: str | None = None) -> str
def next(cls, dt: pendulum.DateTime, day_of_week: int | None = None, *, keep_time: bool = False) -> pendulum.DateTime
def previous(cls, dt: pendulum.DateTime, day_of_week: int | None = None, *, keep_time: bool = False) -> pendulum.DateTime
def average(cls, dt1: pendulum.DateTime, dt2: pendulum.DateTime | None = None) -> pendulum.DateTime
def firstOf(cls, dt: pendulum.DateTime, unit: str, day_of_week: int | None = None) -> pendulum.DateTime
def lastOf(cls, dt: pendulum.DateTime, unit: str, day_of_week: int | None = None) -> pendulum.DateTime
def nthOf(cls, dt: pendulum.DateTime, unit: str, nth: int, day_of_week: int) -> pendulum.DateTime
```

Los mutadores privados de configuración son `_loadConfig(cls, timezone_name: str | None = None, locale: str | None = None) -> None`, `_setTimezone(cls, timezone_name: str) -> None` y `_setLocale(cls, locale: str) -> None`. `_setTimezone` produce `ValueError` para una zona horaria no válida. Los significados de parámetros se describen en los docstrings de [datetime.py](../facades/datetime.py).

### Formatter

Los símbolos públicos son `Parser`, `ExceptionParser` y el protocolo estructural `IExceptionParser`. La llamada habitual es `Parser.exception(exception: Exception) -> ExceptionParser`, una fábrica estática. `ExceptionParser(exception: Exception) -> None` captura los datos del traceback al construirse; `toDict(self) -> dict[str, Any]` devuelve `error_type`, `error_message`, `error_code` y `stack_trace`. Las entradas de la pila incluyen contexto de líneas de fuente cuando está disponible. Consulta [el manual de formatter](../formatter/docs/README.es.md) para el esquema de salida y detalles completos de la API.

### Inspirational

`Inspire(quotes: list[dict] | None = None) -> None` implementa `IInspire`; `random(self) -> dict` elige un elemento de su lista de citas. `INSPIRATIONAL_QUOTES` es la tupla incluida de mappings de citas. El módulo usa `secrets.choice`; el comportamiento alternativo para una lista vacía está descrito en [su manual](../inspirational/docs/README.es.md).

### Patterns

`Final` y `Singleton` son metaclases que se importan de `orionis.support.patterns.final.meta` y `orionis.support.patterns.singleton.meta`, respectivamente. `Final.__new__(metacls: type, name: str, bases: tuple[type, ...], namespace: dict[str, object]) -> type` marca una clase y rechaza con `TypeError` las subclases de una base marcada.

`Singleton` proporciona `__init__(cls, name: str, bases: tuple[type, ...], namespace: dict[str, object]) -> None`, `__call__(cls, *args: object, **kwargs: object) -> object` y `async __acall__(cls, *args: object, **kwargs: object) -> object`. El constructor asíncrono se espera explícitamente como `await MyClass.__acall__()`; `MyClass()` usa la ruta síncrona. Consulta [el manual de patterns](../patterns/docs/README.es.md) para más comportamiento y detalles de concurrencia.

### Performance

`PerformanceCounter() -> None` implementa `IPerformanceCounter`. Su API pública ofrece pares síncronos/asíncronos: `start`/`astart`, `stop`/`astop`, `restart`/`arestart`, lectores de tiempo transcurrido (`elapsedTime`, `aelapsedTime`, `getSeconds`, `agetSeconds`, `getMilliseconds`, `agetMilliseconds`, `getMicroseconds`, `agetMicroseconds`, `getMinutes`, `agetMinutes`) y gestores de contexto `with`/`async with`. Los lectores requieren una medición completada; mezclar modos de inicio/parada síncronos y asíncronos produce `RuntimeError`. Consulta [el manual de performance](../performance/docs/README.es.md) para las firmas completas y las condiciones de excepción.

### Structures

`FreezeThaw` expone los métodos estáticos `freeze(obj: object) -> object` y `thaw(obj: object) -> object`. `freeze` transforma recursivamente diccionarios/listas mutables en `MappingProxyType`/tuplas; `thaw` convierte árboles compatibles de nuevo en diccionarios/listas mutables. El helper privado `_isContainer(obj: object) -> bool` no forma parte de la API pública. Consulta [el manual de structures](../structures/docs/README.es.md) para el manejo de identidad y referencias compartidas.

### System

`Workers` implementa `IWorkers` con dos métodos de clase: `setRamPerWorker(cls, ram_per_worker: float) -> None` y `calculate(cls) -> int`. El primero cambia el presupuesto de RAM de clase utilizado por el segundo. Los valores de CPU y RAM total se obtienen al importar el módulo. Consulta [el manual de system](../system/docs/README.es.md) para los valores predeterminados y los casos límite.

### Types

El paquete exporta `Collection`, `DotDict`, `MISSING`, `StdClass` y `Stringable` desde `orionis.support.types`. También define los contratos `ICollection` e `IStdClass` en `orionis.support.types.contracts`.

| Símbolo | Constructor / API principal | Comportamiento |
|---|---|---|
| `Collection` | `Collection(items: list[Any] | None = None) -> None` | Operaciones fluidas sobre listas, iteración, indexación, agregación, filtrado, agrupación y serialización. Algunos métodos mutan y devuelven la misma colección; consulta su tabla de métodos. |
| `DotDict` | `DotDict(*args, **kwargs)` (hereda de `dict`) | Añade acceso por atributo a las claves del mapping; al consultar un atributo ausente devuelve `None`. |
| `MISSING` | Valor singleton | Marcador falsy cuya representación es `"<MISSING>"`, usado para distinguir valores omitidos de `None`. |
| `StdClass` | `StdClass(**kwargs: object) -> None` | Contenedor de atributos dinámicos; `update`, `remove`, `toDict` y el método de clase `fromDict` operan sobre los atributos de instancia. |
| `Stringable` | `Stringable(object: object = "") -> Stringable` | Subclase inmutable de `str` con métodos fluidos de transformación, predicados, conversión y callbacks. `encrypt`/`decrypt` delegan en la fachada `Crypt`. |

El subpaquete `types` también exporta los contratos `ICollection` e `IStdClass`. `DotDict` y `Stringable` no tienen contratos propios. Consulta [el manual de types](../types/docs/README.es.md) para el catálogo de métodos y la semántica de mutación/devolución.

## Ejemplos de uso

### Uso común: transformar una colección

```python
from orionis.support.types import Collection, Stringable

names = Collection(["Ada Lovelace", "Grace Hopper"])
slugs = names.map(lambda name: Stringable(name).snake()).all()
print(slugs)
```

### Convertir una excepción en datos estructurados

```python
from orionis.support.formatter.serializer import Parser

try:
    int("not-an-integer")
except ValueError as exc:
    payload = Parser.exception(exc).toDict()
    assert payload["error_type"] == "ValueError"
    assert payload["stack_trace"]
```

### Combinar serialización de entidades y operaciones de colección

```python
from dataclasses import dataclass

from orionis.support.entities import BaseEntity
from orionis.support.types import Collection


@dataclass(frozen=True)
class Product(BaseEntity):
    name: str
    price: int


products = Collection([
    Product("Notebook", 12),
    Product("Pen", 3),
])
payload = products.map(lambda product: product.toDict()).all()
assert payload[0] == {"name": "Notebook", "price": 12}
```

## Consideraciones de rendimiento y concurrencia

> ⚠️ No especificado en el código fuente: garantías de seguridad entre hilos para cambios concurrentes de configuración de `DateTime`, para compartir una instancia de `PerformanceCounter` o para mutar simultáneamente `Collection`, `DotDict` o `StdClass`.

- `DateTime` almacena en la clase la zona horaria predeterminada, el locale y la caché de zonas.
- `PerformanceCounter` mantiene estado mutable por instancia.
- `Collection`, `DotDict` y `StdClass` exponen datos mutables.
- `ExceptionParser` captura de forma eager los metadatos del traceback y cachea el diccionario de `toDict()`. Consulta su manual para el comportamiento de caché y la identidad del objeto devuelto.
- `FreezeThaw` utiliza estado de recorrido por llamada y no conserva el árbol de entrada en la clase.
- Los detalles de concurrencia y ciclo de vida de `Singleton` y las fachadas dependen de sus implementaciones en `patterns` y `container`; consulta las referencias de esos módulos en vez de asumir que todos los exports comparten una única garantía.

## Notas de compatibilidad

- El proyecto declara `requires-python = ">=3.14"` en `pyproject.toml`. El paquete support sigue este mínimo global; su código no declara un mínimo diferente.
- Las dependencias externas importadas directamente por `orionis/support` son `dotty-dict>=1.3.1,<2.0` (`Collection`), `pendulum>=3.2.0,<4.0` (`DateTime`) y `psutil>=7.2.2,<8.0` (`Workers`). Las tres son dependencias base del proyecto; no se requiere instalación adicional.
- `Stringable.encrypt()` y `Stringable.decrypt()` requieren la fachada `Crypt` y el binding de su servicio. Los demás helpers de `types` se pueden usar directamente sin resolver una fachada.
- Los métodos de las fachadas pertenecen a los contratos/servicios que estas delegan. Sus firmas y requisitos de ciclo de vida pueden variar según el servicio; consulta la documentación del módulo correspondiente.
# orionis.container

> Contenedor de servicios async-first: bindings, ciclos de vida, scopes, autowiring, service providers y facades.

## Tabla de contenidos

- [Descripción funcional](#descripción-funcional)
  - [Dónde encaja](#dónde-encaja)
  - [Pipeline de resolución](#pipeline-de-resolución)
  - [Orden de resolución de argumentos](#orden-de-resolución-de-argumentos)
  - [Mapa de archivos](#mapa-de-archivos)
  - [Decisiones de diseño](#decisiones-de-diseño)
- [Referencia de API](#referencia-de-api)
  - [`Container`](#container)
    - [`Container.instance()`](#containerinstance)
    - [`Container.transient()`](#containertransient)
    - [`Container.singleton()`](#containersingleton)
    - [`Container.scoped()`](#containerscoped)
    - [`Container.bound()`](#containerbound)
    - [`Container.beginScope()`](#containerbeginscope)
    - [`Container.getCurrentScope()`](#containergetcurrentscope)
    - [`Container.make()`](#containermake)
    - [`Container.build()`](#containerbuild)
    - [`Container.invoke()`](#containerinvoke)
    - [`Container.call()`](#containercall)
  - [`IContainer`](#icontainer)
  - [`Lifetime`](#lifetime)
  - [`Binding`](#binding)
  - [`ScopeManager`](#scopemanager)
  - [`ScopedContext`](#scopedcontext)
  - [`CircularDependencyException`](#circulardependencyexception)
  - [`ServiceProvider`](#serviceprovider)
  - [`DeferrableProvider`](#deferrableprovider)
  - [`IServiceProvider`](#iserviceprovider)
  - [`IDeferrableProvider`](#ideferrableprovider)
  - [`Facade`](#facade)
  - [`FacadeMeta`](#facademeta)
  - [`IFacade`](#ifacade)
  - [Exportaciones del paquete](#exportaciones-del-paquete)
- [Ejemplos de uso](#ejemplos-de-uso)
  - [Registrar y resolver servicios](#registrar-y-resolver-servicios)
  - [Trabajar con scopes](#trabajar-con-scopes)
  - [Manejo de errores de resolución](#manejo-de-errores-de-resolución)
  - [Construir un service provider](#construir-un-service-provider)
  - [Exponer un servicio con una facade](#exponer-un-servicio-con-una-facade)
  - [Inspeccionar bindings y scopes](#inspeccionar-bindings-y-scopes)
  - [Resolver de forma concurrente](#resolver-de-forma-concurrente)
- [Consideraciones de rendimiento y concurrencia](#consideraciones-de-rendimiento-y-concurrencia)
- [Notas de compatibilidad](#notas-de-compatibilidad)

---

## Descripción funcional

`orionis.container` es el motor de inyección de dependencias del framework. Asocia
contratos (clases abstractas o alias de texto) con implementaciones concretas, decide
cuánto vive cada objeto resuelto y construye instancias leyendo por reflexión la firma
de sus constructores, de modo que quien lo usa nunca cablea dependencias a mano.

### Dónde encaja

- `orionis.foundation.application.Application` extiende `Container` y añade la capa de
  arranque. El MRO verificado es
  `Application -> Container -> IApplication -> IContainer -> ABC -> object`, así que el
  contenedor real de una aplicación en ejecución *es* el singleton de `Application`.
- `orionis.introspection` aporta `ReflectionConcrete` y `ReflectionCallable`, que
  producen los metadatos `Signature`/`Argument` usados para inyectar parámetros de
  constructores y de callables.
- `orionis.schemas.validator.Schema` y `orionis.http.request.Request` se importan a
  nivel de módulo en `container.py`: un parámetro anotado con una subclase de
  `msgspec.Struct` se resuelve validando el cuerpo de la petición actual.
- `orionis.support.entities.base.BaseEntity` es la base del dataclass `Binding`.
- `orionis.foundation.contracts.application.IApplication` lo importa en runtime
  `ServiceProvider` para tipar su argumento de constructor.

### Pipeline de resolución

`make(key)` ejecuta estos pasos, en este orden:

1. Si `key` no es una cadena y la caché de singletons ya lo contiene, se devuelve el
   objeto cacheado de inmediato.
2. `key` se normaliza a un tipo abstracto. Una cadena se busca en la tabla de alias; si
   no aparece, se consulta el registro de proveedores diferidos, se importa el
   proveedor correspondiente, se construye, se ejecuta su `register()` y su `boot()`, y
   se vuelve a leer la tabla de alias. Un alias que sigue siendo desconocido lanza
   `ValueError`.
3. Se comprueba de nuevo la caché de singletons con el tipo abstracto ya resuelto.
4. Si hay un scope activo que ya contiene el tipo abstracto, se devuelve esa instancia.
5. Se consulta la tabla de bindings. Si no hay binding, se consulta otra vez el
   registro diferido. Si sigue sin haber binding y la clave es una clase, el contenedor
   recurre a `build()`; en caso contrario lanza `ValueError`.
6. El binding se resuelve según su `Lifetime`: `SINGLETON` cachea la instancia contra
   el contrato, `TRANSIENT` construye siempre una nueva y `SCOPED` la guarda en el
   scope activo (lanzando `RuntimeError` si no hay ninguno abierto).

`build()` nunca consulta la caché de singletons: siempre construye un objeto nuevo.

### Orden de resolución de argumentos

`Container` inspecciona la firma del objetivo una sola vez y luego resuelve cada
parámetro en orden de declaración. Los parámetros llamados `self`, `cls`, `args` y
`kwargs`, además de `*args` y `**kwargs`, los descarta la capa de reflexión.

Para parámetros posicionales-o-keyword:

1. El parámetro está anotado con una subclase de `msgspec.Struct` → el valor se produce
   validando el cuerpo de la petición.
2. El tipo anotado está registrado en el contenedor **y** el nombre del parámetro no se
   pasó como keyword → se resuelve con `make()`.
3. Queda algún argumento posicional aportado por quien llama → se consume.
4. Un argumento keyword aportado por quien llama coincide con el nombre → se consume.
5. En otro caso el argumento se resuelve por sí solo: gana el valor por defecto
   declarado y, si no lo hay, se usa `make()`. Los parámetros sin resolver cuyo tipo
   vive en `builtins` o `typing` lanzan `TypeError`.

Para parámetros keyword-only:

1. Parámetros de schema, igual que arriba.
2. Un argumento keyword aportado por quien llama coincide con el nombre → se consume.
3. El tipo anotado está registrado en el contenedor → se resuelve con `make()`.
4. En otro caso el argumento se resuelve por sí solo, como en el paso 5 anterior.

Los argumentos posicionales que la firma no consumió se añaden al final y los keyword
sin usar se fusionan en la llamada final.

### Mapa de archivos

| Ruta | Contenido |
|---|---|
| `container.py` | `Container`, el motor concreto. |
| `contracts/container.py` | `IContainer` — 11 métodos abstractos. |
| `contracts/service_provider.py` | `IServiceProvider` — `register()` / `boot()`. |
| `contracts/deferrable_provider.py` | `IDeferrableProvider` — `provides()`. |
| `contracts/facade.py` | `IFacade` — `getFacadeAccessor()` / `resolve()` / `pin()` / `unpin()`. |
| `context/scope.py` | `ScopedContext` y los atajos de módulo `get_current_scope` / `set_current_scope` / `reset_scope`. |
| `context/manager.py` | `ScopeManager`, el context manager async que respalda el ciclo de vida scoped. |
| `entities/binding.py` | `Binding`, el registro inmutable que describe una registración. |
| `enums/lifetimes.py` | `Lifetime` — `TRANSIENT`, `SINGLETON`, `SCOPED`. |
| `exceptions/container.py` | `CircularDependencyException`. |
| `facades/facade.py` | `Facade`, la clase base de proxy estático. |
| `facades/meta.py` | `FacadeMeta` y el privado `_FacadeDispatch`. |
| `providers/service_provider.py` | Clase base `ServiceProvider`. |
| `providers/deferrable_provider.py` | Clase base marcadora `DeferrableProvider`. |

### Decisiones de diseño

- **Singleton por clase.** `Container.__new__` guarda una instancia por clase en el
  diccionario de clase `_instances` usando double-checked locking sobre un
  `threading.RLock`. Las subclases que no redeclaran `_instances` comparten ese único
  diccionario, indexado por objeto-clase, así que cada subclase sigue teniendo su
  propia instancia.
- **`__init__` idempotente.** La inicialización está protegida por la presencia de
  `_Container__initialized` en `self.__dict__`, así que volver a construir el singleton
  nunca borra registros existentes.
- **API de resolución asíncrona.** `make`, `build`, `invoke` y `call` son corrutinas
  porque los `boot()` de los proveedores y la validación de schemas pueden hacer await.
- **`contextvars` para scopes y detección de ciclos.** Tanto el scope activo como la
  pila de resolución en curso viven en `ContextVar`s, así que tareas asyncio
  concurrentes nunca observan el estado de las demás.
- **El trabajo de una sola vez se serializa por clave.** Construir un singleton,
  rellenar una entrada de scope y arrancar un proveedor diferido atraviesan varios
  puntos `await`, así que cada uno se ejecuta bajo un `asyncio.Lock` indexado por
  contrato (o por clave de proveedor). Las tareas concurrentes comparten esa única
  construcción en lugar de duplicarla.
- **`Binding` inmutable.** Las registraciones se describen con un dataclass inmutable y
  hasheable, seguro de compartir entre la tabla de bindings y quien lo consulte.
- **Dispatch perezoso en las facades.** `FacadeMeta.__getattr__` devuelve una función
  normal cacheada; el contenedor solo se toca cuando el `_FacadeDispatch` resultante se
  awaita o se entra como context manager, lo que respeta los bindings transitorios.
- **Sin `__slots__`.** `Container`, `ScopeManager` y `Binding` conservan `__dict__`;
  solo `_FacadeDispatch` declara `__slots__`.

---

## Referencia de API

### `Container`

```python
class Container(IContainer):
    _instances: ClassVar[dict] = {}
    _lock: ClassVar[threading.RLock] = threading.RLock()

    def __new__(cls, *args, **kwargs) -> Self: ...
    def __init__(self) -> None: ...
```

Implementación concreta de `IContainer`, en `orionis.container.container`. Su docstring
de clase declara el contrato de concurrencia reproducido en [Consideraciones de
rendimiento y concurrencia](#consideraciones-de-rendimiento-y-concurrencia).

**Atributos de clase**

| Nombre | Tipo | Significado |
|---|---|---|
| `_instances` | `ClassVar[dict]` | Registro de singletons indexado por objeto-clase. Lo comparte toda subclase que no lo redeclare. |
| `_lock` | `ClassVar[threading.RLock]` | Protege la creación del singleton dentro de `__new__`. |

**Estado de instancia creado por `__init__`**

| Nombre | Tipo | Significado |
|---|---|---|
| `_deferred_providers` | `dict[str, dict[str, str]]` | Asocia una clave solicitada con `{"module": ..., "class": ...}`. Lo puebla `Application.create()`, no este módulo. |
| `__singleton_cache` | `dict[str, Any]` | Instancias singleton resueltas, indexadas por contrato. |
| `__aliases` | `dict[str, type]` | Alias de texto → tipo abstracto. |
| `__bindings` | `dict[Any, Binding]` | Tipo abstracto → `Binding`. |
| `__cache_resolve_deferred_providers` | `set[Any]` | Claves cuyo proveedor diferido ya se ejecutó. |
| `__creation_locks` | `dict[Any, tuple[AbstractEventLoop, asyncio.Lock]]` | Lock de creación por clave junto al loop que lo posee. |

**Efectos secundarios.** Construir cualquier subclase de `Container` muta el
diccionario compartido `_instances`. Los métodos de registro mutan los diccionarios de
instancia listados arriba. La resolución puede importar módulos (proveedores diferidos)
y leer la petición HTTP actual (argumentos de schema).

#### `Container.instance()`

```python
def instance(
    self,
    abstract: type[Any] | None,
    instance: object,
    *,
    alias: str | None = None,
    override: bool = False,
) -> bool: ...
```

Registra un objeto ya construido.

- `abstract` — contrato a asociar con el objeto, o `None` para usar `type(instance)`.
- `instance` — el objeto ya inicializado. Pasar una clase lanza `TypeError`.
- `alias` — alias opcional. Se le hace `strip` y debe ser una cadena no vacía.
- `override` — permite reemplazar una registración existente.
- **Devuelve** `True` cuando la registración fue correcta.

El comportamiento depende de si hay un scope activo:

- **Dentro de un scope**, el objeto se guarda en ese scope. Pasar `alias` lanza
  `ValueError("Alias registration is only allowed globally.")`.
- **Fuera de un scope**, se guarda un `Binding` con `Lifetime.SINGLETON` y el objeto se
  coloca en la caché de singletons; el alias, si lo hay, se añade a la tabla de alias.

**Lanza**

- `TypeError` — `instance` es una clase; `abstract` no es una clase; `instance` no es
  instancia de `abstract`; `alias` no es una cadena.
- `ValueError` — `alias` queda vacío tras el `strip`; el contrato o el alias ya están
  registrados y `override` es `False`; se pasó un alias dentro de un scope.

#### `Container.transient()`

```python
def transient(
    self,
    abstract: type[Any] | None,
    concrete: type[Any],
    *,
    alias: str | None = None,
    override: bool = False,
) -> bool: ...
```

Registra `concrete` con `Lifetime.TRANSIENT`; cada resolución construye un objeto
nuevo. Cuando `abstract` es `None`, `concrete` se enlaza consigo mismo.

**Lanza**

- `TypeError` — `abstract` o `concrete` no son clases; `concrete` no es subclase de
  `abstract`; `alias` no es una cadena.
- `ValueError` — alias vacío, o contrato/alias duplicado sin `override`.

#### `Container.singleton()`

```python
def singleton(
    self,
    abstract: type[Any] | None,
    concrete: type[Any],
    *,
    alias: str | None = None,
    override: bool = False,
) -> bool: ...
```

Misma validación que `transient()`, con `Lifetime.SINGLETON`. La instancia se crea en
el primer `make()` y a partir de ahí queda cacheada contra el contrato.

#### `Container.scoped()`

```python
def scoped(
    self,
    abstract: type[Any] | None,
    concrete: type[Any],
    *,
    alias: str | None = None,
    override: bool = False,
) -> bool: ...
```

Misma validación que `transient()`, con `Lifetime.SCOPED`. Resolver el binding sin un
scope activo lanza `RuntimeError`.

#### `Container.bound()`

```python
def bound(
    self,
    key: type[Any] | str,
) -> bool: ...
```

Indica si `key` se puede resolver. Una cadena se traduce primero por la tabla de alias
y devuelve `False` si es desconocida. La búsqueda revisa el scope activo, después la
tabla de bindings y por último la caché de singletons. `bound()` nunca dispara
proveedores diferidos.

#### `Container.beginScope()`

```python
def beginScope(self) -> ScopeManager: ...
```

Devuelve un `ScopeManager` nuevo. El scope solo pasa a estar activo cuando el manager
se entra con `async with`.

#### `Container.getCurrentScope()`

```python
def getCurrentScope(self) -> dict[Any, Any] | None: ...
```

Devuelve el objeto de scope activo, o `None`. El valor sale del `ContextVar` de
`orionis.container.context.scope`, así que es por tarea.

#### `Container.make()`

```python
async def make(
    self,
    key: type[Any] | str,
    *args: tuple[Any, ...],
    **kwargs: dict[str, Any],
) -> Any: ...
```

Resuelve un servicio siguiendo el [pipeline de resolución](#pipeline-de-resolución).
`*args` y `**kwargs` se reenvían al constructor cuando hay que construir el objeto.

Cuando varias tareas del mismo event loop resuelven a la vez el mismo binding
`SINGLETON` o `SCOPED` aún sin cachear, solo se ejecuta una construcción y todas
reciben esa instancia.

**Lanza**

- `ValueError` — clave de texto desconocida, o clave que no es clase y no tiene binding.
- `RuntimeError` — binding `SCOPED` resuelto sin scope activo.
- `CircularDependencyException` — el grafo de dependencias tiene un ciclo.
- `TypeError` — algún parámetro del constructor no se puede resolver.

#### `Container.build()`

```python
async def build(
    self,
    type_: Callable[..., Any],
    *args: tuple[Any, ...],
    **kwargs: dict[str, Any],
) -> Any: ...
```

Instancia `type_` con dependencias autocableadas, ignorando la caché de singletons.
Cuando `type_` no está registrado todavía, primero se consulta el registro de
proveedores diferidos.

**Lanza**

- `TypeError` — `type_` no es una clase, o algún parámetro del constructor no se puede
  resolver.
- `CircularDependencyException` — el grafo de dependencias tiene un ciclo.

#### `Container.invoke()`

```python
async def invoke(
    self,
    fn: Callable[..., Any],
    *args: tuple[Any, ...],
    **kwargs: dict[str, Any],
) -> Any: ...
```

Llama a `fn` con argumentos autocableados y devuelve su resultado. Las funciones
corrutina se awaitan; los callables síncronos se llaman directamente.

**Lanza**

- `TypeError` — `fn` no es invocable o es una clase.

#### `Container.call()`

```python
async def call(
    self,
    instance: object,
    method_name: str,
    *args: tuple,
    **kwargs: dict,
) -> Any: ...
```

Busca `method_name` en `instance` y lo invoca con argumentos autocableados.

**Lanza**

- `AttributeError` — el atributo no existe en la instancia.
- `TypeError` — el atributo existe pero no es invocable.

### `IContainer`

Clase base abstracta en `orionis.container.contracts.container`. Declara exactamente
estos métodos abstractos:

`instance`, `transient`, `singleton`, `scoped`, `bound`, `beginScope`,
`getCurrentScope`, `make`, `build`, `invoke`, `call`.

`make`, `build`, `invoke` y `call` se declaran con `async def`. El módulo usa
`from __future__ import annotations`, así que sus anotaciones son cadenas en runtime
mientras que las de la implementación son objetos reales; solo los nombres de los
parámetros son directamente comparables.

### `Lifetime`

```python
class Lifetime(Enum):
    TRANSIENT = auto()
    SINGLETON = auto()
    SCOPED = auto()
```

`enum.Enum` con tres miembros. Valores verificados: `TRANSIENT = 1`, `SINGLETON = 2`,
`SCOPED = 3`.

### `Binding`

```python
@dataclass(frozen=True, kw_only=True)
class Binding(BaseEntity):
    contract: type | None = None
    concrete: type | None = None
    instance: object | None = None
    lifetime: Lifetime = Lifetime.TRANSIENT
    alias: str | None = None
```

Registro inmutable, hasheable y keyword-only que describe una registración. Hereda
`toDict()` y `getFields()` de `BaseEntity`; `toDict()` convierte el miembro `lifetime`
a su valor entero.

`__post_init__` lanza `TypeError` cuando `lifetime` no es un miembro de `Lifetime`.

`Container` rellena `contract`, `concrete`, `lifetime` y `alias`. Los objetos ya
construidos los guarda en su caché interna de singletons y no en el campo `instance`,
por lo que los bindings creados por el contenedor dejan `instance` en `None`.

### `ScopeManager`

```python
class ScopeManager:
    def __init__(self) -> None: ...
    def __getitem__(self, key: object) -> object | None: ...
    def __setitem__(self, key: object, value: object) -> None: ...
    def __contains__(self, key: object) -> bool: ...
    def clear(self) -> None: ...
    async def __aenter__(self) -> Self: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None: ...
    async def get(self, key: object) -> Any | None: ...
    def set(self, key: object, value: Any) -> None: ...
    async def resolve(self, key: object) -> Any: ...
```

Contenedor tipo diccionario para instancias scoped, en
`orionis.container.context.manager`.

- `__getitem__` devuelve `None` para claves ausentes en lugar de lanzar.
- `__aenter__` publica el manager como scope activo y guarda el token de reset en
  `self._token`; ese atributo solo existe tras entrar, así que llamar antes a
  `__aexit__` lanza `AttributeError`.
- `__aexit__` limpia todas las instancias guardadas y resetea el `ContextVar` del
  scope. Siempre limpia, incluso si el bloque lanzó una excepción.
- `get()` awaita corrutinas y `asyncio.Task` almacenados, reemplazando el valor
  guardado por el resultado resuelto para que las llamadas siguientes sean baratas.
  Devuelve `None` tanto para una clave ausente como para una clave que guarda `None`.
- `resolve()` delega en `get()` y lanza `KeyError` cuando el resultado es `None`, lo
  que incluye el caso de un valor que realmente es `None`.

### `ScopedContext`

```python
class ScopedContext:
    _active_scope: contextvars.ContextVar[object | None] = contextvars.ContextVar(
        "x-orionis-container-context-scope",
        default=None,
    )

    @classmethod
    def getCurrentScope(cls) -> object | None: ...
    @classmethod
    def setCurrentScope(cls, scope: object) -> contextvars.Token: ...
    @classmethod
    def reset(cls, token: contextvars.Token) -> None: ...
```

Envoltorio mínimo sobre un único `ContextVar` llamado
`"x-orionis-container-context-scope"`, con valor por defecto `None`.

El módulo expone además tres atajos ligados directamente a los métodos del
`ContextVar`:

```python
get_current_scope = ScopedContext._active_scope.get
set_current_scope = ScopedContext._active_scope.set
reset_scope       = ScopedContext._active_scope.reset
```

`Container` usa `get_current_scope` internamente.

### `CircularDependencyException`

```python
class CircularDependencyException(Exception): ...
```

La lanza `Container` durante el autowiring cuando un tipo ya está presente en la pila
de resolución de la tarea actual. El mensaje nombra el tipo culpable, por ejemplo
`Circular dependency detected while resolving argument '__main__.NodeB'.`

### `ServiceProvider`

```python
class ServiceProvider(IServiceProvider):
    def __init__(self, app: IApplication) -> None: ...
    def register(self) -> None: ...
    async def boot(self) -> None: ...
```

Clase base de los proveedores. El constructor guarda el contenedor en `self.app`. Los
dos hooks del ciclo de vida están vacíos en la clase base, así que las subclases
sobrescriben solo lo que necesitan: `register()` es síncrono y está pensado para los
bindings; `boot()` es una corrutina y se ejecuta después del registro.

### `DeferrableProvider`

```python
class DeferrableProvider(IDeferrableProvider):
    @classmethod
    def provides(cls) -> list[type | str]: ...
```

Clase base marcadora para proveedores que deben registrarse bajo demanda. El
`provides()` base lanza `NotImplementedError("Subclasses must implement the provides
method.")`.

`provides()` solo declara qué tipos o alias son responsabilidad del proveedor. El
registro que lee `Container.__resolveDeferredProvider` — `_deferred_providers`, que
asocia una clave con `{"module": ..., "class": ...}` — lo puebla
`orionis.foundation.application.Application.create()`, no esta clase.

### `IServiceProvider`

Clase base abstracta que declara exactamente `register` (síncrono) y `boot` (corrutina).

### `IDeferrableProvider`

Clase base abstracta que declara exactamente el classmethod `provides`.

### `Facade`

```python
class Facade(metaclass=FacadeMeta):
    _application: IApplication | None = None
    _pinned_instance: Any = None

    @classmethod
    def getFacadeAccessor(cls) -> str: ...
    @classmethod
    async def resolve(cls, *args: object, **kwargs: object) -> object: ...
    @classmethod
    async def pin(cls) -> None: ...
    @classmethod
    def unpin(cls) -> None: ...
```

Clase base de proxy estático.

- `getFacadeAccessor()` debe sobrescribirse; la implementación base lanza
  `NotImplementedError` con el mensaje `Class <Name> must define
  getFacadeAccessor()`.
- `resolve()` crea `orionis.foundation.application.Application()` de forma perezosa
  cuando `_application` es `None`, lanza `RuntimeError("Application not booted. Boot
  your app first.")` cuando la aplicación reporta `isBooted` como falso, y en caso
  contrario devuelve `await application.make(cls.getFacadeAccessor(), *args,
  **kwargs)`.
- `pin()` guarda la instancia resuelta en `_pinned_instance`.
- `unpin()` devuelve `_pinned_instance` a `None`.

`_application` y `_pinned_instance` son **atributos de clase**, así que los comparte
todo el que use esa clase de facade dentro del proceso.

### `FacadeMeta`

```python
class FacadeMeta(type):
    def __getattr__(cls, name: str) -> object: ...
```

Metaclase que gobierna el acceso a atributos en las clases facade. Python solo llama a
`__getattr__` cuando la búsqueda normal falla, así que los métodos reales y los
atributos de clase declarados en una subclase de facade la esquivan por completo.

- Cuando `cls._pinned_instance` no es `None`, el atributo se toma directamente del
  objeto pineado; un nombre inexistente lanza `AttributeError` como siempre.
- En caso contrario se devuelve una función `dispatcher` síncrona normal. Los
  dispatchers se memoizan en el diccionario de módulo `_dispatcher_cache`, indexado por
  `(cls, name)`, así que accesos repetidos devuelven el objeto idéntico.

Llamar a un dispatcher construye un `_FacadeDispatch`:

```python
class _FacadeDispatch:
    __slots__ = ("_args", "_cls", "_context", "_kwargs", "_name")

    def __await__(self) -> Generator[object, None, object]: ...
    async def __aenter__(self) -> object: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool: ...
```

`_FacadeDispatch` es privado. Construirlo no toca el contenedor; la resolución ocurre
cuando el objeto se awaita o se entra:

- Al awaitarlo se resuelve el servicio, se lee el atributo, se llama si es invocable y
  se awaita el resultado si es awaitable. Un atributo no invocable se devuelve tal
  cual, y por eso `await SomeFacade.attribute()` entrega el valor plano.
- `async with` resuelve el servicio, llama al atributo y delega en el `__aenter__` /
  `__aexit__` del objeto devuelto. `__aexit__` exige un `__aenter__` previo.

### `IFacade`

Clase base abstracta que declara exactamente `getFacadeAccessor`, `resolve`, `pin` y
`unpin`, todos como classmethods; `resolve` y `pin` son corrutinas.

### Exportaciones del paquete

`orionis/container/__init__.py` y `orionis/container/context/__init__.py` están vacíos;
hay que importar desde los módulos concretos. Los demás subpaquetes reexportan un
nombre público cada uno:

| Módulo | `__all__` |
|---|---|
| `orionis.container.contracts` | `IFacade` |
| `orionis.container.entities` | `Binding` |
| `orionis.container.enums` | `Lifetime` |
| `orionis.container.exceptions` | `CircularDependencyException` |
| `orionis.container.facades` | `Facade` |
| `orionis.container.providers` | `DeferrableProvider`, `ServiceProvider` |

---

## Ejemplos de uso

Cada fragmento de abajo es un script completo y ejecutable. La salida mostrada se
capturó ejecutándolos.

### Registrar y resolver servicios

```python
import asyncio

from orionis.container.container import Container


class IClock:
    """Contract implemented by every clock service."""


class SystemClock(IClock):
    """Clock returning a fixed timestamp."""

    def now(self) -> str:
        return "2026-09-01T00:00:00Z"


class Reporter:
    """Service whose constructor declares an IClock dependency."""

    def __init__(self, clock: IClock) -> None:
        self.clock = clock


async def main() -> None:
    container = Container()

    container.singleton(IClock, SystemClock, alias="clock")
    container.transient(None, Reporter)

    clock = await container.make(IClock)
    print(type(clock).__name__, clock.now())

    # An alias resolves to exactly the same singleton instance.
    print("alias hits the singleton:", await container.make("clock") is clock)

    # Reporter is transient and its IClock argument is injected automatically.
    reporter = await container.make(Reporter)
    print("injected dependency:", type(reporter.clock).__name__)
    print("transient reuse:", await container.make(Reporter) is reporter)

    # build() always constructs a new object, even for singleton bindings.
    print("build returns a new object:", await container.build(SystemClock) is not clock)

    print("bound(IClock):", container.bound(IClock))
    print("bound('clock'):", container.bound("clock"))
    print("bound('missing'):", container.bound("missing"))


asyncio.run(main())
```

```text
SystemClock 2026-09-01T00:00:00Z
alias hits the singleton: True
injected dependency: SystemClock
transient reuse: False
build returns a new object: True
bound(IClock): True
bound('clock'): True
bound('missing'): False
```

### Trabajar con scopes

```python
import asyncio

from orionis.container.container import Container


class RequestState:
    """Service that must live for exactly one scope."""


async def main() -> None:
    container = Container()
    container.scoped(None, RequestState)

    print("scope before:", container.getCurrentScope())

    async with container.beginScope() as scope:
        first = await container.make(RequestState)
        second = await container.make(RequestState)
        print("same instance inside the scope:", first is second)
        print("scope is active:", container.getCurrentScope() is scope)

        # Instances registered while a scope is active land in that scope.
        container.instance(None, "request-id-42")
        print("scoped instance:", await container.make(str))

    print("scope after:", container.getCurrentScope())

    async with container.beginScope():
        third = await container.make(RequestState)
        print("new scope, new instance:", third is first)


asyncio.run(main())
```

```text
scope before: None
same instance inside the scope: True
scope is active: True
scoped instance: request-id-42
scope after: None
new scope, new instance: False
```

### Manejo de errores de resolución

```python
import asyncio

from orionis.container.container import Container
from orionis.container.exceptions.container import CircularDependencyException


class RequestState:
    """Scoped service used to trigger the missing-scope error."""


class NodeA:
    """First node of the dependency cycle."""


class NodeB:
    """Second node of the dependency cycle."""

    def __init__(self, a: NodeA) -> None:
        self.a = a


def _node_a_init(self, b: NodeB) -> None:
    self.b = b


# Closing the cycle after both classes exist keeps the annotations resolvable.
NodeA.__init__ = _node_a_init


class NeedsPort:
    """Service asking for a builtin type the container cannot invent."""

    def __init__(self, port: int) -> None:
        self.port = port


class IClockLike:
    """Contract that RequestState does not implement."""


async def main() -> None:
    container = Container()

    try:
        await container.make("missing-service")
    except ValueError as exc:
        print(f"ValueError: {exc}")

    container.scoped(None, RequestState)
    try:
        await container.make(RequestState)
    except RuntimeError as exc:
        print(f"RuntimeError: {exc}")

    try:
        await container.build(NodeB)
    except CircularDependencyException as exc:
        print(f"CircularDependencyException: {exc}")

    try:
        await container.build(NeedsPort)
    except TypeError as exc:
        print(f"TypeError: {exc}")

    try:
        container.transient(IClockLike, RequestState)
    except TypeError as exc:
        print(f"TypeError: {exc}")

    try:
        container.transient(None, RequestState, alias="   ")
    except ValueError as exc:
        print(f"ValueError: {exc}")


asyncio.run(main())
```

```text
ValueError: Service 'missing-service' is not registered.
RuntimeError: No active scope for scoped service. Use 'beginScope()' to create a scope.
CircularDependencyException: Circular dependency detected while resolving argument '__main__.NodeB'.
TypeError: Cannot auto-resolve built-in type 'int' for parameter 'port'. Provide a default value.
TypeError: RequestState must implement IClockLike
ValueError: Alias cannot be empty.
```

### Construir un service provider

```python
import asyncio

from orionis.container.container import Container
from orionis.container.providers.deferrable_provider import DeferrableProvider
from orionis.container.providers.service_provider import ServiceProvider


class IMailer:
    """Contract for the mail transport."""


class SmtpMailer(IMailer):
    """Concrete mail transport."""

    def send(self, to: str) -> str:
        return f"sent to {to}"


class MailProvider(ServiceProvider):
    """Register and boot the mail transport."""

    def register(self) -> None:
        self.app.singleton(IMailer, SmtpMailer, alias="mailer")

    async def boot(self) -> None:
        mailer = await self.app.make(IMailer)
        print("booted with:", type(mailer).__name__)


class DeferredMailProvider(MailProvider, DeferrableProvider):
    """Same provider, but registered only when its services are requested."""

    @classmethod
    def provides(cls) -> list[type | str]:
        return [IMailer, "mailer"]


async def main() -> None:
    container = Container()

    provider = MailProvider(container)
    provider.register()
    await provider.boot()

    print("bound('mailer'):", container.bound("mailer"))
    mailer = await container.make("mailer")
    print(mailer.send("ops@example.com"))

    print("declared services:", DeferredMailProvider.provides())

    try:
        DeferrableProvider.provides()
    except NotImplementedError as exc:
        print(f"NotImplementedError: {exc}")


asyncio.run(main())
```

```text
booted with: SmtpMailer
bound('mailer'): True
sent to ops@example.com
declared services: [<class '__main__.IMailer'>, 'mailer']
NotImplementedError: Subclasses must implement the provides method.
```

### Exponer un servicio con una facade

```python
import asyncio

from orionis.container.container import Container
from orionis.container.facades.facade import Facade


class Cache:
    """Service reachable through the facade."""

    driver = "memory"

    def get(self, key: str) -> str:
        return f"value:{key}"


class CacheFacade(Facade):
    """Static proxy for the cache service."""

    @classmethod
    def getFacadeAccessor(cls) -> str:
        return "cache"


class BootedApplication(Container):
    """Container double reporting itself as booted."""

    isBooted = True


async def main() -> None:
    app = BootedApplication()
    app.singleton(None, Cache, alias="cache")

    # Facade.resolve() reads the shared application from the class attribute.
    CacheFacade._application = app

    # Without a pinned instance every attribute access returns a dispatcher
    # that only touches the container once it is awaited.
    dispatcher = CacheFacade.get
    print("dispatcher is cached:", dispatcher is CacheFacade.get)
    print("await a method:", await CacheFacade.get("users"))
    print("await an attribute:", await CacheFacade.driver())

    # After pin() the facade forwards attribute access directly.
    await CacheFacade.pin()
    print("pinned method call:", CacheFacade.get("users"))
    print("pinned attribute:", CacheFacade.driver)

    CacheFacade.unpin()
    print("pinned instance cleared:", CacheFacade._pinned_instance)

    try:
        Facade.getFacadeAccessor()
    except NotImplementedError as exc:
        print(f"NotImplementedError: {exc}")


asyncio.run(main())
```

```text
dispatcher is cached: True
await a method: value:users
await an attribute: memory
pinned method call: value:users
pinned attribute: memory
pinned instance cleared: None
NotImplementedError: Class Facade must define getFacadeAccessor()
```

### Inspeccionar bindings y scopes

```python
import asyncio

from orionis.container.context.manager import ScopeManager
from orionis.container.context.scope import ScopedContext
from orionis.container.entities.binding import Binding
from orionis.container.enums.lifetimes import Lifetime


class IClock:
    """Contract stored in the binding."""


class SystemClock(IClock):
    """Implementation stored in the binding."""


def describe_binding() -> None:
    binding = Binding(
        contract=IClock,
        concrete=SystemClock,
        lifetime=Lifetime.SINGLETON,
        alias="clock",
    )
    print("lifetime:", binding.lifetime)
    print("serialised:", binding.toDict())
    print("fields:", [field["name"] for field in binding.getFields()])

    try:
        Binding(lifetime="singleton")
    except TypeError as exc:
        print(f"TypeError: {exc}")


async def describe_scope_manager() -> None:
    manager = ScopeManager()
    manager.set("config", {"debug": True})
    print("subscript:", manager["config"])
    print("membership:", "config" in manager)
    print("await get:", await manager.get("config"))
    print("missing get:", await manager.get("absent"))

    try:
        await manager.resolve("absent")
    except KeyError as exc:
        print(f"KeyError: {exc}")

    manager.clear()
    print("after clear:", "config" in manager, manager["config"])


def describe_scoped_context() -> None:
    print("initial scope:", ScopedContext.getCurrentScope())
    token = ScopedContext.setCurrentScope("outer")
    print("after set:", ScopedContext.getCurrentScope())
    ScopedContext.reset(token)
    print("after reset:", ScopedContext.getCurrentScope())


describe_binding()
asyncio.run(describe_scope_manager())
describe_scoped_context()
```

```text
lifetime: Lifetime.SINGLETON
serialised: {'contract': <class '__main__.IClock'>, 'concrete': <class '__main__.SystemClock'>, 'instance': None, 'lifetime': 2, 'alias': 'clock'}
fields: ['contract', 'concrete', 'instance', 'lifetime', 'alias']
TypeError: The 'lifetime' attribute must be an instance of 'Lifetime', but received type 'str'.
subscript: {'debug': True}
membership: True
await get: {'debug': True}
missing get: None
KeyError: "Instance for key 'absent' not found in scope"
after clear: False None
initial scope: None
after set: outer
after reset: None
```

### Resolver de forma concurrente

```python
import asyncio

from orionis.container.container import Container


class Config:
    """Singleton whose construction suspends before returning."""

    constructions = 0

    def __init__(self) -> None:
        Config.constructions += 1


class Report:
    """Service depending on a type published by a deferred provider."""

    def __init__(self, config: Config) -> None:
        self.config = config


class ConfigProvider:
    """Deferred provider that suspends while booting."""

    container: Container | None = None
    registrations = 0

    def register(self) -> None:
        ConfigProvider.registrations += 1
        ConfigProvider.container.singleton(None, Config)

    async def boot(self) -> None:
        await asyncio.sleep(0)


CONFIG_KEY = f"{Config.__module__}.{Config.__name__}"


async def main() -> None:
    container = Container()
    ConfigProvider.container = container

    # The bootstrap layer normally fills this registry; here it is explicit.
    container._deferred_providers = {
        CONFIG_KEY: {"module": __name__, "class": "ConfigProvider"},
    }

    reports = await asyncio.gather(*(container.build(Report)
                                     for _ in range(8)))

    print("reports built:", len(reports))
    print("provider registrations:", ConfigProvider.registrations)
    print("Config constructions:", Config.constructions)
    print("shared singleton:", len({id(r.config) for r in reports}))


asyncio.run(main())
```

```text
reports built: 8
provider registrations: 1
Config constructions: 1
shared singleton: 1
```

---

## Consideraciones de rendimiento y concurrencia

- **La creación del singleton está protegida por lock.** `Container.__new__` lee
  `_instances` sin el lock primero y solo adquiere el `threading.RLock` cuando falla,
  revisando de nuevo dentro de la sección crítica. Verificado: 32 hilos construyendo la
  misma subclase a la vez observan una única instancia.
- **La construcción de una sola vez se serializa por clave dentro de un loop.** Las
  creaciones `SINGLETON` y `SCOPED` y el arranque de proveedores diferidos corren bajo
  un `asyncio.Lock` obtenido de `__creationLock`, revisando la caché de nuevo tras
  adquirirlo. Verificado: ocho tareas resolviendo el mismo singleton sin cachear (cuya
  construcción se suspende) producen una instancia y una sola llamada al constructor;
  lo mismo vale para un servicio scoped dentro de un scope, y un proveedor diferido se
  registra exactamente una vez.
- **Los locks pertenecen al loop que los creó.** `__creation_locks` guarda el loop en
  ejecución junto a cada lock y reemplaza la entrada cuando otro loop pide la misma
  clave, así que un lock nunca se awaita desde un loop ajeno. Dos loops sobre el mismo
  contenedor se serializan por separado, no entre sí.
- **Los caminos rápidos nunca toman un lock.** Un acierto de caché, un acierto de
  scope, un binding transitorio y una clave que no es diferida retornan antes de pedir
  cualquier lock.
- **La construcción anidada no produce deadlock.** Cada contrato tiene su propio lock, y
  un tipo concreto que ya está en la pila de resolución se salta el lock por completo,
  así que un ciclo de dependencias sigue apareciendo como
  `CircularDependencyException` en lugar de bloquearse.
- **El registro no está protegido.** Salvo `__new__`, el módulo no declara
  sincronización para `_deferred_providers`, la tabla de bindings, la tabla de alias ni
  la caché de singletons: son diccionarios normales que se mutan in situ, así que el
  registro está pensado para el arranque y no para ejecutarse concurrentemente desde
  varios hilos del SO.
- **El aislamiento entre tareas viene de `contextvars`.** Tanto el scope activo
  (`"x-orionis-container-context-scope"`) como la pila de dependencias circulares
  (`"x-orionis-resolution-stack"`) son `ContextVar`s, así que tareas asyncio
  concurrentes nunca comparten ese estado. La pila de ciclos se apila con un token y se
  restaura en un bloque `finally`, así que una resolución fallida no deja residuos.
- **`make()` tiene camino rápido.** Una clave que no es cadena y ya está en la caché de
  singletons retorna antes de ejecutar cualquier búsqueda de alias, de proveedor
  diferido o de scope.
- **Los proveedores diferidos se ejecutan una vez por clave.** Las claves resueltas se
  anotan en un conjunto, y el registro se consulta antes que ese conjunto para que los
  tipos no diferidos salgan tras una única búsqueda en diccionario.
- **La reflexión se cachea aguas arriba.** La inspección de firmas se delega en
  `orionis.introspection`, cuyos helpers `_get_signature` y `_get_resolved_signature`
  están envueltos en `functools.lru_cache(maxsize=1024)` indexados por el objeto
  destino.
- **Los dispatchers de facade se cachean para siempre.** `_dispatcher_cache` es un
  diccionario de módulo indexado por `(clase_facade, nombre_atributo)` sin desalojo,
  así que cada entrada mantiene una referencia fuerte a la clase facade durante toda la
  vida del proceso.
- **Pinear elimina una resolución por llamada.** Mientras `_pinned_instance` está
  puesto, el acceso a atributos es un `getattr` directo sobre el objeto cacheado; sin
  pinear, cada await delega en el contenedor.
- **`ScopeManager.get()` memoiza los valores awaitados.** Una corrutina almacenada se
  promueve a `asyncio.Task`, se awaita una vez y se sustituye por su resultado.

---

## Notas de compatibilidad

- **Python:** `requires-python = ">=3.14"` en `pyproject.toml`. El módulo usa
  `typing.Self`, uniones `X | Y` y la evaluación diferida de anotaciones de PEP 649.
- **Dependencias de runtime:** solo la biblioteca estándar (`contextvars`,
  `importlib`, `inspect`, `threading`, `collections`, `abc`, `dataclasses`, `enum`,
  `asyncio`), más los módulos hermanos de Orionis `orionis.introspection`,
  `orionis.schemas`, `orionis.http` y `orionis.support.entities`. No hay nada extra que
  instalar más allá de `pip install orionis`.
- **Coste de import:** `container.py` importa `orionis.http.request.Request` y
  `orionis.schemas.validator.Schema` a nivel de módulo, así que importar el contenedor
  arrastra también esas capas.
- **No uses `from __future__ import annotations` en las clases que construye el
  contenedor.** Con ese import las anotaciones del constructor quedan como cadenas y la
  capa de reflexión las trata como forward references de tipo `str`; el contenedor
  inyecta entonces un `str` en lugar de la dependencia esperada. Verificado: un
  servicio anotado `def __init__(self, repo: Repo)` dentro de un módulo con el future
  import recibe un `str`. Los módulos que confían en PEP 649 (el comportamiento por
  defecto en 3.14) inyectan correctamente.
- **`Application` es el contenedor real.** `orionis.foundation.application.Application`
  hereda de `Container`, así que el singleton del framework devuelto por
  `Application()` posee los bindings usados en runtime, y `Facade.resolve()` llega a él
  automáticamente.
- **Los módulos de contratos usan anotaciones en texto.** `contracts/container.py`,
  `contracts/service_provider.py` y `contracts/deferrable_provider.py` declaran
  `from __future__ import annotations`; compararlos contra las implementaciones debe
  hacerse por nombres de parámetros, no por objetos de anotación resueltos.

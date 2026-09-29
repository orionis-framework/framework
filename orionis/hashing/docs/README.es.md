# Orionis Hashing (`orionis.hashing`)

> Servicio de hashing de contraseñas con drivers intercambiables (Argon2id y
> bcrypt) que quema su coste en un hilo de trabajo, expuesto mediante el
> contrato `IHashManager` y la facade `Hash`.
>
> 🇬🇧 English version: [README.md](README.md)

## Tabla de contenidos

- [Descripción funcional](#descripción-funcional)
  - [Dónde encaja](#dónde-encaja)
  - [Mapa del módulo](#mapa-del-módulo)
  - [Configuración](#configuración)
  - [Notas de diseño](#notas-de-diseño)
- [Referencia de API](#referencia-de-api)
  - [`IHasher`](#ihasher)
  - [`IHashManager`](#ihashmanager)
  - [`HashManager`](#hashmanager)
    - [`HashManager.__init__()`](#hashmanager__init__)
    - [`HashManager.driver()`](#hashmanagerdriver)
    - [`HashManager.getDefaultDriver()`](#hashmanagergetdefaultdriver)
    - [`HashManager.make()`](#hashmanagermake)
    - [`HashManager.check()`](#hashmanagercheck)
    - [`HashManager.needsRehash()`](#hashmanagerneedsrehash)
    - [`HashManager.getAlgorithm()`](#hashmanagergetalgorithm)
    - [`HashManager.setRounds()`](#hashmanagersetrounds)
    - [`HashManager._build()`](#hashmanager_build)
  - [`Argon2Hasher`](#argon2hasher)
    - [Constantes del módulo Argon2](#constantes-del-módulo-argon2)
    - [`Argon2Hasher.__init__()`](#argon2hasher__init__)
    - [`Argon2Hasher.make()`](#argon2hashermake)
    - [`Argon2Hasher.check()`](#argon2hashercheck)
    - [`Argon2Hasher.needsRehash()`](#argon2hasherneedsrehash)
    - [`Argon2Hasher.getAlgorithm()`](#argon2hashergetalgorithm)
    - [Setters fluidos de Argon2](#setters-fluidos-de-argon2)
    - [Helpers internos de Argon2](#helpers-internos-de-argon2)
  - [`BcryptHasher`](#bcrypthasher)
    - [Constantes del módulo bcrypt](#constantes-del-módulo-bcrypt)
    - [`BcryptHasher.__init__()`](#bcrypthasher__init__)
    - [`BcryptHasher.make()`](#bcrypthashermake)
    - [`BcryptHasher.check()`](#bcrypthashercheck)
    - [`BcryptHasher.needsRehash()`](#bcrypthasherneedsrehash)
    - [`BcryptHasher.getAlgorithm()`](#bcrypthashergetalgorithm)
    - [`BcryptHasher.setRounds()`](#bcrypthashersetrounds)
    - [Helpers internos de bcrypt](#helpers-internos-de-bcrypt)
  - [`import_hasher_backend()`](#import_hasher_backend)
  - [Excepciones](#excepciones)
  - [`HashProvider`](#hashprovider)
  - [Facade `Hash`](#facade-hash)
- [Ejemplos de uso](#ejemplos-de-uso)
  - [Hashear y verificar una contraseña](#hashear-y-verificar-una-contraseña)
  - [Elegir driver y ajustar el coste](#elegir-driver-y-ajustar-el-coste)
  - [Manejo de errores](#manejo-de-errores)
  - [Migrar un hash heredado](#migrar-un-hash-heredado)
  - [Resolver el servicio y la facade](#resolver-el-servicio-y-la-facade)
- [Consideraciones de rendimiento y concurrencia](#consideraciones-de-rendimiento-y-concurrencia)
- [Notas de compatibilidad](#notas-de-compatibilidad)

## Descripción funcional

`orionis.hashing` almacena y verifica contraseñas. `HashManager` lee la sección
de configuración `hashing`, resuelve el driver configurado —`Argon2Hasher`
(Argon2id) o `BcryptHasher`— y expone las mismas cinco operaciones que un driver
individual, de modo que el código de la aplicación nunca nombra un algoritmo. El
hash codificado lleva consigo su propio algoritmo, sus parámetros y su sal, y eso
es lo que permite que `check()` y `needsRehash()` funcionen aunque cambie la
configuración.

### Dónde encaja

| Componente | Relación |
|---|---|
| `orionis.foundation.contracts.application.IApplication` | Se lee una sola vez en `HashManager.__init__` mediante `app.config("hashing")`. |
| `orionis.foundation.config.hashing.entities.hashing.Hashing` | Entidad de configuración que el manager construye a partir de la sección cruda. |
| `orionis.foundation.config.hashing.enums.drivers.Drivers` | Catálogo de drivers (`argon2`, `bcrypt`) que compara `HashManager._build`. |
| `orionis.foundation.core_config.CORE_CONFIG` | Incluye la sección `hashing`, así que el manager siempre encuentra su configuración. |
| `orionis.foundation.core_providers.CORE_PROVIDERS` | Contiene `HashProvider`, por lo que `IHashManager` queda vinculado en el arranque. |
| `orionis.container.providers.service_provider.ServiceProvider` | Clase base de `HashProvider`. |
| `orionis.support.facades.hash.Hash` | Facade cuyo accessor es `IHashManager`; la fija `HashProvider.boot()`. |
| `pwdlib` | Backend de terceros que aporta las primitivas reales de Argon2id y bcrypt. |

### Mapa del módulo

| Archivo | Contenido |
|---|---|
| `orionis/hashing/__init__.py` | Exporta `Argon2Hasher`, `BcryptHasher` y `HashManager`. |
| `orionis/hashing/hash_manager.py` | `HashManager`, el punto de entrada agnóstico del algoritmo. |
| `orionis/hashing/exceptions.py` | `HashException` y sus tres subclases especializadas. |
| `orionis/hashing/provider.py` | `HashProvider`. |
| `orionis/hashing/contracts/__init__.py` | Exporta `IHashManager` e `IHasher`. |
| `orionis/hashing/contracts/hasher.py` | Contrato abstracto `IHasher`. |
| `orionis/hashing/contracts/hash_manager.py` | `IHashManager`, que extiende `IHasher`. |
| `orionis/hashing/hashers/__init__.py` | Exporta `Argon2Hasher` y `BcryptHasher`. |
| `orionis/hashing/hashers/argon2_hasher.py` | Driver Argon2id y sus constantes de coste por defecto. |
| `orionis/hashing/hashers/bcrypt_hasher.py` | Driver bcrypt y sus límites de coste. |
| `orionis/hashing/hashers/functions.py` | `import_hasher_backend`, el importador perezoso del backend. |

### Configuración

`HashManager` lee una única sección. Con la configuración incluida en este
repositorio, `app.config("hashing")` devuelve:

```python
{
    "driver": "argon2",
    "argon2": {"memory": 65536, "threads": 4, "time": 3},
    "bcrypt": {"rounds": 12},
}
```

| Clave | Variable de entorno | Valor por defecto | Validación |
|---|---|---|---|
| `hashing.driver` | `HASH_DRIVER` | `"argon2"` | Debe ser un miembro de `Drivers` o uno de `"argon2"` / `"bcrypt"`. |
| `hashing.argon2.memory` | `ARGON_MEMORY` | `65536` | Entero ≥ 1 (kibibytes). |
| `hashing.argon2.threads` | `ARGON_THREADS` | `4` | Entero ≥ 1 (carriles). |
| `hashing.argon2.time` | `ARGON_TIME` | `3` | Entero ≥ 1 (iteraciones). |
| `hashing.bcrypt.rounds` | `BCRYPT_ROUNDS` | `12` | Entero entre `4` y `31`. |

La validación de las entidades vive en
`orionis/foundation/config/hashing/entities/` y lanza `TypeError` / `ValueError`;
los drivers vuelven a validar los mismos rangos y lanzan
`HashConfigurationException`.

Cuando la aplicación no expone ninguna sección `hashing` —`config()` resuelve una
clave desconocida a `None`— el manager recurre a los valores por defecto que
declara la entidad `Hashing`.

### Notas de diseño

- `HashManager` declara `__slots__ = ("_config", "_default", "_drivers")`, y
  tanto `IHasher` como `IHashManager` declaran `__slots__ = ()`, así que ni el
  manager ni los drivers arrastran diccionario de atributos.
- `IHashManager` **extiende** `IHasher` en lugar de duplicarlo, de modo que el
  manager puede sustituir a un driver individual en cualquier punto.
- Los drivers se crean de forma perezosa y se cachean en `_drivers`, indexados
  por nombre, así que cada algoritmo se instancia como mucho una vez por manager.
- El paquete del backend se importa en el primer uso mediante
  `import_hasher_backend`, por lo que ambos drivers siguen siendo construibles
  aunque falte la dependencia opcional; el fallo aflora solo cuando el driver se
  usa de verdad.
- Cada driver cachea una instancia de backend construida con sus costes
  configurados y la descarta cuando un setter fluido cambia un coste; los
  overrides por llamada construyen un backend desechable y nunca tocan el
  cacheado.
- `HashProvider` vincula `IHashManager` como **singleton**, así que toda la
  aplicación comparte un manager y, por tanto, un backend por algoritmo.
- `HashProvider` es un `ServiceProvider` normal, no diferido, de modo que su
  `boot()` corre en el arranque de la aplicación y la facade `Hash` queda fijada
  antes de atender ninguna petición. Los miembros que siguen siendo síncronos
  —`needsRehash()`, `getAlgorithm()`, `setRounds()` y `driver()`— dependen de
  ello.
- `make()` y `check()` son las únicas operaciones costosas, y ambas ejecutan su
  trabajo bloqueante mediante `asyncio.to_thread`, así que un login nunca frena
  las demás peticiones atendidas por el mismo worker.

## Referencia de API

### `IHasher`

Ubicación: `orionis/hashing/contracts/hasher.py`. También se reexporta desde
`orionis.hashing.contracts`.

```python
class IHasher(ABC):

    __slots__ = ()

    @abstractmethod
    async def make(
        self,
        value: str,
        *,
        rounds: int | None = None,
        memory: int | None = None,
        threads: int | None = None,
    ) -> str: ...

    @abstractmethod
    async def check(self, value: str, hashed: str) -> bool: ...

    @abstractmethod
    def needsRehash(self, hashed: str) -> bool: ...

    @abstractmethod
    def getAlgorithm(self) -> str: ...

    @abstractmethod
    def setRounds(self, rounds: int) -> Self: ...
```

Miembros abstractos: `make`, `check`, `needsRehash`, `getAlgorithm` y
`setRounds`. Los cinco se declaran sin cuerpo, así que una subclase que no los
implemente no puede instanciarse. `make` y `check` son **funciones corrutina**:
cargan con el coste del algoritmo y hay que awaitarlas. El docstring indica que
las implementaciones deben apoyarse en algoritmos diseñados para almacenar
contraseñas y nunca en digests de propósito general como MD5 o la familia SHA.

`__slots__ = ()` implica que las subclases que declaren sus propios `__slots__`
quedan libres de un `__dict__` por instancia.

### `IHashManager`

Ubicación: `orionis/hashing/contracts/hash_manager.py`. También se reexporta
desde `orionis.hashing.contracts`.

```python
class IHashManager(IHasher):

    __slots__ = ()

    @abstractmethod
    def driver(self, name: str | None = None) -> IHasher: ...

    @abstractmethod
    def getDefaultDriver(self) -> str: ...
```

Añade exactamente dos miembros abstractos a los cinco heredados de `IHasher`.
Este es el contrato que se usa como clave del contenedor y como accessor de la
facade `Hash`.

### `HashManager`

Ubicación: `orionis/hashing/hash_manager.py`. Única implementación de
`IHashManager` que incluye el framework.

```python
class HashManager(IHashManager):

    __slots__ = ("_config", "_default", "_drivers")
```

Atributos de instancia, todos asignados en `__init__`:

| Atributo | Tipo | Significado |
|---|---|---|
| `_config` | `Hashing` | Entidad de configuración, construida a partir de la sección cruda cuando esta es un `dict`. |
| `_default` | `str` | Nombre del driver por defecto configurado. |
| `_drivers` | `dict[str, IHasher]` | Caché de drivers ya construidos, indexada por nombre. |

#### `HashManager.__init__()`

```python
def __init__(self, app: IApplication) -> None:
```

| Parámetro | Tipo | Descripción |
|---|---|---|
| `app` | `IApplication` | Objeto que da acceso a la configuración. Solo se lee `app.config("hashing")`; no hay comprobación `isinstance`, así que sirve cualquier objeto que exponga `config(path)`. |

**Devuelve:** `None`.

**Comportamiento:** cuando la sección es un `dict` se expande en una entidad
`Hashing` (`Hashing(**config_data)`); cualquier otro valor se guarda tal cual, y
por eso se acepta una entidad ya construida. Una sección ausente —`None`— se
sustituye por un mapping vacío, así que el manager recurre a los valores por
defecto de la entidad en lugar de fallar en la primera operación. `_default` es
`str(self._config.driver)`.

**Efectos secundarios:** ninguno más allá de leer la configuración. Aquí no se
construye ningún driver, no hay registro en el contenedor y la configuración se
lee una sola vez: los cambios posteriores en la configuración de la aplicación no
se observan.

#### `HashManager.driver()`

```python
def driver(self, name: str | None = None) -> IHasher:
```

| Parámetro | Tipo | Descripción |
|---|---|---|
| `name` | `str \| None` | Nombre del driver (`'argon2'` o `'bcrypt'`). `None` selecciona el driver por defecto configurado. |

**Devuelve:** `IHasher` — la instancia del driver, creada en el primer acceso y
cacheada después.

**Lanza:** `HashDriverNotSupportedException` cuando el driver solicitado no tiene
implementación.

**Comportamiento:** la resolución es `name or self._default`, así que cualquier
valor falsy —tanto `None` como la cadena vacía— selecciona el driver por defecto.
Llamadas repetidas con el mismo nombre resuelto devuelven exactamente la misma
instancia.

#### `HashManager.getDefaultDriver()`

```python
def getDefaultDriver(self) -> str:
```

**Devuelve:** `str` — el nombre del driver configurado, como `'argon2'` o
`'bcrypt'`. Es el valor de configuración, no el identificador de algoritmo que
devuelve `getAlgorithm()`.

#### `HashManager.make()`

```python
async def make(
    self,
    value: str,
    *,
    rounds: int | None = None,
    memory: int | None = None,
    threads: int | None = None,
) -> str:
```

| Parámetro | Tipo | Descripción |
|---|---|---|
| `value` | `str` | Valor en texto plano a hashear. |
| `rounds` | `int \| None` | Override de coste para esta llamada. |
| `memory` | `int \| None` | Override del coste de memoria para esta llamada, en kibibytes. |
| `threads` | `int \| None` | Override del paralelismo para esta llamada. |

**Devuelve:** `str` — el hash codificado producido por el driver por defecto.
Hay que awaitar la llamada.

**Lanza:** lo que lance el driver resuelto, en particular
`HashConfigurationException` ante un override inválido.

**Comportamiento:** la resolución del driver ocurre de forma síncrona antes de
la primera suspensión; después la llamada delega en `self.driver()`, así que los
overrides los interpreta el driver activo (ver
[`Argon2Hasher.make()`](#argon2hashermake) y
[`BcryptHasher.make()`](#bcrypthashermake)).

#### `HashManager.check()`

```python
async def check(self, value: str, hashed: str) -> bool:
```

| Parámetro | Tipo | Descripción |
|---|---|---|
| `value` | `str` | Valor en texto plano a verificar. |
| `hashed` | `str` | Hash generado previamente. |

**Devuelve:** `bool` — `True` cuando el valor coincide con el hash, `False` en
caso contrario. Un hash producido por otro algoritmo, un hash malformado y una
cadena vacía devuelven `False` en lugar de lanzar una excepción.

#### `HashManager.needsRehash()`

```python
def needsRehash(self, hashed: str) -> bool:
```

| Parámetro | Tipo | Descripción |
|---|---|---|
| `hashed` | `str` | Hash generado previamente. |

**Devuelve:** `bool` — `True` cuando el hash debe regenerarse con la
configuración actual. Un hash de otro algoritmo siempre devuelve `True`, que es
como se detecta una migración entre drivers.

#### `HashManager.getAlgorithm()`

```python
def getAlgorithm(self) -> str:
```

**Devuelve:** `str` — el identificador de algoritmo del driver por defecto:
`'argon2id'` o `'bcrypt'`.

#### `HashManager.setRounds()`

```python
def setRounds(self, rounds: int) -> Self:
```

| Parámetro | Tipo | Descripción |
|---|---|---|
| `rounds` | `int` | Nuevo factor de coste para el driver por defecto. |

**Devuelve:** `Self` — la misma instancia del manager, para configuración fluida.

**Lanza:** `HashConfigurationException` cuando el valor no es válido para el
driver activo.

**Efectos secundarios:** muta el driver por defecto cacheado, así que todas las
llamadas posteriores del manager —y de cualquier código que tenga ese driver—
usan el coste nuevo. Los hashes producidos antes del cambio siguen siendo
verificables y pasan a reportar `needsRehash() == True`.

#### `HashManager._build()`

```python
def _build(self, name: str) -> IHasher:
```

Fábrica interna que `driver()` invoca cuando falla la caché. Compara `name` con
`Drivers.ARGON2.value` y `Drivers.BCRYPT.value`, reenviando los parámetros de
coste configurados (`memory`, `threads`, `time` para Argon2id; `rounds` para
bcrypt). Cualquier otro nombre lanza `HashDriverNotSupportedException` con el
mensaje `Unsupported hashing driver: '<name>'. Must be one of ['argon2',
'bcrypt'].`

### `Argon2Hasher`

Ubicación: `orionis/hashing/hashers/argon2_hasher.py`. Driver por defecto del
framework; hashea con Argon2id.

```python
class Argon2Hasher(IHasher):

    __slots__ = ("_backend", "_backend_class", "_memory", "_threads", "_time")
```

| Atributo | Tipo | Significado |
|---|---|---|
| `_memory` | `int` | Coste de memoria configurado, en kibibytes. |
| `_threads` | `int` | Grado de paralelismo configurado. |
| `_time` | `int` | Número de iteraciones configurado. |
| `_backend_class` | `Any` | Clase del backend, `None` hasta el primer uso. |
| `_backend` | `Any` | Instancia del backend para los costes configurados, `None` hasta el primer uso. |

#### Constantes del módulo Argon2

| Nombre | Valor | Uso |
|---|---|---|
| `DEFAULT_MEMORY` | `65536` | Coste de memoria por defecto, en kibibytes. |
| `DEFAULT_THREADS` | `4` | Grado de paralelismo por defecto. |
| `DEFAULT_TIME` | `3` | Número de iteraciones por defecto. |
| `_BACKEND_MODULE` | `"pwdlib.hashers.argon2"` | Módulo importado en el primer uso. |
| `_BACKEND_CLASS` | `"Argon2Hasher"` | Clase del backend leída de ese módulo. |
| `_BACKEND_PACKAGE` | `"pwdlib[argon2]"` | Distribución reportada cuando falla la importación. |

#### `Argon2Hasher.__init__()`

```python
def __init__(
    self,
    *,
    memory: int = DEFAULT_MEMORY,
    threads: int = DEFAULT_THREADS,
    time: int = DEFAULT_TIME,
) -> None:
```

| Parámetro | Tipo | Descripción |
|---|---|---|
| `memory` | `int` | Coste de memoria en kibibytes. |
| `threads` | `int` | Grado de paralelismo. |
| `time` | `int` | Número de iteraciones. |

**Devuelve:** `None`.

**Lanza:** `HashConfigurationException` cuando un parámetro de coste no es un
entero mayor que cero. Los booleanos se rechazan explícitamente, aunque `bool`
sea subclase de `int`. El mensaje nombra la opción y su valor, por ejemplo
`The Argon2 'memory' option must be an integer greater than zero, got 0.`

**Efectos secundarios:** ninguno. Aquí no se importa ni se construye el backend.

#### `Argon2Hasher.make()`

```python
async def make(
    self,
    value: str,
    *,
    rounds: int | None = None,
    memory: int | None = None,
    threads: int | None = None,
) -> str:
```

| Parámetro | Tipo | Descripción |
|---|---|---|
| `value` | `str` | Valor en texto plano a hashear. |
| `rounds` | `int \| None` | Override del **coste temporal** para esta llamada. |
| `memory` | `int \| None` | Override del coste de memoria para esta llamada, en kibibytes. |
| `threads` | `int \| None` | Override del paralelismo para esta llamada. |

**Devuelve:** `str` — un hash Argon2id codificado como
`$argon2id$v=19$m=32,t=1,p=1$<salt>$<digest>`. Cada llamada genera una sal
aleatoria nueva, así que dos hashes del mismo valor nunca coinciden.

**Lanza:** `HashConfigurationException` cuando un override no es un entero
positivo. Los errores del backend se propagan sin traducir; por ejemplo, Argon2
exige `memory >= 8 * threads` y en caso contrario lanza
`argon2.exceptions.HashingError: Memory cost is too small`.

**Comportamiento:** toda la derivación corre en
`asyncio.to_thread(self._make, ...)`, así que los errores de validación y los
del backend afloran al awaitar la llamada. Sin overrides se reutiliza el backend
cacheado; con cualquier override se construye un backend desechable para esa
llamada y el cacheado queda intacto.

#### `Argon2Hasher.check()`

```python
async def check(self, value: str, hashed: str) -> bool:
```

**Devuelve:** `bool`. La verificación corre en
`asyncio.to_thread(self._check, ...)`. Responde `False` de inmediato cuando
`hashed` está vacío o cuando el backend no lo identifica como un hash Argon2; en
otro caso delega en el backend, que devuelve `False` ante una discrepancia en
lugar de lanzar. Se usan los costes codificados en el hash, así que un hash
producido con otra configuración también se verifica.

#### `Argon2Hasher.needsRehash()`

```python
def needsRehash(self, hashed: str) -> bool:
```

**Devuelve:** `bool`. Devuelve `True` cuando `hashed` está vacío o no es un hash
Argon2; en otro caso pregunta al backend si los parámetros codificados difieren
de los configurados.

#### `Argon2Hasher.getAlgorithm()`

```python
def getAlgorithm(self) -> str:
```

**Devuelve:** `str` — siempre `'argon2id'`.

#### Setters fluidos de Argon2

```python
def setRounds(self, rounds: int) -> Self:

def setMemory(self, memory: int) -> Self:

def setThreads(self, threads: int) -> Self:
```

`setRounds` fija el **coste temporal**, siguiendo el vocabulario del contrato
compartido. Los tres validan su argumento con la misma regla que `__init__`,
lanzan `HashConfigurationException` si falla, descartan el backend cacheado para
que el coste nuevo tenga efecto y devuelven la misma instancia.

#### Helpers internos de Argon2

| Método | Propósito |
|---|---|
| `_validate(name, value)` | `staticmethod` que exige "entero mayor que cero" y rechaza `bool`. |
| `_backendClass()` | Importa la clase del backend en el primer uso mediante `import_hasher_backend` y la cachea. |
| `_build(memory, threads, time)` | Construye una instancia del backend con `time_cost`, `memory_cost` y `parallelism`. |
| `_default()` | Devuelve el backend construido con los costes configurados, creándolo en el primer uso. |
| `_make(value, *, rounds, memory, threads)` | Cuerpo bloqueante de hashing que `make()` ejecuta en un hilo de trabajo. |
| `_check(value, hashed)` | Cuerpo bloqueante de verificación que `check()` ejecuta en un hilo de trabajo. |
| `_identify(hashed)` | Pregunta a la clase del backend si el hash pertenece a la familia Argon2. |

### `BcryptHasher`

Ubicación: `orionis/hashing/hashers/bcrypt_hasher.py`. Se mantiene por
interoperabilidad con aplicaciones que ya almacenan hashes bcrypt.

```python
class BcryptHasher(IHasher):

    __slots__ = ("_backend", "_backend_class", "_rounds")
```

| Atributo | Tipo | Significado |
|---|---|---|
| `_rounds` | `int` | Factor de coste configurado. |
| `_backend_class` | `Any` | Clase del backend, `None` hasta el primer uso. |
| `_backend` | `Any` | Instancia del backend para el coste configurado, `None` hasta el primer uso. |

#### Constantes del módulo bcrypt

| Nombre | Valor | Uso |
|---|---|---|
| `MIN_ROUNDS` | `4` | Límite inferior impuesto por bcrypt. |
| `MAX_ROUNDS` | `31` | Límite superior impuesto por bcrypt. |
| `DEFAULT_ROUNDS` | `12` | Factor de coste por defecto. |
| `_BACKEND_MODULE` | `"pwdlib.hashers.bcrypt"` | Módulo importado en el primer uso. |
| `_BACKEND_CLASS` | `"BcryptHasher"` | Clase del backend leída de ese módulo. |
| `_BACKEND_PACKAGE` | `"pwdlib[bcrypt]"` | Distribución reportada cuando falla la importación. |

#### `BcryptHasher.__init__()`

```python
def __init__(self, *, rounds: int = DEFAULT_ROUNDS) -> None:
```

| Parámetro | Tipo | Descripción |
|---|---|---|
| `rounds` | `int` | Factor de coste, expresado como el logaritmo en base 2 del número de iteraciones. |

**Devuelve:** `None`.

**Lanza:** `HashConfigurationException` cuando `rounds` no es un entero entre
`MIN_ROUNDS` y `MAX_ROUNDS`. Los booleanos se rechazan explícitamente. El mensaje
reporta ambos límites y el valor rechazado, por ejemplo `The bcrypt 'rounds'
option must be an integer between 4 and 31, got 99.`

**Efectos secundarios:** ninguno. Aquí no se importa ni se construye el backend.

#### `BcryptHasher.make()`

```python
async def make(
    self,
    value: str,
    *,
    rounds: int | None = None,
    memory: int | None = None,
    threads: int | None = None,
) -> str:
```

| Parámetro | Tipo | Descripción |
|---|---|---|
| `value` | `str` | Valor en texto plano a hashear. |
| `rounds` | `int \| None` | Override del factor de coste para esta llamada. |
| `memory` | `int \| None` | Se ignora, bcrypt no tiene parámetro de memoria. |
| `threads` | `int \| None` | Se ignora, bcrypt no tiene parámetro de paralelismo. |

**Devuelve:** `str` — un hash bcrypt de 60 caracteres como
`$2b$04$<salt+digest>`, con una sal aleatoria nueva en cada llamada.

**Lanza:** `HashConfigurationException` cuando el override queda fuera del rango
soportado. Los errores del backend se propagan sin traducir; el paquete `bcrypt`
rechaza valores de más de 72 bytes con `ValueError: password cannot be longer
than 72 bytes, truncate manually if necessary (e.g. my_password[:72])`.

**Comportamiento:** la derivación corre en `asyncio.to_thread(self._make, ...)`.
Sin override se reutiliza el backend cacheado; con override se construye un
backend desechable para esa llamada.

#### `BcryptHasher.check()`

```python
async def check(self, value: str, hashed: str) -> bool:
```

**Devuelve:** `bool`. La verificación corre en
`asyncio.to_thread(self._check, ...)`. Responde `False` de inmediato cuando
`hashed` está vacío o cuando el backend no lo identifica como un hash bcrypt; en
otro caso delega en el backend. Se usa el coste codificado en el hash, así que
un hash producido con otro coste también se verifica.

#### `BcryptHasher.needsRehash()`

```python
def needsRehash(self, hashed: str) -> bool:
```

**Devuelve:** `bool`. Devuelve `True` cuando `hashed` está vacío o cuando el
backend no lo identifica como un hash bcrypt —incluido un hash Argon2id—; en
otro caso pregunta al backend si el factor de coste o el prefijo codificados
difieren de los configurados.

#### `BcryptHasher.getAlgorithm()`

```python
def getAlgorithm(self) -> str:
```

**Devuelve:** `str` — siempre `'bcrypt'`.

#### `BcryptHasher.setRounds()`

```python
def setRounds(self, rounds: int) -> Self:
```

Valida el valor con la misma regla que `__init__`, lanza
`HashConfigurationException` si falla, descarta el backend cacheado para que el
coste nuevo tenga efecto y devuelve la misma instancia.

#### Helpers internos de bcrypt

| Método | Propósito |
|---|---|
| `_validate(rounds)` | `staticmethod` que exige el rango `MIN_ROUNDS`–`MAX_ROUNDS` y rechaza `bool`. |
| `_backendClass()` | Importa la clase del backend en el primer uso mediante `import_hasher_backend` y la cachea. |
| `_build(rounds)` | Construye una instancia del backend con el factor de coste indicado. |
| `_default()` | Devuelve el backend construido con el coste configurado, creándolo en el primer uso. |
| `_make(value, *, rounds, memory, threads)` | Cuerpo bloqueante de hashing que `make()` ejecuta en un hilo de trabajo. |
| `_check(value, hashed)` | Cuerpo bloqueante de verificación que `check()` ejecuta en un hilo de trabajo. |
| `_identify(hashed)` | Pregunta a la clase del backend si el hash pertenece a este driver. |

### `import_hasher_backend()`

Ubicación: `orionis/hashing/hashers/functions.py`.

```python
def import_hasher_backend(module: str, attribute: str, package: str) -> Any:
```

| Parámetro | Tipo | Descripción |
|---|---|---|
| `module` | `str` | Módulo completamente cualificado que expone la clase del backend. |
| `attribute` | `str` | Nombre de la clase del backend dentro de `module`. |
| `package` | `str` | Nombre de la distribución que se reporta al usuario cuando falla la importación. |

**Devuelve:** `Any` — la clase del backend, lista para instanciarse. Se devuelve
la clase en sí; aquí no se instancia nada.

**Lanza:** `MissingHashDependencyException` cuando `importlib.import_module`
lanza `ImportError` o cuando el módulo del backend lanza
`pwdlib.exceptions.HasherNotAvailable` durante su importación. El error original
se conserva en `__cause__` y el mensaje es `The '<package>' package is required
by this hashing driver. Install it with: pip install <package>`.

Un `attribute` inexistente en el módulo importado lanza un `AttributeError`
normal, que no se traduce.

### Excepciones

Ubicación: `orionis/hashing/exceptions.py`.

```python
class HashException(Exception): ...

class HashConfigurationException(HashException): ...

class HashDriverNotSupportedException(HashException): ...

class MissingHashDependencyException(HashException): ...
```

| Excepción | Se lanza cuando |
|---|---|
| `HashException` | Clase base; nunca se lanza directamente, pero captura cualquier fallo del módulo. |
| `HashConfigurationException` | Un driver recibe parámetros de coste inválidos, ya sea al construirse, mediante un setter fluido o como override por llamada. |
| `HashDriverNotSupportedException` | `HashManager._build` recibe un nombre de driver sin implementación. |
| `MissingHashDependencyException` | No se puede importar el paquete del backend de un driver. |

### `HashProvider`

Ubicación: `orionis/hashing/provider.py`.

```python
class HashProvider(ServiceProvider):

    def register(self) -> None:
        self.app.singleton(IHashManager, HashManager)

    async def boot(self) -> None:
        await HashFacade.pin()
```

`register()` realiza un único binding: `IHashManager` → `HashManager`, como
singleton. `boot()` es asíncrono y solo fija la facade `Hash`; no registra nada.

`HashProvider` figura en `orionis.foundation.core_providers.CORE_PROVIDERS` y
**no** extiende `DeferrableProvider`, así que ambas fases corren en el arranque
de la aplicación.

### Facade `Hash`

Ubicación: `orionis/support/facades/hash.py`, reexportada desde
`orionis.support.facades`.

```python
class Hash(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> type:
        return IHashManager
```

La facade resuelve `IHashManager` desde el contenedor. `HashProvider.boot()` la
fija durante el arranque, de modo que bajo el runtime CLI o HTTP
`Hash.needsRehash(...)`, `Hash.getAlgorithm(...)` y el resto de miembros
síncronos son llamadas normales, mientras que `await Hash.make(...)` y
`await Hash.check(...)` se awaitan —que es justo de lo que depende
`app/http/controllers/auth/register_controller.py`—. En un script
suelto que solo importa `bootstrap.app`, el arranque no se ha ejecutado, la
facade sigue sin fijar y el acceso a atributos devuelve un objeto
`_FacadeDispatch` que hay que awaitar; awaitarlo resuelve el manager y llama al
método, pero no fija la facade. El stub `orionis/support/facades/hash.pyi` existe
solo para el autocompletado del editor y nunca se ejecuta.

## Ejemplos de uso

### Hashear y verificar una contraseña

`HashManager` lee la sección `hashing` directamente del contenedor, así que puede
construirse sin registrar el provider.

```python
import asyncio

from bootstrap.app import app
from orionis.hashing.hash_manager import HashManager


async def main() -> None:
    hasher = HashManager(app)

    hashed = await hasher.make("s3cr3t-password")

    print("driver:", hasher.getDefaultDriver())
    print("algorithm:", hasher.getAlgorithm())
    print("stored prefix:", hashed.split("$")[1])
    print("verified:", await hasher.check("s3cr3t-password", hashed))
    print("wrong value:", await hasher.check("another-password", hashed))
    print("needs rehash:", hasher.needsRehash(hashed))


asyncio.run(main())
```

Salida con la configuración por defecto de este repositorio:

```text
driver: argon2
algorithm: argon2id
stored prefix: argon2id
verified: True
wrong value: False
needs rehash: False
```

### Elegir driver y ajustar el coste

`__init__` solo llama a `config(path)`, así que cualquier objeto que exponga ese
método puede aportar la sección. Los overrides por llamada nunca modifican los
costes configurados.

```python
import asyncio

from orionis.hashing.hash_manager import HashManager


class StaticConfig:
    """Any object exposing config(path) satisfies what HashManager reads."""

    def __init__(self, section: dict) -> None:
        self._section = section

    def config(self, path: str) -> object:
        return self._section


hasher = HashManager(
    StaticConfig(
        {
            "driver": "bcrypt",
            "argon2": {"memory": 32, "threads": 1, "time": 1},
            "bcrypt": {"rounds": 4},
        },
    ),
)

argon2 = hasher.driver("argon2")


async def main() -> None:
    print("default driver:", hasher.getDefaultDriver())
    print("bcrypt cost:", (await hasher.make("secret"))[:7])
    print("bcrypt override:", (await hasher.make("secret", rounds=5))[:7])
    print("argon2 costs:", (await argon2.make("secret")).split("$")[3])
    override = await argon2.make("secret", rounds=2, memory=64)
    print("argon2 override:", override.split("$")[3])
    print("driver is cached:", argon2 is hasher.driver("argon2"))
    print("configured cost is untouched:", (await hasher.make("secret"))[:7])


asyncio.run(main())
```

Salida:

```text
default driver: bcrypt
bcrypt cost: $2b$04$
bcrypt override: $2b$05$
argon2 costs: m=32,t=1,p=1
argon2 override: m=64,t=2,p=1
driver is cached: True
configured cost is untouched: $2b$04$
```

### Manejo de errores

Los fallos de configuración lanzan subclases de `HashException`; la verificación
nunca lanza.

```python
import asyncio

from orionis.hashing.exceptions import (
    HashConfigurationException,
    HashDriverNotSupportedException,
)
from orionis.hashing.hash_manager import HashManager
from orionis.hashing.hashers.argon2_hasher import Argon2Hasher
from orionis.hashing.hashers.bcrypt_hasher import BcryptHasher


class StaticConfig:
    """Any object exposing config(path) satisfies what HashManager reads."""

    def __init__(self, section: dict) -> None:
        self._section = section

    def config(self, path: str) -> object:
        return self._section


hasher = HashManager(
    StaticConfig(
        {
            "driver": "argon2",
            "argon2": {"memory": 32, "threads": 1, "time": 1},
            "bcrypt": {"rounds": 4},
        },
    ),
)


async def main() -> None:
    # 1. A driver without an implementation is rejected on resolution.
    try:
        hasher.driver("md5")
    except HashDriverNotSupportedException as exc:
        print("driver ->", exc)

    # 2. Cost parameters are validated when the driver is built.
    try:
        Argon2Hasher(memory=0)
    except HashConfigurationException as exc:
        print("argon2 cost ->", exc)

    try:
        BcryptHasher(rounds=99)
    except HashConfigurationException as exc:
        print("bcrypt cost ->", exc)

    # 3. A per-call override is validated before anything is hashed.
    try:
        await hasher.make("secret", rounds=0)
    except HashConfigurationException as exc:
        print("override ->", exc)

    # 4. Verifying never raises: a foreign or malformed hash simply fails.
    legacy = await BcryptHasher(rounds=4).make("secret")
    print("foreign hash verifies:", await hasher.check("secret", legacy))
    print("foreign hash needs rehash:", hasher.needsRehash(legacy))
    print("malformed hash verifies:", await hasher.check("secret", "not-a-hash"))
    print("empty hash verifies:", await hasher.check("secret", ""))


asyncio.run(main())
```

Salida:

```text
driver -> Unsupported hashing driver: 'md5'. Must be one of ['argon2', 'bcrypt'].
argon2 cost -> The Argon2 'memory' option must be an integer greater than zero, got 0.
bcrypt cost -> The bcrypt 'rounds' option must be an integer between 4 and 31, got 99.
override -> The Argon2 'time' option must be an integer greater than zero, got 0.
foreign hash verifies: False
foreign hash needs rehash: True
malformed hash verifies: False
empty hash verifies: False
```

### Migrar un hash heredado

`needsRehash()` reporta `True` para un hash producido por otro driver, y el
driver antiguo sigue accesible mediante `driver(name)` para verificar el valor
recibido antes de sustituir el hash almacenado.

```python
import asyncio

from orionis.hashing.hash_manager import HashManager


class StaticConfig:
    """Any object exposing config(path) satisfies what HashManager reads."""

    def __init__(self, section: dict) -> None:
        self._section = section

    def config(self, path: str) -> object:
        return self._section


hasher = HashManager(
    StaticConfig(
        {
            "driver": "argon2",
            "argon2": {"memory": 32, "threads": 1, "time": 1},
            "bcrypt": {"rounds": 4},
        },
    ),
)


async def main() -> None:
    # A credential stored years ago by another application.
    stored = await hasher.driver("bcrypt").make("s3cr3t-password")
    submitted = "s3cr3t-password"

    print("stored algorithm:", stored[:4])
    print("needs rehash:", hasher.needsRehash(stored))

    if hasher.needsRehash(stored) and await hasher.driver("bcrypt").check(
        submitted, stored,
    ):
        stored = await hasher.make(submitted)

    print("upgraded algorithm:", stored.split("$")[1])
    print("needs rehash now:", hasher.needsRehash(stored))
    print("login still works:", await hasher.check(submitted, stored))


asyncio.run(main())
```

Salida:

```text
stored algorithm: $2b$
needs rehash: True
upgraded algorithm: argon2id
needs rehash now: False
login still works: True
```

### Resolver el servicio y la facade

El framework arranca `HashProvider`, así que `IHashManager` ya está vinculado y
la facade `Hash` queda fijada una vez ha arrancado el runtime CLI o HTTP. El
script siguiente corre fuera de ese runtime, así que la facade sigue sin fijar;
en cualquier caso `make()` y `check()` se awaitan.

```python
import asyncio

from bootstrap.app import app
from orionis.hashing.contracts.hash_manager import IHashManager
from orionis.support.facades.hash import Hash


async def main() -> None:
    service = await app.make(IHashManager)
    print("resolved:", type(service).__name__)
    print("singleton:", service is await app.make(IHashManager))
    print("facade pinned:", Hash._pinned_instance is not None)

    hashed = await Hash.make("through the facade", rounds=1, memory=8, threads=1)
    print("facade returns:", type(hashed).__name__)
    print("verified:", await Hash.check("through the facade", hashed))


asyncio.run(main())
```

Salida:

```text
resolved: HashManager
singleton: True
facade pinned: False
facade returns: str
verified: True
```

## Consideraciones de rendimiento y concurrencia

- `make()` y `check()` son **corrutinas** que ejecutan su cuerpo bloqueante
  mediante `asyncio.to_thread`; el resto de miembros son síncronos y nunca
  awaitan, tocan el sistema de archivos o la red, ni llaman al contenedor
  después de la construcción.
- El hashing de contraseñas es intencionadamente costoso en CPU y memoria. Con la
  configuración por defecto de este repositorio, una llamada Argon2id realiza 3
  iteraciones sobre 64 MiB (`memory=65536` kibibytes) usando 4 carriles; la
  derivación bloquea durante todo su tiempo el hilo de trabajo en el que corre,
  pero el event loop queda libre para atender otras peticiones.
- Las instancias no arrastran `__dict__` (verificado:
  `hasattr(hasher, "__dict__")` es `False`) porque todas las clases declaran
  `__slots__` y ambos contratos declaran `__slots__ = ()`.
- El módulo del backend se importa en la primera operación, no al construir:
  `_backend_class` y `_backend` son `None` hasta ese momento.
- Cada driver conserva una instancia de backend para sus costes configurados. Los
  overrides por llamada construyen un backend desechable, así que una llamada con
  override es más cara que una sin él.
- `HashManager` construye como mucho un driver por nombre y lo guarda en
  `_drivers`; `HashProvider` vincula el manager como singleton, así que una
  aplicación acaba con un manager y un backend por algoritmo.
- `check()` y `needsRehash()` leen los parámetros codificados en el hash, así que
  su coste depende del hash almacenado, no de la configuración actual.
- Cada llamada a `make()` genera una sal aleatoria nueva a través del backend, de
  modo que hashear dos veces el mismo valor nunca produce la misma cadena.
- La concurrencia está declarada en los docstrings de clase de `HashManager`,
  `Argon2Hasher` y `BcryptHasher`: no se usan locks ni primitivas de
  sincronización de `asyncio`.
  El estado mutable es la caché de drivers del manager y la caché de backend de
  cada driver, ambas escritas en el primer uso; un primer uso concurrente desde
  varios hilos puede construir el mismo objeto dos veces, y gana la última
  escritura. Todas las operaciones posteriores solo leen ese estado, y esa
  lectura ocurre antes de que la llamada suspenda, así que las tareas que
  comparten event loop nunca observan una
  caché a medio construir. Los setters fluidos mutan ese estado compartido a
  propósito, de modo que el coste nuevo es visible para todo el que tenga el
  manager o el driver.

## Notas de compatibilidad

- **Python:** el proyecto declara `requires-python = ">=3.14"` en
  `pyproject.toml`. El módulo usa anotaciones `X | None` y `Self` evaluadas de
  forma perezosa (PEP 649); `hash_manager.py` evita deliberadamente
  `from __future__ import annotations` y lleva `# ruff: noqa: TC001` para que el
  contenedor pueda reflectar `HashManager.__init__` e inyectar `IApplication`.
  Los archivos de contratos, que nunca se reflectan, sí usan ese future import.
- **Dependencia de terceros**, ya requisito base del framework —no hay que
  instalar nada extra—: `pwdlib[argon2,bcrypt]>=0.3.1`, que arrastra
  `argon2-cffi` y `bcrypt`. Si falta el backend de un driver, el fallo se reporta
  como `MissingHashDependencyException` en el primer uso, no al importar.
- **Catálogo de drivers:** solo se aceptan `argon2` y `bcrypt`, y los nombres
  provienen de `orionis.foundation.config.hashing.enums.drivers.Drivers`. Añadir
  un miembro a ese enum no añade un driver: `HashManager._build` debe saber cómo
  construirlo.
- **Límites de Argon2id:** el backend exige `memory >= 8 * threads`; el driver
  solo valida que cada coste sea un entero positivo, así que el error del backend
  (`argon2.exceptions.HashingError`) se propaga sin traducir.
- **Límites de bcrypt:** el factor de coste está restringido a `4`–`31`, y el
  paquete `bcrypt` rechaza contraseñas de más de 72 bytes con un `ValueError` que
  el driver no traduce.
- **Portabilidad de los hashes:** los hashes son autodescriptivos. Un hash
  producido con otros parámetros de coste —o por otra aplicación Orionis que use
  el mismo algoritmo— se verifica correctamente y `needsRehash()` lo señala
  cuando sus parámetros dejan de coincidir con la configuración.
- **Cableado del contenedor:** `HashProvider` forma parte de `CORE_PROVIDERS`,
  así que `IHashManager` se vincula como singleton y la facade `Hash` se fija
  durante el arranque. Como la caché compilada del bootstrap
  (`storage/framework/bootstrap`) no se invalida por cambios dentro de
  `orionis/`, una aplicación que ya cacheó sus providers debe borrar esa carpeta
  —o ejecutar `reactor optimize:clear`— para recoger este cableado.

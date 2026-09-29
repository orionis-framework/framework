# Environment (`orionis.environment`)

> Lee y escribe variables de `.env` manteniendo sincronizados `os.environ`, una caché en memoria y el archivo en disco, con una convención explícita `"<tipo>:<valor>"` para que los valores sobrevivan al formato de solo texto de `.env`.

🇬🇧 English version: [README.md](README.md)

## Tabla de contenidos

- [Descripción funcional](#descripción-funcional)
  - [Dónde encaja](#dónde-encaja)
  - [Flujo de lectura y escritura](#flujo-de-lectura-y-escritura)
  - [Mapa de archivos](#mapa-de-archivos)
  - [Convención de valores tipados](#convención-de-valores-tipados)
  - [Decisiones de diseño](#decisiones-de-diseño)
- [Referencia de API](#referencia-de-api)
  - [`Env`](#env)
  - [`env()`](#env-1)
  - [`IEnv`](#ienv)
  - [`DotEnv`](#dotenv)
  - [`EnvironmentCaster`](#environmentcaster)
  - [`IEnvironmentCaster`](#ienvironmentcaster)
  - [`EnvironmentValueType`](#environmentvaluetype)
  - [`ValidateKeyName()`](#validatekeyname)
  - [`ValidateTypes()`](#validatetypes)
  - [`SecureKeyGenerator`](#securekeygenerator)
- [Ejemplos de uso](#ejemplos-de-uso)
  - [Leer y escribir valores](#leer-y-escribir-valores)
  - [Guardar valores tipados](#guardar-valores-tipados)
  - [Manejar errores de validación y casteo](#manejar-errores-de-validación-y-casteo)
  - [Usar el caster por separado](#usar-el-caster-por-separado)
  - [Generar una clave de aplicación](#generar-una-clave-de-aplicación)
  - [Leer configuración desde una entidad](#leer-configuración-desde-una-entidad)
  - [Recargar tras una edición externa](#recargar-tras-una-edición-externa)
- [Consideraciones de rendimiento y concurrencia](#consideraciones-de-rendimiento-y-concurrencia)
- [Notas de compatibilidad](#notas-de-compatibilidad)

## Descripción funcional

Un archivo `.env` solo guarda texto. El código de la aplicación, en cambio,
necesita `int`, `float`, `bool`, `list`, `dict`, `tuple`, `set`, rutas del
sistema de archivos y secretos codificados en base64. Este módulo centraliza
esa traducción, valida cada nombre de variable que toca y mantiene
coherentes tres almacenes: el archivo `.env`, el entorno del proceso
(`os.environ`) y una caché en memoria.

### Dónde encaja

- Cada entidad de configuración bajo `orionis/foundation/config/**` declara
  sus valores por defecto con
  `default_factory=lambda: Env.get("VAR", default)`, y los archivos de la
  aplicación en `config/*.py` hacen lo mismo. Eso convierte a este módulo en
  la puerta de entrada de toda la configuración del framework.
- `orionis.foundation.config.app.entities.app.App.__post_init__` llama a
  `SecureKeyGenerator.generate()` y a `Env.set("APP_KEY", ...)` cuando no hay
  clave configurada, así que la clave que consume `orionis.encrypter` se
  produce aquí.
- El módulo **no tiene service provider ni facade registrada en el
  contenedor**: `Env` es una clase normal con classmethods, importada
  directamente. Solo depende de `orionis.support.patterns.singleton` (para
  la metaclase de `DotEnv`) y, en el caso de `SecureKeyGenerator`, del enum
  `Cipher` de `orionis.foundation.config.app.enums.ciphers`.

### Flujo de lectura y escritura

```text
Env.get(key)      -> DotEnv.get      -> ValidateKeyName -> os.environ -> __parseValue -> value
env(key)          -> Env.get
Env.set(k, v, t)  -> DotEnv.set      -> ValidateKeyName -> ValidateTypes -> EnvironmentCaster.to()
                                     -> set_key(.env)  + cache + os.environ
Env.all()         -> DotEnv.all      -> in-memory cache -> __parseValue per entry
Env.reload()      -> DotEnv.reload   -> load_dotenv(override=True) + cache rebuild
```

Del diagrama se desprenden dos hechos visibles en el código fuente:

- `get()` lee de **`os.environ`**, así que una variable exportada por el
  sistema operativo (o puesta por otra librería) sí se ve a través de
  `Env.get`.
- `all()` lee la **caché en memoria**, que se llena al construir y en
  `reload()` a partir del archivo `.env`, y que actualizan `set()` /
  `unset()` cuando `only_os=False`. Por eso una variable que solo existe en
  `os.environ` la devuelve `get()` pero *no* aparece en `all()`.

### Mapa de archivos

| Ruta | Contenido |
| --- | --- |
| `__init__.py` | Exportaciones públicas: `Env`, `env`. |
| `facade.py` | `Env`, la facade estática que implementa `IEnv`. |
| `functions.py` | `env()`, atajo a nivel de módulo de `Env.get`. |
| `core/dot_env.py` | `DotEnv`, el motor singleton dueño del archivo. |
| `dynamic/caster.py` | `EnvironmentCaster`, el códec `"<tipo>:<valor>"`. |
| `enums/value_type.py` | `EnvironmentValueType`, los diez tipos soportados. |
| `validators/key_name.py` | `ValidateKeyName`, la guarda `^[A-Z][A-Z0-9_]*$`. |
| `validators/types.py` | `ValidateTypes`, validación de valor y type hint. |
| `key/key_generator.py` | `SecureKeyGenerator`, claves `base64:` de aplicación. |
| `contracts/env.py` | Contrato abstracto `IEnv`. |
| `contracts/caster.py` | Contrato abstracto `IEnvironmentCaster`. |

### Convención de valores tipados

Un valor escrito con type hint se guarda como `"<tipo>:<valor>"` y se
decodifica al leer. La comparación de prefijo que hace
`DotEnv.__parseValue` es **sensible a mayúsculas y sin recorte de espacios**
(`value_str.split(":", 1)`), así que `INT:5` *no* se trata como valor tipado
y vuelve como la cadena `'INT:5'`.

| Type hint | Forma almacenada | Valor devuelto por `get()` |
| --- | --- | --- |
| `str` | `str:hello` | `'hello'` (sin espacios iniciales) |
| `int` | `int:42` | `42` |
| `float` | `float:3.5` | `3.5` |
| `bool` | `bool:true` | `True` |
| `list` | `list:[1, 2, 3]` | `[1, 2, 3]` |
| `dict` | `dict:{'a': 1}` | `{'a': 1}` |
| `tuple` | `tuple:(1, 2)` | `(1, 2)` |
| `set` | `set:{1, 2}` | `{1, 2}` |
| `path` | `path:/ruta/posix/absoluta` | `str` con separadores `/` |
| `base64` | `base64:aGVsbG8=` | `'hello'` (`bytes` si no es UTF-8 válido) |

La lectura se guía por el prefijo, no por el hint: cualquier valor ya
guardado con un prefijo reconocido se decodifica aunque se haya escrito sin
type hint. Por eso `APP_KEY`, que el framework guarda como `base64:<...>`,
lo devuelve `Env.get("APP_KEY")` como `bytes` decodificados y no como la
cadena literal.

Los valores sin prefijo también se parsean: `none`/`null`/`nan`/`nil` (sin
distinguir mayúsculas) y la cadena vacía pasan a `None`, `true`/`false`
pasan a booleanos, y todo lo demás se intenta con `ast.literal_eval`,
devolviendo la cadena original cuando eso falla.

### Decisiones de diseño

- **Singleton (`DotEnv`)** — una sola ruta `.env` resuelta por proceso, de
  modo que la caché y el archivo nunca divergen entre puntos de llamada. La
  instancia la crea la *primera* llamada; las siguientes ignoran sus
  argumentos.
- **Facade estática (`Env`)** — solo classmethods, sin estado, para que las
  entidades de configuración puedan llamarla dentro de un `default_factory`
  sin inyección de dependencias.
- **`__slots__` en todas las clases** — ninguna clase del módulo da
  `__dict__` a sus instancias: `EnvironmentCaster` declara sus dos slots
  (escritos con los nombres ya manglados), `DotEnv` declara
  `("__cache", "__resolved_path")`, y las clases sin estado `Env` y
  `SecureKeyGenerator` declaran `__slots__ = ()`, en coherencia con el
  `__slots__ = ()` de sus contratos.
- **`lru_cache` en ambos validadores** — los nombres de clave (512 entradas)
  y los type hints (64 entradas) salen de un conjunto pequeño y finito, así
  que validar se vuelve una búsqueda en diccionario tras la primera llamada.
- **Los contratos son `abc.ABC` con `__slots__ = ()`** — `IEnv` e
  `IEnvironmentCaster` no añaden almacenamiento por instancia a sus
  implementaciones.
- **`threading.Lock` (no `RLock`) dentro de `DotEnv`** — cada método público
  toma una sola vez el lock de clase y nunca llama a otro método bloqueado
  mientras lo mantiene.

## Referencia de API

### `Env`

```python
from orionis.environment import Env
```

Facade estática definida en `orionis/environment/facade.py`, que implementa
`IEnv`. Todos sus métodos son `@classmethod` y delegan en el singleton
compartido `DotEnv()`; la clase no guarda estado y declara
`__slots__ = ()`, así que instanciarla no aporta nada.

```python
@classmethod
def get(cls, key: str, default: object | None = None) -> object: ...

@classmethod
def set(
    cls,
    key: str,
    value: str | float | bool | list | dict | tuple | set,
    type_hint: str | EnvironmentValueType | None = None,
    *,
    only_os: bool = False,
) -> bool: ...

@classmethod
def unset(cls, key: str, *, only_os: bool = False) -> bool: ...

@classmethod
def all(cls) -> dict[str, Any]: ...

@classmethod
def reload(cls) -> bool: ...
```

| Método | Devuelve | Notas |
| --- | --- | --- |
| `get` | el valor parseado, o `default` | `default` se devuelve **tal cual**, nunca se parsea. |
| `set` | `True` | Efectos: escribe en `.env` (salvo `only_os=True`), actualiza la caché y `os.environ`. |
| `unset` | `True` | Devuelve `True` incluso si la clave no existía. |
| `all` | `dict[str, Any]` | Instantánea parseada de la caché en memoria. |
| `reload` | `bool` | `False` cuando construir el `DotEnv` compartido lanza `OSError` o `ValueError`. |

**Lanza**

- `TypeError` — `key` no es una cadena, `value` no es uno de los tipos
  soportados, o `type_hint` no es ni `str` ni `EnvironmentValueType`.
- `ValueError` — `key` no coincide con `^[A-Z][A-Z0-9_]*$`, o un valor no se
  puede serializar/parsear para el tipo pedido.
- `RuntimeError` — `type_hint` es una cadena que no corresponde a ningún
  miembro de `EnvironmentValueType`. También en `reload()`: solo captura
  `OSError` y `ValueError`, pero `DotEnv.reload()` envuelve cualquier fallo
  en `RuntimeError`, así que una recarga fallida se propaga en vez de
  devolver `False`.

### `env()`

```python
from orionis.environment import env
```

```python
def env(key: str, default: object | None = None) -> object: ...
```

Atajo a nivel de módulo definido en `orionis/environment/functions.py`.
Llama a `Env.get(key, default)` y tiene exactamente el mismo comportamiento,
valor de retorno y excepciones.

### `IEnv`

```python
from orionis.environment.contracts.env import IEnv
```

`abc.ABC` con `__slots__ = ()` que declara cinco classmethods abstractos:
`get`, `set`, `unset`, `all` y `reload`, con las mismas firmas listadas para
`Env`.

### `DotEnv`

```python
from orionis.environment.core.dot_env import DotEnv
```

Motor dueño del archivo `.env`. Usa la metaclase `Singleton` de
`orionis.support.patterns.singleton`, así que hay exactamente una instancia
por proceso, y protege cada método público con un `threading.Lock` de clase.
Todo su estado de instancia está declarado en
`__slots__ = ("__cache", "__resolved_path")`.

#### `DotEnv.__init__()`

```python
def __init__(self, path: str | None = None) -> None: ...
```

| Parámetro | Tipo | Descripción |
| --- | --- | --- |
| `path` | `str \| None` | Ruta del archivo `.env`. Por defecto `Path.cwd() / ".env"`; una ruta indicada se resuelve con `expanduser().resolve()`. |

Efectos: crea el archivo con `touch()` si no existe, lo carga en
`os.environ` con `load_dotenv(..., override=True)` y construye la caché en
memoria con `dotenv_values(...)`.

**Lanza**

- `OSError` — el archivo no se puede crear ni acceder.
- `RuntimeError` — cualquier otro fallo durante la inicialización.

> **Nota:** como la clase es un singleton, solo aplica la primera
> construcción del proceso. En una aplicación Orionis estándar esa primera
> construcción ya ocurrió mientras se importaba el framework
> (`orionis/foundation/core_config.py` construye `App()` a nivel de módulo,
> lo que escribe `APP_KEY` mediante `Env.set`), así que pasar un `path`
> propio desde el código de la aplicación no tiene efecto y el `.env` por
> defecto del directorio de trabajo actual es el que queda en uso.

#### `DotEnv.set()`

```python
def set(
    self,
    key: str,
    value: str | float | bool | list | dict | tuple | set,
    type_hint: str | EnvironmentValueType | None = None,
    *,
    only_os: bool = False,
) -> bool: ...
```

Valida la clave, resuelve el tipo con `ValidateTypes` cuando se pasa
`type_hint`, serializa el valor, lo escribe con `set_key` (salvo
`only_os=True`), actualiza la caché y siempre asigna `os.environ[key]`.
Devuelve `True`.

**Lanza** `TypeError` / `ValueError` desde la validación de clave y tipo, y
`RuntimeError` desde `ValidateTypes` si el nombre del type hint es
desconocido.

#### `DotEnv.get()`

```python
def get(self, key: str, default: object | None = None) -> object: ...
```

Valida la clave, lee `os.environ.get(key)` y lo parsea con `__parseValue`.
Devuelve `default` sin modificar cuando la clave no existe.

**Lanza** `TypeError` / `ValueError` de la validación de clave, más
cualquier `ValueError` / `TypeError` producido al decodificar un valor
tipado.

#### `DotEnv.unset()`

```python
def unset(self, key: str, *, only_os: bool = False) -> bool: ...
```

Valida la clave, la elimina del archivo con `unset_key` y de la caché
(salvo `only_os=True`), y la saca de `os.environ`. Devuelve `True` incluso
si la clave no existía; en ese caso `python-dotenv` imprime su propio aviso
por stdout.

#### `DotEnv.all()`

```python
def all(self) -> dict: ...
```

Devuelve un diccionario nuevo construido desde la caché en memoria, con
cada valor pasado por `__parseValue`. Una clave presente en el archivo sin
`=` se almacena como `None` y se devuelve como `None`.

#### `DotEnv.reload()`

```python
def reload(self) -> bool: ...
```

Vuelve a ejecutar `load_dotenv(..., override=True)` y reconstruye la caché
desde disco. Devuelve `True`.

**Lanza** `RuntimeError` envolviendo cualquier excepción producida durante
la recarga (por ejemplo un `.env` que no es UTF-8 válido).

#### Helpers privados

No forman parte de la API pública, pero definen el comportamiento
observable descrito arriba:

- `__serializeValue(value, type_hint=None)` — `None` pasa a `"null"`; con
  type hint delega en `EnvironmentCaster(value).to(type_hint)`; si no, las
  cadenas se recortan, los booleanos pasan a `"true"`/`"false"`, los números
  usan `str()` y `list`/`dict`/`tuple`/`set` usan `repr()`.
- `__parseValue(value)` — implementa los tokens nulos, las cadenas
  booleanas, el despacho por prefijo `"<tipo>:"` hacia
  `EnvironmentCaster.parseTyped` y el respaldo con `ast.literal_eval`.

### `EnvironmentCaster`

```python
from orionis.environment.dynamic.caster import EnvironmentCaster
```

Códec de la convención `"<tipo>:<valor>"`, implementa
`IEnvironmentCaster`. Expone `OPTIONS`, un `ClassVar[frozenset[str]]`
construido a partir de `EnvironmentValueType`, y declara `__slots__`, así
que sus instancias no tienen `__dict__`.

#### `EnvironmentCaster.supportedTypes()`

```python
@staticmethod
def supportedTypes() -> frozenset[str]: ...
```

Devuelve el propio `EnvironmentCaster.OPTIONS` (el mismo objeto):
`{'base64', 'bool', 'dict', 'float', 'int', 'list', 'path', 'set', 'str', 'tuple'}`.

#### `EnvironmentCaster.parseTyped()`

```python
@staticmethod
def parseTyped(value_str: str) -> object: ...
```

Camino rápido que usa `DotEnv.__parseValue`. `int`, `float`, `bool` y `str`
se resuelven en línea sin crear una instancia; el resto de tipos delega en
`EnvironmentCaster(value_str).get()`.

**Lanza**

- `ValueError` — `value_str` no contiene `":"` (`substring not found`,
  desde `str.index`), o el valor no encaja con el tipo anunciado.
- `TypeError` — el valor es incompatible con el tipo anunciado.

#### `EnvironmentCaster.__init__()`

```python
def __init__(self, raw: str | object) -> None: ...
```

Con una cadena de entrada, la parte anterior al primer `":"` se toma como
type hint **solo si** es una de las `OPTIONS` tras `strip().lower()`; en
caso contrario la cadena completa se conserva como valor. Las entradas que
no son cadenas se guardan como valor sin type hint. Los espacios iniciales
del valor se eliminan.

#### `EnvironmentCaster.get()`

```python
def get(self) -> object: ...
```

Decodifica el valor guardado según el type hint actual. Sin hint devuelve
el valor crudo sin tocar (ya sin espacios iniciales).

Comportamiento a tener en cuenta:

- `path` solo normaliza separadores; **no** vuelve absoluta la ruta y
  devuelve un `str`, no un `Path`.
- `base64` devuelve `str` cuando los bytes decodificados son UTF-8 válido, y
  `bytes` en caso contrario.
- `list`, `dict`, `tuple` y `set` usan `ast.literal_eval` y exigen que el
  literal sea del tipo anunciado.

**Lanza** `TypeError` cuando el fallo subyacente es un `TypeError` (por
ejemplo `list:{1}`), y `ValueError` en cualquier otro caso. Ambos mensajes
llevan el prefijo
`Error processing value '<raw>' with type hint '<hint>':`.

#### `EnvironmentCaster.to()`

```python
def to(self, type_hint: str | EnvironmentValueType) -> str: ...
```

Serializa el valor guardado y devuelve `"<type_hint>:<valor>"`. Acepta el
miembro del enum o su valor en cadena.

**Efecto secundario:** asigna `type_hint` a la instancia, de modo que un
`get()` posterior sobre la misma instancia decodifica con ese hint y no con
el original.

Comportamiento a tener en cuenta:

- `path` produce una ruta POSIX **absoluta**: un valor relativo se une a
  `Path.cwd()` y luego se aplica `expanduser()`.
- `base64` deja el valor tal cual si ya es Base64 válido, y lo codifica en
  caso contrario; solo acepta `str` y `bytes`.
- `int`, `float` y `bool` aceptan entrada en cadena (`"42"`, `"on"`,
  `"yes"`, `"disabled"`, ...); `list`, `dict`, `tuple` y `set` exigen que el
  valor ya sea exactamente de ese tipo.

**Lanza** `ValueError` ante un type hint inválido y ante cualquier fallo de
conversión — incluidos los que internamente son `TypeError`, que este
método envuelve. Los mensajes llevan el prefijo
`Error converting value '<raw>' to type '<hint>':`.

### `IEnvironmentCaster`

```python
from orionis.environment.contracts.caster import IEnvironmentCaster
```

`abc.ABC` con `__slots__ = ()` que declara dos métodos abstractos, `get()` y
`to(type_hint)`.

### `EnvironmentValueType`

```python
from orionis.environment.enums import EnvironmentValueType
```

`enum.Enum` (no `StrEnum`) con diez miembros cuyos valores son los type
hints aceptados: `BASE64`, `PATH`, `STR`, `INT`, `FLOAT`, `BOOL`, `LIST`,
`DICT`, `TUPLE`, `SET`. Al ser un `Enum` normal, un miembro no es igual a su
cadena; usa `.value` cuando necesites un string. `Env.set`,
`EnvironmentCaster.to` y `ValidateTypes` aceptan ambas formas.

### `ValidateKeyName()`

```python
from orionis.environment.validators import ValidateKeyName
```

```python
def ValidateKeyName(key: str) -> str: ...
```

Alias a nivel de módulo de `_validate_key_name`, decorada con
`functools.lru_cache(maxsize=512)`. Devuelve la clave sin cambios cuando
coincide con `^[A-Z][A-Z0-9_]*$` (comprobado con `fullmatch`).

**Lanza**

- `TypeError` — `key` no es `str`.
- `ValueError` — el nombre no coincide con el patrón.

### `ValidateTypes()`

```python
from orionis.environment.validators import ValidateTypes
```

```python
def ValidateTypes(
    *,
    value: str | float | bool | list | dict | tuple | set,
    type_hint: str | EnvironmentValueType | None = None,
) -> str: ...
```

Instancia a nivel de módulo de la clase privada `__ValidateTypes`; ambos
parámetros son solo por nombre. Devuelve el nombre canónico del tipo: el
`type_hint` normalizado cuando se indica (la búsqueda es por **nombre** del
enum, así que `"INT"`, `"int"` y `EnvironmentValueType.INT` son
equivalentes), o `type(value).__name__.lower()` en caso contrario.

**Lanza**

- `TypeError` — `value` no es `str`, `int`, `float`, `bool`, `list`, `dict`,
  `tuple` ni `set`; o `type_hint` no es `str` ni `EnvironmentValueType`.
- `RuntimeError` — `type_hint` es una cadena que no corresponde a ningún
  nombre de miembro de `EnvironmentValueType`.

### `SecureKeyGenerator`

```python
from orionis.environment.key.key_generator import SecureKeyGenerator
```

```python
KEY_SIZES: ClassVar[dict[Cipher, int]]

@staticmethod
def generate(cipher: str | Cipher = Cipher.AES_256_CBC) -> str: ...
```

Produce una clave `"base64:<...>"` a partir de `os.urandom`, con el tamaño
que exige el cifrado pedido: 16 bytes para `AES-128-CBC` y `AES-128-GCM`, 32
bytes para `AES-256-CBC` y `AES-256-GCM`. El argumento `cipher` acepta un
miembro de `Cipher` o su valor en cadena.

**Lanza** `ValueError` cuando el cifrado no es uno de los cuatro soportados
(el mensaje enumera las opciones válidas).

Consumidor dentro del framework: `App.__post_init__`
(`orionis/foundation/config/app/entities/app.py`) llama a `generate()` y
guarda el resultado con `Env.set("APP_KEY", ...)` cuando no hay clave
configurada.

## Ejemplos de uso

Todos los ejemplos siguientes se ejecutaron tal cual; la salida mostrada es
la real.

### Leer y escribir valores

```python
from orionis.environment import Env, env

# Write a value into the .env file and the process environment.
Env.set("APP_NAME", "Orionis")

# Env.get() and the env() shorthand read the very same value.
print(Env.get("APP_NAME"))
print(env("APP_NAME"))

# A missing key falls back to the provided default.
print(Env.get("APP_TIMEOUT", 30))

# Remove it again: gone from the file and from os.environ.
print(Env.unset("APP_NAME"))
print(Env.get("APP_NAME"))
```

```text
Orionis
Orionis
30
True
None
```

### Guardar valores tipados

```python
from orionis.environment import Env
from orionis.environment.enums import EnvironmentValueType

# The type hint is stored in the file as a "<type>:<value>" prefix.
Env.set("QUEUE_RETRIES", 5, "int")
Env.set("ALLOWED_HOSTS", ["localhost", "127.0.0.1"], "list")
Env.set("FEATURE_FLAGS", {"beta": True}, EnvironmentValueType.DICT)
Env.set("MAIL_ENABLED", True, "bool")

for key in ("QUEUE_RETRIES", "ALLOWED_HOSTS", "FEATURE_FLAGS", "MAIL_ENABLED"):
    value = Env.get(key)
    print(f"{key}: {value!r} ({type(value).__name__})")

# Any value already stored with a known prefix is decoded on read,
# even when it was written without a type hint.
Env.set("SIGNING_SECRET", "base64:aGVsbG8=")
print("SIGNING_SECRET:", repr(Env.get("SIGNING_SECRET")))
```

```text
QUEUE_RETRIES: 5 (int)
ALLOWED_HOSTS: ['localhost', '127.0.0.1'] (list)
FEATURE_FLAGS: {'beta': True} (dict)
MAIL_ENABLED: True (bool)
SIGNING_SECRET: 'hello'
```

### Manejar errores de validación y casteo

```python
from orionis.environment import Env
from orionis.environment.dynamic.caster import EnvironmentCaster

# Key names must match ^[A-Z][A-Z0-9_]*$.
try:
    Env.get("app_name")
except ValueError as exc:
    print("ValueError:", exc)

# A non-string key is rejected before the pattern check.
try:
    Env.set(42, "value")
except TypeError as exc:
    print("TypeError:", exc)

# Parsing failures keep the concrete exception type.
try:
    EnvironmentCaster("int:not-a-number").get()
except ValueError as exc:
    print("ValueError:", exc)

# Serialising a value whose type does not match the hint fails too.
try:
    EnvironmentCaster([1, 2]).to("dict")
except ValueError as exc:
    print("ValueError:", exc)
```

```text
ValueError: Invalid environment variable name 'app_name'. It must start with an uppercase letter, contain only uppercase letters, numbers, or underscores. Example: 'MY_ENV_VAR'.
TypeError: Environment variable name must be a string, got int.
ValueError: Error processing value 'not-a-number' with type hint 'int': Cannot convert 'not-a-number' to int: invalid literal for int() with base 10: 'not-a-number'
ValueError: Error converting value '[1, 2]' to type 'dict': Value must be a dict to convert to dict, got list instead.
```

### Usar el caster por separado

```python
from orionis.environment.dynamic.caster import EnvironmentCaster

# Serialise a Python value into its .env representation...
encoded = EnvironmentCaster([1, 2, 3]).to("list")
print(encoded)

# ...and read it back into a real Python object.
print(EnvironmentCaster(encoded).get())

# Fast path for primitives: no instance is allocated.
print(EnvironmentCaster.parseTyped("bool:on"))
print(EnvironmentCaster.parseTyped("float: 3.5"))

# Without a recognised prefix the raw string is returned untouched.
print(EnvironmentCaster("mailto:someone@example.com").get())

print(sorted(EnvironmentCaster.supportedTypes()))
```

```text
list:[1, 2, 3]
[1, 2, 3]
True
3.5
mailto:someone@example.com
['base64', 'bool', 'dict', 'float', 'int', 'list', 'path', 'set', 'str', 'tuple']
```

### Generar una clave de aplicación

```python
import base64

from orionis.environment.key.key_generator import SecureKeyGenerator
from orionis.foundation.config.app.enums.ciphers import Cipher

# Each cipher gets a key of the exact size it needs.
for cipher in (Cipher.AES_128_CBC, Cipher.AES_256_GCM):
    key = SecureKeyGenerator.generate(cipher)
    raw = base64.b64decode(key.split(":", 1)[1])
    print(f"{cipher.value}: prefix={key[:7]!r} bytes={len(raw)}")

# The cipher may also be given as its string value.
print(SecureKeyGenerator.generate("AES-256-CBC").startswith("base64:"))

# Anything outside the catalogue is rejected.
try:
    SecureKeyGenerator.generate("AES-512-CBC")
except ValueError as exc:
    print("ValueError:", exc)
```

```text
AES-128-CBC: prefix='base64:' bytes=16
AES-256-GCM: prefix='base64:' bytes=32
True
ValueError: Cipher 'AES-512-CBC' is not supported. Options: AES-128-CBC, AES-256-CBC, AES-128-GCM, AES-256-GCM
```

### Leer configuración desde una entidad

```python
from dataclasses import dataclass, field

from orionis.environment import Env

# This is how every entity under orionis/foundation/config reads its
# defaults: a default_factory that calls Env.get() at construction time.
@dataclass(frozen=True, kw_only=True)
class CacheSection:
    default: str = field(default_factory=lambda: Env.get("CACHE_STORE", "file"))
    ttl: int = field(default_factory=lambda: Env.get("CACHE_TTL", 3600))

# No variable set yet: the declared defaults win.
print(CacheSection())

# Once the variable exists, the same declaration picks it up.
Env.set("CACHE_STORE", "redis")
Env.set("CACHE_TTL", 60, "int")
print(CacheSection())
```

```text
CacheSection(default='file', ttl=3600)
CacheSection(default='redis', ttl=60)
```

### Recargar tras una edición externa

```python
from pathlib import Path

from orionis.environment import Env

# Simulate an external process appending a variable to the .env file.
with Path(".env").open("a", encoding="utf-8") as handle:
    handle.write("\nEXTERNALLY_ADDED=42\n")

# The process environment has not changed yet.
print(Env.get("EXTERNALLY_ADDED"))

# reload() re-reads the file into os.environ and rebuilds the cache.
print(Env.reload())
print(Env.get("EXTERNALLY_ADDED"))

# all() lists what the .env file holds, parsed to native types.
# APP_KEY is there because the App config entity generated one on boot.
print(sorted(Env.all()))
```

```text
None
True
42
['APP_KEY', 'EXTERNALLY_ADDED']
```

## Consideraciones de rendimiento y concurrencia

- **Las lecturas no tocan el disco.** `get()` solo consulta `os.environ`; el
  archivo se lee al construir y en `reload()`.
- **Seguridad entre hilos dentro del proceso.** `DotEnv` protege `__init__`,
  `set`, `get`, `unset`, `all` y `reload` con un `threading.Lock` de clase.
  Llamadas concurrentes a `set()` desde varios hilos terminan sin errores y
  todos los valores quedan almacenados (verificado con doce hilos
  escribiendo claves distintas). El lock es un `Lock` simple, no un `RLock`:
  ningún método público llama a otro mientras lo mantiene, así que no hace
  falta reentrada.
- **Las escrituras no son atómicas ni están sincronizadas entre procesos.**
  `set()` / `unset()` delegan en `set_key` / `unset_key` de `python-dotenv`,
  que reescriben el archivo. Dos procesos escribiendo el mismo `.env` a la
  vez no están coordinados por este módulo.
- **No hay API asíncrona.** El módulo no contiene ningún `async def`; todas
  las llamadas son síncronas y bloqueantes. `set`, `unset` y `reload` hacen
  E/S de archivos, así que llamarlas dentro de un event loop lo bloquean.
- **Los validadores están cacheados.** `ValidateKeyName` (512 entradas) y el
  normalizador de type hints (64 entradas) usan `functools.lru_cache`, de
  modo que validar de nuevo es una búsqueda en diccionario.
- **`parseTyped` evita asignaciones** para `int`, `float`, `bool` y `str`;
  solo los hints de contenedor, ruta y base64 construyen una instancia de
  `EnvironmentCaster`.
- **`all()` copia.** Construye un diccionario nuevo y reparsea cada entrada
  en cada llamada, así que no está pensado para rutas calientes.
- **Constantes a nivel de módulo.** `_NULL_VALUES` y `_ENV_TYPE_PREFIXES`
  son `frozenset` calculados una vez al importar; las comprobaciones de
  pertenencia son O(1).

## Notas de compatibilidad

- **Python:** el framework declara `requires-python = ">=3.14"`
  (`pyproject.toml`). El módulo usa `from __future__ import annotations` en
  todos sus archivos, uniones `X | Y` y `ClassVar`.
- **Dependencia de terceros:** `python-dotenv~=1.2`, que ya es dependencia
  base de `orionis`, así que basta con `pip install orionis`. El módulo usa
  `dotenv_values`, `load_dotenv`, `set_key` y `unset_key` sin cambiar sus
  valores por defecto, lo que implica codificación UTF-8,
  `quote_mode="always"` (los valores se escriben entre comillas simples) e
  `interpolate=True` (una referencia `${OTRA_VAR}` se expande al cargar el
  archivo).
- **`SecureKeyGenerator` importa del framework:** depende de
  `orionis.foundation.config.app.enums.ciphers.Cipher`, a diferencia del
  resto del módulo, que solo depende de
  `orionis.support.patterns.singleton`.
- **Sin provider ni facade de contenedor.** Nada de este módulo se registra
  en el contenedor de servicios, así que funciona en scripts sueltos,
  comandos de consola y tests sin arrancar la aplicación.
- **Windows:** los valores `path` siempre se normalizan a separadores POSIX,
  y una ruta relativa pasada a `to("path")` se ancla al directorio de
  trabajo actual, por lo que el valor guardado incluye la letra de unidad de
  ese directorio.

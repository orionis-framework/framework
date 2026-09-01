# Environment de Orionis (`orionis.environment`)

> Gestión thread-safe de archivos `.env` con conversión tipada de valores,
> validación de claves y generación segura de la clave de aplicación para
> el Orionis Framework.
>
> 🇬🇧 English version: [README.md](README.md)

`orionis.environment` es la única fuente de verdad del framework para leer
y escribir variables de entorno. Combina un gestor de archivos `.env`
(`DotEnv`), una fachada estática sencilla (`Env`) y una función auxiliar
(`env()`), un conversor de valores tipado (`EnvironmentCaster`) que permite
que los valores conserven su tipo de Python a través del formato `.env`
(que solo admite cadenas), y un generador de claves seguro usado para
producir la clave de cifrado de la aplicación (`APP_KEY`, consumida por
[`orionis.encrypter`](../../encrypter)).

---

## Tabla de contenidos

1. [Requisitos](#requisitos)
2. [Qué problema resuelve](#qué-problema-resuelve)
3. [Referencia de API](#referencia-de-api)
   - [`Env`](#env)
   - [`env()`](#env-1)
   - [`IEnv`](#ienv)
   - [`DotEnv`](#dotenv)
   - [`EnvironmentCaster`](#environmentcaster)
   - [`IEnvironmentCaster`](#ienvironmentcaster)
   - [`EnvironmentValueType`](#environmentvaluetype)
   - [`ValidateKeyName`](#validatekeyname)
   - [`ValidateTypes`](#validatetypes)
   - [`SecureKeyGenerator`](#securekeygenerator)
4. [Ejemplos de uso](#ejemplos-de-uso)
5. [Notas de diseño](#notas-de-diseño)
6. [Consideraciones de rendimiento y concurrencia](#consideraciones-de-rendimiento-y-concurrencia)
7. [Notas de compatibilidad](#notas-de-compatibilidad)

---

## Requisitos

No se necesita ningún paso de instalación adicional además del propio
framework:

```bash
pip install orionis
```

- **Python:** 3.14 o superior.
- **Dependencia de terceros** (ya declarada por el framework):
  [`python-dotenv`](https://pypi.org/project/python-dotenv/) `~=1.2`
  (`dotenv_values`, `load_dotenv`, `set_key`, `unset_key`).
- Se crea automáticamente un archivo `.env` (vacío, si aún no existe) en el
  directorio de trabajo actual la primera vez que se usa `DotEnv`, salvo
  que se indique una ruta explícita.

## Qué problema resuelve

Los archivos de entorno (`.env`) solo almacenan cadenas de texto planas,
pero el código de la aplicación normalmente necesita `int`, `float`,
`bool`, `list`, `dict`, `tuple`, `set`, rutas del sistema de archivos o
secretos codificados en base64. Leer y escribir estos valores de forma
consistente, validar los nombres de las variables, y mantener sincronizados
el estado de `os.environ` en el proceso, una caché en memoria y el propio
archivo `.env` — de forma segura entre hilos — es exactamente lo que
centraliza este módulo:

- `Env` / `env()` ofrecen al resto del framework (y al código de la
  aplicación) una forma estática y sencilla de leer y escribir
  configuración sin tocar directamente `os.environ` ni `python-dotenv`.
- `DotEnv` es el motor real detrás de `Env`: un singleton thread-safe por
  proceso que posee la ruta resuelta del archivo `.env`, mantiene
  sincronizados `os.environ` y una caché en memoria, y valida cada clave
  que toca.
- `EnvironmentCaster` implementa una pequeña convención
  `"<tipo>:<valor>"` (por ejemplo, `int:42`, `list:[1, 2, 3]`,
  `path:/ruta/abs`, `base64:aGVsbG8=`) para que un valor escrito con un
  indicador de tipo se recupere con el mismo tipo de Python, en lugar de
  ser siempre una cadena de texto plana.
- `SecureKeyGenerator` produce claves aleatorias criptográficamente
  seguras, con formato `base64:<...>` al estilo Laravel y dimensionadas
  correctamente para un cifrador AES dado — se usa para autogenerar
  `APP_KEY` la primera vez que una aplicación arranca sin tenerla
  definida.

## Referencia de API

### `Env`

```python
from orionis.environment import Env
# o
from orionis.environment.facade import Env
```

Fachada estática que implementa `IEnv`. Cada método es un `@classmethod`
que delega en el singleton compartido `DotEnv()` — no es necesario (ni
está soportado) instanciar `Env`.

| Método | Firma | Descripción |
| --- | --- | --- |
| `get` | `Env.get(key: str, default: object \| None = None) -> object` | Devuelve el valor procesado de `key`, o `default` si no está definido. |
| `set` | `Env.set(key: str, value: str \| float \| bool \| list \| dict \| tuple \| set, type_hint: str \| EnvironmentValueType \| None = None, *, only_os: bool = False) -> bool` | Escribe/actualiza `key` en el archivo `.env` (salvo que `only_os=True`) y en `os.environ`. Devuelve `True` si tuvo éxito. |
| `unset` | `Env.unset(key: str, *, only_os: bool = False) -> bool` | Elimina `key` del archivo `.env` (salvo que `only_os=True`) y de `os.environ`. Devuelve `True`. |
| `all` | `Env.all() -> dict[str, Any]` | Devuelve todas las variables presentes actualmente en la caché en memoria respaldada por `.env`, procesadas a tipos nativos de Python. |
| `reload` | `Env.reload() -> bool` | Recarga las variables desde disco hacia `os.environ` y reconstruye la caché interna. Devuelve `True` si tuvo éxito, `False` ante `OSError`/`ValueError`. |

**Excepciones:** `get`/`set`/`unset` propagan `TypeError`/`ValueError`
desde la validación de la clave (ver [`ValidateKeyName`](#validatekeyname))
cuando `key` no es un nombre de variable de entorno válido.

---

### `env()`

```python
from orionis.environment import env
# o
from orionis.environment.functions import env
```

```python
def env(key: str, default: object | None = None) -> object
```

Función de conveniencia equivalente a `Env.get(key, default)` — un
auxiliar global al estilo Laravel para leer valores de configuración.

| Parámetro | Tipo | Descripción |
| --- | --- | --- |
| `key` | `str` | Nombre de la variable de entorno a recuperar. |
| `default` | `object \| None`, opcional | Valor devuelto cuando `key` no está definida. |

**Devuelve:** el valor procesado, o `default`.

**Excepciones:** las mismas que `Env.get`.

---

### `IEnv`

```python
from orionis.environment.contracts.env import IEnv
```

Clase base abstracta (`abc.ABC`) que define el contrato implementado por
`Env`: los métodos de clase abstractos `get`, `set`, `unset`, `all` y
`reload`, con exactamente las mismas firmas descritas arriba.

---

### `DotEnv`

```python
from orionis.environment.core.dot_env import DotEnv
```

**Singleton** thread-safe por proceso (impuesto mediante la metaclase
`Singleton` de `orionis.support.patterns.singleton`) que gestiona un
archivo `.env` resuelto. Los métodos de `Env` son envoltorios delgados
sobre esta clase.

#### `DotEnv(path=None)`

Constructor (solo tiene efecto en la **primera** llamada — llamadas
posteriores a `DotEnv(...)` devuelven la misma instancia singleton sin
importar los argumentos pasados).

| Parámetro | Tipo | Descripción |
| --- | --- | --- |
| `path` | `str \| None`, opcional | Ruta al archivo `.env`. Por defecto, `.env` en el directorio de trabajo actual. |

**Comportamiento:** resuelve la ruta, crea el archivo si falta, lo carga
en `os.environ` mediante `load_dotenv(..., override=True)`, y construye
una caché en memoria (`dotenv_values(...)`) usada por `all()`.

**Excepciones:** `OSError` si el archivo no puede crearse/accederse;
`RuntimeError` ante cualquier otro fallo inesperado de inicialización.

#### `dotenv.get(key, default=None)`

Mismo contrato que `Env.get`. Internamente, `get` lee directamente de
`os.environ` (la fuente única de verdad tras
`load_dotenv(override=True)` y las llamadas posteriores a `set`/`unset`)
en lugar de la caché en memoria, y procesa la cadena cruda con la misma
lógica que `EnvironmentCaster` (prefijos de tipo, booleanos, tokens nulos
y `ast.literal_eval` como respaldo).

**Excepciones:** `TypeError`/`ValueError` desde `ValidateKeyName` para
nombres de clave inválidos.

#### `dotenv.set(key, value, type_hint=None, *, only_os=False)`

Mismo contrato que `Env.set`. Valida la clave, serializa `value` (vía
`EnvironmentCaster` cuando se indica `type_hint`, o mediante una
conversión simple `str`/`repr` en caso contrario), lo escribe en el
archivo `.env` con `set_key` y actualiza la caché en memoria (salvo que
`only_os=True`), y siempre actualiza `os.environ`.

**Excepciones:** `TypeError`/`ValueError` desde la validación de
clave/tipo.

#### `dotenv.unset(key, *, only_os=False)`

Mismo contrato que `Env.unset`. Elimina la clave del archivo `.env` (vía
`unset_key`) y de la caché en memoria (salvo que `only_os=True`), y
siempre la elimina de `os.environ`. Devuelve `True` incluso si la clave no
existía.

**Excepciones:** `TypeError`/`ValueError` desde la validación de clave.

#### `dotenv.all()`

Mismo contrato que `Env.all`. Devuelve un diccionario construido
procesando cada entrada actualmente en la **caché en memoria**
(poblada en el momento de la construcción y refrescada por `reload()`,
más cualquier clave añadida vía `set(..., only_os=False)`).

#### `dotenv.reload()`

Mismo contrato que `Env.reload`, pero lanza en lugar de silenciar
errores: vuelve a ejecutar `load_dotenv(..., override=True)` y reconstruye
la caché en memoria desde el disco.

**Excepciones:** `RuntimeError` envolviendo cualquier excepción encontrada
durante la recarga.

---

### `EnvironmentCaster`

```python
from orionis.environment.dynamic.caster import EnvironmentCaster
```

Implementa `IEnvironmentCaster`. Convierte entre valores tipados de
Python y la convención de cadena `"<tipo>:<valor>"` usada para el
almacenamiento en `.env`. Usa
`__slots__ = ("_EnvironmentCaster__type_hint", "_EnvironmentCaster__value_raw")`
— no se permiten atributos dinámicos en las instancias.

#### `EnvironmentCaster.supportedTypes()`

```python
@staticmethod
def supportedTypes() -> frozenset[str]
```

Devuelve el conjunto de cadenas de indicador de tipo válidas:
`{"base64", "path", "str", "int", "float", "bool", "list", "dict", "tuple", "set"}`.

#### `EnvironmentCaster.parseTyped(value_str)`

```python
@staticmethod
def parseTyped(value_str: str) -> object
```

Ruta rápida para procesar una cadena ya tipada como `"int:42"` sin
construir una instancia completa de `EnvironmentCaster` para tipos
primitivos (`int`, `float`, `bool`, `str`); recurre a una instancia
completa (`EnvironmentCaster(value_str).get()`) para tipos complejos
(`list`, `dict`, `tuple`, `set`, `path`, `base64`).

| Parámetro | Tipo | Descripción |
| --- | --- | --- |
| `value_str` | `str` | Una cadena con formato `"<tipo>:<valor>"`, por ejemplo `"int:42"`. |

**Devuelve:** el valor de Python procesado.

**Excepciones:** `ValueError` si el valor no puede convertirse al tipo
indicado; `TypeError` si el valor es incompatible con dicho tipo.

#### `EnvironmentCaster(raw)`

Constructor.

| Parámetro | Tipo | Descripción |
| --- | --- | --- |
| `raw` | `str \| object` | Si es una cadena que contiene dos puntos cuyo prefijo es un indicador de tipo válido, el prefijo se convierte en el indicador de tipo y el resto en el valor crudo. En caso contrario, toda la entrada se trata como el valor crudo sin indicador de tipo. |

#### `caster.get()`

```python
def get(self) -> object
```

Devuelve el valor procesado según el indicador de tipo detectado (`str`,
`int`, `float`, `bool`, `list`, `dict`, `tuple`, `set`, `path` o
`base64`), o el valor crudo sin cambios si no se detectó ningún
indicador de tipo.

**Excepciones:** `ValueError` o `TypeError` si la conversión falla (el
tipo específico depende del fallo; ambos se relanzan con un mensaje
descriptivo).

#### `caster.to(type_hint)`

```python
def to(self, type_hint: str | EnvironmentValueType) -> str
```

Convierte el valor interno al `type_hint` indicado y devuelve la
representación en cadena `"<tipo>:<valor>"`, apta para escribirse en un
archivo `.env`.

| Parámetro | Tipo | Descripción |
| --- | --- | --- |
| `type_hint` | `str \| EnvironmentValueType` | El tipo destino. Debe ser uno de `EnvironmentCaster.supportedTypes()`. |

**Devuelve:** `str`, por ejemplo `"int:42"`, `"list:[1, 2, 3]"`,
`"path:/home/user/app"`, `"base64:aGVsbG8="`.

**Excepciones:** `ValueError` si `type_hint` es inválido o la conversión
falla.

---

### `IEnvironmentCaster`

```python
from orionis.environment.contracts.caster import IEnvironmentCaster
```

Clase base abstracta (`abc.ABC`) que define el contrato
`get()`/`to(type_hint)` implementado por `EnvironmentCaster`.

---

### `EnvironmentValueType`

```python
from orionis.environment.enums import EnvironmentValueType
```

`Enum` que lista los diez identificadores de tipo soportados:
`BASE64 = "base64"`, `PATH = "path"`, `STR = "str"`, `INT = "int"`,
`FLOAT = "float"`, `BOOL = "bool"`, `LIST = "list"`, `DICT = "dict"`,
`TUPLE = "tuple"`, `SET = "set"`.

---

### `ValidateKeyName`

```python
from orionis.environment.validators import ValidateKeyName
```

Un invocable (respaldado por una función decorada con
`functools.lru_cache`, `maxsize=512`) que valida el nombre de una
variable de entorno.

```python
ValidateKeyName(key: str) -> str
```

| Parámetro | Tipo | Descripción |
| --- | --- | --- |
| `key` | `str` | El nombre a validar. Debe coincidir con `^[A-Z][A-Z0-9_]*$` (comienza con una letra mayúscula, seguida de letras mayúsculas, dígitos o guiones bajos). |

**Devuelve:** `key` sin cambios, si es válido.

**Excepciones:** `TypeError` si `key` no es un `str`; `ValueError` si no
coincide con el patrón requerido.

---

### `ValidateTypes`

```python
from orionis.environment.validators import ValidateTypes
```

Una **instancia** invocable (objeto a nivel de módulo, similar a un
singleton) usada para determinar/validar el tipo de serialización de un
valor.

```python
ValidateTypes(*, value: str | int | float | bool | list | dict | tuple | set,
              type_hint: str | EnvironmentValueType | None = None) -> str
```

| Parámetro | Tipo | Descripción |
| --- | --- | --- |
| `value` | `str \| int \| float \| bool \| list \| dict \| tuple \| set` | El valor cuyo tipo se está validando/determinando. |
| `type_hint` | `str \| EnvironmentValueType \| None`, opcional | Indicador de tipo explícito; si se omite, el tipo se infiere de `value` mediante `type(value).__name__.lower()`. |

**Devuelve:** la cadena canónica del indicador de tipo (por ejemplo,
`"int"`, `"list"`).

**Excepciones:** `TypeError` si el tipo de `value` no es soportado, o si
`type_hint` se proporciona pero no es ni un `str` ni un
`EnvironmentValueType`; `RuntimeError` si `type_hint` (como cadena) no
coincide con ningún miembro conocido de `EnvironmentValueType`.

---

### `SecureKeyGenerator`

```python
from orionis.environment.key.key_generator import SecureKeyGenerator
```

Clase utilitaria para generar claves de aplicación criptográficamente
seguras, al estilo Laravel, dimensionadas para un cifrador AES dado.

#### `SecureKeyGenerator.generate(cipher=Cipher.AES_256_CBC)`

```python
@staticmethod
def generate(cipher: str | Cipher = Cipher.AES_256_CBC) -> str
```

| Parámetro | Tipo | Descripción |
| --- | --- | --- |
| `cipher` | `str \| Cipher`, opcional | El cifrador para el que se dimensiona la clave. Uno de `AES_128_CBC`, `AES_256_CBC`, `AES_128_GCM`, `AES_256_GCM` (de `orionis.foundation.config.app.enums.ciphers.Cipher`). Por defecto, `Cipher.AES_256_CBC`. |

**Devuelve:** `str` — una clave con formato
`"base64:<bytes-aleatorios-codificados-en-base64>"`, usando
`os.urandom(16)` para cifradores de 128 bits o `os.urandom(32)` para
cifradores de 256 bits.

**Excepciones:** `ValueError` si `cipher` no es uno de los valores
soportados.

> Este es el mecanismo que usa el framework para autopoblar `APP_KEY`
> cuando falta al arrancar (ver [orionis.encrypter](../../encrypter)), y
> el formato `"base64:..."` que produce es exactamente lo que
> `EnvironmentCaster`/`DotEnv.get()` decodifican de vuelta a `bytes` sin
> procesar al leerlo mediante `Env.get("APP_KEY")`.

## Ejemplos de uso

### 1. Lectura/escritura básica con la fachada `Env`

```python
from orionis.environment import Env

Env.set("APP_NAME", "Orionis Demo")
print(Env.get("APP_NAME"))              # "Orionis Demo"
print(Env.get("MISSING_VAR", "fallback"))  # "fallback"

Env.unset("APP_NAME")
print(Env.get("APP_NAME"))              # None
```

### 2. Usando el atajo `env()`

```python
from orionis.environment import env

debug_mode = env("APP_DEBUG", False)
if debug_mode:
    print("Ejecutando en modo debug")
```

### 3. Almacenar y leer valores tipados

```python
from orionis.environment import Env

Env.set("MAX_RETRIES", 5, type_hint="int")
Env.set("ALLOWED_HOSTS", ["api.example.com", "web.example.com"], type_hint="list")
Env.set("STORAGE_PATH", "storage/app", type_hint="path")

retries = Env.get("MAX_RETRIES")           # 5 (int)
hosts = Env.get("ALLOWED_HOSTS")           # ["api.example.com", "web.example.com"]
storage_path = Env.get("STORAGE_PATH")     # ruta POSIX absoluta como cadena
```

### 4. Usar `EnvironmentCaster` directamente para una conversión puntual

```python
from orionis.environment.dynamic.caster import EnvironmentCaster

encoded = EnvironmentCaster("super-secreto").to("base64")
print(encoded)  # "base64:c3VwZXItc2VjcmV0bw=="

decoded = EnvironmentCaster(encoded).get()
print(decoded)  # "super-secreto"

# Ruta rápida para cadenas ya tipadas:
value = EnvironmentCaster.parseTyped("int:42")  # 42
```

### 5. Generar una clave de aplicación segura

```python
from orionis.environment.key.key_generator import SecureKeyGenerator
from orionis.environment import Env

new_key = SecureKeyGenerator.generate("AES-256-GCM")
Env.set("APP_KEY", new_key)  # almacenada tal cual, p. ej. "base64:...="
```

### 6. Recargar tras una edición externa de `.env`

```python
from orionis.environment import Env

# Algún proceso externo (o un editor de texto) modificó el archivo .env en disco.
reloaded = Env.reload()
if reloaded:
    print("Variables de entorno actualizadas:", Env.all())
```

## Notas de diseño

Las siguientes notas describen decisiones de diseño **ya existentes** con
fines exclusivamente informativos — no son propuestas de cambio.

- **`DotEnv` singleton mediante metaclase.** `DotEnv` usa
  `orionis.support.patterns.singleton.Singleton` como su metaclase, de
  modo que `DotEnv()` (con o sin argumento `path`) siempre devuelve la
  misma instancia a nivel de proceso después de la primera construcción —
  los argumentos posteriores se ignoran porque `__init__` solo se ejecuta
  una vez.
- **`os.environ` como fuente única de verdad para `get`.** `DotEnv.get`
  lee de `os.environ`, no de la caché en memoria, por lo que siempre
  refleja el estado más reciente, incluidos valores establecidos con
  `only_os=True` o modificados de otra manera durante la vida del
  proceso. `DotEnv.all()`, en cambio, lee de la **caché en memoria**, que
  solo se actualiza mediante `set(..., only_os=False)` (el valor por
  defecto) y se reconstruye por completo con `reload()` — las variables
  establecidas con `only_os=True` **no** aparecerán en `Env.all()` aunque
  `Env.get()` sí pueda leerlas. `Env.reload()` solo captura
  `OSError`/`ValueError` provenientes del `DotEnv.reload()` subyacente;
  como `DotEnv.reload()` envuelve los fallos inesperados como
  `RuntimeError`, dicho `RuntimeError` **no** es capturado por
  `Env.reload()` y se propagará a quien llame.
- **`threading.Lock` explícito por instancia.** Todas las operaciones de
  `DotEnv` (`get`, `set`, `unset`, `all`, `reload` y `__init__`) adquieren
  el mismo `_lock`, serializando cada llamada entre hilos — se prioriza
  la simplicidad y la corrección sobre el rendimiento concurrente para el
  acceso a `.env`, que no se espera que sea una ruta de alta frecuencia.
- **`lru_cache` en los validadores.** Tanto `ValidateKeyName`
  (`maxsize=512`) como la función interna `_normalize_type_hint` usada por
  `ValidateTypes` (`maxsize=64`) están memoizadas, ya que el conjunto de
  nombres de variables de entorno e indicadores de tipo usados por una
  aplicación dada es pequeño y finito, de modo que la validación repetida
  se reduce a una búsqueda O(1) en un diccionario tras la primera llamada.
- **Despacho `if`/`elif` en lugar de una tabla de invocables.** Tanto
  `EnvironmentCaster.get()` como `EnvironmentCaster.to()` despachan según
  el indicador de tipo mediante una cadena explícita `if`/`elif` en lugar
  de una tabla de despacho, evitando la asignación de métodos vinculados
  en cada llamada.
- **Slots con "name mangling".** `EnvironmentCaster` lista explícitamente
  los nombres de atributo con mangling en `__slots__`
  (`"_EnvironmentCaster__type_hint"`, `"_EnvironmentCaster__value_raw"`),
  combinando atributos privados de doble guion bajo con el ahorro de
  memoria de `__slots__`.
- **`"<tipo>:<valor>"` es una convención de cadena, no un esquema.**
  Cualquier cadena que contenga dos puntos cuyo prefijo coincida con un
  indicador de tipo conocido (por ejemplo, `"int:"`, `"path:"`) se
  interpreta como tipada; no existe un mecanismo de escape para los dos
  puntos que aparezcan al inicio de un valor de cadena que, por lo demás,
  no está tipado.

## Consideraciones de rendimiento y concurrencia

Estas son notas informativas sobre el comportamiento existente, no
recomendaciones de optimización:

- Cada operación de `DotEnv` (`get`, `set`, `unset`, `all`, `reload`)
  adquiere el **mismo lock único**, por lo que las llamadas concurrentes
  desde múltiples hilos se serializan por completo — no hay distinción
  entre lectura/escritura ni bloqueo por clave. Bajo acceso concurrente
  intenso, las llamadas se encolan en lugar de ejecutarse en paralelo.
- `set` y `unset` (salvo que `only_os=True`) escriben en el archivo `.env`
  en disco mediante `set_key`/`unset_key` de `python-dotenv`, lo que
  implica E/S de archivo en cada llamada — esto es E/S bloqueante y
  síncrona, sin variante asíncrona provista por este módulo.
- `get` evita la E/S de disco leyendo de `os.environ` (poblado una vez en
  la construcción de `DotEnv()`/`reload()` y mantenido sincronizado por
  `set`/`unset`), por lo que llamadas repetidas a `Env.get(...)` son
  económicas en comparación con `set`/`unset`.
- `ValidateKeyName` y la normalización del indicador de tipo usada por
  `ValidateTypes` están memoizadas con `lru_cache`, por lo que validar
  repetidamente la misma clave/indicador de tipo (por ejemplo, dentro de
  una ruta de lectura de configuración de alta frecuencia) es O(1) tras la
  primera llamada — pero las cachés son de ámbito de proceso y no están
  acotadas por el contenido de la clave más allá de su `maxsize` (512 y 64
  respectivamente), por lo que una aplicación que genere una cantidad muy
  grande de claves dinámicas distintas podría desalojar entradas
  anteriores.
- `DotEnv` es un singleton basado en metaclase sin variante asíncrona;
  llamar a cualquiera de sus métodos desde código `async def` se ejecuta
  de forma síncrona en el hilo/bucle de eventos que llama (no hay
  delegación tipo `run_in_executor` dentro de este módulo) — ver
  [orionis.aio](../../aio) si se necesita delegar de forma segura para
  asyncio llamadas bloqueantes para una carga de trabajo específica.

## Notas de compatibilidad

- **Versión mínima de Python:** 3.14.
- **Dependencias:**
  - `python-dotenv ~= 1.2` — provee `dotenv_values`, `load_dotenv`,
    `set_key`, `unset_key`.
  - Librería estándar: `os`, `ast`, `threading`, `pathlib`, `re`,
    `functools`, `base64`, `enum`, `abc`, `typing`.
  - `SecureKeyGenerator` importa
    `orionis.foundation.config.app.enums.ciphers.Cipher` (un enum interno
    del framework), acoplando la generación de claves a la lista de
    cifradores soportados por el framework.
- **Integración con el framework:** `config/app.py` lee `APP_KEY` /
  `APP_CIPHER` mediante `Env.get(...)`, y `orionis.encrypter.Encrypter`
  consume el valor `bytes` resultante; otros archivos de configuración del
  framework (database, cache, mail, queue, etc.) siguen el mismo patrón
  `Env.get(...)` para leer ajustes controlados por variables de entorno.

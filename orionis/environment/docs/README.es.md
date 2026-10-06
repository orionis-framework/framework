# orionis.environment

> `orionis.environment` carga valores `.env`, expone configuración tipada del proceso, persiste cambios controlados y genera claves de cifrado de aplicación.

## Descripción general

La API del paquete es `Env` junto al helper `env()`. Ambos delegan a un singleton de proceso `DotEnv`. En el primer uso resuelve `.env` desde el directorio actual, lo crea si falta, lo carga en `os.environ` dando precedencia al archivo y conserva sus entradas para `all()`.

Los valores pueden usar prefijos explícitos como `int:`, `bool:`, `list:`, `path:` o `base64:`. Los no prefijados aún reconocen nulos, booleanos y literales Python seguros. `EnvironmentCaster` implementa serialización y parsing tipado.

## Requisitos

- Python 3.14 o posterior.
- `python-dotenv>=1.2.3,<2.0`, instalado por Orionis.
- Acceso de lectura/escritura al `.env` elegido para `set`, `unset` y `reload` persistentes.
- Nombres en mayúscula que coincidan con `[A-Z][A-Z0-9_]*`.

## Inicio rápido

```python
from orionis.environment import Env, env

Env.set("ORIONIS_DOC_SAMPLE", 7, "int", only_os=True)
assert Env.get("ORIONIS_DOC_SAMPLE") == 7
assert env("MISSING_DOC_KEY", "fallback") == "fallback"
Env.unset("ORIONIS_DOC_SAMPLE", only_os=True)
print("7 fallback")
```

Validación: **Executed successfully** en CPython 3.14.6. `only_os=True` mantuvo intacto el `.env` del repositorio.

## Conceptos principales

### Entorno de proceso y caché de archivo

`get()` lee `os.environ`, fuente vigente del proceso. Escrituras persistentes actualizan archivo/caché y entorno. `all()` devuelve solo entradas cacheadas que provienen del `.env`; no vuelca todas las variables del sistema operativo.

### Valores tipados

Los hints son `str`, `int`, `float`, `bool`, `list`, `dict`, `tuple`, `set`, `path` y `base64`. El almacenamiento tipado usa `<hint>:<payload>`. Contenedores emplean literales seguros; rutas se normalizan a POSIX; Base64 retorna texto UTF-8 cuando es posible y bytes en otro caso.

### Ruta singleton

`DotEnv` usa metaclase singleton. La ruta entregada en la primera construcción del proceso define el archivo de las llamadas posteriores de la fachada. Aplicaciones normales usan `.env` del directorio actual; pruebas con otra ruta deben aislar el singleton en un proceso nuevo o reiniciarlo con utilidades de prueba.

## Estructura del módulo

| Ruta | Responsabilidad |
|---|---|
| `facade.py`, `functions.py` | Métodos públicos `Env` y helper `env()`. |
| `core/dot_env.py` | Ciclo del archivo, sincronización, caché, parsing y lock. |
| `dynamic/caster.py` | Serialización y deserialización tipada. |
| `enums/value_type.py` | Valores `EnvironmentValueType` soportados. |
| `validators/` | Validación de nombres/hints con cachés limitadas. |
| `key/key_generator.py` | Claves AES aleatorias compatibles con Laravel. |
| `contracts/` | Interfaces abstractas de entorno y caster. |

## API pública

### `Env.get(key, default=None)` y `env(key, default=None)`

Validan la clave en mayúscula y devuelven su valor de proceso parseado, o exactamente el default si falta. `env()` delega una sola llamada a `Env.get`.

### `Env.set(key, value, type_hint=None, *, only_os=False)`

Serializa el valor, opcionalmente con prefijo tipado. Por defecto actualiza `.env`, caché y `os.environ`; `only_os=True` cambia solo el proceso actual. Devuelve `True` al lograrlo.

### `Env.unset(key, *, only_os=False)`

Elimina la entrada de archivo/caché y proceso, o solo del proceso. Claves válidas ausentes se consideran eliminadas y retornan `True`; `python-dotenv` puede mostrar un mensaje informativo si no existe en archivo.

### `Env.all()` y `Env.reload()`

`all()` devuelve un diccionario nuevo con valores parseados del caché respaldado por archivo. `reload()` recarga el archivo con override y reconstruye el caché. Un fallo de recarga se envuelve como `RuntimeError` en `DotEnv` y se propaga.

### Componentes avanzados

`EnvironmentCaster`, `EnvironmentValueType`, `DotEnv` y `SecureKeyGenerator` viven en sus subpaquetes. Sirven para integración y pruebas, pero `orionis.environment` solo exporta `Env` y `env`.

## Flujos de trabajo comunes

### Leer defaults de configuración

Usa `env("NAME", fallback)` en fábricas de configuración. Los valores pueden ser booleanos, números, colecciones, rutas o Base64 decodificado; no asumas que todo es string.

### Persistir un valor tipado

Usa `Env.set("WORKERS", 4, "int")`; el archivo guarda `int:4` y lecturas posteriores retornan entero `4`. Usa `EnvironmentValueType.INT` en lugar de string si el enum resulta más claro.

### Aplicar una edición externa

Llama `Env.reload()` tras cambiar el `.env` fuera del proceso. Sobrescribe valores coincidentes y refresca `all()`. Una clave borrada del archivo sale del caché, pero `python-dotenv` no elimina automáticamente una variable que ya existe en el proceso.

## Ejemplos

### Serializar y parsear un diccionario tipado

```python
from orionis.environment.dynamic.caster import EnvironmentCaster

stored = EnvironmentCaster({"workers": 4}).to("dict")
assert stored == "dict:{'workers': 4}"
assert EnvironmentCaster.parseTyped(stored) == {"workers": 4}
print(stored)
```

Validación: **Executed successfully** en CPython 3.14.6.

### Trabajar con un `.env` aislado

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.environment.core.dot_env import DotEnv

with TemporaryDirectory() as directory:
    path = Path(directory) / ".env"
    values = DotEnv(str(path))
    values.set("FEATURES", ["mail", "queue"], "list")
    assert values.get("FEATURES") == ["mail", "queue"]
    assert values.all() == {"FEATURES": ["mail", "queue"]}
    values.unset("FEATURES")

print("temporary .env ok")
```

Validación: **Executed successfully** en CPython 3.14.6 dentro de un directorio temporal.

### Generar una clave AES de aplicación

```python
import base64
from orionis.environment.key.key_generator import SecureKeyGenerator

key = SecureKeyGenerator.generate("AES-256-GCM")
raw = base64.b64decode(key.removeprefix("base64:"), validate=True)
assert len(raw) == 32
print("key bytes:", len(raw))
```

Validación: **Executed successfully** en CPython 3.14.6; la clave decodificada tuvo 32 bytes.

## Configuración

El subsistema elige `Path.cwd() / ".env"`, salvo que la primera construcción directa `DotEnv(path)` indique otra ruta. No hay archivo de configuración Orionis separado para este módulo.

El archivo admite sintaxis dotenv y estos prefijos:

| Prefijo | Valor parseado |
|---|---|
| `str:` | String sin espacios iniciales del valor. |
| `int:`, `float:` | Número Python. |
| `bool:` | `true/1/yes/on/enabled` o `false/0/no/off/disabled`. |
| `list:`, `dict:`, `tuple:`, `set:` | Contenedor literal Python correspondiente. |
| `path:` | String de ruta POSIX normalizada. |
| `base64:` | String UTF-8 decodificado o bytes raw. |

Sin prefijo, `none`, `null`, `nan` y `nil` se vuelven `None`; literales seguros se parsean con `ast.literal_eval`.

## Integración con Orionis

Las dataclasses de configuración llaman `Env.get` en sus default factories, así que el parsing ocurre antes de que providers consuman config normalizada. La validación de clave de aplicación usa `SecureKeyGenerator` y persiste `APP_KEY` generada mediante `Env.set` si falta.

Configuración de console, HTTP, database, cache, queue, session, mail, logging, view, MCP y testing depende de este módulo. No tiene service provider porque su fachada singleton se usa durante bootstrap temprano.

## Errores y casos límite

- Las claves deben usar mayúsculas, dígitos y guiones bajos; claves inválidas lanzan `TypeError` o `ValueError`.
- Hints explícitos desconocidos en `Env.set` lanzan `RuntimeError`; valores incompatibles lanzan `TypeError` o `ValueError`.
- Strings almacenados vacíos se parsean como `None`, distinto del comportamiento explícito `str:`.
- `base64:` usa validación estricta; payloads inválidos fallan en vez de retornar texto sin decodificar.
- `only_os=True` no actualiza el caché: `get()` puede ver el valor mientras `all()` no.
- `all()` recolecta un diccionario nuevo y los mutables anidados se parsean nuevamente, no son objetos compartidos del caché.
- El módulo guarda secretos como texto `.env`; Base64 codifica, no cifra.

## Rendimiento y concurrencia

Todas las operaciones `DotEnv` usan un `threading.Lock` de clase, protegiendo consistencia entre proceso/archivo/caché pero serializando lecturas y escrituras entre hilos. Código async debe evitar escrituras persistentes frecuentes en el camino caliente porque el acceso a archivo es síncrono.

Las entradas se cachean para `all()`, tipos primitivos tienen fast path, validación de claves usa LRU de 512 nombres y normalización de hints usa LRU de 64. `get()` aún lee `os.environ`, por lo que cambios solo de proceso se ven inmediatamente.

## Compatibilidad

Orionis declara Python 3.14+ y `python-dotenv` 1.2.3+. La validación usó CPython 3.14.6 en Windows. Las rutas persistidas usan separadores POSIX entre plataformas; colecciones usan literales Python, no JSON.

## Notas de verificación

La validación usó CPython 3.14.6. Se inspeccionaron exports, fachada/helper, singleton/archivo, caster, enums, validadores, generador de clave, integraciones bootstrap y `tests/environment`. Las 210 pruebas pasaron con el runner Orionis. Cuatro ejemplos independientes se ejecutaron correctamente sin cambiar el `.env` del repositorio.

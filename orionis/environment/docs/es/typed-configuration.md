# Leer y escribir configuración de entorno

Cada bloque de esta página es un programa independiente. Ejecútalo en un proceso nuevo desde un directorio temporal: la primera construcción del singleton determina su archivo para todo el proceso. `only_os=True` limita la modificación solicitada; no omite la carga inicial del `.env`.

## Inicio rápido

```python
from orionis.environment import Env, env

Env.set("ORIONIS_DOC_SAMPLE", 7, "int", only_os=True)
assert Env.get("ORIONIS_DOC_SAMPLE") == 7
assert env("MISSING_DOC_KEY", "fallback") == "fallback"
Env.unset("ORIONIS_DOC_SAMPLE", only_os=True)
print("7 fallback")
```

## Conceptos principales

### Entorno de proceso y caché de archivo

`get()` lee `os.environ`, fuente vigente del proceso. Escrituras persistentes actualizan archivo/caché y entorno. `all()` devuelve solo entradas cacheadas que provienen del `.env`; no vuelca todas las variables del sistema operativo.

### Valores tipados

Los hints son `str`, `int`, `float`, `bool`, `list`, `dict`, `tuple`, `set`, `path` y `base64`. El almacenamiento tipado usa `<hint>:<payload>`. Los contenedores emplean literales seguros. La serialización de rutas expande `~`, resuelve rutas relativas y normaliza los separadores a POSIX. Base64 devuelve texto UTF-8 cuando es posible y bytes en otro caso.

`EnvironmentCaster(value).to("base64")` también acepta bytes binarios que no sean UTF-8. Los valores que ya contienen Base64 válido se conservan; los demás strings o bytes se codifican. Esta interfaz directa admite más tipos que `Env.set` con hint, cuyo validador acepta strings, números, booleanos y contenedores literales.

### Ruta singleton

`DotEnv` usa metaclase singleton. La ruta entregada en la primera construcción del proceso define el archivo de las llamadas posteriores de la fachada. Aplicaciones normales usan `.env` del directorio actual; pruebas con otra ruta deben aislar el singleton en un proceso nuevo o reiniciarlo con utilidades de prueba.

## Flujos de trabajo comunes

### Leer defaults de configuración

Usa `env("NAME", fallback)` en fábricas de configuración. Los valores pueden ser booleanos, números, colecciones, rutas o Base64 decodificado; no asumas que todo es string.

### Persistir un valor tipado

Usa `Env.set("WORKERS", 4, "int")`; el archivo guarda `int:4` y lecturas posteriores retornan entero `4`. Usa `EnvironmentValueType.INT` en lugar de string si el enum resulta más claro.

### Aplicar una edición externa

Llama `Env.reload()` tras cambiar el `.env` fuera del proceso. Lee e interpola el archivo una sola vez, y usa esos mismos valores para sobrescribir coincidencias en el proceso y refrescar `all()`. Una clave borrada del archivo sale del caché; una variable ya existente en el proceso se conserva.

## Ejemplos

### Serializar y parsear un diccionario tipado

```python
from orionis.environment.dynamic.caster import EnvironmentCaster

stored = EnvironmentCaster({"workers": 4}).to("dict")
assert stored == "dict:{'workers': 4}"
assert EnvironmentCaster.parseTyped(stored) == {"workers": 4}
print(stored)
```


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


### Generar una clave AES de aplicación

```python
import base64
from orionis.environment.key.key_generator import SecureKeyGenerator

key = SecureKeyGenerator.generate("AES-256-GCM")
raw = base64.b64decode(key.removeprefix("base64:"), validate=True)
assert len(raw) == 32
print("key bytes:", len(raw))
```

## Configuración

El subsistema elige `Path.cwd() / ".env"`, salvo que la primera construcción directa `DotEnv(path)` indique otra ruta. No hay archivo de configuración Orionis separado para este módulo.

El archivo admite sintaxis dotenv y estos prefijos:

| Prefijo | Valor parseado |
|---|---|
| `str:` | String sin espacios iniciales del valor; un payload vacío produce `""`. |
| `int:`, `float:` | Número Python. |
| `bool:` | `true/1/yes/on/enabled` o `false/0/no/off/disabled`, sin distinguir mayúsculas; otras formas lanzan `ValueError`. |
| `list:`, `dict:`, `tuple:`, `set:` | Contenedor literal Python correspondiente. |
| `path:` | String de ruta POSIX normalizada. |
| `base64:` | String UTF-8 decodificado o bytes; un payload vacío produce `""`. |

Sin prefijo, `none`, `null`, `nan` y `nil` se vuelven `None`; literales seguros se parsean con `ast.literal_eval`.

Asigna `1`, `true`, `t`, `yes` o `y` a `PYTHON_DOTENV_DISABLED` (sin distinguir mayúsculas) para impedir la publicación automática de valores del archivo en `os.environ`. `all()` sigue mostrando los valores del archivo, y las operaciones explícitas `set` y `unset` siguen modificando el entorno del proceso.

## Fuentes y siguientes pasos

[dot_env.py](../../core/dot_env.py) · [caster.py](../../dynamic/caster.py) · [facade.py](../../facade.py)

[Volver al índice del módulo](README.md).

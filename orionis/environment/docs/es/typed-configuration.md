# Leer y escribir configuración de entorno

Cada bloque de esta página es un programa independiente. Ejecuta el ejemplo de `DotEnv` en un proceso nuevo: la primera construcción del singleton determina su archivo para todo el proceso.

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

Los hints son `str`, `int`, `float`, `bool`, `list`, `dict`, `tuple`, `set`, `path` y `base64`. El almacenamiento tipado usa `<hint>:<payload>`. Contenedores emplean literales seguros; rutas se normalizan a POSIX; Base64 retorna texto UTF-8 cuando es posible y bytes en otro caso.

### Ruta singleton

`DotEnv` usa metaclase singleton. La ruta entregada en la primera construcción del proceso define el archivo de las llamadas posteriores de la fachada. Aplicaciones normales usan `.env` del directorio actual; pruebas con otra ruta deben aislar el singleton en un proceso nuevo o reiniciarlo con utilidades de prueba.

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
| `str:` | String sin espacios iniciales del valor. |
| `int:`, `float:` | Número Python. |
| `bool:` | `true/1/yes/on/enabled` o `false/0/no/off/disabled`. |
| `list:`, `dict:`, `tuple:`, `set:` | Contenedor literal Python correspondiente. |
| `path:` | String de ruta POSIX normalizada. |
| `base64:` | String UTF-8 decodificado o bytes raw. |

Sin prefijo, `none`, `null`, `nan` y `nil` se vuelven `None`; literales seguros se parsean con `ast.literal_eval`.

## Fuentes y siguientes pasos

[dot_env.py](../../core/dot_env.py) · [caster.py](../../dynamic/caster.py) · [facade.py](../../facade.py)

[Volver al índice del módulo](README.md).

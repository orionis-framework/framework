# Persistencia, recarga y referencia de Env

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

Orionis declara Python 3.14+ y `python-dotenv` 1.2.3+.

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

## Fuentes y siguientes pasos

[dot_env.py](../../core/dot_env.py) · [key_name.py](../../validators/key_name.py) · [key_generator.py](../../key/key_generator.py)

[Volver al índice del módulo](README.md).

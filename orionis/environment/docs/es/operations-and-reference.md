# Persistencia, recarga y referencia de Env

## API pública

### `Env.get(key, default=None)` y `env(key, default=None)`

Validan la clave en mayúscula y devuelven su valor de proceso parseado, o exactamente el default si falta. `env()` delega una sola llamada a `Env.get`.

### `Env.set(key, value, type_hint=None, *, only_os=False)`

Serializa el valor, opcionalmente con prefijo tipado. Por defecto actualiza `.env`, caché y `os.environ`; `only_os=True` cambia solo el proceso actual. Devuelve `True` al lograrlo. Sin hint admite `None`, strings, escalares y contenedores literales; los demás objetos se convierten con `str`. Un hint explícito requiere un valor admitido por el validador de tipos.

### `Env.unset(key, *, only_os=False)`

Elimina la entrada de archivo/caché y proceso, o solo del proceso. Claves válidas ausentes se consideran eliminadas y retornan `True`; `python-dotenv` puede mostrar un mensaje informativo si no existe en archivo.

### `Env.all()` y `Env.reload()`

`all()` devuelve un diccionario nuevo con valores parseados del caché respaldado por archivo. `reload()` lee e interpola el archivo una vez, valida los valores para publicarlos en el proceso y usa esos mismos datos para actualizar el proceso y reconstruir el caché. Un fallo de recarga se envuelve como `RuntimeError` en `DotEnv` y se propaga, incluido UTF-8 inválido. La fachada devuelve `False` solo ante un `OSError` o `ValueError` que escape de la inicialización o la llamada delegada.

### Componentes avanzados

`EnvironmentCaster`, `EnvironmentValueType`, `DotEnv` y `SecureKeyGenerator` viven en sus subpaquetes. Sirven para integración y pruebas, pero `orionis.environment` solo exporta `Env` y `env`.

## Integración con Orionis

Las dataclasses de configuración llaman `Env.get` en sus default factories, así que el parsing ocurre antes de que providers consuman config normalizada. La validación de clave de aplicación usa `SecureKeyGenerator` y persiste `APP_KEY` generada mediante `Env.set` si falta.

Configuración de console, HTTP, database, cache, queue, session, mail, logging, view, MCP y testing depende de este módulo. No tiene service provider porque su fachada singleton se usa durante bootstrap temprano.

## Errores y casos límite

- Las claves de consulta y modificación públicas deben comenzar por una letra mayúscula y contener solo mayúsculas, dígitos y guiones bajos; claves inválidas lanzan `TypeError` o `ValueError`. La carga del archivo conserva las reglas de nombres de dotenv.
- Hints explícitos desconocidos en `Env.set` lanzan `RuntimeError`; valores incompatibles lanzan `TypeError` o `ValueError`.
- Strings vacíos sin prefijo se parsean como `None`; los prefijos explícitos `str:` y `base64:` producen un string vacío. Los payloads numéricos vacíos son inválidos.
- Los booleanos tipados rechazan formas desconocidas. Los payloads numéricos, booleanos, de contenedores y Base64 inválidos producen errores de conversión que omiten el valor suministrado en sus mensajes y tracebacks formateados normales.
- `base64:` usa validación estricta; payloads inválidos fallan en vez de retornar texto sin decodificar.
- Los bytes nulos serializados se rechazan antes de que `set` cambie archivo, caché o proceso. La carga del archivo valida las entradas de proceso antes de publicarlas; un fallo de validación conserva el caché y los valores de proceso anteriores.
- En Windows, `KEY=VALUE` debe caber en 32.767 unidades UTF-16, incluido `=`. Este límite se comprueba antes de escribir en el archivo o publicar los datos recargados; no se impone en otras plataformas.
- `only_os=True` no actualiza el caché: `get()` puede ver el valor mientras `all()` no.
- `all()` recolecta un diccionario nuevo y los mutables anidados se parsean nuevamente, no son objetos compartidos del caché.
- El módulo guarda secretos como texto `.env`; Base64 codifica, no cifra.

## Rendimiento y concurrencia

`DotEnv` coordina sus operaciones de proceso, archivo y caché mediante un `threading.Lock` de clase. El acceso a archivo es síncrono; el código async debe evitar escrituras persistentes frecuentes en el camino crítico del bucle de eventos. El lock protege llamadas al mismo servicio dentro de un proceso; no coordina escritores externos ni convierte cambios directos arbitrarios de `os.environ` en transacciones.

Las entradas se cachean para `all()`, tipos primitivos tienen fast path, validación de claves usa LRU de 512 nombres y normalización de hints usa LRU de 64. `get()` aún lee `os.environ`, por lo que cambios solo de proceso se ven inmediatamente.

## Compatibilidad

Orionis declara Python 3.14+ y `python-dotenv` 1.2.3+.

Las rutas persistidas usan separadores POSIX en todas las plataformas; las colecciones emplean literales Python, no JSON.

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

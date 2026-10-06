# orionis.environment

> Lee, persiste y decodifica valores de entorno mediante un servicio `.env`
> compartido.

Versión en inglés: [README.md](README.md). Punto de entrada para agentes:
[SKILL.md](SKILL.md).

## Tabla de contenidos

- [Descripción funcional](#descripción-funcional)
- [Estructura del módulo](#estructura-del-módulo)
- [Referencia de API](#referencia-de-api)
- [Env](#env)
- [Función de consulta del entorno](#función-de-consulta-del-entorno)
- [DotEnv](#dotenv)
- [EnvironmentCaster](#environmentcaster)
- [EnvironmentValueType](#environmentvaluetype)
- [ValidateKeyName](#validatekeyname)
- [ValidateTypes](#validatetypes)
- [SecureKeyGenerator](#securekeygenerator)
- [IEnv](#ienv)
- [IEnvironmentCaster](#ienvironmentcaster)
- [Ejemplos de uso](#ejemplos-de-uso)
- [Características de diseño](#características-de-diseño)
- [Rendimiento y concurrencia](#rendimiento-y-concurrencia)
- [Notas de compatibilidad](#notas-de-compatibilidad)
- [Verificación y limitaciones](#verificación-y-limitaciones)

## Descripción funcional

El módulo expone lecturas y escrituras síncronas mediante `Env` y `env()`.
`DotEnv` conserva un archivo seleccionado y una instantánea de este en caché;
las lecturas consultan `os.environ`, no esa instantánea. `EnvironmentCaster`
implementa valores tipados explícitos, los validadores comprueban nombres y
tipos, y `SecureKeyGenerator` produce claves Base64 aleatorias. Consulta
[facade.py](../facade.py), [core/dot_env.py](../core/dot_env.py) y
[dynamic/caster.py](../dynamic/caster.py).

La integración concreta son los valores predeterminados de configuración, por
ejemplo `App.name`, `App.debug` y `App.key` en
[orionis/foundation/config/app/entities/app.py](../../foundation/config/app/entities/app.py).
`App.__validateKey` genera y persiste `APP_KEY` únicamente cuando `key is None`.
`Env` hereda de `IEnv`, no de la `Facade` del contenedor; sus métodos de clase
no requieren arrancar la aplicación, inyección de dependencias ni `pin()`.

### Inicialización y efectos de importación

El archivo inspeccionado [orionis/__init__.py](../../__init__.py) resuelve sus
exportaciones de forma diferida, y [core_config.py](../../foundation/core_config.py)
construye los valores predeterminados dentro de `get_core_config_mapping()`, no
al importar el módulo. Se verificó que importar este módulo, su conversor y su
generador de claves no crea `.env` ni inicializa `DotEnv`. La primera operación
de `Env` o construcción explícita de `DotEnv(...)` sí inicializa el servicio,
incluso `set(..., only_os=True)` o `get()` sobre una clave ausente.

Selecciona un archivo personalizado con `DotEnv(path)` **antes de la primera
operación que construya el singleton**. Los argumentos posteriores del
constructor se ignoran. Construir valores predeterminados de configuración
puede inicializarlo antes y generar `APP_KEY`; distingue esa construcción de
una simple importación. Evidencia: [DotEnv.__init__](../core/dot_env.py),
[Singleton.__call__](../../support/patterns/singleton/meta.py) y
[App.__validateKey](../../foundation/config/app/entities/app.py).

### Vistas del proceso, caché y archivo

| Operación | Entorno del proceso | Instantánea del archivo en caché | Archivo |
| --- | --- | --- | --- |
| Primera construcción | Carga valores del archivo con `override=True`. | Lee `dotenv_values`. | Lo crea si falta; no crea directorios padre. |
| `get(key, default)` | Lee y parsea esta vista. | No se consulta. | No se consulta después de inicializar. |
| `all()` | No se consulta directamente; la interpolación anterior puede haberlo usado. | Parsea en un diccionario nuevo. | No se consulta después de inicializar. |
| `set(key, value)` | Asigna la cadena serializada al final. | Actualiza después de escribir el archivo. | Reescribe mediante `set_key`. |
| `set(..., only_os=True)` | Asigna la cadena serializada. | No cambia. | No cambia después de inicializar. |
| `unset(key)` | Elimina al final. | Elimina después de `unset_key`. | Reescribe mediante `unset_key`. |
| `unset(..., only_os=True)` | Elimina únicamente aquí. | No cambia. | No cambia después de inicializar. |
| `reload()` | Sobrescribe las claves proporcionadas por el archivo. | Sustituye por una instantánea nueva. | Lee dos veces mediante la dependencia. |

La tabla se deriva de [DotEnv](../core/dot_env.py). `reload()` **no** elimina
del proceso las claves ausentes del archivo nuevo. Una declaración sin valor,
como `DOC_BARE`, aparece como `None` en `all()`, pero no se asigna a
`os.environ`; por tanto, puede conservar un valor anterior del proceso. No hay
reversión conjunta de las tres vistas si falla un paso posterior. Se inspeccionó
el comportamiento de la dependencia en
`dotenv.main.DotEnv.set_as_environment_variables`, `dotenv_values` y `rewrite`
de `python-dotenv` 1.2.4 instalado.

## Estructura del módulo

Se inspeccionaron los 17 archivos Python. Las rutas siguientes son relativas a
`orionis/environment`; ninguno de sus recursos no Python participa en la
ejecución.

| Archivos | Responsabilidad y símbolos públicos |
| --- | --- |
| [__init__.py](../__init__.py) | Reexporta exactamente `Env` y `env` mediante `__all__`. |
| [facade.py](../facade.py) | `Env`, cinco métodos de clase que delegan. |
| [functions.py](../functions.py) | `env`, una función que delega. |
| [core/dot_env.py](../core/dot_env.py) | `DotEnv`, selección del archivo, bloqueo, caché y E/S del proceso. |
| [dynamic/caster.py](../dynamic/caster.py) | `EnvironmentCaster`, conversión y `OPTIONS`. |
| [enums/value_type.py](../enums/value_type.py) | `EnvironmentValueType`, diez miembros. |
| [enums/__init__.py](../enums/__init__.py) | Reexporta `EnvironmentValueType`. |
| [validators/key_name.py](../validators/key_name.py) | `ValidateKeyName`, alias de una función con caché. |
| [validators/types.py](../validators/types.py) | `ValidateTypes`, una instancia invocable. |
| [validators/__init__.py](../validators/__init__.py) | Reexporta ambos validadores. |
| [key/key_generator.py](../key/key_generator.py) | `SecureKeyGenerator`, `KEY_SIZES` y `generate`. |
| [contracts/env.py](../contracts/env.py) | `IEnv`, cinco métodos de clase abstractos. |
| [contracts/caster.py](../contracts/caster.py) | `IEnvironmentCaster`, dos métodos abstractos. |
| [contracts/__init__.py](../contracts/__init__.py), [core/__init__.py](../core/__init__.py), [dynamic/__init__.py](../dynamic/__init__.py), [key/__init__.py](../key/__init__.py) | Inicializadores vacíos; importa sus símbolos desde los archivos concretos. |

Los nombres importados de la biblioteca estándar y las dependencias son
dependencias de implementación, no exportaciones públicas intencionadas
adicionales. Los auxiliares privados de parseo, `_lock`, los atributos de
almacenamiento, `_NULL_VALUES`, `_ENV_TYPE_PREFIXES`, `_pattern`,
`_normalize_type_hint`, `_ALLOWED_TYPE_HINT_VALUES` y `__ValidateTypes` se excluyen
como API independiente; sus efectos observables se documentan mediante las
operaciones públicas siguientes.

## Referencia de API

Las declaraciones de esta sección reproducen cabeceras, decoradores y valores
predeterminados del código. Los cuerpos se omiten intencionadamente: son
**fragmentos de referencia**, no scripts autónomos. Las importaciones identifican
rutas públicas reales. Las declaraciones literales conservan las anotaciones
originales, incluidas `Any`, `str | object` y la ausencia de `int` o `None`
explícitos en algunas uniones de valores.

### Env

Importa `Env` desde `orionis.environment` o `orionis.environment.facade`.
Fuente: [orionis/environment/facade.py](../facade.py), símbolo `Env`.

```python
class Env(IEnv):
```

No se declara un constructor explícito. `Env()` está permitido, pero no aporta
un estado de entorno independiente; sus métodos siempre obtienen el `DotEnv()`
compartido.

#### Env.get

```python
@classmethod
def get(
        cls,
        key: str,
        default: object | None = None,
) -> object:
```

`key` debe satisfacer `ValidateKeyName`. `default` puede ser cualquier objeto,
vale `None` por defecto y se devuelve sin cambios solo si la clave del proceso
está ausente. Un valor existente vacío o equivalente a nulo devuelve `None`, no
`default`. Los resultados, excepciones de parseo, efectos de inicialización y
bloqueos son los de [DotEnv.get](#dotenvget).

#### Env.set

```python
@classmethod
def set(
        cls,
        key: str,
        value: str | float | bool | list | dict | tuple | set,
        type_hint: str | EnvironmentValueType | None = None,
        *,
        only_os: bool = False,
) -> bool:
```

Se valida `key` y se serializa `value`; `type_hint` puede especificar un miembro
del enum o un tipo textual admitido. `only_os` es solo por nombre y omite las
actualizaciones del archivo y la caché, no la inicialización inicial. Devuelve
`True` al completar normalmente. Consulta [DotEnv.set](#dotenvset) para los
valores admitidos en ejecución, `TypeError`, `ValueError`, `RuntimeError` y los
fallos de E/S propagados.

#### Env.unset

```python
@classmethod
def unset(
        cls,
        key: str,
        *,
        only_os: bool = False,
) -> bool:
```

Elimina la `key` validada; `only_os=False`, solo por nombre, controla la
persistencia. Devuelve `True` incluso para una clave ausente. Sus excepciones y
efectos son los de [DotEnv.unset](#dotenvunset), no un informe booleano del fallo
de la dependencia.

#### Env.all

```python
@classmethod
def all(
        cls,
) -> dict[str, Any]:
```

Devuelve el diccionario parseado del archivo en caché, no todas las variables
del proceso. No tiene parámetros aparte de `cls`; la inicialización y la
decodificación pueden lanzar excepciones. Consulta [DotEnv.all](#dotenvall) para
el objeto nuevo devuelto y el comportamiento ante entradas malformadas.

#### Env.reload

```python
@classmethod
def reload(cls) -> bool:
```

Actualiza el mismo singleton. Devuelve `False` si la construcción o llamada
delegada lanza `OSError` o `ValueError`; en otro caso devuelve el resultado
delegado. `DotEnv.reload` envuelve sus fallos reales en `RuntimeError`, que se
propaga mediante este método. **No** reinicia el singleton ni cambia de archivo.
Fuente: `Env.reload` en [facade.py](../facade.py); regresión:
[TestEnvReload.testKeepsTheSingletonAlive](../../../tests/environment/test_facade.py).

### Función de consulta del entorno

Importa `env` desde `orionis.environment` o `orionis.environment.functions`.
Fuente: [orionis/environment/functions.py](../functions.py), símbolo `env`.

```python
def env(key: str, default: object | None = None) -> object:
```

Llama a `Env.get(key, default)` exactamente una vez y devuelve su objeto sin
cambios. Se aplican la misma validación de nombres, alternativa para claves
ausentes, decodificación e inicialización; no añade estado, conversión ni manejo
de excepciones. Casos de delegación verificados:
[test_functions.py](../../../tests/environment/test_functions.py).

### DotEnv

Importa desde `orionis.environment.core.dot_env`. Fuente:
[orionis/environment/core/dot_env.py](../core/dot_env.py), símbolo `DotEnv`.

```python
class DotEnv(metaclass=Singleton):
```

`Singleton` crea una instancia **por clase**; las construcciones posteriores la
reutilizan sin evaluar nuevos argumentos del constructor. Su bloqueo de
construcción síncrona es distinto de `DotEnv._lock`. No hay métodos públicos
para cerrar, reiniciar ni cambiar la ruta del archivo. No conserva un descriptor
abierto; las funciones de la dependencia delimitan sus propios descriptores.

#### DotEnv.__init__

```python
def __init__(
        self,
        path: str | None = None,
) -> None:
```

`path=None` o `path=""` selecciona `Path.cwd() / ".env"`. Una ruta indicada
verdadera usa `Path(path).expanduser().resolve()`. Es una selección explícita,
no una búsqueda ascendente de `.env`. Crea archivos ausentes, pero no sus
directorios padre. Bajo `_lock`, carga con `override=True` y después guarda
`dict(dotenv_values(path))` en caché; las cadenas aún no se decodifican mediante
Orionis.

La inicialización relanza `OSError` como un `OSError` encadenado con contexto de
la ruta; las demás excepciones capturadas pasan a `RuntimeError` encadenado. El
singleton se publica solo después de una construcción exitosa. Los contenidos,
las variables del proceso y los archivos creados no se revierten si falla.
Evidencia: [DotEnv.__init__](../core/dot_env.py),
[Singleton.__call__](../../support/patterns/singleton/meta.py) y
[TestDotEnvInitialisation](../../../tests/environment/core/test_dot_env.py).

La metaclase también proporciona la siguiente fábrica **heredada**. Esta
declaración pertenece a `Singleton.__acall__`, no a una función definida en este
módulo:

```python
async def __acall__(
        cls,
        *args: object,
        **kwargs: object,
) -> object:
```

Esperar explícitamente `DotEnv.__acall__()` obtiene la misma instancia. Usa el
mismo `threading.Lock` y construye síncronamente sin un `await` dentro de su
cuerpo; no convierte la E/S del entorno en una operación no bloqueante.
Evidencia: [Singleton.__acall__](../../support/patterns/singleton/meta.py).

#### DotEnv.set

```python
def set(
        self,
        key: str,
        value: str | float | bool | list | dict | tuple | set,
        type_hint: str | EnvironmentValueType | None = None,
        *,
        only_os: bool = False,
) -> bool:
```

Adquiere `_lock`, valida `key` y serializa `value`; si `only_os` es falso,
llama a `set_key` y después actualiza la caché. Asigna `os.environ[key]` al
final. Devuelve `True` e ignora la tupla devuelta por la dependencia.

| Ruta de entrada | Comportamiento implementado |
| --- | --- |
| `type_hint is None` | Omite `ValidateTypes`; `None` pasa a `"null"`, las cadenas usan `strip()`, los booleanos usan texto en minúsculas, los números usan `str()`, los contenedores usan `repr()` y los demás objetos usan `str()`. |
| Tipo explícito | `ValidateTypes` comprueba el catálogo de valores en ejecución y normaliza el tipo; después `EnvironmentCaster(value).to(hint)` realiza la conversión. |
| Escritura del tipo | Los nombres no distinguen mayúsculas mediante la búsqueda del enum, pero no se recortan espacios: `"INT"` funciona; `" INT "` lanza `RuntimeError`. |
| Contenido de contenedores | Se representa mediante literales Python, no JSON ni validación recursiva de tipos. Los valores anidados no literales pueden serializarse y fallar al decodificar. |

Los enteros se aceptan en ejecución. Sin tipo explícito, `None` y objetos fuera
de la unión anotada también se aceptan por la conversión de respaldo; con tipo,
`None`, `bytes`, `Path` y `frozenset` son rechazados por `ValidateTypes`. Es una
discrepancia de alcance entre anotación, docstring y comportamiento, no una
declaración ampliada de tipos. Evidencia:
[DotEnv.__serializeValue](../core/dot_env.py) y
[TestDotEnvSet](../../../tests/environment/core/test_dot_env.py).

`TypeError` proviene de tipos de clave inválidos, valores con tipo no admitidos
o tipos inválidos del propio hint. `ValueError` proviene de nombres inválidos o
serialización fallida; los tipos textuales desconocidos lanzan `RuntimeError`.
`set` no traduce `OSError` del sistema de archivos, errores de asignación del
proceso ni excepciones de `str()`/`repr()` personalizados. La serialización no
promete un recorrido reversible: cadenas como `"42"` se decodifican como
números, salvo que se almacenen explícitamente como `str`.

#### DotEnv.get

```python
def get(
        self,
        key: str,
        default: object | None = None,
) -> object:
```

Bajo `_lock`, valida `key`, obtiene `os.environ.get(key)` y lo parsea. Las
claves ausentes devuelven `default` por identidad. Una cadena vacía existente
produce `None`; un texto formado solo por espacios no equivale a una cadena
vacía.

El orden de parseo en `DotEnv.__parseValue` es relevante:

1. `None` permanece como `None`; los valores booleanos, numéricos y contenedores
   nativos existentes permanecen intactos en llamadas internas, aunque
   `os.environ` proporciona cadenas.
2. `""` pasa a `None`; `none`, `null`, `nan` y `nil`, recortados y sin distinguir
   mayúsculas, pasan a `None`; `true` y `false` pasan a booleanos.
3. Un prefijo exacto en minúsculas, sin recorte, de `EnvironmentValueType`
   delega en `EnvironmentCaster.parseTyped`.
4. En otro caso usa `ast.literal_eval`; `ValueError` o `SyntaxError` devuelve
   la cadena original, conservando sus espacios.

Así, `"INT:5"`, `" int:5"` y las URL permanecen como texto, mientras `"int:5"`
devuelve `5`. Sin tipo, `"yes"` permanece como texto; `"bool:yes"` es `True`.
El parseo booleano rápido devuelve `False` para `"bool:maybe"`. `"int:abc"`
inválido lanza `ValueError`; `"list:{1}"` lanza `TypeError`; los errores de
forma de dict/tuple/set se envuelven como `ValueError` en sus parsers
individuales. La validación de claves lanza `TypeError` o `ValueError`. Pueden
propagarse otros fallos de parseo o recursos de la biblioteca estándar; la
lista no es exhaustiva. Fuente: [DotEnv.__parseValue](../core/dot_env.py),
[EnvironmentCaster.parseTyped y get](../dynamic/caster.py).

#### DotEnv.unset

```python
def unset(
        self,
        key: str,
        *,
        only_os: bool = False,
) -> bool:
```

Valida `key` bajo `_lock`; salvo `only_os=True`, llama a `unset_key` y elimina
la entrada en caché; después ejecuta `os.environ.pop(key, None)`. Devuelve
`True` incluso para una clave ausente o un resultado de la dependencia que
indique que no eliminó nada. Los tipos y nombres de clave inválidos lanzan
`TypeError` y `ValueError`; los errores del sistema de archivos se propagan.
En la dependencia inspeccionada, una clave ausente emite una advertencia del
logger `dotenv.main`, no un mensaje garantizado en stdout. Eliminar solo del
proceso deja `all()` intacto; `reload()` puede restaurar el valor del archivo.

#### DotEnv.all

```python
def all(self) -> dict:
```

Bajo `_lock`, construye un diccionario nuevo parseando cada valor crudo de la
caché. No relee el disco, valida los nombres cargados del archivo ni enumera
claves exclusivas del proceso. Los literales mutables se vuelven a parsear en
contenedores nuevos; mutar el diccionario devuelto no actualiza las cadenas
en caché. Las entradas del archivo vacías o sin valor producen `None`. Una
entrada tipada malformada puede hacer fallar toda la llamada con las mismas
excepciones de decodificación que `get`; no devuelve un diccionario parcial.
La caché privada está anotada como `dict[str, str]`, aunque `dotenv_values`
puede introducir `None` para claves sin valor; aquí prevalece el comportamiento
en ejecución. Fuente: [DotEnv.all](../core/dot_env.py).

#### DotEnv.reload

```python
def reload(self) -> bool:
```

Adquiere `_lock`, ejecuta `load_dotenv(path, override=True)` y sustituye la
caché por `dict(dotenv_values(path))`. Devuelve `True` sin comprobar el resultado
de carga de la dependencia, incluso para un archivo vacío o ausente. No cambia
de archivo ni limpia claves exclusivas del proceso o eliminadas externamente.
Cada `Exception` capturada se envuelve en `RuntimeError` encadenado; un UTF-8
inválido produce una causa `UnicodeDecodeError`. Las dos lecturas no forman una
instantánea transaccional frente a escritores externos. Fuente:
[DotEnv.reload](../core/dot_env.py).

### EnvironmentCaster

Importa desde `orionis.environment.dynamic.caster`. Fuente:
[orionis/environment/dynamic/caster.py](../dynamic/caster.py).

```python
class EnvironmentCaster(IEnvironmentCaster):
```

#### OPTIONS y supportedTypes

```python
OPTIONS: ClassVar[frozenset[str]] = frozenset(e.value for e in EnvironmentValueType)
```

```python
@staticmethod
def supportedTypes() -> frozenset[str]:
```

`OPTIONS` conserva los diez valores del enum calculados al definir la clase.
`supportedTypes()` devuelve el propio `EnvironmentCaster.OPTIONS`, no una copia
ni `cls.OPTIONS`. El objeto es un `frozenset`; el atributo de clase no está
protegido frente a reasignación. El método no tiene parámetros ni hace E/S.
Su docstring Returns indica `set[str]`, mientras la firma y la implementación
devuelven `frozenset[str]`.

#### EnvironmentCaster.__init__

```python
def __init__(
        self,
        raw: str | object,
) -> None:
```

Para una cadena `raw`, conserva `raw.lstrip()`. Si su primer separador dos
puntos delimita un prefijo cuyo `strip().lower()` está en `OPTIONS`, conserva
el tipo normalizado y el contenido sin espacios iniciales. Un contenido
exactamente vacío se almacena como `None`; un prefijo desconocido conserva
la cadena completa sin tipo. Las entradas que no son cadenas se conservan por
referencia sin hint. El constructor no parsea de inmediato, copia contenedores
ni valida la conversión posterior.

La docstring del constructor describe la parte anterior a los dos puntos como
un tipo sin indicar la guarda de prefijos admitidos; la implementación aplica
esa guarda. Fuente: `EnvironmentCaster.__init__` en
[caster.py](../dynamic/caster.py).

#### EnvironmentCaster.parseTyped

```python
@staticmethod
def parseTyped(value_str: str) -> object:
```

`value_str` debe ser una cadena con dos puntos. Recorta y convierte a minúsculas
el prefijo; elimina los espacios iniciales del contenido. `int`, `float`,
`bool` y `str` se parsean directamente sin construir un conversor; otros
prefijos usan el `get()` de un conversor nuevo. Por tanto, los prefijos
desconocidos devuelven texto sin tipo, no una excepción por hint no admitido.
La ausencia del separador lanza el `ValueError` de `str.index`; entradas
inválidas que no son cadenas pueden lanzar `AttributeError` o `TypeError`
antes de la conversión.

| Prefijo | Resultado del camino rápido |
| --- | --- |
| `int` | `int(raw.strip())`; contextualiza el `ValueError` de conversión. |
| `float` | `float(raw.strip())`; contextualiza el `ValueError` de conversión. |
| `bool` | `True` solo para `true`, `1`, `yes`, `on`, `enabled`; **cualquier otro texto**, incluido el vacío, es `False`. |
| `str` | Contenido después de `lstrip()`, incluido `""`; conserva los espacios finales. |

`DotEnv` comprueba un prefijo exacto más estricto antes de llamar a este método.
La llamada directa `parseTyped(" INT :5")` funciona, aunque `Env.get` deja ese
texto almacenado sin parsear. Evidencia:
[DotEnv.__parseValue](../core/dot_env.py) y
[TestEnvironmentCasterParseTyped](../../../tests/environment/dynamic/test_caster.py).

#### EnvironmentCaster.get

```python
def get(  # noqa: PLR0911, PLR0912, C901
        self,
) -> object:
```

Sin argumentos aparte de `self`. Decodifica el valor crudo conservado con el
tipo actual, o lo devuelve intacto si no existe hint. No muta el archivo ni el
proceso. La siguiente tabla describe el parser completo, no el camino rápido
de primitivas:

| Tipo | Resultado y restricciones |
| --- | --- |
| `str` | `raw.lstrip()`; `"str:"` falla porque el constructor conservó `None`. |
| `int`, `float` | Recorta el texto y llama a la conversión numérica incorporada. |
| `bool` | Recorta y convierte a minúsculas; acepta true/1/yes/on/enabled o false/0/no/off/disabled; otras formas lanzan `ValueError`. |
| `list` | `ast.literal_eval`, exige `isinstance(result, list)`; una forma incorrecta produce `TypeError`. |
| `dict`, `tuple`, `set` | Evalúa un literal Python y exige el contenedor correspondiente; los fallos de forma o sintaxis pasan a `ValueError`. El parser incorporado acepta `set()` para un conjunto vacío. |
| `path` | Convierte `Path` a texto POSIX y sustituye barras inversas para cadenas; no resuelve, expande `~` ni vuelve absolutas las rutas relativas. |
| `base64` | Decodifica con `validate=True`; devuelve texto UTF-8 si es decodificable, o `bytes` crudos en otro caso. |

`get()` conserva un `TypeError` capturado como `TypeError` encadenado y un
`ValueError` como `ValueError` encadenado; envuelve las demás excepciones
capturadas en `ValueError`. Su mensaje contextual comienza por
`Error processing value`. Los auxiliares individuales pueden haber cambiado
antes el tipo concreto de excepción. Fuente: `EnvironmentCaster.get` y sus
auxiliares `__parse*` en [caster.py](../dynamic/caster.py).

#### EnvironmentCaster.to

```python
def to(  # noqa: PLR0911, PLR0912, C901
        self,
        type_hint: str | EnvironmentValueType,
) -> str:
```

Acepta un miembro del enum o un valor **exacto en minúsculas** de `OPTIONS`;
a diferencia de `ValidateTypes`, no normaliza mayúsculas ni espacios de los
hints textuales. Devuelve una cadena tipada; toda excepción de conversión o
validación capturada pasa a `ValueError` encadenado, incluidos los `TypeError`
internos. El mensaje comienza por `Error converting value`; el orden del
conjunto de opciones mostrado no es estable.

| Tipo | Entrada admitida y serialización |
| --- | --- |
| `str` | Exige `str`; conserva el contenido retenido tras el procesamiento del constructor. |
| `int` | Usa enteros directamente, o la conversión incorporada `int`; `True` entra en la rama de enteros y produce `"int:True"`, que no se decodifica numéricamente. |
| `float` | Usa floats directamente, o la conversión incorporada `float`. |
| `bool` | Booleanos directamente; vocabulario booleano textual admitido; otros objetos mediante `bool(value)`. |
| `list`, `dict`, `tuple`, `set` | Exige `isinstance` del contenedor correspondiente y admite subclases; usa `repr`, no conversión de elementos ni JSON. |
| `path` | Exige `str` o `Path`; recorta y normaliza las barras, une las entradas relativas a `Path.cwd()` y después llama a `expanduser().as_posix()`. No llama a `resolve()` ni crea nada. |
| `base64` | Exige `str` o `bytes` decodificables como UTF-8; conserva un candidato Base64 ya válido, o lo codifica en Base64. Rechaza bytes crudos no UTF-8 antes de codificar. |

La ruta relativa `~/file` se une al directorio de trabajo **antes** de
`expanduser`, así que no se expande al directorio del usuario. `a/../file`
conserva el componente `..`. Un texto que parezca Base64 puede tratarse como
entrada codificada; no es un codificador incondicional de binarios arbitrarios.
Evidencia: `__toPath`, `__toBase64` y `__toInt` en
[caster.py](../dynamic/caster.py).

El estado importa: tras validar el hint, `to()` lo asigna a la instancia,
pero **no** sustituye el valor crudo original por la salida serializada. El
tipo puede quedar cambiado después de un fallo de conversión. Un `get()`
posterior interpreta el valor crudo original con ese tipo nuevo y puede fallar.
Para decodificar la cadena emitida, construye otro conversor o usa `parseTyped`.
Las entradas que no son cadenas conservadas por referencia pueden reflejar
mutaciones posteriores del llamador.

### EnvironmentValueType

Importa desde `orionis.environment.enums` o
`orionis.environment.enums.value_type`. Fuente:
[orionis/environment/enums/value_type.py](../enums/value_type.py).

```python
class EnvironmentValueType(Enum):
```

Asignaciones literales de miembros en el orden original:

```python
BASE64 = "base64"
PATH = "path"
STR = "str"
INT = "int"
FLOAT = "float"
BOOL = "bool"
LIST = "list"
DICT = "dict"
TUPLE = "tuple"
SET = "set"
```

Es `enum.Enum`, no `StrEnum`; sus miembros tienen `.name` y `.value` estándar
y no son iguales a sus cadenas. La búsqueda por valor generada por el enum,
`EnvironmentValueType("int")`, distingue mayúsculas y lanza `ValueError` para
valores desconocidos; la búsqueda por nombre `EnvironmentValueType["INT"]`
lanza `KeyError` para nombres desconocidos. No declara un constructor explícito.
Pruebas: [test_value_type.py](../../../tests/environment/enums/test_value_type.py).

### ValidateKeyName

Importa desde `orionis.environment.validators` o
`orionis.environment.validators.key_name`. Fuente:
[orionis/environment/validators/key_name.py](../validators/key_name.py).
El nombre público es un alias, no una definición separada `def ValidateKeyName`:

```python
@functools.lru_cache(maxsize=512)
def _validate_key_name(key: str) -> str:
```

```python
ValidateKeyName = _validate_key_name
```

`ValidateKeyName(key)` exige `str` y una coincidencia completa de
`^[A-Z][A-Z0-9_]*$`. La primera letra debe ser ASCII mayúscula; después solo se
admiten letras ASCII mayúsculas, dígitos y guiones bajos. No recorta ni cambia
mayúsculas. Devuelve la cadena validada; un texto vacío, `_` o dígito inicial,
letras no ASCII, minúsculas y salto de línea final lanzan `ValueError`. Las
claves que no son cadenas lanzan `TypeError`; las no hashables pueden fallar
en el wrapper de caché antes del cuerpo.

El alias expone los métodos heredados del wrapper `cache_info()`,
`cache_parameters()` y `cache_clear()`; provienen de `functools.lru_cache`, no
de métodos escritos manualmente en el módulo. Los resultados exitosos retienen
referencias a claves en una LRU del proceso de 512 entradas; las excepciones
no se cachean. Pruebas:
[test_key_name.py](../../../tests/environment/validators/test_key_name.py).

### ValidateTypes

Importa desde `orionis.environment.validators` o
`orionis.environment.validators.types`. Fuente:
[orionis/environment/validators/types.py](../validators/types.py).
Este invocable público es una instancia, no una declaración de función:

```python
ValidateTypes = __ValidateTypes()
```

La cabecera literal de la implementación de su llamada es:

```python
def __call__(
        self,
        *,
        value: str | float | bool | list | dict | tuple | set,
        type_hint: str | EnvironmentValueType | None = None,
) -> str:
```

Llama a `ValidateTypes(value=..., type_hint=...)` con argumentos solo por nombre.
Valida `value` mediante `isinstance` frente a str/int/float/bool/list/dict/tuple/set;
los valores no admitidos, incluidos `None`, `bytes` y `Path`, lanzan `TypeError`.
Valida los hints aunque sean falsos: si no son cadena ni enum, lanza `TypeError`;
un nombre textual de miembro desconocido, vacío o con espacios lanza
`RuntimeError`.

Un hint indicado se busca con `EnvironmentValueType[type_hint.upper()]` y se
devuelve como su `.value` en minúsculas; los miembros del enum devuelven su
`.value`. Sin hint, devuelve `type(value).__name__.lower()`; por ello, las
subclases pueden producir nombres fuera del catálogo del enum. **No** valida
la compatibilidad entre el tipo y el valor:
`ValidateTypes(value=42, type_hint="str")` devuelve `"str"`, mientras
`EnvironmentCaster(42).to("str")` falla.

El auxiliar privado `_normalize_type_hint` tiene una LRU de 64 entradas
indexada por el argumento hint original, incluidas su escritura e identidad
del enum. La validación del valor se ejecuta en cada llamada; el objeto público
no tiene API `cache_info()` ni `cache_clear()`. Pruebas:
[test_types.py](../../../tests/environment/validators/test_types.py).

### SecureKeyGenerator

Importa desde `orionis.environment.key.key_generator`. Fuente:
[orionis/environment/key/key_generator.py](../key/key_generator.py).
El `Cipher` relacionado pertenece a
[orionis.foundation.config.app.enums.ciphers](../../foundation/config/app/enums/ciphers.py),
no es un enum de environment.

```python
class SecureKeyGenerator:
```

```python
KEY_SIZES: ClassVar[dict[Cipher, int]] = {
        Cipher.AES_128_CBC: 16,
        Cipher.AES_256_CBC: 32,
        Cipher.AES_128_GCM: 16,
        Cipher.AES_256_GCM: 32,
}
```

```python
@staticmethod
def generate(cipher: str | Cipher = Cipher.AES_256_CBC) -> str:
```

Acepta un miembro de `Cipher` o su valor exacto, sensible a mayúsculas
(`AES-128-CBC`, `AES-256-CBC`, `AES-128-GCM`, `AES-256-GCM`). El valor
predeterminado `Cipher.AES_256_CBC` obtiene 32 bytes. Busca el tamaño en
`KEY_SIZES`, llama a `os.urandom`, codifica los bytes en Base64 y devuelve
una cadena con prefijo `base64:`. No persiste, muta el entorno, cifra datos,
conserva estado de instancia ni cachea claves aleatorias.

Los cifrados textuales inválidos y los objetos hashables no admitidos lanzan
`ValueError` explícito; un objeto no hashable puede lanzar `TypeError` en la
búsqueda del diccionario. No traduce los errores de la fuente aleatoria ni de
la codificación estándar. `KEY_SIZES` es un diccionario de clase mutable
consultado en cada llamada; no implementa copia, congelación ni sincronización
de modificaciones. Pruebas:
[test_key_generator.py](../../../tests/environment/key/test_key_generator.py).

### IEnv

Importa desde `orionis.environment.contracts.env`. Fuente:
[orionis/environment/contracts/env.py](../contracts/env.py).

```python
class IEnv(ABC):
```

```python
@classmethod
@abstractmethod
def get(
        cls,
        key: str,
        default: object | None = None,
) -> object:
```

```python
@classmethod
@abstractmethod
def set(
        cls,
        key: str,
        value: str | float | bool | list | dict | tuple | set,
        type_hint: str | EnvironmentValueType | None = None,
        *,
        only_os: bool = False,
) -> bool:
```

```python
@classmethod
@abstractmethod
def unset(
        cls,
        key: str,
        *,
        only_os: bool = False,
) -> bool:
```

```python
@classmethod
@abstractmethod
def all(
        cls,
) -> dict[str, Any]:
```

```python
@classmethod
@abstractmethod
def reload(cls) -> bool:
```

ABC con `__slots__ = ()`, sin constructor explícito ni implementación aparte
de cuerpos abstractos formados solo por docstrings. La instanciación directa
o incompleta lanza el `TypeError` del mecanismo ABC. Los parámetros y resultados
declarados coinciden con `Env`; lectura, serialización, mutación y excepciones
pertenecen a la implementación concreta, no a un cuerpo ejecutable de este
contrato. Las docstrings de set/unset admiten `False`, mientras los métodos
concretos devuelven `True` al completar normalmente. Pruebas:
[test_env.py](../../../tests/environment/contracts/test_env.py).

### IEnvironmentCaster

Importa desde `orionis.environment.contracts.caster`. Fuente:
[orionis/environment/contracts/caster.py](../contracts/caster.py).

```python
class IEnvironmentCaster(ABC):
```

```python
@abstractmethod
def get(
        self,
) -> object:
```

```python
@abstractmethod
def to(
        self,
        type_hint: str | EnvironmentValueType,
) -> str:
```

ABC con `__slots__ = ()` y sin constructor explícito. Sus dos cuerpos abstractos
solo contienen docstrings; el `TypeError` de ABC impide instanciarla de forma
directa o incompleta. El resultado de `get` y el parámetro, resultado y
contratos documentados `ValueError`/`TypeError` de `to` los implementa
`EnvironmentCaster`; el wrapper concreto de `to` convierte los `TypeError`
internos en `ValueError`. Pruebas:
[test_caster.py](../../../tests/environment/contracts/test_caster.py).

## Ejemplos de uso

Cada bloque es un **script independiente en un proceso nuevo** para el framework
local instalado con Python 3.14+. Los directorios temporales, el directorio de
trabajo y las variables del proceso se restauran. No concatentes los scripts
en un mismo proceso: restaurar el directorio de trabajo no cambia el archivo
del singleton ya seleccionado, y su archivo temporal deja de existir tras
limpiar. Los scripts no arrancan una aplicación, contactan servicios ni necesitan
credenciales privadas.

### Leer y persistir valores

Escribe un valor, observa las tres vistas, oculta solo el valor del proceso y
recarga. Las aserciones comprueban la diferencia entre clave ausente y valor
equivalente a nulo.

```python
import os
import tempfile
from pathlib import Path

previous_cwd = Path.cwd()
previous_environment = dict(os.environ)
with tempfile.TemporaryDirectory() as temporary:
    try:
        os.chdir(temporary)
        from orionis.environment import Env, env

        assert Env.set("DOC_VALUE", "Orionis") is True
        assert env("DOC_VALUE") == "Orionis"
        assert Env.all()["DOC_VALUE"] == "Orionis"
        assert "DOC_VALUE=" in Path(".env").read_text(encoding="utf-8")
        assert Env.unset("DOC_VALUE", only_os=True) is True
        fallback = ["int:5"]
        assert Env.get("DOC_VALUE", fallback) is fallback
        assert Env.all()["DOC_VALUE"] == "Orionis"
        assert Env.reload() is True
        assert Env.get("DOC_VALUE") == "Orionis"
        os.environ["DOC_EMPTY"] = ""
        assert Env.get("DOC_EMPTY", "fallback") is None
        assert Env.unset("DOC_VALUE") is True
        assert "DOC_VALUE" not in Env.all()
    finally:
        os.environ.clear()
        os.environ.update(previous_environment)
        os.chdir(previous_cwd)
```

### Guardar valores tipados

Ejercita todos los tipos mediante escrituras exclusivas del proceso. El servicio
inicial sigue creando su `.env` temporal; ninguno de estos valores se añade al
archivo en caché.

```python
import os
import tempfile
from pathlib import Path

previous_cwd = Path.cwd()
previous_environment = dict(os.environ)
with tempfile.TemporaryDirectory() as temporary:
    try:
        os.chdir(temporary)
        from orionis.environment import Env
        from orionis.environment.enums import EnvironmentValueType

        values = (
            ("DOC_TEXT", "42", "str", "42"),
            ("DOC_NUMBER", 42, "int", 42),
            ("DOC_RATIO", 2.5, "float", 2.5),
            ("DOC_FLAG", True, "bool", True),
            ("DOC_LIST", [1, 2], "list", [1, 2]),
            ("DOC_DICT", {"active": True}, "dict", {"active": True}),
            ("DOC_TUPLE", (1, 2), "tuple", (1, 2)),
            ("DOC_SET", {1, 2}, "set", {1, 2}),
            ("DOC_PATH", "logs", "path", (Path.cwd() / "logs").as_posix()),
            ("DOC_BASE64", "hi!", "base64", "hi!"),
        )
        for key, value, hint, expected in values:
            assert Env.set(key, value, hint, only_os=True) is True
            assert Env.get(key) == expected
            assert key not in Env.all()
        Env.set("DOC_ENUM", [3], EnvironmentValueType.LIST, only_os=True)
        assert Env.get("DOC_ENUM") == [3]
        Env.set("DOC_UNTYPED", "42", only_os=True)
        assert Env.get("DOC_UNTYPED") == 42
        os.environ["DOC_CASE"] = "INT:5"
        assert Env.get("DOC_CASE") == "INT:5"
    finally:
        os.environ.clear()
        os.environ.update(previous_environment)
        os.chdir(previous_cwd)
```

### Manejar errores reales de validación

Comprueba los validadores invocables públicos y tres categorías distintas de
excepción. Ninguna aserción depende del orden inestable del conjunto de opciones
en un error.

```python
import os
import tempfile
from pathlib import Path

previous_cwd = Path.cwd()
previous_environment = dict(os.environ)
with tempfile.TemporaryDirectory() as temporary:
    try:
        os.chdir(temporary)
        from orionis.environment import Env
        from orionis.environment.validators import ValidateKeyName, ValidateTypes

        assert ValidateKeyName("DOC_VALID") == "DOC_VALID"
        assert ValidateKeyName.cache_parameters()["maxsize"] == 512
        assert ValidateTypes(value=42, type_hint="INT") == "int"
        failures = []
        try:
            Env.get("lower_case")
        except ValueError:
            failures.append("name")
        try:
            Env.set("DOC_BYTES", b"payload", "base64", only_os=True)
        except TypeError:
            failures.append("value")
        try:
            Env.set("DOC_HINT", "value", "decimal", only_os=True)
        except RuntimeError:
            failures.append("hint")
        os.environ["DOC_BROKEN"] = "int:abc"
        try:
            Env.get("DOC_BROKEN")
        except ValueError:
            failures.append("decode")
        assert failures == ["name", "value", "hint", "decode"]
        assert "DOC_BYTES" not in os.environ
    finally:
        os.environ.clear()
        os.environ.update(previous_environment)
        os.chdir(previous_cwd)
```

### Usar el conversor directamente

Contrasta los parsers rápido y completo, decodifica mediante una instancia
nueva, y comprueba la decodificación binaria, las rutas relativas y el valor
crudo conservado después de `to()`.

```python
import os
import tempfile
from pathlib import Path

previous_cwd = Path.cwd()
with tempfile.TemporaryDirectory() as temporary:
    try:
        os.chdir(temporary)
        from orionis.environment.dynamic.caster import EnvironmentCaster

        payload = {"ports": [8000, 8001]}
        encoded = EnvironmentCaster(payload).to("dict")
        assert EnvironmentCaster(encoded).get() == payload
        assert EnvironmentCaster.supportedTypes() is EnvironmentCaster.OPTIONS
        assert EnvironmentCaster("  INT :5").get() == 5
        assert EnvironmentCaster.parseTyped("bool:maybe") is False
        try:
            EnvironmentCaster("bool:maybe").get()
        except ValueError:
            pass
        else:
            raise AssertionError("The full boolean parser must reject maybe")
        assert EnvironmentCaster.parseTyped("str:") == ""
        assert EnvironmentCaster("base64:/w==").get() == b"\xff"
        assert EnvironmentCaster("path:logs\\app").get() == "logs/app"
        stored_path = EnvironmentCaster("logs/app").to("path")
        assert stored_path == "path:" + (Path.cwd() / "logs/app").as_posix()
        caster = EnvironmentCaster("hi!")
        assert caster.to("base64") == "base64:aGkh"
        try:
            caster.get()
        except ValueError:
            pass
        else:
            raise AssertionError("The retained plaintext is not Base64")
    finally:
        os.chdir(previous_cwd)
```

### Generar claves

Genera material aleatorio temporal sin mostrarlo ni persistirlo. Valida el
tamaño decodificado de cada cifrado y rechaza un cifrado realmente no admitido.

```python
import base64
import os
import tempfile
from pathlib import Path

previous_cwd = Path.cwd()
with tempfile.TemporaryDirectory() as temporary:
    try:
        os.chdir(temporary)
        from orionis.environment.key.key_generator import SecureKeyGenerator
        from orionis.foundation.config.app.enums.ciphers import Cipher

        for cipher, expected_size in SecureKeyGenerator.KEY_SIZES.items():
            generated = SecureKeyGenerator.generate(cipher)
            assert generated.startswith("base64:")
            raw = base64.b64decode(generated[7:], validate=True)
            assert len(raw) == expected_size
        generated = SecureKeyGenerator.generate(Cipher.AES_256_CBC.value)
        assert len(base64.b64decode(generated[7:], validate=True)) == 32
        try:
            SecureKeyGenerator.generate("AES-512-CBC")
        except ValueError:
            pass
        else:
            raise AssertionError("Unsupported cipher must fail")
        assert not Path(".env").exists()
    finally:
        os.chdir(previous_cwd)
```

### Integrar con la configuración App

Construye la entidad **real** `App`. Los campos basados en el entorno se leen
al construir la entidad; cambiar el entorno del proceso no actualiza una
entidad congelada existente. Los bytes explícitos de clave válidos evitan
una generación de claves ajena al ejemplo.

```python
import os
import tempfile
from pathlib import Path

previous_cwd = Path.cwd()
previous_environment = dict(os.environ)
with tempfile.TemporaryDirectory() as temporary:
    try:
        os.chdir(temporary)
        from orionis.environment import Env
        from orionis.foundation.config.app.entities.app import App
        from orionis.foundation.config.app.enums.ciphers import Cipher

        for key in (
            "APP_NAME", "APP_ENV", "APP_DEBUG", "APP_TIMEZONE", "APP_LOCALE",
            "APP_FALLBACK_LOCALE", "APP_LANGUAGE_PATH", "APP_MAINTENANCE",
        ):
            os.environ.pop(key, None)
        Env.set("APP_NAME", "Environment example", "str", only_os=True)
        Env.set("APP_DEBUG", False, "bool", only_os=True)
        settings = App(cipher=Cipher.AES_256_CBC, key=b"x" * 32)
        assert settings.name == "Environment example"
        assert settings.debug is False
        assert settings.key == b"x" * 32
        Env.set("APP_NAME", "Second snapshot", "str", only_os=True)
        newer = App(cipher=Cipher.AES_256_CBC, key=b"x" * 32)
        assert newer.name == "Second snapshot"
        assert settings.name == "Environment example"
    finally:
        os.environ.clear()
        os.environ.update(previous_environment)
        os.chdir(previous_cwd)
```

### Archivo personalizado, recarga y recuperación

Combina primera construcción personalizada, interpolación, sobrescrituras
exclusivas del proceso, claves retiradas del archivo, la fábrica heredada y
recuperación ante UTF-8 inválido. El `RuntimeError` es un fallo observado
esperado, no se convierte silenciosamente en `False`.

```python
import asyncio
import os
import tempfile
from pathlib import Path

previous_cwd = Path.cwd()
previous_environment = dict(os.environ)
with tempfile.TemporaryDirectory() as temporary:
    try:
        os.chdir(temporary)
        os.environ.pop("PYTHON_DOTENV_DISABLED", None)
        from orionis.environment import Env
        from orionis.environment.core.dot_env import DotEnv

        selected = Path("settings.env")
        selected.write_text(
            "DOC_ROOT=site\nDOC_URL=${DOC_ROOT}/api\nDOC_RETRIES=int:2\n"
            "DOC_LEGACY=retained\nDOC_BARE\n",
            encoding="utf-8",
        )
        manager = DotEnv(str(selected))
        assert DotEnv("ignored.env") is manager
        assert not Path("ignored.env").exists()
        assert not Path(".env").exists()
        assert Env.get("DOC_URL") == "site/api"
        assert Env.all()["DOC_BARE"] is None
        Env.set("DOC_RETRIES", 9, "int", only_os=True)
        assert Env.get("DOC_RETRIES") == 9
        assert Env.all()["DOC_RETRIES"] == 2
        selected.write_text("DOC_RETRIES=int:3\nDOC_BARE\n", encoding="utf-8")
        assert Env.reload() is True
        assert Env.get("DOC_RETRIES") == 3
        assert "DOC_LEGACY" not in Env.all()
        assert Env.get("DOC_LEGACY") == "retained"
        assert asyncio.run(DotEnv.__acall__()) is manager
        selected.write_bytes(b"DOC_BROKEN=\xff\xfe\n")
        try:
            Env.reload()
        except RuntimeError as failure:
            assert isinstance(failure.__cause__, UnicodeDecodeError)
        else:
            raise AssertionError("Invalid UTF-8 must fail the reload")
        selected.write_text("DOC_RETRIES=int:4\n", encoding="utf-8")
        assert Env.reload() is True
        assert Env.get("DOC_RETRIES") == 4
        assert Env.unset("DOC_LEGACY", only_os=True) is True
    finally:
        os.environ.clear()
        os.environ.update(previous_environment)
        os.chdir(previous_cwd)
```

## Características de diseño

- Métodos de clase de `Env` más delegación de `env()` -> ninguna resolución del
  contenedor por llamada; ambos usan el mismo `DotEnv`. Fuente:
  [facade.py](../facade.py), [functions.py](../functions.py).
- Metaclase `Singleton` -> estado de construcción por clase y argumentos
  posteriores ignorados; `reload` muta la instancia existente. Fuente:
  [singleton/meta.py](../../support/patterns/singleton/meta.py).
- `DotEnv.__slots__`, `EnvironmentCaster.__slots__` y slots vacíos en `Env`,
  `SecureKeyGenerator` y ambas ABC -> estas instancias concretas no tienen
  diccionario de instancia. No se afirma lo mismo del enum ni del invocable
  privado.
- Referencias crudas conservadas y hint mutable del conversor -> un conversor
  es estado reutilizable, no un resultado inmutable de códec. Fuente:
  [caster.py](../dynamic/caster.py).
- Parseo de literales Python y prefijos explícitos -> no hay esquema JSON,
  validación recursiva de tipos de elementos ni garantía de que cualquier
  `repr()` sea decodificable. Fuente: `DotEnv.__parseValue` y auxiliares
  `__parse*`/`__to*` del conversor.
- `SecureKeyGenerator.KEY_SIZES` mutable -> el llamador accede a un diccionario
  compartido, no a una instantánea congelada de configuración. Fuente:
  [key_generator.py](../key/key_generator.py).

## Rendimiento y concurrencia

- `get()` lee memoria del proceso después de inicializar; decodificar sigue
  creando objetos y puede parsear literales en cada llamada. `all()` materializa
  un diccionario nuevo y reparsea cada entrada; el trabajo crece con las entradas
  y sus tamaños. Fuente: [DotEnv.get, all y __parseValue](../core/dot_env.py).
- La construcción inicial y `reload` llaman tanto a `load_dotenv` como a
  `dotenv_values`: dos parseos síncronos del archivo, con interpolación activada
  por la dependencia. Set/unset persistentes reescriben el archivo; no son
  actualizaciones escalares in situ.
- Las ramas primitivas de `parseTyped` no construyen `EnvironmentCaster`;
  **no** implica ausencia de asignaciones. Los valores complejos construyen
  un conversor y parsean o convierten su contenido. Fuente:
  [parseTyped](../dynamic/caster.py).
- `ValidateKeyName` conserva entradas exitosas en una LRU de 512, indexada por
  argumentos de llamada. `_normalize_type_hint` conserva 64 argumentos hint
  originales, no valores ni lecturas completas del entorno; las variantes de
  mayúsculas ocupan entradas distintas. Ambas usan expulsión LRU estándar y
  solo exponen los controles descritos en sus respectivas secciones de API.
  No hay caché de lecturas decodificadas.
- `DotEnv._lock` serializa su construcción y cinco operaciones públicas en
  este proceso. La fábrica singleton tiene un bloqueo separado por clase.
  Ninguno coordina mutaciones directas de `os.environ`, ediciones externas del
  archivo u otros procesos. Estos mecanismos no establecen seguridad global
  entre hilos ni una transacción entre las vistas del proceso, caché y archivo.
- `dotenv.main.rewrite` de `python-dotenv` 1.2.4 instalado escribe un temporal
  con nombre único en el directorio de destino y usa `os.replace`. Limpia los
  temporales fallidos, pero no hace bloqueo de lectura-modificación-escritura
  entre procesos ni un paso de durabilidad con fsync. En Windows puede propagarse
  `PermissionError` al reemplazar. Son observaciones de esa versión de la
  dependencia, no una garantía para todas las versiones futuras permitidas;
  el módulo simplemente llama a `set_key`/`unset_key`.
- El módulo no define `async def`. Las llamadas pueden bloquear un event loop
  en `threading.Lock` y E/S de archivos. La fábrica heredada
  `Singleton.__acall__` se puede esperar, pero construye síncronamente; no
  desplaza la E/S a otro hilo.

Evidencia: [dot_env.py](../core/dot_env.py), [caster.py](../dynamic/caster.py),
[key_name.py](../validators/key_name.py), [types.py](../validators/types.py) y
[Singleton](../../support/patterns/singleton/meta.py). Las funciones de la
dependencia se inspeccionaron en `python-dotenv` 1.2.4 instalado; su rango
declarado y archivo de bloqueo se indican a continuación. No se hicieron
benchmarks.

> ⚠️ No especificado en el código fuente: un contrato de concurrencia para
> compartir una instancia mutable de `EnvironmentCaster` o mutar
> `SecureKeyGenerator.KEY_SIZES` mientras se usa. Estas clases no sincronizan
> ninguna de las dos operaciones.

## Notas de compatibilidad

| Aspecto | Evidencia verificada |
| --- | --- |
| Mínimo declarado del framework | `requires-python = ">=3.14"` en [pyproject.toml](../../../pyproject.toml). |
| Sintaxis observada | Anotaciones genéricas incorporadas y uniones `X | Y`; varios archivos usan anotaciones pospuestas, pero el enum y los inicializadores no. Esto por sí solo no establece soporte del framework para Python anterior. |
| Intérprete de validación | CPython 3.14.6, Windows, entorno virtual del repositorio. |
| Dependencia obligatoria | `python-dotenv>=1.2.3,<2.0` en [pyproject.toml](../../../pyproject.toml); no hay extra ni paso de instalación específico del módulo. |
| Dependencia resuelta | `python-dotenv` 1.2.4 en [uv.lock](../../../uv.lock); la versión instalada de validación también es 1.2.4. No es una declaración de versión mínima. |
| Biblioteca estándar | `os`, `ast`, `pathlib`, `threading`, `functools`, `re`, `base64`, `enum`, `abc` y `typing`, según los imports de las fuentes enumeradas. |
| Dependencias directas de Orionis | [Singleton](../../support/patterns/singleton/meta.py) y [Cipher](../../foundation/config/app/enums/ciphers.py). |

Los valores predeterminados de la dependencia usados por esta implementación
son UTF-8, `interpolate=True` y, para `set_key`, `quote_mode="always"`. Los
valores se persisten entre comillas simples; `${OTHER}` se interpola al cargar,
incluidos los valores escritos mediante `set`. Por ello, el valor serializado
inmediato de caché/proceso puede diferir del valor después de recargar. Las
líneas inválidas y la eliminación de claves ausentes pueden emitir advertencias
del logger de la dependencia; una línea malformada no garantiza una excepción
de Orionis.

`PYTHON_DOTENV_DISABLED` puede impedir la carga al proceso de la dependencia,
mientras `dotenv_values` sigue construyendo la caché; Orionis no comprueba el
resultado booleano del cargador. Se inspeccionó este comportamiento en
`dotenv.main.load_dotenv` 1.2.4. Las rutas explícitas y la conversión `path`
siguen la semántica de `pathlib` del sistema anfitrión; los separadores POSIX
no implican un sistema de archivos POSIX ni validez entre plataformas. No
proporciona aislamiento de archivos, validación de traversal ni expansión
universal del directorio del usuario.

## Verificación y limitaciones

### Cobertura y fidelidad al código

El inventario cubre 17 archivos Python del módulo y diez símbolos públicos
principales: `Env`, `env`, `DotEnv`, `EnvironmentCaster`, `EnvironmentValueType`,
`ValidateKeyName`, `ValidateTypes`, `SecureKeyGenerator`, `IEnv` e
`IEnvironmentCaster`. Incluye sus métodos y constructores explícitos, diez
miembros del enum, dos constantes de clase, dos asignaciones invocables públicas
y reexportaciones. Hay 48 entradas de referencia del código más la fábrica
singleton heredada. Los símbolos privados y las dependencias importadas se
excluyen por los motivos indicados en
[Estructura del módulo](#estructura-del-módulo), no por una carencia de cobertura
pública.

La inspección del código prevaleció sobre la documentación y docstrings
anteriores. Las diferencias relevantes son la escritura sin hint permisiva,
el resultado frozenset, la guarda de prefijos del constructor, el parseo
booleano no uniforme y los resultados exitosos concretos de set/unset. La
creación de `.env`/`APP_KEY` al importar y las reescrituras de la dependencia
descritas como incondicionalmente no atómicas en la documentación anterior no
corresponden a la implementación actual inspeccionada.

### Comprobaciones ejecutables

En una validación con escrituras al repositorio bloqueadas, las comprobaciones
de ejecución pasaron para imports locales, primera construcción con archivo
personalizado, divergencia proceso/caché, identidad del predeterminado,
conservación en el proceso de claves retiradas, normalización de hints,
diferencias de parsers booleanos y cadenas vacías, `None` con y sin hint,
restricciones Base64, mutación del conversor, orden de rutas, límites de caché,
slots y errores de recarga UTF-8.

La suite existente [tests/environment](../../../tests/environment) se ejecutó
mediante el flujo nativo `Application.boot -> TestingEngine.run -> TestRunner.run`,
con 11 copias de archivos de prueba idénticas byte a byte fuera del checkout:
**210 pruebas exitosas, cero fallos, cero errores y cero omisiones**. Se
comprobaron las colecciones crudas de fallos y errores del runner, no solo el
resumen impreso. El bytecode, los archivos de aplicación, fixtures e informes
se mantuvieron fuera del repositorio; no se instalaron dependencias.

| Ejemplo | Sintaxis | Imports locales | Estado de ejecución |
| --- | --- | --- | --- |
| Leer y persistir valores | Correcta | Código local verificado | Ejecutado correctamente |
| Guardar valores tipados | Correcta | Código local verificado | Ejecutado correctamente |
| Manejar errores reales de validación | Correcta | Código local verificado | Ejecutado correctamente |
| Usar el conversor directamente | Correcta | Código local verificado | Ejecutado correctamente |
| Generar claves | Correcta | Código local verificado | Ejecutado correctamente |
| Integrar con la configuración App | Correcta | Código local verificado | Ejecutado correctamente |
| Archivo personalizado, recarga y recuperación | Correcta | Código local verificado | Ejecutado correctamente |

Los siete scripts se extrajeron literalmente del README inglés, se compilaron
por separado y se ejecutaron en subprocesos individuales, con escrituras al
checkout bloqueadas y conexiones externas desactivadas. Los módulos de Orionis
cargados se resolvieron al código local; cada script terminó con código 0 y
completó todas las aserciones; stdout y stderr quedaron vacíos. No se mostró
ninguna clave del entorno ni material de claves generado. Las 48 entradas de
referencia coincidieron con el inventario. Se resolvieron los 106 enlaces de
cada README y las 18 referencias del skill, incluidas sus anclas internas. El
par de README tiene 48 encabezados equivalentes y 47 bloques de código idénticos.
El frontmatter del skill se parseó como YAML válido con exactamente `name` y
`description`, y se verificó su nombre `orionis-environment`. El directorio de
salida contiene exactamente los dos README y el skill, sin subdirectorios ni
artefactos de validación.

### Límites de la verificación

La validación usó CPython 3.14.6 y `python-dotenv` 1.2.4. No se ejecutaron
otras versiones permitidas de dependencias, otros sistemas operativos ni
intérpretes sin GIL. Los bloqueos inspeccionados describen coordinación, no
una certificación ejecutada de estrés multihilo o multiproceso. No se usaron
benchmarks, servicios externos ni credenciales reales. El módulo no tiene
excepciones propias; no se enumeran exhaustivamente los fallos propagados
de dependencias, tipos incorporados y objetos del usuario.

> ⚠️ No ejecutado en este entorno: escritores concurrentes en múltiples
> procesos, durabilidad ante pérdida de energía y validación en plataformas
> o versiones de dependencias distintas de las registradas. No se infieren
> resultados ni garantías para esos escenarios.

[SKILL.md](SKILL.md) es un punto de entrada documental local llamado
`orionis-environment`; su ubicación aquí no instala ni registra automáticamente
un skill.

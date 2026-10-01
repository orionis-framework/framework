# Orionis Formatter (`orionis.support.formatter`)

> Serializador de excepciones a diccionario (`Parser` / `ExceptionParser`) que convierte cualquier excepción de Python en un diccionario estructurado apto para JSON, con tipo, mensaje, código de error y una traza de pila anotada (incluyendo las líneas de código fuente circundantes).
>
> 🇬🇧 English version: [README.md](README.md)

`orionis.support.formatter` provee una pequeña utilidad enfocada para
convertir una `Exception` capturada en un `dict` estructurado, apto para
registro (logging), respuestas de error HTTP, o serialización JSON. Lo
usan las respuestas de error HTTP por defecto del framework
(`orionis.http.default.responses`) para construir payloads de error
consistentes, pero no depende de la capa HTTP y puede usarse en
cualquier lugar donde una excepción deba convertirse en datos
estructurados.

---

## Tabla de contenidos

1. [Requisitos](#requisitos)
2. [Descripción funcional del módulo](#descripción-funcional-del-módulo)
3. [Referencia de API](#referencia-de-api)
   - [`Parser`](#parser-orionissupportformatterserializerparser)
   - [`ExceptionParser`](#exceptionparser-orionissupportformatterexceptionsparserexceptionparser)
   - [Contrato (`IExceptionParser`)](#contrato-iexceptionparser)
4. [Ejemplos de uso](#ejemplos-de-uso)
5. [Consideraciones de rendimiento y concurrencia](#consideraciones-de-rendimiento-y-concurrencia)
6. [Notas de diseño](#notas-de-diseño)
7. [Notas de compatibilidad](#notas-de-compatibilidad)

---

## Requisitos

No se necesita instalación adicional además del propio framework:

```bash
uv add orionis
```

- **Python:** 3.14 o superior (el mismo mínimo que el resto del framework).
- **Dependencias:** ninguna más allá de la librería estándar de Python
  (`traceback`, `linecache`, `typing`).

## Descripción funcional del módulo

| Tipo | Archivo | Propósito |
|---|---|---|
| `Parser` | [serializer.py](../serializer.py) | Fábrica mínima: `Parser.exception(exception)` construye un `ExceptionParser` para la excepción dada. |
| `ExceptionParser` | [exceptions/parser.py](../exceptions/parser.py) | Hace el trabajo real: captura la traza (traceback) de la excepción en el momento de construirse y expone `toDict()` para renderizarla como un diccionario plano. |
| `IExceptionParser` | [exceptions/contracts/parser.py](../exceptions/contracts/parser.py) | `typing.Protocol` que describe el contrato `toDict()` que `ExceptionParser` satisface estructuralmente. |

Flujo típico: capturar una excepción → `Parser.exception(exc)` →
`.toDict()` → pasar el `dict` resultante a un logger, una respuesta de
error HTTP, o `json.dumps`.

---

## Referencia de API

### `Parser` (`orionis.support.formatter.serializer.Parser`)

```python
class Parser:
    @staticmethod
    def exception(exception: Exception) -> ExceptionParser: ...
```

| Método | Firma | Descripción |
|---|---|---|
| `exception` | `exception(exception: Exception) -> ExceptionParser` *(staticmethod)* | Instancia y devuelve un `ExceptionParser` que envuelve la `exception` dada. Acepta cualquier subclase de `Exception`. |

### `ExceptionParser` (`orionis.support.formatter.exceptions.parser.ExceptionParser`)

```python
ExceptionParser(exception: Exception) -> None
```

Un objeto basado en `__slots__` (`_cache`, `_error_code`, `_exc_type`,
`_tb`) que parsea **de forma anticipada (eager)** los metadatos de la
traza de la excepción en `__init__` — usando
`traceback.TracebackException.from_exception(exception,
capture_locals=False)` — de modo que llamar a `toDict()` después no
repite ese trabajo.

| Método | Firma | Descripción |
|---|---|---|
| `__init__` | `__init__(exception: Exception) -> None` | Captura la traza (`traceback.TracebackException`, sin variables locales), resuelve el nombre del tipo de excepción, y lee un atributo opcional `code` de la excepción (`getattr(exception, "code", None)`) como código de error. |
| `toDict` | `toDict() -> dict[str, Any]` | Serializa la excepción en un diccionario (ver claves abajo). El resultado se calcula una sola vez y se cachea internamente; las llamadas posteriores devuelven el mismo objeto `dict` sin cómputo adicional. |

`toDict()` devuelve un diccionario con estas claves:

| Clave | Tipo | Descripción |
|---|---|---|
| `error_type` | `str` | El nombre de la clase de la excepción (p. ej. `"ValueError"`). |
| `error_message` | `str` | El texto de traza formateado (`str(TracebackException)`, recortado a la derecha). |
| `error_code` | `Any` | El valor del atributo `code` de la excepción si lo tiene, si no `None`. |
| `stack_trace` | `list[dict]` | Una entrada por cada frame de la pila, **más reciente primero** (el frame donde se lanzó la excepción aparece primero). |

Cada entrada de `stack_trace` es un dict con estas claves:

| Clave | Tipo | Descripción |
|---|---|---|
| `id` | `int` | Índice del frame, base 1, más reciente primero. |
| `filename` | `str` | Ruta del archivo fuente, con `\` normalizado a `/`. |
| `lineno` | `int` | Número de línea donde se ejecutaba el frame (`0` si se desconoce). |
| `name` | `str` | Nombre de la función/método del frame (`"<unknown>"` si no está disponible). |
| `line_code` | `str \| None` | La única línea de código fuente reportada por la traza para ese frame. |
| `code` | `list[str]` | Hasta 5 líneas de código fuente de contexto alrededor de `lineno` (2 antes, la línea misma, 2 después), leídas vía `linecache`. |
| `lines` | `list[int]` | Los números de línea correspondientes (base 1) para las entradas de `code`. |
| `code_with_lines` | `list[str]` | Cadenas `"{lineno}:{code}"` que emparejan cada número de línea con su texto fuente. |

`ExceptionParser` tiene dos métodos auxiliares internos,
`_getSourceCode(filename, lineno)` y `_parseStack(stack)`, que son
detalles de implementación usados por `toDict()` y no forman parte del
contrato público.

### Contrato (`IExceptionParser`)

```python
class IExceptionParser(Protocol):
    def toDict(self) -> dict[str, Any]: ...
```

Definido en `orionis/support/formatter/exceptions/contracts/parser.py`
como un `typing.Protocol` (tipado estructural) en lugar de un
`abc.ABC` — cualquier objeto que exponga un método `toDict()`
compatible satisface `IExceptionParser` sin necesidad de heredar de él
explícitamente. `ExceptionParser` satisface este protocolo.

---

## Ejemplos de uso

### Serialización básica de una excepción

```python
from orionis.support.formatter.serializer import Parser

try:
    1 / 0
except ZeroDivisionError as exc:
    payload = Parser.exception(exc).toDict()
    print(payload["error_type"])     # "ZeroDivisionError"
    print(payload["error_message"])  # texto de traza formateado
    print(payload["error_code"])     # None (sin atributo `code`)
    print(len(payload["stack_trace"]) > 0)  # True
```

### Excepciones personalizadas con código de error

```python
from orionis.support.formatter.serializer import Parser

class AppError(Exception):
    def __init__(self, message: str, code: int) -> None:
        super().__init__(message)
        self.code = code

try:
    raise AppError("invalid payload", code=422)
except AppError as exc:
    payload = Parser.exception(exc).toDict()
    print(payload["error_code"])  # 422
```

### Usar `ExceptionParser` directamente

```python
import json
from orionis.support.formatter.exceptions.parser import ExceptionParser

try:
    raise RuntimeError("boom")
except RuntimeError as exc:
    parser = ExceptionParser(exc)
    as_json = json.dumps(parser.toDict())
    print(as_json)
```

### Inspeccionar el primer frame de la pila

```python
from orionis.support.formatter.serializer import Parser

def inner() -> None:
    raise ValueError("nested failure")

try:
    inner()
except ValueError as exc:
    top_frame = Parser.exception(exc).toDict()["stack_trace"][0]
    print(top_frame["name"])      # "inner"
    print(top_frame["filename"])  # ruta a este script, con barras diagonales
```

---

## Consideraciones de rendimiento y concurrencia

- `ExceptionParser.__init__` hace todo el parseo de la traza de forma
  **anticipada** (por adelantado), mientras que `toDict()` en sí solo
  lee campos cacheados y construye el dict de salida — esto cambia un
  costo de construcción ligeramente mayor por llamadas a `toDict()`
  baratas y repetibles.
- El resultado de `toDict()` (`self._cache`) se memoiza después de la
  primera llamada: la segunda llamada y las siguientes devuelven
  exactamente el mismo objeto `dict` sin volver a parsear. Esta es una
  memoización simple, sin bloqueo — llamar a `toDict()` concurrentemente
  desde varios hilos sobre la misma instancia de `ExceptionParser` antes
  de que la caché se llene podría calcular el diccionario más de una
  vez, pero cada cálculo es determinista y produce un resultado igual,
  por lo que no hay corrupción de datos, solo un posible cómputo
  redundante.
- `_getSourceCode` lee las líneas de código fuente circundantes con una
  llamada a `linecache.getlines(filename)` por frame. `linecache` cachea
  el contenido de los archivos entre llamadas dentro del proceso.
- `_parseStack` itera el `StackSummary` directamente en reversa para
  producir el orden "más reciente primero" sin copiar la pila a otra
  lista. Los IDs aumentan desde 1 en ese mismo orden.
- `ExceptionParser` está basado en `__slots__`, manteniendo la huella de
  memoria por instancia pequeña y fija (`_cache`, `_error_code`,
  `_exc_type`, `_tb`).
- Ninguna de las clases de este módulo realiza E/S de red o asíncrona;
  `_getSourceCode` sí realiza lecturas de archivo síncronas vía
  `linecache` la primera vez que se accede a cada archivo fuente dentro
  del proceso.

## Notas de diseño

- **División fábrica + trabajador**: `Parser` es una fábrica estática
  mínima (`Parser.exception(...)`) que existe puramente para dar un
  punto de entrada corto y descriptivo; toda la lógica real vive en
  `ExceptionParser`.
- **Parseo anticipado, formateo perezoso**: capturar la traza vía
  `traceback.TracebackException.from_exception(..., capture_locals=False)`
  ocurre una sola vez en `__init__`; `capture_locals=False` evita
  deliberadamente capturar variables locales de cada frame, lo cual
  mantiene al parser ligero y evita retener referencias a estado local
  potencialmente grande o sensible.
- **Contrato basado en `Protocol`**: `IExceptionParser` es un
  `typing.Protocol`, no un `abc.ABC` — una forma deliberadamente más
  ligera de tipado por interfaz que se basa en compatibilidad
  estructural (tener un método `toDict()` compatible) en lugar de
  herencia explícita, a diferencia de los contratos basados en
  `abc.ABC` usados en otras partes de `orionis.support`.
- **Orden con el frame más reciente primero**: la lista `stack_trace` se
  ordena de modo que el frame donde realmente se lanzó la excepción
  quede primero, lo cual coincide con la forma típica de leer un reporte
  de error (la "causa" antes del contexto de la llamada).

## Notas de compatibilidad

- Requiere **Python 3.14+**, en línea con el resto del framework
  `orionis` (`requires-python = ">=3.14"` en `pyproject.toml`).
- Sin dependencias de terceros; solo usa `traceback`, `linecache` y
  `typing` de la librería estándar.
- Sin comportamiento específico de plataforma, aparte de la
  normalización estándar de separador de ruta de `\\` a `/` aplicada a
  `filename` en cada entrada de frame de la pila (relevante
  principalmente en Windows).
- Se usa internamente en `orionis.http.default.responses` para construir
  los payloads de las respuestas de error, pero el módulo en sí no
  depende de la capa HTTP ni de ninguna otra parte del framework.

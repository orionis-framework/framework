# Orionis Types (`orionis.support.types`)

> Bloques base fluidos y con pocas dependencias — `Collection`, `DotDict`, `MISSING`, `StdClass` y `Stringable` — usados en todo el framework Orionis cuando una lista, un diccionario, un marcador de "sin valor", un objeto plano o una cadena necesitan una API más rica y encadenable.
>
> 🇬🇧 English version: [README.md](README.md)

`orionis.support.types` no tiene controladores, providers ni facades
propios. Es una pequeña librería estándar de tipos auxiliares orientados
a valores, sobre la que se apoyan otros módulos del framework
(resultados del ORM, configuración, payloads HTTP, salida de consola,
etc.). Todos los tipos de este módulo son seguros de importar y usar
directamente, sin necesidad de arrancar la aplicación — **excepto**
`Stringable.encrypt()` / `Stringable.decrypt()`, que resuelven la facade
`Crypt` y por lo tanto requieren una `Application` de Orionis ya
arrancada.

---

## Tabla de contenidos

1. [Requisitos](#requisitos)
2. [Descripción funcional del módulo](#descripción-funcional-del-módulo)
3. [Referencia de API](#referencia-de-api)
   - [`Collection`](#collection-orionissupporttypescollectioncollection)
   - [`DotDict`](#dotdict-orionissupporttypesdot_dictdotdict)
   - [`MISSING`](#missing-orionissupporttypessentinelmissing)
   - [`StdClass`](#stdclass-orionissupporttypesstdstdclass)
   - [`Stringable`](#stringable-orionissupporttypesstringablestringable)
   - [Contratos (`ICollection`, `IStdClass`)](#contratos-icollection-istdclass)
4. [Ejemplos de uso](#ejemplos-de-uso)
5. [Consideraciones de rendimiento y concurrencia](#consideraciones-de-rendimiento-y-concurrencia)
6. [Notas de diseño](#notas-de-diseño)
7. [Notas de compatibilidad](#notas-de-compatibilidad)

---

## Requisitos

No se necesita instalación adicional además del propio framework:

```bash
pip install orionis
```

- **Python:** 3.14 o superior (el mismo mínimo que el resto del framework).
- **Dependencia de terceros:** [`dotty-dict`](https://pypi.org/project/dotty-dict/)
  (`dotty-dict~=1.3`), ya declarada como dependencia central de `orionis` —
  usada internamente por `Collection` para búsquedas por clave con notación
  de puntos/comodines (`"a.b.c"`, `"items.*.id"`).
- `Stringable.encrypt()` / `Stringable.decrypt()` además requieren una
  `Application` de Orionis arrancada con la facade `Crypt` fijada
  (provista por `EncrypterProvider`); `Stringable.toDate()` **no**
  necesita el contenedor de la aplicación, solo lee la zona horaria por
  defecto de `DateTime`.

## Descripción funcional del módulo

| Tipo | Archivo | Clase base | Propósito |
|---|---|---|---|
| `Collection` | [collection.py](../collection.py) | `ICollection` (`ABC`) | Envoltorio encadenable estilo Laravel sobre una `list` (o un `dict` producido por `groupBy`), con ayudantes de map/filter/reduce/agregación. |
| `DotDict` | [dot_dict.py](../dot_dict.py) | `dict` | Diccionario que también admite acceso tipo atributo (`d.a.b`), promoviendo automáticamente los `dict` planos anidados a `DotDict`. |
| `MISSING` | [sentinel.py](../sentinel.py) | `object` (instancia única de `_MISSING_TYPE`) | Valor centinela para distinguir "atributo/clave ausente" de un `None` explícito. |
| `StdClass` | [std.py](../std.py) | `IStdClass` (`ABC`) | Contenedor dinámico de atributos ad-hoc, similar a `stdClass` de PHP, con protección de nombres reservados. |
| `Stringable` | [stringable.py](../stringable.py) | `str` | Envoltorio de cadenas inmutable y fluido (estilo `Str` de Laravel) que expone más de 140 operaciones encadenables. |

Cada clase concreta (excepto `Stringable`, que extiende `str`
directamente) implementa una interfaz equivalente en
`orionis/support/types/contracts/` (`ICollection` para `Collection`,
`IStdClass` para `StdClass`), de modo que el contrato público se puede
anotar/mockear independientemente de la implementación.

Exportaciones públicas (desde `orionis/support/types/__init__.py`):

```python
from orionis.support.types import MISSING, Collection, DotDict, StdClass, Stringable
```

---

## Referencia de API

### `Collection` (`orionis.support.types.collection.Collection`)

```python
Collection(items: list[Any] | None = None) -> None
```

Envuelve una `list` de Python (internamente `self._items`) y expone una
amplia API fluida inspirada en Laravel. La mayoría de los métodos de
transformación devuelven una **nueva** instancia de `Collection`; un
conjunto más pequeño de métodos "en el lugar" (`each`, `forget`, `merge`,
`prepend`, `push`, `put`, `reject`, `reverse`, `sort`, `transform`,
`pop`, `pull`, `shift`, `random(count=...)`, `setAppends`,
`addRelation`) mutan `self._items` y devuelven `self` para poder
encadenar. `groupBy` es la excepción: devuelve una `Collection` que
envuelve un `dict` en lugar de una `list`.

`Collection` también implementa los protocolos del modelo de datos de
Python: `__iter__`, `__len__`, `__getitem__`/`__setitem__`/`__delitem__`
(los slices devuelven una nueva `Collection`), `__eq__`/`__ne__`/
`__lt__`/`__le__`/`__gt__`/`__ge__` (comparan contra otra `Collection` o
una `list` cruda) y `__hash__` (aplica hash a `tuple(self._items)` — solo
funciona si todos los elementos son hasheables).

| Método | Firma | Descripción |
|---|---|---|
| `take` | `take(number: int) -> Collection` | Primeros/últimos `number` elementos (negativo = desde el final). |
| `first` | `first(callback: Callable \| None = None) -> object` | Primer elemento, opcionalmente tras filtrar; `None` si está vacío. |
| `last` | `last(callback: Callable \| None = None) -> object` | Último elemento, opcionalmente tras filtrar; `None` si está vacío. |
| `all` | `all() -> list[Any]` | La lista/dict subyacente sin procesar. |
| `avg` | `avg(key: str \| None = None) -> float` | Promedio de todos los elementos o de `key`; `0` si está vacío o hay error. |
| `max` | `max(key: str \| None = None) -> object` | Valor máximo; `0` si está vacío o hay error. |
| `min` | `min(key: str \| None = None) -> object` | Valor mínimo; `0` si está vacío o hay error. |
| `chunk` | `chunk(size: int) -> Collection` | Divide en sub-`Collection`s de `size` elementos. Lanza `ValueError` si `size <= 0`. |
| `collapse` | `collapse() -> Collection` | Aplana un nivel de listas/`Collection`s anidadas. |
| `contains` | `contains(key: str \| Callable, value: object = None) -> bool` | El elemento existe (por callback, por `key == value`, o por pertenencia). |
| `count` | `count() -> int` | Número de elementos. |
| `diff` | `diff(items: list[Any] \| Collection) -> Collection` | Elementos no presentes en `items`. |
| `each` | `each(callback: Callable) -> Collection` | Aplica `callback` a cada elemento en el lugar; se detiene antes si `callback` devuelve un valor falsy. |
| `every` | `every(callback: Callable) -> bool` | `True` si todos los elementos satisfacen `callback`. |
| `filter` | `filter(callback: Callable) -> Collection` | Conserva los elementos donde `callback` es verdadero. |
| `flatten` | `flatten() -> Collection` | Aplana recursivamente listas/diccionarios anidados en una sola dimensión. |
| `forget` | `forget(*keys: int \| str) -> Collection` | Elimina elementos en los índices/claves dados, en el lugar. |
| `forPage` | `forPage(page: int, number: int) -> Collection` | Slice para paginación (`page` empieza en 1). Lanza `ValueError` si `number <= 0`. |
| `get` | `get(key: int \| str, default: object = None) -> object` | Elemento en `key`, o `default` (evaluado vía `__value` si es callable) si está fuera de rango. |
| `implode` | `implode(glue: str = ",", key: str \| None = None) -> str` | Une los elementos (o un `key` extraído) en una cadena. |
| `isEmpty` | `isEmpty() -> bool` | `True` si la colección no tiene elementos. |
| `map` | `map(callback: Callable) -> Collection` | Nueva colección con `callback` aplicado a cada elemento. |
| `mapInto` | `mapInto(cls: type, method: str \| None = None, **kwargs) -> Collection` | Mapea cada elemento a `cls(item)` o `cls.method(item, **kwargs)`; los fallos se convierten en `None`. |
| `merge` | `merge(items: list[Any] \| Collection) -> Collection` | Anexa `items` en el lugar. Lanza `TypeError` para otros tipos. |
| `pluck` | `pluck(value: str, key: str \| None = None) -> Collection` | Extrae `value` (opcionalmente indexado por `key`) de cada elemento. |
| `pop` | `pop() -> object` | Elimina y devuelve el último elemento, o `None` si está vacío. |
| `prepend` | `prepend(value: object) -> Collection` | Inserta `value` en el índice 0, en el lugar. |
| `pull` | `pull(key: int \| str) -> object` | Elimina y devuelve el elemento en `key`. |
| `push` | `push(value: object) -> Collection` | Anexa `value` en el lugar. |
| `put` | `put(key: int \| str, value: object) -> Collection` | Asigna `value` en `key`, en el lugar. |
| `random` | `random(count: int \| None = None) -> object \| Collection \| None` | Un elemento aleatorio (`secrets.choice`), o una `Collection` de `count` elementos (`random.sample`, muta en el lugar). Lanza `ValueError` si `count` es inválido. |
| `reduce` | `reduce(callback: Callable, initial: object = 0) -> object` | `functools.reduce` sobre los elementos. |
| `reject` | `reject(callback: Callable) -> Collection` | Elimina en el lugar los elementos donde `callback` es verdadero. |
| `reverse` | `reverse() -> Collection` | Invierte los elementos en el lugar. |
| `serialize` | `serialize() -> list[Any]` | Llama a `.serialize()`/`.to_dict()` en cada elemento si está disponible (aplicando los `setAppends` pendientes), si no lo deja tal cual. |
| `shift` | `shift() -> object` | Elimina y devuelve el primer elemento (`pull(0)`). |
| `sort` | `sort(key: str \| None = None) -> Collection` | Ordena los elementos en el lugar, opcionalmente por `key`. |
| `sum` | `sum(key: str \| None = None) -> float` | Suma de todos los elementos o de `key`; `0` en caso de error. |
| `toJson` | `toJson(**kwargs) -> str` | `json.dumps(self.serialize(), **kwargs)`. |
| `groupBy` | `groupBy(key: str) -> Collection` | Agrupa los elementos por `key` en una `Collection` respaldada por un **dict**. |
| `transform` | `transform(callback: Callable) -> Collection` | Reemplaza cada elemento con `callback(item)`, en el lugar. |
| `unique` | `unique(key: str \| None = None) -> Collection` | Elimina duplicados, opcionalmente por `key`. |
| `where` | `where(key: str, *args: object) -> Collection` | Filtra por `key` usando `==` o un operador explícito: `where("age", ">", 18)`. |
| `whereIn` | `whereIn(key: str, values: list[Any] \| Collection) -> Collection` | Conserva elementos cuyo valor de `key` está en `values`. |
| `whereNotIn` | `whereNotIn(key: str, values: list[Any] \| Collection) -> Collection` | Conserva elementos cuyo valor de `key` **no** está en `values`. |
| `zip` | `zip(items: list[Any] \| Collection) -> Collection` | Empareja elementos posicionalmente con `items`. Lanza `TypeError` para otros tipos. |
| `setAppends` | `setAppends(appends: list[str]) -> Collection` | Registra nombres de atributos extra a adjuntar en `serialize()` (usado con elementos tipo modelo que exponen `set_appends`). |
| `addRelation` | `addRelation(relation_data: dict[str, Any]) -> Collection` | Llama a `item.setRelation(key, value)` en cada elemento que lo soporte (integración con el ORM). |

Operadores soportados en `where()`: `<`, `<=`, `==`, `!=`, `>`, `>=`. Un
operador no soportado lanza `ValueError`.

### `DotDict` (`orionis.support.types.dot_dict.DotDict`)

```python
DotDict(*args, **kwargs)  # misma firma que dict
```

Una subclase de `dict` (`__slots__ = ()`, sin estado extra de instancia)
que añade acceso tipo atributo sobre el acceso normal de `dict` — ambos
funcionan al mismo tiempo (`d["a"]` y `d.a`).

| Método | Firma | Descripción |
|---|---|---|
| `__getattr__` | `__getattr__(key: str) -> object \| None` | Devuelve el valor de `key`, promoviendo un valor `dict` plano a `DotDict` (guardado de vuelta en el mapeo). Devuelve `None` — **no** `AttributeError` — si `key` no existe. |
| `__setattr__` | `__setattr__(key: str, value: object) -> None` | Asigna `self[key] = value`; un valor `dict` plano se convierte primero a `DotDict`. |
| `__delattr__` | `__delattr__(key: str) -> None` | Elimina `self[key]`. Lanza `AttributeError` si `key` no existe. |
| `get` | `get(key: str, default: object \| None = None) -> object \| None` | Como `dict.get`, promoviendo un resultado `dict` plano a `DotDict`. |
| `export` | `export() -> dict[str, Any]` | Convierte recursivamente el `DotDict` (y cualquier `DotDict`/`dict` anidado) de vuelta a `dict` planos. |
| `copy` | `copy() -> DotDict` | Copia profunda recursiva que conserva el tipo `DotDict` en cada nivel de anidación. |

El comportamiento estándar de `dict` (acceso por índice, iteración,
`keys()`/`values()`/`items()`, igualdad, etc.) se hereda sin cambios, ya
que `DotDict` no sobrescribe `__getitem__`/`__setitem__`.

### `MISSING` (`orionis.support.types.sentinel.MISSING`)

Una instancia única a nivel de módulo de la clase privada
`_MISSING_TYPE`, usada como centinela de argumento por defecto para
distinguir "valor no proporcionado" de un `None` explícito.

| Miembro | Descripción |
|---|---|
| `MISSING` | La instancia única. Siempre es falsy (`bool(MISSING) is False`). |
| `repr(MISSING)` | Devuelve `"<MISSING>"`. |

```python
from orionis.support.types import MISSING

def get(d: dict, key: str, default: object = MISSING) -> object:
    value = d.get(key, MISSING)
    if value is MISSING:
        return None if default is MISSING else default
    return value
```

### `StdClass` (`orionis.support.types.std.StdClass`)

```python
StdClass(**kwargs: object) -> None
```

Un objeto dinámico tipo "bolsa de atributos", similar a `stdClass` de PHP
o a un objeto plano de JS: cualquier argumento con nombre se convierte en
un atributo de la instancia, y se pueden añadir más atributos en tiempo
de ejecución con una asignación normal (`obj.nuevo_campo = 1`) o vía
`update()`.

| Método | Firma | Descripción |
|---|---|---|
| `__init__` | `__init__(**kwargs: object) -> None` | Asigna cada argumento con nombre como atributo vía `update()`. |
| `update` | `update(**kwargs: object) -> None` | Asigna/sobrescribe atributos en el lugar. Lanza `ValueError` para nombres tipo dunder (`__x__`) o nombres que colisionan con un atributo/método de clase existente. |
| `remove` | `remove(*attributes: str) -> None` | Elimina uno o más atributos. Lanza `AttributeError` si alguno no existe. |
| `toDict` | `toDict() -> dict` | Copia superficial de `self.__dict__`. |
| `fromDict` | `fromDict(dictionary: dict) -> StdClass` *(classmethod)* | Construye una nueva instancia desde un `dict` plano sin llamar a `__init__` (usa `cls.__new__`), aplicando la misma validación de nombres reservados. |
| `__eq__` | `__eq__(other: object) -> bool` | `True` solo si `other` es exactamente del mismo tipo y `__dict__` es igual. |
| `__hash__` | `__hash__() -> int` | XOR del hash de cada par `(key, value)` — independiente del orden, pero requiere que todos los valores de los atributos sean hasheables. |
| `__repr__` / `__str__` | — | `"NombreClase({...})"` / `"{...}"` mostrando `self.__dict__`. |

`StdClass.RESERVED` (y su equivalente para cada subclase, reconstruido
en `__init_subclass__`) es un `frozenset` con todos los nombres
definidos en cualquier punto del MRO de la clase; `update()`/`fromDict()`
se niegan a sombrear cualquiera de ellos.

### `Stringable` (`orionis.support.types.stringable.Stringable`)

```python
Stringable(object: object = "") -> Stringable  # misma construcción que str
```

Una subclase de `str` (`__slots__ = ()`) que provee una amplia API fluida
estilo `Str`/`Stringable` de Laravel. Como `str` es inmutable, **todos
los métodos de transformación devuelven una nueva instancia de
`Stringable`** — el valor original nunca se muta. Los métodos
booleanos/de comprobación devuelven `bool` plano, y algunos métodos
utilitarios devuelven `int`/`float`/`list`/`datetime`/`str` planos cuando
ese es el tipo de retorno natural.

Los métodos se agrupan a continuación por propósito; el nombre y la
firma exactos siempre coinciden con el archivo fuente.

**Búsqueda y extracción**

| Método | Descripción |
|---|---|
| `after(search)` / `afterLast(search)` | Subcadena tras la primera/última ocurrencia de `search`. |
| `before(search)` / `beforeLast(search)` | Subcadena antes de la primera/última ocurrencia de `search`. |
| `between(from_str, to_str)` / `betweenFirst(from_str, to_str)` | Subcadena entre dos delimitadores (`Stringable` vacío si no se encuentra). |
| `substr(start, length=None)` | Subcadena por `start`/`length` (semántica de slicing de Python). |
| `charAt(index)` | Carácter en `index`, o `False` si está fuera de rango. |
| `position(needle, offset=0, encoding=None)` | Índice de `needle` (como `str.find`), o `False` si no se encuentra. |
| `basename(suffix="")` / `dirname(levels=1)` | Ayudantes de rutas basados en `pathlib.Path`. |
| `excerpt(phrase="", options=None)` | Texto alrededor de la primera coincidencia de `phrase` (opciones `radius`, `omission`); `None` si `phrase` no se encuentra. |
| `take(limit)` | Primeros/últimos `limit` caracteres (negativo = desde el final). |
| `numbers()` | Conserva solo caracteres dígito. |

**Predicados (`bool`)**

| Método | Descripción |
|---|---|
| `contains(needles, *, ignore_case=False)` / `containsAll(needles, *, ignore_case=False)` / `doesntContain(...)` | Comprobaciones de pertenencia de subcadenas. |
| `startsWith(needles)` / `doesntStartWith(needles)` / `endsWith(needles)` / `doesntEndWith(needles)` | Comprobaciones de prefijo/sufijo (aceptan una cadena o lista de cadenas). |
| `exactly(value)` | Igualdad exacta de cadenas. |
| `isEmpty()` / `isNotEmpty()` | Comprobaciones basadas en longitud. |
| `isAlnum` / `isAlpha` / `isDecimal` / `isDigit` / `isIdentifier` / `isLower` / `isNumeric` / `isPrintable` / `isSpace` / `isTitle` / `isUpper` | Envoltorios finos sobre los predicados `str.is*()` equivalentes. |
| `isAscii()` | Comprobación de ASCII de 7 bits vía `encode("ascii")`. |
| `isJson()` | JSON válido vía `json.loads`. |
| `isUrl(protocols=None)` | URL válida con un esquema permitido (por defecto `["http", "https"]`). |
| `isUuid(version=None)` | UUID válido, opcionalmente de una versión específica (`1`-`8` o `"max"`). |
| `isUlid()` | ULID válido de 26 caracteres en Base32 de Crockford. |
| `isPattern(pattern, *, ignore_case=False)` | Coincidencia por comodines (`fnmatch`, `*`/`?`) contra uno o varios patrones. |
| `isMatch(pattern)` / `test(pattern)` | Búsqueda por expresión regular contra uno/varios patrones. |

**Mayúsculas/minúsculas y formato**

| Método | Descripción |
|---|---|
| `lower()` / `upper()` / `swapCase()` / `ucfirst()` / `lcfirst()` | Operaciones básicas de mayúsculas/minúsculas. |
| `camel()` / `kebab()` / `snake(delimiter="_")` / `studly()` / `pascal()` / `slug(separator="-", dictionary=None)` | Conversiones de formato para identificadores y URLs. |
| `title()` / `headline()` / `apa()` | Variantes de "title case" (`apa()` sigue las reglas de capitalización APA). |
| `convertCase(mode=None)` | `0`/`None`=casefold, `1`=mayúsculas, `2`=minúsculas, `3`=título. |
| `ascii()` / `transliterate(unknown="?", *, strict=False)` | Normaliza/transcribe a ASCII (NFKD de Unicode). |

**Transformación**

| Método | Descripción |
|---|---|
| `append(*values)` / `prepend(*values)` | Concatena cadenas después/antes. |
| `newLine(count=1)` | Añade `count` caracteres de nueva línea. |
| `repeat(times)` | Repite la cadena. |
| `reverse()` | Invierte el orden de los caracteres. |
| `replace(search, replace, *, case_sensitive=True)` | Reemplazo de una o varias subcadenas. |
| `replaceArray(search, replace)` | Reemplaza cada ocurrencia de `search` secuencialmente con elementos de `replace`. |
| `replaceFirst` / `replaceLast` / `replaceStart` / `replaceEnd` | Reemplazos posicionales únicos. |
| `replaceMatches(pattern, replace, limit=-1)` | Reemplazo basado en regex (cadena o callback). |
| `remove(search, *, case_sensitive=True)` | Elimina todas las ocurrencias de una o varias subcadenas. |
| `substrReplace(replace, offset=0, length=None)` | `substr_replace` estilo PHP, admite argumentos escalares o en lista. |
| `mask(character, index, length=None)` | Enmascara parte de la cadena con un carácter repetido. |
| `swap(map_dict)` | Reemplaza cada clave de `map_dict` por su valor. |
| `deduplicate(character=" ")` | Colapsa ocurrencias consecutivas de `character`. |
| `squish()` | Colapsa tramos de espacios internos y recorta. |
| `stripTags(allowed_tags=None)` | Elimina etiquetas tipo HTML/PHP (o solo desescapa entidades si se indica `allowed_tags`). |
| `toHtmlString()` | Escapa HTML (`html.escape`). |
| `wrap(before, after=None)` / `unwrap(before, after=None)` | Añade/elimina un par prefijo+sufijo. |
| `finish(cap)` / `start(prefix)` | Garantiza que la cadena termine/empiece con un valor (sin duplicarlo). |
| `chopStart(needle)` / `chopEnd(needle)` | Elimina un valor inicial/final si está presente. |

**Relleno y recorte**

| Método | Descripción |
|---|---|
| `padBoth(length, pad=" ")` / `padLeft(length, pad=" ")` / `padRight(length, pad=" ")` | Rellena hasta una longitud objetivo. |
| `trim(characters=None)` / `ltrim(characters=None)` / `rtrim(characters=None)` | Recorta como `str.strip`/`lstrip`/`rstrip`. |
| `lStrip(chars=None)` / `rStrip(chars=None)` | Alias sobre `str.lstrip`/`rstrip`. |
| `zFill(width)` | Rellena con ceros (`str.zfill`). |
| `wordWrap(characters=75, break_str="\n", *, cut_long_words=False)` | Ajusta el texto a un ancho de columna (`textwrap.fill`). |

**División y palabras**

| Método | Descripción |
|---|---|
| `explode(delimiter, limit=-1)` | Divide por un delimitador literal en una `list[str]`. |
| `split(pattern, limit=-1, flags=0)` | Divide por regex o por longitud de bloque fijo (`pattern` entero) en una `list[str]`. |
| `ucsplit()` | Divide en los límites de letras mayúsculas. |
| `words(words=100, end="...")` | Trunca a un número máximo de palabras. |
| `wordCount(characters=None)` | Cuenta palabras (con caracteres separadores extra opcionales). |
| `scan(format_str)` | Extracción tipo `sscanf` usando marcadores `%s`/`%d`/`%f`. |
| `match(pattern)` / `matchAll(pattern)` | Primera coincidencia regex / todas las coincidencias. |
| `parseCallback(default=None)` | Analiza una cadena `"Clase@metodo"` en `[clase, metodo]`. |

**Pluralización**

| Método | Descripción |
|---|---|
| `plural(count=2, *, prepend_count=False)` | Pluralización en inglés (reglas simples de sufijo), sensible a `count`. |
| `pluralStudly(count=2)` / `pluralPascal(count=2)` | Pluraliza solo la última palabra de un identificador StudlyCase/PascalCase. |
| `singular()` | Singularización en inglés (reglas simples de sufijo). |

**Ejecución condicional (`when*`)**

Todos los métodos `when*` comparten la forma
`whenX(..., callback: Callable, default: Callable | None = None) -> Stringable`:
si la condición se cumple, se invoca `callback(self)` (envuelto en
`Stringable` si aún no lo es); en caso contrario se ejecuta
`default(self)` si se proporcionó, o se devuelve el `Stringable`
original sin cambios.

| Método | Condición |
|---|---|
| `when(condition, callback, default=None)` | `condition` (bool o callable aplicado a `self`). |
| `whenContains` / `whenContainsAll` | `contains()` / todas las subcadenas presentes. |
| `whenEmpty` / `whenNotEmpty` | `isEmpty()` / `isNotEmpty()`. |
| `whenEndsWith` / `whenDoesntEndWith` | `endsWith()` y su negación. |
| `whenStartsWith` / `whenDoesntStartWith` | Comprobación de prefijo y su negación. |
| `whenExactly` / `whenNotExactly` | `exactly(value)` y su negación. |
| `whenTest` | `test(pattern)`. |
| `whenIs` | `isPattern(pattern)` (coincidencia por comodines). |
| `whenIsAscii` | `isAscii()`. |
| `whenIsUuid` / `whenIsUlid` | `isUuid()` / `isUlid()`. |

**Conversión y hashing**

| Método | Descripción |
|---|---|
| `value()` | Valor `str` plano. |
| `length()` | `len(self)`. |
| `toInteger(base=10)` / `toFloat()` | Conversión numérica; lanzan `ValueError` si falla. |
| `toBoolean()` | `True` para `"1"`, `"true"`, `"on"`, `"yes"` (sin distinguir mayúsculas/minúsculas). |
| `toDate(format_str="%Y-%m-%d")` | Parsea con `datetime.strptime`, adjuntando `DateTime.getZoneInfo()`; lanza `ValueError` si no coincide el formato. |
| `toBase64()` / `fromBase64(*, strict=False)` | Codificación/decodificación Base64. |
| `md5()` / `sha1()` / `sha256()` / `hash(algorithm)` | Digests hexadecimales vía `hashlib`. |
| `encrypt()` / `decrypt()` | Delega en la facade `Crypt` (`orionis.support.facades.encrypter`) — **requiere una `Application` arrancada**. |
| `jsonSerialize()` | `str(self)`, para integración con `json.dumps(..., default=...)`. |
| `offsetExists(offset)` / `offsetGet(offset)` | Ayudantes tipo acceso por índice (semántica `in`/`[]`). |

**Ayudantes funcionales**

| Método | Descripción |
|---|---|
| `pipe(callback)` | Pasa `self` por `callback` y envuelve el resultado en `Stringable`. |
| `tap(callback)` | Llama a `callback(self)` como efecto secundario, siempre devuelve `self` sin cambios. |

### Contratos (`ICollection`, `IStdClass`)

`orionis/support/types/contracts/collection.py` y
`.../contracts/std.py` definen `ICollection` e `IStdClass` como clases
`abc.ABC` con declaraciones `@abstractmethod` que reflejan la API
pública de `Collection` y `StdClass` respectivamente (con docstrings
incluidos, sin implementación). Existen para que otros módulos puedan
depender de la interfaz (`ICollection`, `IStdClass`) en lugar de la clase
concreta — útil para anotaciones de tipo y dobles de prueba.
`Stringable` y `DotDict` no tienen contrato aparte; se usan
directamente.

---

## Ejemplos de uso

### `Collection`

```python
from orionis.support.types import Collection

users = Collection([
    {"name": "Ada", "age": 34, "active": True},
    {"name": "Grace", "age": 41, "active": False},
    {"name": "Alan", "age": 29, "active": True},
])

active_names = (
    users.where("active", True)
         .sort(key="age")
         .pluck("name")
         .implode(", ")
)
print(active_names)  # "Alan, Ada"

by_status = users.groupBy("active")
print(by_status.all().keys())  # dict_keys([True, False])

print(users.avg("age"))  # 34.666...
```

### `DotDict`

```python
from orionis.support.types import DotDict

config = DotDict({"app": {"name": "Orionis", "debug": False}})
print(config.app.name)          # "Orionis"
config.app.debug = True
config.database = {"driver": "sqlite"}
print(config.database.driver)   # "sqlite"
print(config.export())          # dict anidado plano
```

### `MISSING`

```python
from orionis.support.types import MISSING

def resolve(value: object = MISSING) -> str:
    if value is MISSING:
        return "sin valor proporcionado"
    return f"valor: {value!r}"

print(resolve())        # "sin valor proporcionado"
print(resolve(None))    # "valor: None"
```

### `StdClass`

```python
from orionis.support.types import StdClass

point = StdClass(x=1, y=2)
point.z = 3
print(point.toDict())            # {"x": 1, "y": 2, "z": 3}

point.remove("z")
same_shape = StdClass.fromDict({"x": 1, "y": 2})
print(point == same_shape)       # True
```

### `Stringable`

```python
from orionis.support.types import Stringable

title = Stringable("  hello_world  ")
slug = title.trim().studly().slug()
print(slug.value())  # "hello-world"

message = (
    Stringable("orionis")
    .studly()
    .append(" Framework")
    .whenContains("Framework", lambda s: s.upper())
)
print(message)  # "ORIONIS FRAMEWORK"

print(Stringable("2026-07-27").toDate().year)  # 2026
```

---

## Consideraciones de rendimiento y concurrencia

- Los cinco tipos son objetos **planos, síncronos y limitados por CPU**
  — no hay E/S, ni `async`/`await`, ni bloqueos en ningún punto de este
  módulo. Son seguros de compartir entre tareas de `asyncio` siempre que
  los datos subyacentes que envuelven no se muten concurrentemente desde
  varias tareas/hilos a la vez (ninguno de los métodos mutadores está
  protegido por un lock).
- Los métodos de `Collection` que mutan en el lugar (`each`, `sort`,
  `transform`, `reject`, `push`, `pop`, `merge`, …) operan directamente
  sobre `self._items` y son `O(n)`; las agregaciones de solo lectura
  (`sum`, `avg`, `max`, `min`) devuelven `0` directamente si la entrada
  está vacía en lugar de lanzar una excepción. `diff()`/`whereIn()`/
  `whereNotIn()` construyen un `set` internamente para comprobaciones de
  pertenencia `O(n+m)` en vez del enfoque ingenuo `O(n*m)`, recurriendo a
  recorridos de lista solo cuando los elementos no son hasheables.
  `contains(callback)` corta en corto con `any()` en lugar de
  materializar una `Collection` filtrada.
- `Stringable` hereda la inmutabilidad de `str`: cada transformación
  crea un nuevo objeto de cadena. Para cadenas muy grandes o bucles
  intensivos, encadenar muchos métodos de `Stringable` tiene el mismo
  costo de asignación que encadenar las operaciones `str` equivalentes
  manualmente — no hay evaluación perezosa ni por streaming.
- `Stringable` precompila sus expresiones regulares como constantes a
  nivel de módulo (`_RE_CAMEL_SEP`, `_RE_KEBAB_CAMEL`, `_ULID_RE`, etc.),
  de modo que las llamadas repetidas a `camel()`, `kebab()`, `isUlid()` y
  similares evitan recompilar el patrón en cada llamada.
- `DotDict.__getattr__`/`get()` guardan la versión envuelta en `DotDict`
  de un `dict` plano anidado de vuelta en el mapeo la primera vez que se
  accede, de modo que las lecturas posteriores por atributo de la misma
  clave anidada no la vuelven a envolver.
- `StdClass.__hash__` y `Collection.__hash__` calculan un hash a partir
  de su contenido (elementos de `__dict__` / `tuple(self._items)`); ambos
  **requieren** que todos los valores contenidos sean hasheables, y
  lanzarán `TypeError` si se intenta hashear una instancia que contenga
  una `list`/`dict`/otro valor no hasheable.
- `Stringable.encrypt()`/`decrypt()` pasan por la facade `Crypt` y el
  contenedor de DI de Orionis; cada llamada paga el costo de una
  resolución de facade (con capacidad async) y debe ejecutarse donde ya
  se haya arrancado una `Application`.

## Notas de diseño

- **API fluida/encadenable**: `Collection` y `Stringable` siguen el mismo
  diseño que `Illuminate\Support\Collection` y `Stringable` de Laravel —
  la mayoría de los métodos devuelven una nueva instancia del mismo tipo
  para poder encadenar llamadas (`Stringable(...).trim().studly().slug()`).
- **Inmutabilidad por tipo base**: `Stringable` extiende `str` y usa
  `__slots__ = ()`, así que las instancias no llevan estado extra por
  objeto más allá del propio valor de cadena; cada "mutador" es en
  realidad una llamada al constructor para una nueva instancia.
- **Patrón centinela**: `MISSING` es una clase privada de instancia
  única (`_MISSING_TYPE`) en lugar de usar `None`, siguiendo el idioma
  bien conocido de Python para distinguir "no pasado" de "pasado como
  `None`" (reflejado internamente por los centinelas `_MISSING` usados
  dentro de `Collection` y `DotDict` con el mismo propósito).
- **Protección de nombres reservados**: `StdClass` calcula `RESERVED` —
  un `frozenset` con todos los nombres de atributo/método a lo largo del
  MRO de la clase — en `__init_subclass__`, de modo que asignar un
  atributo dinámicamente nunca puede sombrear silenciosamente un método
  real (`update()`/`fromDict()` lanzan `ValueError` en su lugar).
- **Contratos como ABC**: `ICollection`/`IStdClass` son clases `abc.ABC`
  solo con declaraciones `@abstractmethod` (sin implementación, sin
  conflictos de `__slots__` con las clases concretas), usadas
  exclusivamente para anotaciones de tipo basadas en interfaz y para
  pruebas.
- **Dualidad dict/lista en `Collection`**: `Collection` normalmente
  envuelve una `list`, pero `groupBy()` devuelve deliberadamente una
  `Collection` que envuelve un `dict`; los métodos que asumen una lista
  (por ejemplo `forget`, `sort` sin clave) no están pensados para
  llamarse sobre una `Collection` respaldada por un dict.

## Notas de compatibilidad

- Requiere **Python 3.14+**, en línea con el resto del framework
  `orionis` (`requires-python = ">=3.14"` en `pyproject.toml`).
- Depende de `dotty-dict~=1.3`, ya una dependencia central de `orionis`
  (usada por `Collection.__dataGet` para búsquedas por clave con
  notación de puntos/comodines sobre elementos tipo dict).
- `Stringable.toDate()` depende de
  `orionis.support.facades.datetime.DateTime` (respaldado por
  `pendulum` y `zoneinfo`) únicamente para su zona horaria por defecto;
  no requiere el contenedor de DI.
- `Stringable.encrypt()`/`decrypt()` dependen de
  `orionis.support.facades.encrypter.Crypt`, que requiere una
  `Application` de Orionis arrancada con `EncrypterProvider` registrado
  (el valor por defecto en una aplicación Orionis estándar).
- Sin comportamiento específico de plataforma; los cinco tipos son
  Python puro sin dependencias a nivel de sistema operativo.

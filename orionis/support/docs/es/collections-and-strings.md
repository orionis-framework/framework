# Transformar colecciones y cadenas

## Inicio rápido

```python
from orionis.support.types import Collection, Stringable

names = Collection(["Ada", "Grace", "Linus"])
long_names = names.filter(lambda name: len(name) > 3).map(str.upper)

assert long_names.all() == ["GRACE", "LINUS"]
assert Stringable("  Orionis framework  ").squish().slug() == "orionis-framework"
```

## Preparar un resumen sin cambiar los datos originales

`Collection` trabaja en memoria. Usa consultas de Database/ORM para filtrar grandes volúmenes antes de materializarlos; encadenar `where()` sobre una colección no envía SQL. `filter`, `map`, `pluck`, `where`, `chunk`, `forPage` y las operaciones de consulta devuelven otra colección. `push`, `put`, `forget`, `merge` y `transform` modifican la actual. Los elementos anidados pueden seguir siendo los mismos objetos: una colección nueva no significa una copia profunda.

En este programa, el pipeline produce etiquetas para los productos disponibles. `where("stock", ">", 0)` admite un operador explícito; `where("active", True)` usa igualdad. Los tipos no comparables pueden ser omitidos por el filtro. `groupBy(key)` ordena las claves para agrupar: usa valores comparables entre sí. `unique()` con elementos hashables usa un set y no promete orden estable; si el orden importa, elige una transformación cuya estabilidad controles.

`Stringable` es un `str` inmutable: cada transformación produce otro valor. `slug` crea un texto apto para identificadores pero no comprueba su unicidad en la base de datos. `toHtmlString()` aplica `html.escape` y devuelve un `Stringable` ordinario. Un motor de plantillas con autoescape puede escapar de nuevo sus entidades; tenlo en cuenta al elegir dónde escapar el texto. El hashing genérico de texto (`md5`, `sha1`, `sha256`) no sustituye los algoritmos de contraseña del módulo Hashing.

`pull()` y `shift()` devuelven `None` sobre una colección vacía. `random()` devuelve un elemento, mientras que `random(count)` modifica y devuelve la colección actual; el valor cero la vacía. `mapInto(Target, **kwargs)` pasa esos argumentos por nombre junto con cada elemento. Las operaciones que aceptan `ICollection` también aceptan otras implementaciones de ese contrato. Los resultados agrupados exponen un diccionario mediante `all()`, incluido `{}` cuando no hay grupos. Los agregados por clave omiten claves ausentes y admiten una clave de cadena vacía.

El texto de reemplazo de `replace()` es literal incluso en búsquedas que ignoran mayúsculas. `replaceArray()` consume en orden las coincidencias del texto original, sin volver a buscar en los valores insertados. `replaceMatches()` conserva la API de expresiones regulares. `stripTags(allowed_tags)` conserva las etiquetas permitidas con sus atributos, elimina las demás etiquetas y conserva su texto; una lista no vacía también decodifica entidades HTML. Esta operación no sanitiza HTML. `encrypt()` y `decrypt()` delegan en el servicio Crypt configurado y devuelven cadenas ordinarias. `toDate()` admite entrada ISO sin formato explícito y conserva el desplazamiento horario de la entrada salvo que se indique una zona de destino.

`Stringable.split()` y `split(None, limit)` usan la separación nativa por espacios, incluida la entrada vacía y los espacios consecutivos. Un patrón textual mantiene la separación regex; un entero positivo conserva los fragmentos de longitud fija. El modo de fragmentos conserva todos los elementos independientemente de `limit`. Los tamaños inválidos y límites no enteros lanzan errores explícitos en vez de descartar la entrada silenciosamente.

## Paginación y serialización

`forPage(page, number)` selecciona una ventana de una colección ya cargada y no conoce el total persistido en una base de datos. `chunk(size)` agrupa elementos en memoria. `chunk` requiere un tamaño positivo y `forPage` un `number` positivo; las páginas inferiores a 1 se normalizan a 1. Usa `serialize()` para estructuras serializables y `toJson(**kwargs)` para JSON; el resultado de `all()` puede exponer la estructura actual. Evita compartir y mutar la misma instancia entre tareas.

```python
from orionis.support.types import Collection, Stringable

products = Collection(
    [
        {"name": "Desk lamp", "stock": 3, "active": True},
        {"name": "Notebook", "stock": 0, "active": True},
        {"name": "USB cable", "stock": 2, "active": False},
    ]
)
labels = products.where("active", True).where("stock", ">", 0).pluck("name")
slugs = labels.map(lambda name: str(Stringable(name).slug()))
assert slugs.all() == ["desk-lamp"]
assert products.count() == 3
assert Stringable("  Ada   Lovelace  ").squish().value() == "Ada Lovelace"
```

## Fuentes y siguientes pasos

[collection.py](../../types/collection.py) · [stringable.py](../../types/stringable.py)

[Volver al índice del módulo](README.md).

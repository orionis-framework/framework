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

## Paginación y serialización

`forPage(page, number)` selecciona una ventana de una colección ya cargada y no conoce el total persistido en una base de datos. `chunk(size)` agrupa elementos en memoria. `chunk` requiere un tamaño positivo y `forPage` un `number` positivo; las páginas inferiores a 1 se normalizan a 1. Usa `serialize()` para estructuras serializables y `toJson(**kwargs)` para JSON; el resultado de `all()` puede exponer la estructura actual. Evita compartir y mutar la misma instancia entre tareas.

```python
from orionis.support.types import Collection, Stringable

products = Collection([
    {"name": "Desk lamp", "stock": 3, "active": True},
    {"name": "Notebook", "stock": 0, "active": True},
    {"name": "USB cable", "stock": 2, "active": False},
])
labels = products.where("active", True).where("stock", ">", 0).pluck("name")
slugs = labels.map(lambda name: str(Stringable(name).slug()))
assert slugs.all() == ["desk-lamp"]
assert products.count() == 3
assert Stringable("  Ada   Lovelace  ").squish().value() == "Ada Lovelace"
```

## Fuentes y siguientes pasos

[collection.py](../../types/collection.py) · [stringable.py](../../types/stringable.py)

[Volver al índice del módulo](README.md).

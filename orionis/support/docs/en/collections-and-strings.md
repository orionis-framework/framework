# Transforming collections and strings

## Quick start

```python
from orionis.support.types import Collection, Stringable

names = Collection(["Ada", "Grace", "Linus"])
long_names = names.filter(lambda name: len(name) > 3).map(str.upper)

assert long_names.all() == ["GRACE", "LINUS"]
assert Stringable("  Orionis framework  ").squish().slug() == "orionis-framework"
```

## Build a summary without changing the original data

`Collection` works in memory. Use Database/ORM queries to filter large datasets before materializing them; chaining `where()` on a collection does not send SQL. `filter`, `map`, `pluck`, `where`, `chunk`, `forPage`, and query operations return another collection. `push`, `put`, `forget`, `merge`, and `transform` mutate the current one. Nested elements may still be the same objects: a new collection is not a deep copy.

This program produces labels for available products. `where("stock", ">", 0)` accepts an explicit operator; `where("active", True)` uses equality. Incomparable values may be omitted by the filter. `groupBy(key)` sorts grouping keys: use mutually comparable values. With hashable elements, `unique()` uses a set and does not promise stable order; choose a transformation with controlled stability when order matters.

`Stringable` is an immutable `str`: transformations return another value. `slug` produces identifier-friendly text but does not check database uniqueness. `toHtmlString()` applies `html.escape` and returns an ordinary `Stringable`. A template engine with autoescaping may escape its entities again; account for that when choosing where escaping occurs. Generic text hashing (`md5`, `sha1`, `sha256`) does not replace the Hashing module's password algorithms.

## Pagination and serialization

`forPage(page, number)` selects a window of an already loaded collection and does not know a database's persisted total. `chunk(size)` groups elements in memory. `chunk` requires a positive size and `forPage` a positive `number`; page values below 1 are normalized to 1. Use `serialize()` for serializable structures and `toJson(**kwargs)` for JSON; `all()` may expose the current structure. Avoid sharing and mutating the same instance across tasks.

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

## Evidence and next steps

[collection.py](../../types/collection.py) · [stringable.py](../../types/stringable.py)

[Return to the module index](README.md).

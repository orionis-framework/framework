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

`pull()` and `shift()` return `None` on an empty collection. `random()` returns one item, while `random(count)` mutates and returns the current collection; a count of zero empties it. `mapInto(Target, **kwargs)` passes those keyword arguments alongside each item. Operations accepting `ICollection` also accept other implementations of that contract. Grouped results expose a dictionary through `all()`, including `{}` for an empty group. Keyed aggregates skip missing keys and accept an empty-string key.

Replacement text passed to `replace()` is literal even for case-insensitive searches. `replaceArray()` consumes matches from the original text in order; inserted values are not searched again. `replaceMatches()` remains the regular-expression API. `stripTags(allowed_tags)` preserves allowed tags and their attributes, removes other tags, and retains their text; a nonempty allowlist also decodes HTML entities. This operation does not sanitize HTML. `encrypt()` and `decrypt()` delegate to the configured Crypt service and return plain strings. `toDate()` accepts ISO input when no format is supplied and preserves an explicit input offset unless a target timezone is given.

`Stringable.split()` and `split(None, limit)` use native whitespace splitting, including empty input and consecutive whitespace. A string pattern keeps regex splitting; a positive integer keeps fixed-length chunks. Chunk mode retains every chunk regardless of `limit`. Invalid chunk sizes and non-integer limits raise explicit errors rather than silently discarding input.

## Pagination and serialization

`forPage(page, number)` selects a window of an already loaded collection and does not know a database's persisted total. `chunk(size)` groups elements in memory. `chunk` requires a positive size and `forPage` a positive `number`; page values below 1 are normalized to 1. Use `serialize()` for serializable structures and `toJson(**kwargs)` for JSON; `all()` may expose the current structure. Avoid sharing and mutating the same instance across tasks.

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

## Evidence and next steps

[collection.py](../../types/collection.py) · [stringable.py](../../types/stringable.py)

[Return to the module index](README.md).

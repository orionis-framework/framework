# Orionis Types (`orionis.support.types`)

> Fluent, dependency-light building blocks — `Collection`, `DotDict`, `MISSING`, `StdClass`, and `Stringable` — used throughout the Orionis framework wherever a list, a dict, a "no value" marker, a plain object, or a string needs a richer, chainable API.
>
> 🇪🇸 Versión en español: [README.es.md](README.es.md)

`orionis.support.types` has no controllers, providers, or facades of its
own. It is a small standard library of value-oriented helper types that
other framework modules (ORM results, configuration, HTTP payloads,
console output, etc.) build on top of. Every type in this module is safe
to import and use directly, with no application bootstrap required —
**except** `Stringable.encrypt()` / `Stringable.decrypt()`, which resolve
the `Crypt` facade and therefore need a booted Orionis `Application`.

---

## Table of contents

1. [Requirements](#requirements)
2. [Module overview](#module-overview)
3. [API reference](#api-reference)
   - [`Collection`](#collection-orionissupporttypescollectioncollection)
   - [`DotDict`](#dotdict-orionissupporttypesdot_dictdotdict)
   - [`MISSING`](#missing-orionissupporttypessentinelmissing)
   - [`StdClass`](#stdclass-orionissupporttypesstdstdclass)
   - [`Stringable`](#stringable-orionissupporttypesstringablestringable)
   - [Contracts (`ICollection`, `IStdClass`)](#contracts-icollection-istdclass)
4. [Usage examples](#usage-examples)
5. [Performance and concurrency considerations](#performance-and-concurrency-considerations)
6. [Design notes](#design-notes)
7. [Compatibility notes](#compatibility-notes)

---

## Requirements

No extra installation is required beyond the framework itself:

```bash
pip install orionis
```

- **Python:** 3.14 or newer (the same minimum as the rest of the framework).
- **Third-party dependency:** [`dotty-dict`](https://pypi.org/project/dotty-dict/)
  (`dotty-dict~=1.3`), already declared as a core dependency of `orionis` —
  used internally by `Collection` for dotted/wildcard key lookups
  (`"a.b.c"`, `"items.*.id"`).
- `Stringable.encrypt()` / `Stringable.decrypt()` additionally require a
  booted Orionis `Application` with the `Crypt` facade pinned (provided by
  `EncrypterProvider`); `Stringable.toDate()` does **not** need the
  application container, it only reads `DateTime`'s default timezone.

## Module overview

| Type | File | Base class | Purpose |
|---|---|---|---|
| `Collection` | [collection.py](../collection.py) | `ICollection` (`ABC`) | Laravel-style, chainable wrapper around a `list` (or a `dict` produced by `groupBy`), with map/filter/reduce/aggregation helpers. |
| `DotDict` | [dot_dict.py](../dot_dict.py) | `dict` | Dictionary that also supports attribute-style access (`d.a.b`), auto-promoting nested plain dicts to `DotDict`. |
| `MISSING` | [sentinel.py](../sentinel.py) | `object` (singleton instance of `_MISSING_TYPE`) | Sentinel value to distinguish "attribute/key absent" from a legitimate `None`. |
| `StdClass` | [std.py](../std.py) | `IStdClass` (`ABC`) | Dynamic, PHP-`stdClass`-like container for ad-hoc attributes, with reserved-name protection. |
| `Stringable` | [stringable.py](../stringable.py) | `str` | Immutable, fluent string wrapper (Laravel `Str`-style) exposing 140+ chainable string operations. |

Each concrete class (except `Stringable`, which extends `str` directly)
implements a matching `Interface` in `orionis/support/types/contracts/`
(`ICollection` for `Collection`, `IStdClass` for `StdClass`), so the
public contract can be type-hinted and mocked independently of the
implementation.

Public exports (from `orionis/support/types/__init__.py`):

```python
from orionis.support.types import MISSING, Collection, DotDict, StdClass, Stringable
```

---

## API reference

### `Collection` (`orionis.support.types.collection.Collection`)

```python
Collection(items: list[Any] | None = None) -> None
```

Wraps a Python `list` (internally `self._items`) and exposes a large,
Laravel-inspired fluent API. Most transformation methods return a
**new** `Collection` instance; a smaller set of "in-place" methods
(`each`, `forget`, `merge`, `prepend`, `push`, `put`, `reject`,
`reverse`, `sort`, `transform`, `pop`, `pull`, `shift`, `random(count=...)`,
`setAppends`, `addRelation`) mutate `self._items` and return `self` for
chaining. `groupBy` is the exception that returns a `Collection` wrapping
a `dict` instead of a `list`.

`Collection` also implements the Python data-model protocols: `__iter__`,
`__len__`, `__getitem__`/`__setitem__`/`__delitem__` (slices return a new
`Collection`), `__eq__`/`__ne__`/`__lt__`/`__le__`/`__gt__`/`__ge__`
(compare against another `Collection` or a raw `list`), and `__hash__`
(hashes `tuple(self._items)` — only works if every item is hashable).

| Method | Signature | Description |
|---|---|---|
| `take` | `take(number: int) -> Collection` | First/last `number` items (negative = from the end). |
| `first` | `first(callback: Callable \| None = None) -> object` | First item, optionally after filtering; `None` if empty. |
| `last` | `last(callback: Callable \| None = None) -> object` | Last item, optionally after filtering; `None` if empty. |
| `all` | `all() -> list[Any]` | The raw underlying list/dict. |
| `avg` | `avg(key: str \| None = None) -> float` | Average of all items or of `key`; `0` on empty/error. |
| `max` | `max(key: str \| None = None) -> object` | Maximum value; `0` on empty/error. |
| `min` | `min(key: str \| None = None) -> object` | Minimum value; `0` on empty/error. |
| `chunk` | `chunk(size: int) -> Collection` | Split into sub-`Collection`s of `size` items. Raises `ValueError` if `size <= 0`. |
| `collapse` | `collapse() -> Collection` | Flatten one level of nested lists/`Collection`s. |
| `contains` | `contains(key: str \| Callable, value: object = None) -> bool` | Item exists (by callback, by `key == value`, or by membership). |
| `count` | `count() -> int` | Number of items. |
| `diff` | `diff(items: list[Any] \| Collection) -> Collection` | Items not present in `items`. |
| `each` | `each(callback: Callable) -> Collection` | Apply `callback` to every item in place; stops early if `callback` returns falsy. |
| `every` | `every(callback: Callable) -> bool` | `True` if all items satisfy `callback`. |
| `filter` | `filter(callback: Callable) -> Collection` | Keep items where `callback` is truthy. |
| `flatten` | `flatten() -> Collection` | Recursively flatten nested lists/dicts into one dimension. |
| `forget` | `forget(*keys: int \| str) -> Collection` | Remove items at the given indices/keys in place. |
| `forPage` | `forPage(page: int, number: int) -> Collection` | Slice for pagination (`page` is 1-based). Raises `ValueError` if `number <= 0`. |
| `get` | `get(key: int \| str, default: object = None) -> object` | Item at `key`, or `default` (evaluated via `__value` if callable) if out of range. |
| `implode` | `implode(glue: str = ",", key: str \| None = None) -> str` | Join items (or a plucked `key`) into a string. |
| `isEmpty` | `isEmpty() -> bool` | `True` if the collection has no items. |
| `map` | `map(callback: Callable) -> Collection` | New collection with `callback` applied to every item. |
| `mapInto` | `mapInto(cls: type, method: str \| None = None, **kwargs) -> Collection` | Map each item into `cls(item)` or `cls.method(item, **kwargs)`; failures become `None`. |
| `merge` | `merge(items: list[Any] \| Collection) -> Collection` | Append `items` in place. Raises `TypeError` for other types. |
| `pluck` | `pluck(value: str, key: str \| None = None) -> Collection` | Extract `value` (optionally keyed by `key`) from every item. |
| `pop` | `pop() -> object` | Remove and return the last item, or `None` if empty. |
| `prepend` | `prepend(value: object) -> Collection` | Insert `value` at index 0 in place. |
| `pull` | `pull(key: int \| str) -> object` | Remove and return the item at `key`. |
| `push` | `push(value: object) -> Collection` | Append `value` in place. |
| `put` | `put(key: int \| str, value: object) -> Collection` | Set `value` at `key` in place. |
| `random` | `random(count: int \| None = None) -> object \| Collection \| None` | One random item (`secrets.choice`), or a `Collection` of `count` items (`random.sample`, mutates in place). Raises `ValueError` for invalid `count`. |
| `reduce` | `reduce(callback: Callable, initial: object = 0) -> object` | `functools.reduce` over the items. |
| `reject` | `reject(callback: Callable) -> Collection` | Remove items in place where `callback` is truthy. |
| `reverse` | `reverse() -> Collection` | Reverse items in place. |
| `serialize` | `serialize() -> list[Any]` | Call `.serialize()`/`.to_dict()` on each item if available (applying pending `setAppends`), else keep as-is. |
| `shift` | `shift() -> object` | Remove and return the first item (`pull(0)`). |
| `sort` | `sort(key: str \| None = None) -> Collection` | Sort items in place, optionally by `key`. |
| `sum` | `sum(key: str \| None = None) -> float` | Sum of all items or of `key`; `0` on error. |
| `toJson` | `toJson(**kwargs) -> str` | `json.dumps(self.serialize(), **kwargs)`. |
| `groupBy` | `groupBy(key: str) -> Collection` | Group items by `key` into a **dict-backed** `Collection`. |
| `transform` | `transform(callback: Callable) -> Collection` | Replace every item with `callback(item)` in place. |
| `unique` | `unique(key: str \| None = None) -> Collection` | Deduplicate items, optionally by `key`. |
| `where` | `where(key: str, *args: object) -> Collection` | Filter by `key` using `==` or an explicit operator: `where("age", ">", 18)`. |
| `whereIn` | `whereIn(key: str, values: list[Any] \| Collection) -> Collection` | Keep items whose `key` value is in `values`. |
| `whereNotIn` | `whereNotIn(key: str, values: list[Any] \| Collection) -> Collection` | Keep items whose `key` value is **not** in `values`. |
| `zip` | `zip(items: list[Any] \| Collection) -> Collection` | Pair up items positionally with `items`. Raises `TypeError` for other types. |
| `setAppends` | `setAppends(appends: list[str]) -> Collection` | Register extra attribute names to attach on `serialize()` (used with model-like items exposing `set_appends`). |
| `addRelation` | `addRelation(relation_data: dict[str, Any]) -> Collection` | Call `item.setRelation(key, value)` for every item that supports it (ORM integration). |

Supported `where()` operators: `<`, `<=`, `==`, `!=`, `>`, `>=`. An
unsupported operator raises `ValueError`.

### `DotDict` (`orionis.support.types.dot_dict.DotDict`)

```python
DotDict(*args, **kwargs)  # same signature as dict
```

A `dict` subclass (`__slots__ = ()`, no extra instance state) that adds
attribute-style access on top of normal `dict` access — both work at the
same time (`d["a"]` and `d.a`).

| Method | Signature | Description |
|---|---|---|
| `__getattr__` | `__getattr__(key: str) -> object \| None` | Returns the value for `key`, promoting a plain `dict` value to `DotDict` (cached back into the mapping). Returns `None` — **not** `AttributeError` — if `key` is absent. |
| `__setattr__` | `__setattr__(key: str, value: object) -> None` | Sets `self[key] = value`; a plain `dict` value is converted to `DotDict` first. |
| `__delattr__` | `__delattr__(key: str) -> None` | Deletes `self[key]`. Raises `AttributeError` if `key` is absent. |
| `get` | `get(key: str, default: object \| None = None) -> object \| None` | Like `dict.get`, promoting a plain `dict` result to `DotDict`. |
| `export` | `export() -> dict[str, Any]` | Recursively converts the `DotDict` (and any nested `DotDict`/`dict`) back into plain `dict` instances. |
| `copy` | `copy() -> DotDict` | Recursive deep copy that preserves the `DotDict` type at every nesting level. |

Standard `dict` behavior (item access, iteration, `keys()`/`values()`/
`items()`, equality, etc.) is inherited unchanged since `DotDict` does
not override `__getitem__`/`__setitem__`.

### `MISSING` (`orionis.support.types.sentinel.MISSING`)

A module-level singleton instance of the private `_MISSING_TYPE` class,
used as a default-argument sentinel to tell "value not provided" apart
from an explicit `None`.

| Member | Description |
|---|---|
| `MISSING` | The singleton instance. Always falsy (`bool(MISSING) is False`). |
| `repr(MISSING)` | Returns `"<MISSING>"`. |

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

A dynamic, attribute-bag object similar to PHP's `stdClass` or a JS plain
object: any keyword argument becomes an instance attribute, and further
attributes can be added at runtime with regular assignment
(`obj.new_field = 1`) or via `update()`.

| Method | Signature | Description |
|---|---|---|
| `__init__` | `__init__(**kwargs: object) -> None` | Sets each keyword argument as an attribute via `update()`. |
| `update` | `update(**kwargs: object) -> None` | Sets/overwrites attributes in place. Raises `ValueError` for dunder-style names (`__x__`) or names that collide with an existing class attribute/method. |
| `remove` | `remove(*attributes: str) -> None` | Deletes one or more attributes. Raises `AttributeError` if any is missing. |
| `toDict` | `toDict() -> dict` | Shallow copy of `self.__dict__`. |
| `fromDict` | `fromDict(dictionary: dict) -> StdClass` *(classmethod)* | Builds a new instance from a plain `dict` without calling `__init__` (uses `cls.__new__`), applying the same reserved-name validation. |
| `__eq__` | `__eq__(other: object) -> bool` | `True` only if `other` is the exact same type and `__dict__` is equal. |
| `__hash__` | `__hash__() -> int` | XOR of the hash of every `(key, value)` pair — order-independent, but requires every attribute **value** to be hashable. |
| `__repr__` / `__str__` | — | `"ClassName({...})"` / `"{...}"` showing `self.__dict__`. |

`StdClass.RESERVED` (and the equivalent for every subclass, rebuilt in
`__init_subclass__`) is a `frozenset` of every name defined anywhere in
the class MRO; `update()`/`fromDict()` refuse to shadow any of them.

### `Stringable` (`orionis.support.types.stringable.Stringable`)

```python
Stringable(object: object = "") -> Stringable  # same construction as str
```

A `str` subclass (`__slots__ = ()`) providing a large, fluent, Laravel
`Str`/`Stringable`-style API. Because `str` is immutable, **every
transformation method returns a new `Stringable` instance** — the
original value is never mutated. Boolean/testing methods return plain
`bool`, and a few utility methods return plain `int`/`float`/`list`/
`datetime`/`str` when that is the natural return type.

Methods are grouped below by purpose; the exact method name and
signature always match the source file.

**Search & extraction**

| Method | Description |
|---|---|
| `after(search)` / `afterLast(search)` | Substring after the first/last occurrence of `search`. |
| `before(search)` / `beforeLast(search)` | Substring before the first/last occurrence of `search`. |
| `between(from_str, to_str)` / `betweenFirst(from_str, to_str)` | Substring between two delimiters (empty `Stringable` if not found). |
| `substr(start, length=None)` | Substring by `start`/`length` (Python slicing semantics). |
| `charAt(index)` | Character at `index`, or `False` if out of range. |
| `position(needle, offset=0, encoding=None)` | Index of `needle` (like `str.find`), or `False` if not found. |
| `basename(suffix="")` / `dirname(levels=1)` | Path helpers built on `pathlib.Path`. |
| `excerpt(phrase="", options=None)` | Text around the first match of `phrase` (`radius`, `omission` options); `None` if `phrase` not found. |
| `take(limit)` | First/last `limit` characters (negative = from the end). |
| `numbers()` | Keep only digit characters. |

**Predicates (`bool`)**

| Method | Description |
|---|---|
| `contains(needles, *, ignore_case=False)` / `containsAll(needles, *, ignore_case=False)` / `doesntContain(...)` | Substring membership checks. |
| `startsWith(needles)` / `doesntStartWith(needles)` / `endsWith(needles)` / `doesntEndWith(needles)` | Prefix/suffix checks (accept a string or list of strings). |
| `exactly(value)` | Exact string equality. |
| `isEmpty()` / `isNotEmpty()` | Length-based checks. |
| `isAlnum` / `isAlpha` / `isDecimal` / `isDigit` / `isIdentifier` / `isLower` / `isNumeric` / `isPrintable` / `isSpace` / `isTitle` / `isUpper` | Thin wrappers over the equivalent `str.is*()` predicates. |
| `isAscii()` | 7-bit ASCII check via `encode("ascii")`. |
| `isJson()` | Valid JSON via `json.loads`. |
| `isUrl(protocols=None)` | Valid URL with an allowed scheme (default `["http", "https"]`). |
| `isUuid(version=None)` | Valid UUID, optionally of a specific version (`1`-`8` or `"max"`). |
| `isUlid()` | Valid 26-character Crockford Base32 ULID. |
| `isPattern(pattern, *, ignore_case=False)` | Wildcard match (`fnmatch`, `*`/`?`) against one or more patterns. |
| `isMatch(pattern)` / `test(pattern)` | Regex search against one/many patterns. |

**Case & formatting**

| Method | Description |
|---|---|
| `lower()` / `upper()` / `swapCase()` / `ucfirst()` / `lcfirst()` | Basic case operations. |
| `camel()` / `kebab()` / `snake(delimiter="_")` / `studly()` / `pascal()` / `slug(separator="-", dictionary=None)` | Case/format conversions for identifiers and URLs. |
| `title()` / `headline()` / `apa()` | Title-casing variants (`apa()` follows APA capitalization rules). |
| `convertCase(mode=None)` | `0`/`None`=casefold, `1`=upper, `2`=lower, `3`=title. |
| `ascii()` / `transliterate(unknown="?", *, strict=False)` | Normalize/transliterate to ASCII (Unicode NFKD). |

**Transformation**

| Method | Description |
|---|---|
| `append(*values)` / `prepend(*values)` | Concatenate strings after/before. |
| `newLine(count=1)` | Append `count` newline characters. |
| `repeat(times)` | Repeat the string. |
| `reverse()` | Reverse character order. |
| `replace(search, replace, *, case_sensitive=True)` | Single/multiple substring replacement. |
| `replaceArray(search, replace)` | Replace each occurrence of `search` sequentially with items from `replace`. |
| `replaceFirst` / `replaceLast` / `replaceStart` / `replaceEnd` | Positional single replacements. |
| `replaceMatches(pattern, replace, limit=-1)` | Regex-based replacement (string or callback). |
| `remove(search, *, case_sensitive=True)` | Remove all occurrences of one/many substrings. |
| `substrReplace(replace, offset=0, length=None)` | PHP-style `substr_replace`, supports scalar or list arguments. |
| `mask(character, index, length=None)` | Mask part of the string with a repeated character. |
| `swap(map_dict)` | Replace every key in `map_dict` with its value. |
| `deduplicate(character=" ")` | Collapse consecutive occurrences of `character`. |
| `squish()` | Collapse internal whitespace runs and trim. |
| `stripTags(allowed_tags=None)` | Remove HTML/PHP-like tags (or just unescape entities if `allowed_tags` given). |
| `toHtmlString()` | HTML-escape (`html.escape`). |
| `wrap(before, after=None)` / `unwrap(before, after=None)` | Add/remove a prefix+suffix pair. |
| `finish(cap)` / `start(prefix)` | Ensure the string ends/starts with a value (no duplication). |
| `chopStart(needle)` / `chopEnd(needle)` | Remove a leading/trailing value if present. |

**Padding & trimming**

| Method | Description |
|---|---|
| `padBoth(length, pad=" ")` / `padLeft(length, pad=" ")` / `padRight(length, pad=" ")` | Pad to a target length. |
| `trim(characters=None)` / `ltrim(characters=None)` / `rtrim(characters=None)` | Trim like `str.strip`/`lstrip`/`rstrip`. |
| `lStrip(chars=None)` / `rStrip(chars=None)` | Aliases over `str.lstrip`/`rstrip`. |
| `zFill(width)` | Zero-pad (`str.zfill`). |
| `wordWrap(characters=75, break_str="\n", *, cut_long_words=False)` | Wrap text to a column width (`textwrap.fill`). |

**Splitting & words**

| Method | Description |
|---|---|
| `explode(delimiter, limit=-1)` | Split by a literal delimiter into a `list[str]`. |
| `split(pattern, limit=-1, flags=0)` | Split by regex or by fixed chunk length (`int` pattern) into a `list[str]`. |
| `ucsplit()` | Split on uppercase-letter boundaries. |
| `words(words=100, end="...")` | Truncate to a maximum word count. |
| `wordCount(characters=None)` | Count words (optional extra separator characters). |
| `scan(format_str)` | `sscanf`-like extraction using `%s`/`%d`/`%f` placeholders. |
| `match(pattern)` / `matchAll(pattern)` | First regex match / all matches. |
| `parseCallback(default=None)` | Parse a `"Class@method"` string into `[class, method]`. |

**Pluralization**

| Method | Description |
|---|---|
| `plural(count=2, *, prepend_count=False)` | English pluralization (simple suffix rules), aware of `count`. |
| `pluralStudly(count=2)` / `pluralPascal(count=2)` | Pluralize only the last word of a StudlyCase/PascalCase identifier. |
| `singular()` | English singularization (simple suffix rules). |

**Conditional execution (`when*`)**

All `when*` methods share the shape
`whenX(..., callback: Callable, default: Callable | None = None) -> Stringable`:
if the condition holds, `callback(self)` is invoked (wrapped in
`Stringable` if it isn't one already); otherwise `default(self)` runs if
provided, else the original `Stringable` is returned unchanged.

| Method | Condition |
|---|---|
| `when(condition, callback, default=None)` | `condition` (bool or callable applied to `self`). |
| `whenContains` / `whenContainsAll` | `contains()` / all needles present. |
| `whenEmpty` / `whenNotEmpty` | `isEmpty()` / `isNotEmpty()`. |
| `whenEndsWith` / `whenDoesntEndWith` | `endsWith()` and its negation. |
| `whenStartsWith` / `whenDoesntStartWith` | Prefix check and its negation. |
| `whenExactly` / `whenNotExactly` | `exactly(value)` and its negation. |
| `whenTest` | `test(pattern)`. |
| `whenIs` | `isPattern(pattern)` (wildcard match). |
| `whenIsAscii` | `isAscii()`. |
| `whenIsUuid` / `whenIsUlid` | `isUuid()` / `isUlid()`. |

**Conversion & hashing**

| Method | Description |
|---|---|
| `value()` | Plain `str` value. |
| `length()` | `len(self)`. |
| `toInteger(base=10)` / `toFloat()` | Numeric conversion; raise `ValueError` on failure. |
| `toBoolean()` | `True` for `"1"`, `"true"`, `"on"`, `"yes"` (case-insensitive). |
| `toDate(format_str="%Y-%m-%d")` | Parse with `datetime.strptime`, attaching `DateTime.getZoneInfo()`; raises `ValueError` on mismatch. |
| `toBase64()` / `fromBase64(*, strict=False)` | Base64 encode/decode. |
| `md5()` / `sha1()` / `sha256()` / `hash(algorithm)` | Hex digests via `hashlib`. |
| `encrypt()` / `decrypt()` | Delegates to the `Crypt` facade (`orionis.support.facades.encrypter`) — **requires a booted `Application`**. |
| `jsonSerialize()` | `str(self)`, for `json.dumps(..., default=...)` integration. |
| `offsetExists(offset)` / `offsetGet(offset)` | Array-access style helpers (`in`/`[]` semantics). |

**Functional helpers**

| Method | Description |
|---|---|
| `pipe(callback)` | Pass `self` through `callback` and wrap the result in `Stringable`. |
| `tap(callback)` | Call `callback(self)` for a side effect, always return `self` unchanged. |

### Contracts (`ICollection`, `IStdClass`)

`orionis/support/types/contracts/collection.py` and
`.../contracts/std.py` define `ICollection` and `IStdClass` as `abc.ABC`
classes with `@abstractmethod` declarations mirroring the public API of
`Collection` and `StdClass` respectively (docstrings included, no
implementation). They exist so other modules can depend on the
interface (`ICollection`, `IStdClass`) rather than the concrete class —
useful for type hints and test doubles. `Stringable` and `DotDict` have
no separate contract; they are used directly.

---

## Usage examples

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
print(config.export())          # plain nested dict
```

### `MISSING`

```python
from orionis.support.types import MISSING

def resolve(value: object = MISSING) -> str:
    if value is MISSING:
        return "no value provided"
    return f"value: {value!r}"

print(resolve())        # "no value provided"
print(resolve(None))    # "value: None"
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

## Performance and concurrency considerations

- All five types are **plain, synchronous, CPU-bound** objects — there is
  no I/O, no `async`/`await`, and no locking anywhere in this module.
  They are safe to share across `asyncio` tasks as long as the underlying
  data they wrap is not mutated concurrently from multiple tasks/threads
  at once (none of the mutating methods are protected by a lock).
- `Collection` methods that mutate in place (`each`, `sort`, `transform`,
  `reject`, `push`, `pop`, `merge`, …) operate directly on `self._items`
  and are `O(n)`; read-only aggregations (`sum`, `avg`, `max`, `min`)
  short-circuit to `0` on empty input instead of raising.
  `diff()`/`whereIn()`/`whereNotIn()` build a `set` internally for `O(n+m)`
  membership tests instead of the naive `O(n*m)`, falling back to list
  scans only when items are unhashable.
  `contains(callback)` short-circuits with `any()` rather than
  materializing a filtered `Collection`.
- `Stringable` inherits `str`'s immutability: every transformation
  allocates a new string object. For very large strings or hot loops,
  chaining many `Stringable` methods has the same allocation cost as
  chaining the equivalent `str` operations manually — there is no lazy
  or streaming evaluation.
- `Stringable` precompiles its regular expressions as module-level
  constants (`_RE_CAMEL_SEP`, `_RE_KEBAB_CAMEL`, `_ULID_RE`, etc.), so
  repeated calls to `camel()`, `kebab()`, `isUlid()`, and similar methods
  avoid re-compiling the pattern on every call.
- `DotDict.__getattr__`/`get()` cache the `DotDict`-wrapped version of a
  nested plain `dict` back into the mapping the first time it is
  accessed, so subsequent attribute reads of the same nested key do not
  re-wrap it.
- `StdClass.__hash__` and `Collection.__hash__` compute a hash from their
  contents (`__dict__` items / `tuple(self._items)`); both **require**
  every contained value to be hashable, and will raise `TypeError` if you
  try to hash an instance holding a `list`/`dict`/other unhashable value.
- `Stringable.encrypt()`/`decrypt()` go through the `Crypt` facade and the
  Orionis DI container; each call pays the cost of an (async-capable)
  facade resolution and must run where an `Application` has already been
  booted.

## Design notes

- **Fluent/chainable API**: `Collection` and `Stringable` follow the same
  design as Laravel's `Illuminate\Support\Collection` and `Stringable` —
  most methods return a new instance of the same type so calls can be
  chained (`Stringable(...).trim().studly().slug()`).
- **Immutability by base type**: `Stringable` extends `str` and uses
  `__slots__ = ()`, so instances carry no extra per-object state beyond
  the string payload itself; every "mutator" is really a constructor
  call for a new instance.
- **Sentinel pattern**: `MISSING` is a private, single-instance class
  (`_MISSING_TYPE`) rather than using `None`, matching the well-known
  Python idiom for telling "not passed" apart from "passed as `None`"
  (mirrored internally by `_MISSING` sentinels used inside `Collection`
  and `DotDict` for the same purpose).
- **Reserved-name protection**: `StdClass` computes `RESERVED` — a
  `frozenset` of every attribute/method name across the class MRO — in
  `__init_subclass__`, so dynamically setting an attribute can never
  silently shadow a real method (`update()`/`fromDict()` raise
  `ValueError` instead).
- **Contracts as ABCs**: `ICollection`/`IStdClass` are `abc.ABC` classes
  with only `@abstractmethod` declarations (no implementation, no
  `__slots__` conflicts with the concrete classes), used purely for
  interface-based type hints and testing.
- **Dict/list duality in `Collection`**: `Collection` normally wraps a
  `list`, but `groupBy()` deliberately returns a `Collection` wrapping a
  `dict`; methods that assume a list (e.g. `forget`, `sort` without a
  key) are not meant to be called on a dict-backed `Collection`.

## Compatibility notes

- Requires **Python 3.14+**, consistent with the rest of the `orionis`
  framework (`requires-python = ">=3.14"` in `pyproject.toml`).
- Depends on `dotty-dict~=1.3`, already a core dependency of `orionis`
  (used by `Collection.__dataGet` for dotted/wildcard key lookups on
  dict items).
- `Stringable.toDate()` depends on `orionis.support.facades.datetime.DateTime`
  (backed by `pendulum` and `zoneinfo`) purely for its default timezone;
  it does not require the DI container.
- `Stringable.encrypt()`/`decrypt()` depend on
  `orionis.support.facades.encrypter.Crypt`, which requires a booted
  Orionis `Application` with `EncrypterProvider` registered (the default
  in a standard Orionis application).
- No platform-specific behavior; all five types are pure Python with no
  OS-level dependencies.

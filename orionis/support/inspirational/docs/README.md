# Orionis Inspirational

> A tiny, dependency-free service that returns a random inspirational quote.
>
> 🇪🇸 Spanish version: [README.es.md](README.es.md)

`orionis.inspirational` is a small utility module bundled with the Orionis
Framework. It ships a curated collection of quotes and a minimal service,
`Inspire`, that picks one at random. It is used, among other things, by the
default `app:inspire` console command that is generated in every new Orionis
project as a "hello world" style example of a command with an injected
service.

---

## Table of contents

1. [Requirements](#requirements)
2. [What this module solves](#what-this-module-solves)
3. [Module layout](#module-layout)
4. [API reference](#api-reference)
   - [`IInspire` (contract)](#iinspire-contract)
   - [`Inspire`](#inspire)
   - [`INSPIRATIONAL_QUOTES`](#inspirational_quotes)
5. [Usage examples](#usage-examples)
6. [Design notes](#design-notes)
7. [Performance and concurrency considerations](#performance-and-concurrency-considerations)
8. [Compatibility notes](#compatibility-notes)

---

## Requirements

No extra installation step is required beyond `pip install orionis`. The
module only uses the Python standard library (`secrets`, `typing`, `abc`) —
there are no third-party dependencies.

## What this module solves

Applications (and the framework's own scaffolding) sometimes need a small,
self-contained piece of "flavor text" — a motivational quote to print on a
console command, a splash screen, a log banner, etc. `orionis.inspirational`
solves this in the simplest possible way:

- A read-only dataset of curated quotes (`quotes.py`).
- A tiny service (`Inspire`) that exposes a single operation: pick one quote
  at random.
- An abstract contract (`IInspire`) so the service can be type-hinted,
  mocked, or swapped for a custom implementation (e.g. one that fetches
  quotes from a remote API) without touching the code that consumes it.

It is intentionally minimal: there is no caching, no persistence, and no
network access involved.

## Module layout

```
orionis/inspirational/
├── __init__.py          # Public re-export: Inspire
├── inspire.py            # Inspire service implementation
├── quotes.py              # INSPIRATIONAL_QUOTES dataset (361 curated quotes)
└── contracts/
    ├── __init__.py        # Public re-export: IInspire
    └── inspire.py          # IInspire abstract contract
```

Internal dependency direction: `inspire.py` depends on `contracts/inspire.py`
(to implement `IInspire`) and on `quotes.py` (as its default dataset). There
are no other internal or external dependencies.

## API reference

### `IInspire` (contract)

`orionis.inspirational.contracts.inspire.IInspire`

Abstract base class (`abc.ABC`) that defines the public contract every
"inspire" implementation must follow.

```python
class IInspire(ABC):
    @abstractmethod
    def random(self) -> dict: ...
```

| Member | Description |
| --- | --- |
| `random() -> dict` | Must return a dictionary with `quote` (`str`) and `author` (`str`) keys. Implementations should always return a valid quote, falling back to a default one when no data is available. |

Use this contract to type-hint dependencies (`def handle(self, inspire: IInspire)`)
or to provide an alternative implementation (for tests, or a data source
other than the bundled list).

### `Inspire`

`orionis.inspirational.inspire.Inspire(IInspire)`

Concrete, dependency-free implementation of `IInspire`. Declares `__slots__`
(`_count`, `_quotes`), so instances have no `__dict__` and cannot gain
arbitrary attributes at runtime.

```python
Inspire(quotes: list[dict] | None = None) -> None
```

| Parameter | Type | Description |
| --- | --- | --- |
| `quotes` | `list[dict] \| None` | Optional custom collection of quotes. Each item must be a `dict` containing at least `quote` (`str`) and `author` (`str`). If `None` or an empty list, the built-in `INSPIRATIONAL_QUOTES` dataset (361 entries) is used instead. |

Raises:

| Exception | When |
| --- | --- |
| `TypeError` | Any item in `quotes` is not a `dict`. |
| `ValueError` | Any item in `quotes` is missing the `quote` or `author` key. |

Validation only runs when a custom `quotes` argument is passed — the default
dataset is trusted and not re-validated on every instantiation.

#### `Inspire.random() -> dict`

Returns a random quote as a dictionary with `quote` and `author` keys.

- Uses `secrets.choice(...)` (a cryptographically secure random generator)
  to pick an entry from the internal list — not `random.choice`.
- If the internal quotes collection is empty (only possible if the instance
  was mutated after construction, since the constructor never allows an
  empty final state through the default path), a fixed fallback quote is
  returned instead of raising an exception:

  ```python
  {
      "quote": "Greatness is not measured by what you build, "
               "but by what you inspire others to create.",
      "author": "Raul M. Uñate",
  }
  ```

This method never raises and never returns `None` — it always returns a
valid `dict` with both keys populated.

### `INSPIRATIONAL_QUOTES`

`orionis.inspirational.quotes.INSPIRATIONAL_QUOTES: tuple[dict, ...]`

An immutable tuple of 361 curated `{"quote": str, "author": str}` dictionaries,
used as the default dataset by `Inspire` when no custom list is supplied.
It is exposed at module level so it can be imported directly if you only
need the raw data (e.g. to seed a database, build a custom picker, etc.).

```python
from orionis.inspirational.quotes import INSPIRATIONAL_QUOTES

len(INSPIRATIONAL_QUOTES)  # 361
```

## Usage examples

### Basic usage — random quote with the default dataset

```python
from orionis.inspirational import Inspire

inspire = Inspire()
result = inspire.random()

print(f"{result['quote']} — {result['author']}")
```

### Providing a custom list of quotes

```python
from orionis.inspirational import Inspire

my_quotes = [
    {"quote": "Ship it.", "author": "Anonymous"},
    {"quote": "Done is better than perfect.", "author": "Sheryl Sandberg"},
]

inspire = Inspire(quotes=my_quotes)
print(inspire.random())  # one of the two dicts above, picked at random
```

### Invalid input raises immediately

```python
from orionis.inspirational import Inspire

# TypeError: items must be dictionaries.
Inspire(quotes=["not a dict"])

# ValueError: every dictionary must contain 'quote' and 'author'.
Inspire(quotes=[{"quote": "Missing author"}])
```

### Depending on the abstract contract

```python
from orionis.inspirational.contracts.inspire import IInspire
from orionis.inspirational import Inspire


def print_daily_quote(service: IInspire) -> None:
    data = service.random()
    print(f"\"{data['quote']}\"\n— {data['author']}")


print_daily_quote(Inspire())
```

### Real-world usage: console command with injected service

This is how the module is used by the built-in `app:inspire` command
(`app/console/commands/inspire_command.py`). The Orionis container resolves
`Inspire` automatically because it is a concrete class with only optional,
defaultable constructor parameters, so no explicit binding is required:

```python
from orionis.console.base import BaseCommand
from orionis.inspirational import Inspire


class InspireCommand(BaseCommand):
    signature: str = "app:inspire"
    description: str = "Prints a random inspirational quote."

    async def handle(self, inspire: Inspire) -> None:
        quote, author = inspire.random().values()
        print(f"{quote} — {author}")
```

## Design notes

The following are informational notes about existing design decisions in
this module — they describe *why* the code behaves the way it does, not a
proposal to change it.

- **`__slots__`**: `Inspire` declares `__slots__ = ("_count", "_quotes")` to
  avoid the overhead of a per-instance `__dict__`, since the service holds
  no dynamic state beyond the quotes list and its cached length.
- **Cached length (`_count`)**: the number of quotes is computed once at
  construction time and reused on every `random()` call to avoid calling
  `len(...)` repeatedly and to make the "is the list empty" check a cheap
  integer comparison.
- **`ClassVar` fallback**: `_FALLBACK` is declared as a `ClassVar[dict]`,
  shared by all instances rather than duplicated per instance, since it is
  constant data.
- **`secrets.choice` instead of `random.choice`**: the module favors the
  `secrets` module's cryptographically secure generator for selecting
  quotes. This has no practical security implication for this use case
  (quotes are not sensitive data), but it is the generator actually used by
  the implementation, so callers should not assume statistical properties
  specific to Python's `random` module (e.g. seeding via `random.seed(...)`
  has no effect on `Inspire.random()`).
- **Contract-first design**: `Inspire` implements `IInspire`, an `ABC` with
  a single abstract method. This allows the service to be swapped for a
  different implementation (e.g. quotes from an external source) anywhere
  it is type-hinted as `IInspire`, without changing consumer code.
- **No provider/facade wiring**: unlike other Orionis services, this module
  does not ship a service provider or a facade. `Inspire` is meant to be
  used either via direct instantiation or via constructor injection, relying
  on the container's ability to auto-build concrete classes that expose no
  required constructor arguments.

## Performance and concurrency considerations

- `Inspire.random()` is a synchronous, CPU-bound, allocation-light
  operation (a single call to `secrets.choice` over an in-memory sequence).
  It performs no I/O, so it does not need to be awaited and does not block
  an event loop in any way that matters in practice.
- `Inspire` instances are safe to share and reuse; both `_quotes` and
  `_count` are set once in `__init__` and never mutated by any public
  method. Concurrent calls to `random()` from multiple threads or async
  tasks on the same instance are safe as long as external code does not
  reach into the private attributes (`_quotes`, `_count`) and mutate them
  directly.
- The default `INSPIRATIONAL_QUOTES` dataset is a module-level tuple built
  once at import time and shared by every `Inspire()` instance created
  without a custom `quotes` argument — no per-instance copy is made.
- Validation of custom `quotes` lists is `O(n)` in the number of items and
  only runs once, at construction time — not on every `random()` call.

## Compatibility notes

- **Minimum Python version**: 3.14+ (as required by the Orionis Framework
  as a whole; this module itself only relies on standard-library features
  available in much earlier versions).
- **Dependencies**: none beyond the Python standard library
  (`secrets`, `typing`, `abc`).
- **Type hints**: the module uses PEP 604 union syntax (`list[dict] | None`)
  and `ClassVar` from `typing`.

# Factories and testing

A factory builds example models through their normal constructor. Use factories for tests and development data; they do not discover relationships, migrate tables, or automatically hash passwords.

## Generate reproducible data without persistence

```python
from typing import ClassVar
from orionis.orm import Integer, Model, String
from orionis.orm.factories import Factory, Sequence


class Product(Model):
    id = Integer().primary().autoIncrement()
    name = String(120)
    status = String(30)
    timestamps = False
    fillable: ClassVar[list[str]] = ["name", "status"]


class ProductFactory(Factory[Product]):
    model = Product

    def definition(self) -> dict:
        return {"name": self.fake.word(), "status": "draft"}


products = ProductFactory(seed=7).count(2).sequence(
    Sequence({"status": "draft"}, {"status": "published"})
).make()
assert [product.status for product in products] == ["draft", "published"]
assert all(product.isDirty("name") for product in products)
```

`definition()` must be synchronous and return a dictionary. `model` must be concrete. `make()` neither accesses the database nor fires persistence events: count 1 returns a model; other counts return a `Collection`. `count(0)` allows an empty collection. `seed` applies to that instance's random generator, avoiding dependence on another test's random state.

## States, sequences, and overrides

`state({...})` adds fixed attributes; `state(callable)` derives attributes from the preceding dictionary. States apply in order, then the sequence, then overrides supplied to `make(name="Fixed")` or `create(name="Fixed")`. Every level must respect model column names and `fillable` rules. Nested attributes are copied to avoid sharing a dictionary between models accidentally.

`Sequence({...}, {...})` rotates states; callable states follow the sequence contract. Its index belongs to the factory and advances between generations. Do not rely on a global index shared by tests.

`self.fake` wraps Faker with camelCase names such as `firstName()`, `safeEmail()`, and `word()`. `locale=` selects a locale; otherwise the factory attempts `app.locale` and falls back to `en_US` when configuration or a usable locale is unavailable. `fake.unique` remembers values seen by that instance; `clearUnique()` resets that registry. Faker uniqueness does not ensure uniqueness against existing database rows. Do not use generated data for real credentials.

`fake.optional` exposes a provider view accepting `prob`; `fake.addProvider(provider)` registers custom providers and invalidates cached methods. `seedInstance(seed)` and `seedLocale(locale, seed)` provide explicit reseeding; `locales` returns a detached list. `UniqueFake` and `OptionalFake` are exported for typing and extending these views without placing services in generated attributes.

## Persist with controlled failures

With the application booted and `products` migrated:

```python
from orionis.support.facades import DB


async def create_catalog():
    async with DB.transaction():
        return await ProductFactory(seed=7).count(3).create(status="published")
```

`create()` awaits each model's `save()`, including mutators/casts/events, and returns the same cardinality as `make()`. **It does not open a transaction itself**: earlier models survive a later failure unless the caller provides a transaction. Event veto raises `FactoryPersistenceException`, unlike convenience `Model.create()`, which returns its instance without exposing that veto as a boolean.

## Generate incrementally

`iterMake()` yields models without a complete result collection; `iterCreate()` is an async iterator that saves one at a time. Close partially consumed iterators before reusing the factory. Use `contextlib.aclosing` when stopping async iteration early:

```python
from contextlib import aclosing


async def create_first_product():
    factory = ProductFactory(seed=7).count(100)
    async with aclosing(factory.iterCreate()) as stream:
        async for product in stream:
            return product
```

This example persists only the first model and requires database infrastructure. It is not ORM query streaming.

A factory retains count, states, sequence, and Faker state. Overlapping use or reconfiguration while iterating raises `FactoryConcurrencyException`: create an instance per task. `FactoryConfigurationException` and `FactoryDefinitionException` distinguish invalid definitions from persistence failures. SQL failures retain database-layer errors.

For isolated tests, use in-memory SQLite with a dedicated manager/resolver, as the module tests do. `ConnectionResolver.setManager(manager)` installs the global bridge and `clear()` removes it; do not replace that global while other tests/tasks query. Dialect tests need the corresponding server. Combine these practices with [Testing](../../../test/docs/en/README.md).

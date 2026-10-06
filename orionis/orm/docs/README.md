# orionis.orm

> `orionis.orm` is Orionis' async Active Record layer, fluent query API, relationship system, schema vocabulary, and model factory toolkit.

## Overview

The ORM maps declarative `Model` subclasses to engine-independent table definitions. A metaclass computes table names, columns, casts, mass-assignment rules, accessors, scopes, events, timestamps, and soft-delete metadata once when the class is created. Queries build typed plans; the database package compiles and executes those plans for SQLite, MySQL, PostgreSQL, Oracle, or SQL Server.

Model persistence and query terminals are asynchronous. Definition, attribute manipulation, query composition, serialization, collections, and factory `make()` remain synchronous until I/O is requested.

## Requirements

- Python 3.14 or newer.
- A configured and booted `orionis.database` connection manager before executing queries.
- Database tables matching the model definitions, normally managed by migrations.
- `faker` support included by Orionis when using model factories.

## Quick start

```python
from typing import ClassVar
from orionis.orm import Integer, Model, String


class User(Model):
    id = Integer().primary().autoIncrement()
    name = String(120)
    email = String(255).unique()

    fillable: ClassVar[list[str]] = ["name", "email"]
    timestamps = False


user = User({"name": "Ada", "email": "ada@example.test"})
assert User.__meta__.table_name == "users"
assert User.__meta__.primary_key == "id"
assert user.toDict() == {"name": "Ada", "email": "ada@example.test"}
```

Validation: **Executed successfully** on CPython 3.14.6; no database access occurred.

## Core concepts

### Models and metadata

Concrete models declare `ColumnDefinition` instances as class attributes. Unless overridden, the class name becomes a snake-case plural table name. Model metadata is precomputed and contains a `TableDefinition` shared with migrations and SQL compilers. Set `table`, `connection`, `primary_key`, `incrementing`, `timestamps`, `soft_deletes`, or `uuids` only when conventions do not fit.

### Attributes and state

`fillable` is an allowlist and `guarded` is a denylist; `guarded = ["*"]` blocks all mass assignment. Direct assignment still passes through declared mutators. `casts` apply during assignment/hydration, `hidden` omits values from serialization, and `appends` adds accessor-backed values. Dirty/original/change tracking is available through `getDirty`, `isDirty`, `isClean`, `wasChanged`, `getChanges`, and `getOriginal`.

### Fluent query plans

Class calls such as `User.where(...)` forward to a fresh `ModelQueryBuilder`. The builder accumulates an engine-neutral `SelectPlan`; `get`, `first`, `paginate`, aggregates, inserts, updates, and deletes resolve the model connection only at execution. `clone()` creates independent state. Raw fragments exist, but ordinary fluent clauses preserve binding and portability.

### Relations and eager loading

Instance methods declare `hasOne`, `hasMany`, `belongsTo`, and `belongsToMany` relations. `withRelations()`/`load()` batch eager loading and store results on each model. Many-to-many relations manage pivot reads plus `attach`, `detach`, `sync`, and pivot updates.

### Lifecycle and deletion

Events include `retrieved`, `saving`, `creating`, `created`, `updating`, `updated`, `saved`, `deleting`, `deleted`, `restoring`, and `restored`. Before-events can veto by returning `False`. Soft-delete models add the delete timestamp automatically, exclude trashed rows by default, and support `withTrashed`, `onlyTrashed`, `restore`, and `forceDelete`.

## Module structure

| Path | Responsibility |
|---|---|
| `model.py`, `metaclass.py` | Active Record API and precomputed model metadata. |
| `attributes.py`, `state.py`, `events.py`, `soft_deletes.py` | Attribute, change, lifecycle, and deletion behavior. |
| `query/` | Model and raw builders, immutable expressions, joins, and query plans. |
| `relations/` | One-to-one, one-to-many, inverse, and pivot-backed relations. |
| `schema/` | Engine-neutral tables, columns, constraints, and column types. |
| `collections/` | Framework `Collection` re-export and length-aware `Paginator`. |
| `factories/` | Deterministic model generation, sequences, Faker facade, and streams. |
| `resolver.py`, `provider.py`, `query_builder.py` | Connection bridge and model-less `DB` facade gateway. |
| `contracts/`, `exceptions/` | Stable interfaces and ORM-specific failures. |

## Public API

The root package lazily exports `Model`, `ModelQueryBuilder`, `ConnectionResolver`, `Collection`, `ModelCollection`, `Paginator`, relation classes, ORM exceptions, and the full engine-neutral column-type vocabulary (`Integer`, `String`, `DateTime`, `StrictJson`, `Uuid`, and others).

### `Model`

- Retrieval: `all`, `find`, `findOrFail`, `first`, `firstOrFail`.
- Persistence: `create`, `save`, `update`, `delete`, `destroy`, `restore`, `forceDelete`.
- Serialization: `toDict`, `serialize`, `toJson`, `only`, `exclude`.
- Query entry: `query` plus forwarded fluent builder methods.
- Extensibility: accessors/mutators by naming convention, local/global scopes, observers, and event listeners.

### Builders

`QueryBuilderBase` supplies selection, nested conditions, `IN`/`NULL`/range/pattern predicates, column comparisons, subqueries, joins, grouping, ordering, pagination, locks, unions, aggregates, and writes. `ModelQueryBuilder` adds hydration, scopes, relations, model failures, and soft-delete policy. `RawQueryBuilder` returns dictionaries instead of model instances.

### Factories

`orionis.orm.factories` exports `Factory`, `Sequence`, `Fake`, typed unique/optional Faker wrappers, and factory exceptions. `make()`/`iterMake()` do not persist; `create()`/`iterCreate()` await normal model saves and events.

## Common workflows

### Define and migrate a model

Declare columns on a model, then use its `table_definition`/`__meta__.table` through Orionis migrations. Model declaration does not create tables automatically.

### Query and paginate

Compose filters before awaiting a terminal. Outside a transaction, pagination can count and fetch concurrently; inside a transaction it runs sequentially because both operations share one transactional connection.

### Protect writes

Define `fillable` or `guarded` for every externally populated model. Use transactions from the `DB` facade when several writes must succeed atomically; `Factory.create(count > 1)` does not open an implicit transaction.

### Avoid N+1 relation reads

Use `withRelations("relationName")` for lists. Lazy relationship methods return relation builders and may execute separate queries when resolved.

## Examples

### Inspect a query plan without executing it

```python
from orionis.orm import Integer, Model, String


class Article(Model):
    id = Integer().primary().autoIncrement()
    title = String()
    status = String()
    timestamps = False


plan = (
    Article.where("status", "published")
    .whereContains("title", "Orionis")
    .orderBy("id", "desc")
    .limit(10)
    .toPlan()
)
assert plan.table.name == "articles"
assert plan.limit_value == 10
assert len(plan.wheres) == 2
```

Validation: **Executed successfully** on CPython 3.14.6; only an in-memory query plan was built.

### Use accessors, mutators, hiding, and dirty state

```python
from typing import ClassVar
from orionis.orm import Integer, Model, String


class Account(Model):
    id = Integer().primary().autoIncrement()
    name = String()
    token = String().nullable()
    timestamps = False
    hidden: ClassVar[list[str]] = ["token"]
    appends: ClassVar[list[str]] = ["label"]

    def setNameAttribute(self, value: str) -> str:
        return value.strip()

    def getLabelAttribute(self, value=None) -> str:
        return self.name.upper()


account = Account({"name": " Ada ", "token": "secret"})
assert account.name == "Ada"
assert account.isDirty("name")
assert account.toDict() == {"name": "Ada", "label": "ADA"}
```

Validation: **Executed successfully** on CPython 3.14.6.

### Generate unsaved models with a factory

```python
from orionis.orm import Integer, Model, String
from orionis.orm.factories import Factory, Sequence


class Product(Model):
    id = Integer().primary().autoIncrement()
    name = String()
    status = String()
    timestamps = False


class ProductFactory(Factory[Product]):
    model = Product

    def definition(self) -> dict:
        return {"name": self.fake.word(), "status": "draft"}


products = ProductFactory(seed=7).count(2).sequence(
    Sequence({"status": "draft"}, {"status": "published"}),
).make()
assert len(products) == 2
assert [item.status for item in products] == ["draft", "published"]
```

Validation: **Executed successfully** on CPython 3.14.6; the models were not persisted.

### Serialize pagination metadata

```python
from orionis.orm import Collection, Paginator

page = Paginator(Collection([{"id": 3}, {"id": 4}]), total=5, page=2, per_page=2)
assert page.lastPage == 3
assert page.hasPrevious is True
assert page.hasNext is True
assert page.toDict()["items"] == [{"id": 3}, {"id": 4}]
```

Validation: **Executed successfully** on CPython 3.14.6.

### Execute model workflows in an application

```python
from orionis.support.facades import DB


async def publish_article(article_id: int) -> None:
    async with DB.transaction():
        article = await Article.findOrFail(article_id)
        await article.update({"status": "published"})


async def recent_articles():
    return await (
        Article.withRelations("author")
        .where("status", "published")
        .latest()
        .paginate(page=1, per_page=20)
    )
```

Validation: **Import and syntax validated** on CPython 3.14.6; execution requires a booted application, matching tables, and an `author` relationship.

### Declare relationships

```python
from orionis.orm import Integer, Model, String


class Post(Model):
    id = Integer().primary().autoIncrement()
    user_id = Integer().index()
    title = String()
    timestamps = False

    def author(self):
        return self.belongsTo(User, "user_id")


def user_posts(user: User):
    return user.hasMany(Post, "user_id")


assert Post.__meta__.table.hasColumn("user_id")
```

Validation: **Executed successfully** on CPython 3.14.6; relation queries were declared but not executed.

## Configuration

The ORM has no separate configuration file. It consumes `config/database.py` through the database manager. The principal selector is `DB_CONNECTION`; driver-specific settings include `DB_URL`, `DB_DATABASE`, `DB_HOST`, `DB_PORT`, `DB_USERNAME`, `DB_PASSWORD`, `DB_PREFIX`, charset/collation, SQLite pragmas, PostgreSQL search path/SSL, Oracle DSN/service settings, and SQL Server encryption/ODBC settings.

A model may set `connection = "name"` to select a configured connection. The model-less `DB.connection("name")` returns a new scoped gateway instead of mutating the singleton.

## Integration with Orionis

The database provider installs its connection manager in `ConnectionResolver`. `QueryBuilderProvider` binds `IQueryBuilder` to `QueryBuilder` as a singleton and pins the `DB` facade. Migrations consume the same `TableDefinition` objects generated for models, while factories and tests can use isolated managers.

Model methods never expose SQLAlchemy objects. This boundary lets the database package own dialect compilation, pooling, transactions, and query exceptions.

## Errors and edge cases

- Querying before the database provider installs a manager raises `OrmConfigurationException`.
- `findOrFail`/`firstOrFail` raise `ModelNotFoundException`; missing eager relations raise `RelationNotFoundException`.
- Invalid clauses or pagination values raise `InvalidQueryException`; guarded input raises `MassAssignmentException`.
- Empty `fillable` means all non-guarded declared columns are fillable. Use explicit policy for untrusted input.
- `save()` may return `False` when a before-listener vetoes; callers must not assume every attempted write persisted.
- Builders are mutable. Reuse `clone()` when branching queries and do not share one builder between concurrent tasks.
- Soft deletes affect default model queries; raw table queries do not automatically apply model scopes.

## Performance and concurrency

Reflection and cast lookup are precomputed at class creation. Query builders carry independent plans, and connection selection is stored by value. Eager loading reduces repeated relation queries. Pagination uses concurrent count/data reads only when no transaction is active.

Factories reject overlapping use of one instance; create one factory per task. Large result sets should use bounded queries or pagination. Transaction-bound work is intentionally serialized on the shared connection, while pooled non-transactional queries may proceed concurrently.

## Compatibility

The public model/query vocabulary is engine-neutral across configured SQLite, MySQL, PostgreSQL, Oracle, and SQL Server backends. Individual column types, locks, regular expressions, collations, generated values, and DDL options remain subject to dialect support. Python 3.14+ is required by generic class syntax and the framework baseline.

## Verification notes

- `tests/orm`: **481 test methods passed** with the Orionis runner on CPython 3.14.6.
- Seven bilingual documentation programs were compiled; six standalone programs were executed successfully.
- The application transaction/query example was import/syntax validated because it requires database wiring and schema state.
- Evidence covered model metadata, CRUD/events, casts/state, query plans, relations, soft deletes, factories, collections, pagination, schemas, providers, and lazy package exports.


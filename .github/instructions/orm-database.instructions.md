---
name: "Orionis ORM and Database"
description: "Use when working with the Orionis ORM or database layer: models and column definitions, the shared query builder, relations, soft deletes, scopes, accessors and model events, DB.table(), the SQL compiler, connections, dialects, transactions and migrations."
applyTo: "orionis/orm/**,orionis/database/**,app/models/**,database/**"
---

# ORM and database

> **Read `orionis/orm/README.es.md` first** (module root, Spanish only): it is
> the full manual for models, query builder, relations, soft deletes, scopes,
> events, casts, pagination and testing.
> `orionis/database/` has **no** documentation yet — read the code.

## Architecture

```
Model → ModelQueryBuilder ─┐
                           ├→ IR (SelectPlan/InsertPlan/UpdatePlan/DeletePlan)
DB.table() → RawQueryBuilder ┘        ↓
                              Connection → SQLCompiler → SQLAlchemy Core 2 async
```

- **SQLAlchemy Core 2 async only.** `Session`, `declarative_base` and the SQLAlchemy ORM
  are forbidden. SQLAlchemy is imported only in
  `orionis/database/{compiler,connection,dialect}.py`.
- `QueryBuilderBase` (`orionis/orm/query/base_builder.py`) owns the `SelectPlan` and the
  whole query language; `ModelQueryBuilder` and `RawQueryBuilder` inherit from it. A
  parity test compiles both plans and compares the SQL — keep them sharing the engine.
- The IR (`orionis/orm/query/expressions.py`) is slotted dataclasses with **zero**
  SQLAlchemy dependency.
- Connections come from `ConnectionResolver.connection(name)`, **never** from the
  container.
- Transactions are task-local (`ContextVar`) and nest via `begin_nested()` (SAVEPOINT).
- Drivers: `sqlite` (bundled), `mysql`, `pgsql`, `oracle`, `sqlserver`. Each DB extra
  installs both the async driver (Connection) and the sync one (scheduler jobstore).
- Module-level functions in `orionis/database/dialect.py` are **snake_case**
  (`resolve_driver`, `build_engine_url`, `engine_options`, `missing_dependency_error`).

## Model

```python
from typing import ClassVar
from orionis.orm import Model
from orionis.orm import BigInteger, String, DateTime, Boolean

class User(Model):

    casts: ClassVar[dict[str, str]] = {"active": "bool"}
    hidden: ClassVar[list[str]] = ["password", "remember_token"]
    fillable: ClassVar[list[str]] = ["name", "email", "password"]

    id = BigInteger().primary().autoIncrement()
    name = String(255)
    email = String(255).unique()
    password = String(255)
    active = Boolean().default(value=True)
    created_at = DateTime().nullable()
    updated_at = DateTime().nullable()
```

- **Declaring columns in the class body is mandatory** (unlike Eloquent): `meta.columns`
  comes from there and mass assignment does not work without it.
- `ModelMeta` detaches the `ColumnDefinition`s so instance access goes to `_attributes`,
  resolves the table name as `pluralize(snake_case(Class))`, and forwards builder methods
  (`User.where(...)` works without `.query()`).
- Class options: `__abstract__`, `casts`, `hidden`, `fillable`, `guarded`, `timestamps`,
  `primary_key`, `soft_deletes`, `uuids`, `appends`.
- `ModelMetadata` attributes are snake_case (`table_name`, `primary_key`, `cast_lookup`,
  `created_column`, `updated_column`, `deleted_column`).
- Casts: `int`, `float`, `bool`, `datetime`, `date`, `json`, `uuid` — precompiled.
- `get()` returns `orionis.support.types.collection.Collection`.
- **Composite keys are not supported**, on purpose.

## Query language

`where` / `orWhere` / `whereIn` / `whereNotIn` / `whereNull` / `whereNotNull` /
`whereBetween` / `whereNotBetween` / `whereLike` / `whereNotLike` / `whereILike` /
`whereNotILike` / `whereStartsWith` / `whereEndsWith` / `whereContains` /
`whereRegexpMatch` / `whereColumn` / `whereRaw` / `whereExists` / `whereNotExists` ·
nested groups with `where(lambda q: ...)` · `select` / `selectRaw` / `distinct` /
`orderBy` / `groupBy` / `having` / `limit` / `offset` · `join` / `leftJoin` /
`rightJoin` / `crossJoin` / `joinSub` · `union` · `lock` · `clone` / `toPlan` ·
terminals `get` / `first` / `firstOrFail` / `find` / `count` / `exists` / `paginate` /
`insert` / `update` / `delete`.

Compiler notes: RIGHT JOIN is emulated by swapping sides (SQLAlchemy Core has none),
FULL uses `full=True`, and `not_between` does not exist → use `~column.between(a, b)`.
`_ensureRawColumns` backfills columns for schemaless tables and must run **before** any
`Table.alias(...)` (aliases memoise `.c` on first access).

## Relations

Declared as **instance methods**, never class-level descriptors (descriptors evaluate at
class-definition time and break on real circular model references):

```python
class User(Model):
    def posts(self):
        """Return the posts relation."""
        return self.hasMany(Post)
```

- `hasOne`, `hasMany`, `belongsTo`, `belongsToMany` live in `RelationsMixin`.
- Every `Relation` **inherits from `ModelQueryBuilder`** and implements `__await__`, so
  `await user.posts()` is a shortcut while `user.posts().where(...).get()` still works.
- Eager loading: `User.with_("posts")` (underscore because `with` is a keyword) or
  `.load(...)`. Reading the cached result requires `model.getRelation("posts")` —
  `model.posts` is always the bound method.
- `belongsToMany` runs 2 queries (pivot + related) instead of a JOIN to avoid column name
  collisions; it exposes `attach`, `detach`, `sync`, `toggle`, `wherePivot`.
- Foreign key inference differs from Laravel on `belongsTo`: Orionis uses the **related
  class name**, not the method name (no stack-frame reflection).

## Model features

- **Soft deletes**: `soft_deletes = True` + `deleted_at`; the metaclass forces
  `.nullable()` on that column. Methods: `restore`, `forceDelete`, `trashed`,
  `withTrashed`, `onlyTrashed`, `withoutTrashed`.
- **Scopes**: `scope<Name>` as classmethod/staticmethod → `Model.<name>()`. Global scopes
  and the soft-delete filter are applied in `_beforeExecute()` (idempotent), not in
  `__init__`, so `withTrashed()` works anywhere in the chain.
- **Accessors/mutators**: `get<Name>Attribute` / `set<Name>Attribute`, plus `appends`.
- **11 model events** via `registerEvent`, `observe`, `flushEvents`, `fireEvent`.
  "Before" events (`saving`, `creating`, `updating`, `deleting`, `restoring`) abort the
  operation when a listener returns `False`. Events and global scopes are **class state**
  and are inherited — clear them in test teardown.

## Column types

`orionis/orm/schema/types/` — one class per file.
Generic CamelCase types carry no prefix (`BigInteger`, `Boolean`, `DateTime`, `Integer`,
`Numeric`, `String`, `Text`, `Uuid`, ...); dialect-specific ones use the `Strict` prefix
(`StrictArray`, `StrictBigInt`, `StrictDecimal`, `StrictJson`, `StrictTimestamp`,
`StrictVarChar`, ...). Constructor signatures mirror SQLAlchemy 2.1 except that **every
`bool` parameter is keyword-only** (Ruff FBT001/FBT002). Column state is grouped in
`ColumnOptions`; concrete types never poke slots directly.

## Migrations

```python
class CreateUsersTable(Migration):

    async def up(self) -> None:
        """Create the users table."""
        async with Schema.create("users") as table:
            table.id()
            table.string("email", 255).unique()
            table.boolean("active").default(value=True)
            table.timestamps()

    async def down(self) -> None:
        """Drop the users table."""
        await Schema.drop("users")
```

- `Schema.create(...)` is sync and returns a `TableCreation` supporting both
  `await` and `async with` (the table is only created if the block did not raise).
- `Migrator` tracks the `migrations` table (id / migration / batch / migrated_at) and
  runs **each migration inside its own transaction** together with its tracking row.
- Commands: `migrate`, `migrate:rollback --step=N`, `migrate:reset`, `migrate:refresh`,
  `migrate:fresh`, `migrate:status`, all accepting `--database/-d`.
- `migrator.py` must **not** use `from __future__ import annotations` (the container
  builds it).

## Database gotchas

- **sqlite `:memory:` uses `StaticPool`** — every task shares one DBAPI connection, so a
  `ROLLBACK` undoes another task's `INSERT`. Concurrency tests must use a temp file.
- Storing a `float` in a `BigInteger` column is dialect-dependent: sqlite keeps it,
  PostgreSQL truncates silently. Sub-second TTLs need a `Double` column.
- `createTable` is `IF NOT EXISTS`; editing an already applied migration requires
  `migrate:refresh` or a manual `ALTER`.
- `Column.id()` emits `BigInteger`, and sqlite only autoincrements a PK declared exactly
  `INTEGER`.
- Table prefixes must go through `_physicalName()` everywhere, including composite
  foreign keys.

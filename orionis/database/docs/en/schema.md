# Create schemas

A physical schema defines tables, columns, and constraints. Declaring a model does not create its table. Orionis can create tables from a fluent blueprint or `TableDefinition`, the representation also used by the ORM.

## Create a table inside an application

The `Schema` facade requires a booted application. `create()` is synchronous and returns an async context manager; SQL executes when the block exits successfully:

```python
from orionis.support.facades import Schema


async def create_projects() -> None:
    async with Schema.create("projects") as table:
        table.id()
        table.string("name", 120)
        table.string("slug", 160)
        table.boolean("active").default(True)
        table.timestamps()
        table.unique("slug")
        table.index("active")
```

An exception in the body prevents creation. `timestamps()` adds nullable `created_at` and `updated_at`. The blueprint delegates column factories to `Column`, including `integer`, `bigInteger`, `string`, `text`, `boolean`, `dateTime`, and `uuid`. `ColumnDefinition` modifiers include `.nullable()`, `.default(value)`, `.primary()`, `.autoIncrement()`, `.unique()`, `.index()`, and `.comment(text)`.

Table constraints use `primaryKey(*columns)`, `unique(*columns, name=None)`, `index(*columns, name=None, unique=False)`, `foreignKey(column, ref_table, ref_column, name=None)`, and `comment(text)`. For example, `table.foreignKey("owner_id", "users", "id")` references `users.id`. An ORM relationship does not automatically create a foreign key: declare the constraint and enable enforcement in the backend. See [types and constraints](../../../orm/docs/en/schema-and-type-reference.md) for composite keys and the full type catalog.

## Share a versioned definition

Models accept `table_definition`. Sharing definitions keeps migrations and models consistent, but historical migrations should import a stable version rather than the model's future state.

```python
from orionis.orm import Integer, String
from orionis.orm.schema.table import TableDefinition

project_id = Integer().primary().autoIncrement()
project_id.name = "id"
project_name = String(120)
project_name.name = "name"

PROJECTS_V1 = TableDefinition(
    name="projects",
    columns={"id": project_id, "name": project_name},
    primary_key="id",
)
```

`await Schema.createFromDefinition(PROJECTS_V1)` materializes that definition. `await Schema.createFromModel(Project)` uses the model's current metadata; this suits bootstrap and temporary databases, but changing the model would alter replay of a migration importing it directly.

## Select a connection and drop tables

`Schema.connection("reporting")` explicitly selects a connection for that service. A `Schema` instance allows selection only once: selecting again raises `ValueError`. The facade resolves a transient service, while a directly held instance retains its selection. During migrations, the migrator's contextual connection applies unless an explicit selection overrides it. `createFromModel` also honors the model's connection unless explicitly overridden.

`await Schema.drop("projects")` drops the table. Qualified `schema.table` names are supported. Structured plans apply the connection prefix; identifiers and schemas should come from controlled configuration.

## Builder boundaries

The current service provides creation and deletion. It does not expose a general table-alteration API equivalent to `Schema.table(...)`. For unsupported changes, write backend-specific SQL in a migration and document both `up()` and `down()`. Check strict types, indexes, and DDL support under [backends](dialects-and-production.md), particularly for Redshift.

Conditional creation is not schema verification: an existing table does not prove its columns match. The [migration history](migrations-and-seeders.md) should describe actual schema evolution.

# Crear esquemas

Un esquema físico describe tablas, columnas y restricciones. Declarar un modelo no crea su tabla. Orionis puede construir tablas con un blueprint fluido o con `TableDefinition`, la misma representación que utiliza el ORM.

## Crear una tabla en una aplicación

La facade `Schema` requiere una aplicación inicializada. `create()` es síncrono y devuelve un contexto asíncrono; el SQL se ejecuta al salir correctamente del bloque:

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

Si el cuerpo lanza una excepción, no se crea la tabla. `timestamps()` añade `created_at` y `updated_at` anulables. El blueprint delega las fábricas de columnas en `Column`, por ejemplo `integer`, `bigInteger`, `string`, `text`, `boolean`, `dateTime` y `uuid`. Los modificadores de `ColumnDefinition` incluyen `.nullable()`, `.default(value)`, `.primary()`, `.autoIncrement()`, `.unique()`, `.index()` y `.comment(text)`.

Para restricciones de tabla, usa `primaryKey(*columns)`, `unique(*columns, name=None)`, `index(*columns, name=None, unique=False)`, `foreignKey(column, ref_table, ref_column, name=None)` y `comment(text)`. Por ejemplo, `table.foreignKey("owner_id", "users", "id")` referencia `users.id`. Una relación ORM no crea por sí misma una clave foránea: declara la restricción y activa su enforcement en el motor. Para claves compuestas y el catálogo completo de tipos consulta [tipos y restricciones](../../../orm/docs/es/schema-and-type-reference.md).

## Compartir una definición versionada

Los modelos aceptan `table_definition`. Una definición es útil para mantener consistente el esquema entre migración y modelo, pero una migración histórica debe importar una versión estable, no el estado futuro del modelo.

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

`await Schema.createFromDefinition(PROJECTS_V1)` materializa esa definición. `await Schema.createFromModel(Project)` usa los metadatos actuales del modelo; resulta apropiado para bootstrap y bases temporales, pero cambiar el modelo alteraría la reproducción de una migración que lo importe directamente.

## Selección de conexión y eliminación

`Schema.connection("reporting")` selecciona explícitamente una conexión para ese servicio. La selección de una instancia `Schema` solo puede hacerse una vez: reutilizarla con otra selección produce `ValueError`. La facade está respaldada por una resolución de servicio transitoria, mientras que una instancia directa conserva su selección. Dentro de una migración, la conexión contextual seleccionada por el migrador se usa si no hay una selección explícita. `createFromModel` también respeta la conexión del modelo, salvo selección explícita.

`await Schema.drop("projects")` elimina la tabla. Se admite `schema.table` para nombres calificados. Los planes estructurados aplican el prefijo de conexión; los nombres y esquemas deben proceder de configuración controlada.

## Alcance del constructor

El servicio actual expone creación y eliminación. No ofrece una API pública general de alteración de tablas equivalente a `Schema.table(...)`. Para cambios no cubiertos, escribe SQL específico del motor en una migración y documenta tanto `up()` como `down()`. Comprueba compatibilidad de tipos estrictos, índices y DDL en [motores](dialects-and-production.md), especialmente en Redshift.

No uses creación condicional como verificador de esquema: que una tabla ya exista no garantiza que sus columnas coincidan. El historial de [migraciones](migrations-and-seeders.md) debe describir la evolución real.

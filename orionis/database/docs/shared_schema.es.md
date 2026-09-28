# Un esquema compartido por modelos y migraciones

Una tabla puede declararse una sola vez como `TableDefinition`. El modelo utiliza
esa definición mediante `table_definition`, y una migración crea la misma tabla
con `Schema.createFromDefinition`. Las claves de `columns` son los nombres SQL;
no hace falta asignar manualmente `ColumnDefinition.name`.

```python
# database/schemas/users_v1.py
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import Integer, String

USERS_V1 = TableDefinition(
    name="users",
    columns={
        "id": Integer().primary().autoIncrement(),
        "name": String(120),
        "email": String(255).unique(),
    },
)
```

```python
# app/models/user.py
from database.schemas.users_v1 import USERS_V1
from orionis.orm import Model

class User(Model):
    table_definition = USERS_V1
    timestamps = False
    fillable = ("name", "email")
```

```python
# database/migrations/m0001_create_users.py
from database.schemas.users_v1 import USERS_V1
from orionis.database.contracts.migration import Migration
from orionis.support.facades.schema import Schema

class CreateUsers(Migration):
    async def up(self) -> None:
        await Schema.createFromDefinition(USERS_V1)

    async def down(self) -> None:
        await Schema.drop(USERS_V1.name)
```

`TableDefinition` admite `schema`, claves compuestas, índices y restricciones.
La misma definición se utiliza al compilar las consultas y el DDL; el ORM no
consulta el catálogo de la base de datos para reconstruirla en cada operación.

Las definiciones publicadas deben conservarse sin modificaciones. Cuando cambia
una tabla se crea una nueva versión, por ejemplo `USERS_V2`, el modelo adopta esa
versión y una nueva migración describe la transición. Las migraciones anteriores
continúan importando `USERS_V1`. La estructura de `TableDefinition` es una dataclass
congelada, pero sus columnas y su diccionario todavía admiten modificaciones:
trátalos como datos de solo lectura después de declararlos. Al modificar una
columna para una versión nueva, usa otra instancia o `copy.copy` antes de aplicar
sus métodos de configuración.

Un modelo con `table_definition` no puede volver a declarar columnas en su cuerpo
ni especificar un nombre de tabla o clave primaria incompatible. Las opciones del
modelo como `fillable`, `casts`, `hidden`, `connection` y `timestamps` mantienen su
función. Las columnas de eliminación lógica compartidas deben declararse
explícitamente con `.nullable()`.

Para una base temporal o el arranque inicial también puede utilizarse
`await Schema.createFromModel(User)`. Esta operación reutiliza los metadatos
actuales del modelo, por lo que las migraciones históricas deben seguir empleando
una definición versionada. `createFromModel` no calcula diferencias ni altera una
tabla existente.

`createFromModel` usa la conexión del modelo. Una selección explícita mediante
`Schema.connection("analytics")` tiene prioridad; `Schema.connection(None)` elige
explícitamente la conexión predeterminada. Al ejecutar una migración con
`migrate(connection="analytics")`, las operaciones de esquema y ORM sin conexión
explícita utilizan la conexión y transacción de esa migración. El contexto se
restaura al finalizar, incluso cuando la migración falla, y está aislado entre
tareas asíncronas. Esto no constituye un bloqueo distribuido para impedir que
dos procesos apliquen simultáneamente migraciones sobre la misma base de datos.

La declaración de tablas se realiza con `async with Schema.create("users") as table`;
las columnas y restricciones se agregan al `Blueprint` dentro del bloque.

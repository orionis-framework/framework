# orionis.orm

> `orionis.orm` es la capa Active Record asíncrona, API fluida de consultas, sistema de relaciones, vocabulario de esquema y toolkit de factories de Orionis.

## Descripción general

El ORM mapea subclases declarativas de `Model` a definiciones de tabla independientes del motor. Una metaclase calcula una vez nombres de tabla, columnas, casts, asignación masiva, accessors, scopes, eventos, timestamps y soft deletes. Las consultas construyen planes tipados; el paquete database los compila y ejecuta para SQLite, MySQL, PostgreSQL, Oracle o SQL Server.

La persistencia y terminales de consulta son asíncronos. Definición, atributos, composición, serialización, colecciones y `make()` de factories siguen siendo síncronos hasta solicitar I/O.

## Requisitos

- Python 3.14 o posterior.
- Un manager de conexiones `orionis.database` configurado e iniciado antes de ejecutar consultas.
- Tablas compatibles con los modelos, normalmente gestionadas por migraciones.
- El soporte Faker incluido por Orionis al usar factories.

## Inicio rápido

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

Validación: **Ejecutado correctamente** en CPython 3.14.6; no hubo acceso a base de datos.

## Conceptos principales

### Modelos y metadatos

Los modelos concretos declaran instancias `ColumnDefinition` como atributos de clase. Salvo override, el nombre de clase se convierte en tabla plural snake_case. Los metadatos se precalculan e incluyen un `TableDefinition` compartido con migraciones y compiladores SQL. Fije `table`, `connection`, `primary_key`, `incrementing`, `timestamps`, `soft_deletes` o `uuids` solo cuando las convenciones no sirvan.

### Atributos y estado

`fillable` permite y `guarded` deniega asignación masiva; `guarded = ["*"]` la bloquea toda. La asignación directa aún pasa por mutators declarados. `casts` actúa al asignar/hidratar, `hidden` omite valores y `appends` agrega accessors. El estado se inspecciona con `getDirty`, `isDirty`, `isClean`, `wasChanged`, `getChanges` y `getOriginal`.

### Planes fluidos de consulta

Llamadas como `User.where(...)` se reenvían a un `ModelQueryBuilder` nuevo. El builder acumula un `SelectPlan` neutral; `get`, `first`, `paginate`, agregados y escrituras resuelven conexión solo al ejecutar. `clone()` crea estado independiente. Existen fragmentos raw, pero las cláusulas normales preservan bindings y portabilidad.

### Relaciones y carga anticipada

Métodos de instancia declaran `hasOne`, `hasMany`, `belongsTo` y `belongsToMany`. `withRelations()`/`load()` agrupan la carga y guardan resultados en cada modelo. Las relaciones muchos-a-muchos ofrecen `attach`, `detach`, `sync` y actualización del pivote.

### Ciclo de vida y borrado

Los eventos incluyen `retrieved`, `saving`, `creating`, `created`, `updating`, `updated`, `saved`, `deleting`, `deleted`, `restoring` y `restored`. Eventos previos pueden vetar devolviendo `False`. Soft delete agrega timestamp, excluye borrados por defecto y admite `withTrashed`, `onlyTrashed`, `restore` y `forceDelete`.

## Estructura del módulo

| Ruta | Responsabilidad |
|---|---|
| `model.py`, `metaclass.py` | API Active Record y metadatos precalculados. |
| `attributes.py`, `state.py`, `events.py`, `soft_deletes.py` | Atributos, cambios, ciclo de vida y borrado. |
| `query/` | Builders model/raw, expresiones, joins y planes. |
| `relations/` | Relaciones uno-a-uno, uno-a-muchos, inversas y pivote. |
| `schema/` | Tablas, columnas, constraints y tipos neutrales. |
| `collections/` | Reexport de `Collection` y `Paginator`. |
| `factories/` | Generación determinista, secuencias, Faker y streams. |
| `resolver.py`, `provider.py`, `query_builder.py` | Puente de conexiones y gateway de la fachada `DB`. |
| `contracts/`, `exceptions/` | Interfaces estables y fallos ORM. |

## API pública

La raíz exporta de forma diferida `Model`, `ModelQueryBuilder`, `ConnectionResolver`, `Collection`, `ModelCollection`, `Paginator`, relaciones, excepciones y todo el vocabulario neutral de tipos (`Integer`, `String`, `DateTime`, `StrictJson`, `Uuid` y otros).

### `Model`

- Lectura: `all`, `find`, `findOrFail`, `first`, `firstOrFail`.
- Persistencia: `create`, `save`, `update`, `delete`, `destroy`, `restore`, `forceDelete`.
- Serialización: `toDict`, `serialize`, `toJson`, `only`, `exclude`.
- Consulta: `query` y métodos fluidos reenviados.
- Extensión: accessors/mutators por convención, scopes, observers y listeners.

### Builders

`QueryBuilderBase` ofrece selección, condiciones anidadas, predicados, comparaciones, subconsultas, joins, agrupamiento, orden, paginación, locks, unions, agregados y escrituras. `ModelQueryBuilder` añade hidratación, scopes, relaciones, fallos de modelo y soft delete. `RawQueryBuilder` devuelve diccionarios.

### Factories

`orionis.orm.factories` exporta `Factory`, `Sequence`, `Fake`, wrappers Faker unique/optional y excepciones. `make()`/`iterMake()` no persisten; `create()`/`iterCreate()` esperan saves y eventos normales.

## Flujos de trabajo comunes

### Definir y migrar un modelo

Declare columnas y use `table_definition`/`__meta__.table` mediante migraciones Orionis. Declarar el modelo no crea tablas automáticamente.

### Consultar y paginar

Componga filtros antes de esperar un terminal. Fuera de transacción, paginar puede contar y leer concurrentemente; dentro se hace en serie porque ambas operaciones comparten conexión.

### Proteger escrituras

Defina `fillable` o `guarded` para modelos poblados externamente. Use transacciones de `DB` para atomicidad; `Factory.create(count > 1)` no abre una transacción implícita.

### Evitar lecturas N+1

Use `withRelations("relationName")` para listas. Los métodos de relación devuelven builders y resolverlos de forma perezosa puede ejecutar consultas separadas.

## Ejemplos

### Inspeccionar un plan sin ejecutarlo

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

Validación: **Ejecutado correctamente** en CPython 3.14.6; solo se construyó un plan en memoria.

### Usar accessors, mutators, ocultamiento y estado dirty

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

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Generar modelos no guardados con factory

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

Validación: **Ejecutado correctamente** en CPython 3.14.6; los modelos no se persistieron.

### Serializar metadatos de paginación

```python
from orionis.orm import Collection, Paginator

page = Paginator(Collection([{"id": 3}, {"id": 4}]), total=5, page=2, per_page=2)
assert page.lastPage == 3
assert page.hasPrevious is True
assert page.hasNext is True
assert page.toDict()["items"] == [{"id": 3}, {"id": 4}]
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Ejecutar flujos de modelo en una aplicación

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

Validación: **Importación y sintaxis validadas** en CPython 3.14.6; ejecutar requiere aplicación iniciada, tablas y relación `author`.

### Declarar relaciones

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

Validación: **Ejecutado correctamente** en CPython 3.14.6; las relaciones se declararon sin consultarlas.

## Configuración

El ORM no tiene archivo separado: consume `config/database.py`. El selector principal es `DB_CONNECTION`; los ajustes incluyen `DB_URL`, `DB_DATABASE`, `DB_HOST`, `DB_PORT`, `DB_USERNAME`, `DB_PASSWORD`, `DB_PREFIX`, charset/collation, pragmas SQLite, search path/SSL PostgreSQL, DSN/servicio Oracle y cifrado/ODBC SQL Server.

Un modelo puede fijar `connection = "name"`. `DB.connection("name")` devuelve un gateway nuevo y no muta el singleton.

## Integración con Orionis

El provider de database instala el manager en `ConnectionResolver`. `QueryBuilderProvider` enlaza `IQueryBuilder` a `QueryBuilder` como singleton y fija la fachada `DB`. Las migraciones consumen los mismos `TableDefinition`, mientras factories y tests pueden usar managers aislados.

Los modelos no exponen objetos SQLAlchemy; database posee compilación por dialecto, pools, transacciones y excepciones SQL.

## Errores y casos límite

- Consultar antes de instalar el manager produce `OrmConfigurationException`.
- `findOrFail`/`firstOrFail` producen `ModelNotFoundException`; relaciones inexistentes, `RelationNotFoundException`.
- Cláusulas o paginación inválidas producen `InvalidQueryException`; entrada guardada, `MassAssignmentException`.
- `fillable` vacío permite todas las columnas no guardadas. Use política explícita con entrada no confiable.
- `save()` puede devolver `False` si un listener previo veta la operación.
- Los builders son mutables: use `clone()` al ramificar y no comparta uno entre tareas concurrentes.
- Soft delete afecta consultas de modelo; consultas raw no aplican scopes automáticamente.

## Rendimiento y concurrencia

Reflexión y casts se precalculan al crear la clase. Los builders llevan planes independientes y la conexión se guarda por valor. Eager loading reduce consultas repetidas. La paginación solo hace count/data concurrentes fuera de transacciones.

Las factories rechazan uso solapado de una instancia; cree una por tarea. Use límites o paginación para grandes resultados. El trabajo transaccional se serializa en su conexión, mientras consultas no transaccionales del pool pueden avanzar concurrentemente.

## Compatibilidad

El vocabulario es neutral entre SQLite, MySQL, PostgreSQL, Oracle y SQL Server configurados. Tipos, locks, regex, collations, valores generados y DDL concretos dependen del dialecto. Se requiere Python 3.14+ por la sintaxis genérica y el mínimo del framework.

## Notas de verificación

- `tests/orm`: **481 métodos de prueba aprobados** con el runner de Orionis en CPython 3.14.6.
- Se compilaron siete programas bilingües; seis programas autónomos se ejecutaron correctamente.
- El ejemplo de transacción/consulta se validó por importación/sintaxis porque requiere conexión y esquema.
- La evidencia cubrió metadatos, CRUD/eventos, casts/estado, planes, relaciones, soft delete, factories, colecciones, paginación, esquemas, providers y exports diferidos.


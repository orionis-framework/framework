# Orionis ORM

> Modelos Active Record asíncronos, constructores de consultas, relaciones y definiciones de esquemas de base de datos.

## Tabla de contenidos

- [Requisitos](#requisitos)
- [Model Factories](../factories/docs/IMPLEMENTATION.es.md)
- [Descripción funcional](#descripción-funcional)
- [Referencia de API](#referencia-de-api)
- [Ejemplos de uso](#ejemplos-de-uso)
- [Consideraciones de rendimiento y concurrencia](#consideraciones-de-rendimiento-y-concurrencia)
- [Notas de compatibilidad](#notas-de-compatibilidad)

## Requisitos

No hay pasos de instalación específicos para el ORM además de `uv add orionis`. El ORM usa el subsistema de base de datos del framework, incluidas las dependencias `aiosqlite>=0.22.1` para SQLite y `sqlalchemy[asyncio]>=2.0.54,<3.0`. Los demás motores requieren el extra opcional correspondiente y sus drivers: `orionis[mysql]` (`aiomysql>=0.3.2`, `pymysql>=1.2.3`), `orionis[pgsql]` (`asyncpg>=0.31.0`, `psycopg2-binary>=2.9.13`), `orionis[oracle]` (`oracledb>=26.0.0`) u `orionis[sqlserver]` (`aioodbc>=0.5.0`, `pyodbc>=5.3.0`). Estos requisitos están declarados en `pyproject.toml`.

Para consultar la base de datos, el proveedor de base de datos de la aplicación debe instalar un gestor de conexiones en `ConnectionResolver`. Durante el uso habitual de la aplicación, el arranque del framework realiza esta configuración.

Las [Model Factories](../factories/docs/README.md) opcionales generan datos de
prueba y seeding mediante estos mismos modelos. Ejecuta
`uv add 'orionis[factories]'` para usar Faker. La API ofrece `Factory[Model]`,
`make()` síncrono y `create()` asíncrono; el generador es
`reactor make:factory UserFactory --model=User`.

## Descripción funcional

`orionis.orm` ofrece modelos declarativos cuyas columnas son detectadas por `ModelMeta` y se usan para conversiones de atributos, persistencia y construcción de consultas. `ModelQueryBuilder` y el `QueryBuilder` sin modelo expresan operaciones asíncronas mediante las conexiones de Orionis.

El ORM también define constructores de relaciones, colecciones de resultados y paginadores, además de descripciones de tablas y columnas independientes del motor, consumidas por el compilador de base de datos y el subsistema de migraciones. La superficie pública se reexporta desde `orionis.orm`; los módulos de implementación incluyen `orionis.orm.query`, `orionis.orm.relations` y `orionis.orm.schema`.

## Referencia de API

Salvo que se indique lo contrario, las operaciones de consulta y persistencia que acceden a la base de datos son `async` y deben esperarse con `await`. Las firmas siguen las declaraciones del código fuente. `...` en una fila de constructores de tipos indica una familia descrita en conjunto, no una firma invocable.

### `Model`

`Model` es la clase base de los modelos Active Record declarativos. Las columnas se declaran como atributos de clase con tipos de esquema. Según se necesite, se pueden configurar variables como `table`, `connection`, `fillable`, `guarded`, `hidden`, `casts`, `timestamps`, `soft_deletes` y `uuids`. Si `table` es `None`, la metaclase deriva el nombre de tabla; la clave primaria se obtiene de las marcas de las columnas, salvo que se sobrescriba.

| Firma | Comportamiento |
|---|---|
| `__init__(self, attributes: dict[str, Any] \| None = None) -> None` | Crea un modelo no guardado y asigna los atributos recibidos en masa. Lanza `MassAssignmentException` ante atributos desconocidos o no asignables. |
| `query(cls) -> ModelQueryBuilder[Any]` | Inicia un constructor de consultas para el modelo. |
| `getConnection(cls) -> IConnection` | Resuelve la conexión configurada; lanza `OrmConfigurationException` si no se instaló el gestor. |
| `all(cls) -> Collection` | Asíncrono: devuelve todos los modelos coincidentes. |
| `find(cls, key: Any) -> Model \| None` | Asíncrono: busca por clave primaria y devuelve `None` si no encuentra resultados. |
| `findOrFail(cls, key: Any) -> Model` | Asíncrono: busca y lanza `ModelNotFoundException` si no encuentra resultados. |
| `first(cls) -> Model \| None` / `firstOrFail(cls) -> Model` | Asíncrono: devuelve la primera fila; la variante `OrFail` lanza `ModelNotFoundException` si no hay filas. |
| `create(cls, attributes: dict[str, Any]) -> Model` | Asíncrono: crea, guarda y devuelve un modelo. Puede lanzar `MassAssignmentException` o una `QueryException` de base de datos. |
| `destroy(cls, *keys: Any) -> int` | Asíncrono: elimina las filas con las claves primarias indicadas y devuelve la cantidad afectada. |
| `save(self) -> bool` | Asíncrono: inserta un modelo nuevo o escribe sus atributos modificados; despacha eventos del ciclo de vida y mantiene las marcas de tiempo habilitadas. Un listener puede vetar la escritura y hacer que devuelva `False`. |
| `update(self, attributes: dict[str, Any]) -> bool` | Asíncrono: asigna los atributos en masa y guarda. Puede lanzar `MassAssignmentException` o `QueryException`. |
| `delete(self) -> bool` | Asíncrono: elimina una fila existente o marca la columna de eliminación configurada cuando corresponde usar borrado lógico. |
| `addGlobalScope(cls, name: str, scope: Callable[[ModelQueryBuilder[Any]], None]) -> type[Model]` | Registra una restricción con nombre que se aplica a las consultas del modelo. |
| `removeGlobalScope(cls, name: str) -> type[Model]` | Elimina la restricción indicada, si existe. |
| `freshTimestamp(cls) -> datetime` | Genera la hora UTC actual; devuelve UTC sin zona horaria salvo que la columna de marca de tiempo seleccionada esté declarada como `TIMESTAMP`. |
| `newUniqueId(cls) -> Any` | Genera un UUID para las claves creadas por el cliente; los modelos pueden sobrescribir este método. |

Otros métodos públicos heredados del modelo incluyen `fill`, `setAttribute`, `getAttribute`, `hasAccessor`, `toDict`, `serialize`, `toJson`, `only`, `exclude`, `getDirty`, `isDirty`, `isClean`, `wasChanged`, `getChanges`, `getOriginal` y `syncOriginal`. Los métodos de relaciones se enumeran en [Relaciones](#relaciones). La serialización omite los atributos de `hidden` y puede incluir los `appends` declarados. Las conversiones disponibles son `int`, `float`, `bool`, `datetime`, `date`, `json` y `uuid`. Un nombre de conversión no admitido lanza `OrmException`.

### `ModelQueryBuilder`

`ModelQueryBuilder` vincula el lenguaje de consultas compartido a un modelo y devuelve modelos hidratados o valores `Collection`. Sus firmas principales son:

```python
__init__(self, model: type[TModel]) -> None
withRelations(self, *names: str) -> Self
load(self, *names: str) -> Self
withoutGlobalScope(self, name: str) -> Self
withoutGlobalScopes(self, *names: str) -> Self
scope(self, name: str, *args: Any, **kwargs: Any) -> Self
get(self) -> Collection
first(self) -> TModel | None
firstOrFail(self) -> TModel
find(self, key: Any) -> TModel | None
findOrFail(self, key: Any) -> TModel
value(self, column: str) -> Any
pluck(self, column: str) -> Collection
paginate(self, page: int = 1, per_page: int = _DEFAULT_PER_PAGE) -> Paginator
restore(self) -> int
forceDelete(self) -> int
delete(self) -> int
```

Los métodos asíncronos anteriores se esperan con `await`. `withTrashed`, `onlyTrashed` y `withoutTrashed` controlan si se incluyen filas borradas lógicamente. El constructor también ofrece los métodos de consulta fluidos descritos a continuación.

### Constructores de consulta y lenguaje de consultas

`QueryBuilder` es el punto de entrada sin modelo que usa la fachada de base de datos; `table(self, name: str, *, alias: str | None = None, connection: str | None = None) -> IRawQueryBuilder` devuelve un `RawQueryBuilder`. Este último consulta tablas y devuelve filas como diccionarios. Admite `connection(self, name: str) -> Self`, `table(self, name: str, *, alias: str | None = None) -> Self` y los métodos asíncronos `get(self) -> Collection`, `first(self) -> dict[str, Any] | None`, `value(self, column: str) -> Any`, `pluck(self, column: str) -> Collection` y `paginate(self, page: int = 1, per_page: int = _DEFAULT_PER_PAGE) -> Paginator`.

`QueryBuilder` expone estas firmas: `connection(self, name: str | None = None) -> Self`, `table(self, name: str, *, alias: str | None = None, connection: str | None = None) -> IRawQueryBuilder`, `select(self, sql: str, bindings: dict[str, object] | None = None, name: str | None = None) -> list[dict[str, object]]`, `execute(self, sql: str, bindings: dict[str, object] | None = None, name: str | None = None) -> int`, `statement(self, sql: str, bindings: dict[str, object] | None = None, name: str | None = None) -> bool`, `beginTransaction(self, name: str | None = None) -> None`, `commit(self, name: str | None = None) -> None`, `rollback(self, name: str | None = None) -> None` y `transaction(self, name: str | None = None) -> ITransaction`. La ejecución de SQL y las operaciones de transacción son asíncronas; las consultas a tablas se construyen con `table(...)`.

### `ConnectionResolver`

`ConnectionResolver` es el puente estático hacia el gestor de conexiones de base de datos. Su API es `setManager(cls, manager: IConnectionManager) -> None`, `manager(cls) -> IConnectionManager`, `connection(cls, name: str | None = None) -> IConnection` y `clear(cls) -> None`. `manager()` y `connection()` lanzan `OrmConfigurationException` si no se instaló un gestor. Cuando `name` es `None`, `connection()` primero consulta si hay una conexión de migración activa y después delega la resolución al gestor.

Los constructores de modelos y de tablas sin modelo comparten estos métodos fluidos:

- Proyección: `select(*columns)`, `addSelect(*columns)`, `selectRaw(sql, bindings=None, alias=None)`, `selectSub(query, alias)` y `distinct()`.
- Predicados: `where(column, *args)`, `orWhere(column, *args)`, `whereIn`/`orWhereIn`, `whereNotIn`/`orWhereNotIn`, `whereNull`/`orWhereNull`, `whereNotNull`/`orWhereNotNull`, `whereBetween`, `whereNotBetween`, `whereLike`, `whereNotLike`, `whereILike`, `whereNotILike`, `whereStartsWith`, `whereEndsWith`, `whereContains`, `whereRegexpMatch`, `whereColumn`, `orWhereColumn`, `whereRaw`, `orWhereRaw`, `whereExists`, `orWhereExists`, `whereNotExists` y `orWhereNotExists`.
- Uniones y agrupación: `join`, `leftJoin`, `rightJoin`, `fullJoin`, `crossJoin`, `joinSub`, `leftJoinSub`, `rightJoinSub`, `groupBy`, `having`, `orHaving` y `havingRaw`.
- Orden y paginación: `orderBy(column, direction='asc')`, `latest(column=None)`, `oldest(column=None)`, `limit(value)`, `offset(value)`, `take(value)`, `skip(value)`, `forPage(page, per_page=15)`, `lockForUpdate()` y `sharedLock()`.
- Operaciones y ejecución: `union(query)`, `unionAll(query)`, `count(column='*')`, `exists()`, `doesntExist()`, `max(column)`, `min(column)`, `avg(column)`, `sum(column)`, `insert(values)`, `update(values)` y `delete()`.

Las llamadas al constructor son fluidas y devuelven el constructor, salvo los métodos de ejecución, que son asíncronos y devuelven el tipo correspondiente a la operación (`int`, `bool`, resultado agregado o `InsertResult`). Los argumentos no válidos pueden lanzar `InvalidQueryException`; los errores de base de datos pueden lanzar excepciones del subsistema de base de datos. Las anotaciones exactas de parámetros están declaradas en `orionis.orm.contracts.base_builder.IQueryBuilderBase` e implementadas por `orionis.orm.query.base_builder.QueryBuilderBase`.

### Relaciones

Los métodos de relación se declaran en las instancias de modelos y devuelven objetos de relación que permiten construir consultas:

```python
hasOne(self, related: type[TRelated], foreign_key: str | None = None, local_key: str | None = None) -> HasOneRelation[TRelated]
hasMany(self, related: type[TRelated], foreign_key: str | None = None, local_key: str | None = None) -> HasManyRelation[TRelated]
belongsTo(self, related: type[TRelated], foreign_key: str | None = None, owner_key: str | None = None) -> BelongsToRelation[TRelated]
belongsToMany(self, related: type[TRelated], table: str | None = None, foreign_pivot_key: str | None = None, related_pivot_key: str | None = None, parent_key: str | None = None, related_key: str | None = None) -> BelongsToManyRelation[TRelated]
```

`HasOneRelation` devuelve un modelo o `None`; `HasManyRelation` y `BelongsToManyRelation` devuelven `Collection`; `BelongsToRelation` devuelve un modelo o `None`. `BelongsToManyRelation` también proporciona los métodos asíncronos `attach(ids, attributes=None) -> int`, `detach(ids=None) -> int`, `sync(ids: Iterable[Any]) -> dict[str, list[Any]]` y `toggle(ids: Iterable[Any]) -> dict[str, list[Any]]`, además de `wherePivot(column, *args)`.

`setRelation(name, value) -> Model`, `getRelation(name, default=None) -> Any` y `relationLoaded(name) -> bool` administran en memoria las relaciones cargadas. `withRelations(*names)` solicita carga anticipada; si no se puede resolver un nombre de relación, se lanza `RelationNotFoundException`.

### Colecciones y paginación

`Collection` es el tipo de colección de todo el framework y se reexporta como `ModelCollection`. Ambos nombres apuntan a la misma clase (`ModelCollection = Collection`); las operaciones de colección están definidas en `orionis.support.types.collection`.

`Paginator` se construye mediante `Paginator(items: Collection, total: int, page: int, per_page: int) -> None`. Expone `items() -> Collection`, `total() -> int`, `page() -> int`, `perPage() -> int`, `lastPage() -> int`, `hasNext() -> bool`, `hasPrevious() -> bool`, `toDict() -> dict[str, Any]` y `toJson(**kwargs: Any) -> str`; `len(paginator)` devuelve el número de elementos de la página.

### Definiciones de esquema y tipos de columna

`ColumnDefinition` es la definición fluida y mutable compartida. Sus métodos `primary()`, `nullable()`, `default(value)`, `unique()`, `index()`, `foreign(reference)`, `autoIncrement()` y `comment(text)` devuelven la misma definición; `hasDefault() -> bool` indica si se estableció un valor predeterminado. `foreign` analiza una referencia `"table.column"` y lanza `ValueError` si no es válida.

`TableDefinition` es un dataclass congelado con slots y los campos `name`, `columns`, `primary_key`, `schema`, `comment`, `composite_primary_key`, `unique_constraints`, `foreign_keys` e `indexes`. Ofrece `columnNames() -> tuple[str, ...]` y `hasColumn(name: str) -> bool`. `ColumnOptions` es un dataclass de opciones específicas de tipos SQL. Los objetos de valor de restricción reexportados por `orionis.orm.schema` son `CompositeForeignKey`, `ForeignReference`, `TableIndex` y `UniqueConstraint`; `ForeignReference.parse(reference: str) -> ForeignReference` analiza una referencia cualificada y `qualified() -> str` la formatea.

El paquete raíz exporta los siguientes constructores de tipos de esquema lógicos. Las firmas corresponden a sus declaraciones `__init__` (las clases también heredan los métodos fluidos de columna):

| Clase | Firma del constructor |
|---|---|
| `BigInteger`, `Date`, `Integer`, `MatchType`, `SmallInteger`, `StrictBigInt`, `StrictInt`, `StrictSmallInt`, `Time` | `__init__(self) -> None` |
| `Boolean` | `__init__(self, *, create_constraint: bool = False, name: str \| None = None) -> None` |
| `DateTime` | `__init__(self, *, timezone: bool = False) -> None` |
| `Double`, `Float`, `StrictDoublePrecision`, `StrictReal` | `__init__(self, precision: int \| None = None, *, asdecimal: bool = False, decimal_return_scale: int \| None = None) -> None` |
| `Enum` | `__init__(self, *enums: str, name: str \| None = None, create_constraint: bool = False, native_enum: bool = True, length: int \| None = None, validate_strings: bool = False) -> None` |
| `Interval` | `__init__(self, *, native: bool = True, second_precision: int \| None = None, day_precision: int \| None = None) -> None` |
| `LargeBinary` | `__init__(self, length: int \| None = None) -> None` |
| `Numeric` | `__init__(self, precision: int \| None = None, scale: int \| None = None, decimal_return_scale: int \| None = None, *, asdecimal: bool = True) -> None` |
| `NumericCommon` | `__init__(self) -> None` |
| `PickleType` | `__init__(self, protocol: int = 5, pickler: object \| None = None, impl: object \| None = None) -> None` |
| `SchemaType` | `__init__(self, name: str \| None = None) -> None` |
| `StrictArray` | `__init__(self, item_type: ColumnDefinition, *, as_tuple: bool = False, dimensions: int \| None = None, zero_indexes: bool = False) -> None` |
| `StrictBinary`, `StrictBlob` | `__init__(self, length: int \| None = None) -> None` |
| `StrictChar`, `StrictNChar` | `__init__(self, length: int \| None = None, collation: str \| None = None) -> None` |
| `StrictClob`, `StrictNVarChar` | `__init__(self, length: int \| None = None, collation: str \| None = None) -> None` |
| `StrictVarChar`, `String` | `__init__(self, length: int \| None = DEFAULT_STRING_LENGTH, collation: str \| None = None) -> None` |
| `Text`, `Unicode`, `UnicodeText` | `__init__(self, length: int \| None = None, collation: str \| None = None) -> None` |
| `StrictDecimal` | `__init__(self, precision: int \| None = DEFAULT_DECIMAL_PRECISION, scale: int \| None = DEFAULT_DECIMAL_SCALE, decimal_return_scale: int \| None = None, *, asdecimal: bool = True) -> None` |
| `StrictJson` | `__init__(self, *, none_as_null: bool = False) -> None` |
| `StrictTimestamp` | `__init__(self, *, timezone: bool = False) -> None` |
| `StrictVarBinary` | `__init__(self, length: int \| None = None) -> None` |
| `Uuid` | `__init__(self, *, as_uuid: bool = True, native_uuid: bool = True) -> None` |

`ColumnType` describe los tipos lógicos de columna que consume el compilador SQL.

### Excepciones

Todas las excepciones del ORM heredan de `OrmException`: `OrmConfigurationException` (falta configurar el gestor), `ModelNotFoundException` (una búsqueda obligatoria no encontró filas), `MassAssignmentException` (la asignación en masa incumple las reglas), `InvalidQueryException` (argumentos inválidos del constructor de consultas), `RelationNotFoundException` (no se resuelve una relación del modelo) y `ScopeNotFoundException` (el modelo no declara el scope local solicitado). La ejecución de base de datos también puede lanzar excepciones de `orionis.database.exceptions`, incluida `QueryException`.

## Ejemplos de uso

Los siguientes fragmentos usan imports públicos del paquete. Ejecuta las operaciones de base de datos después de iniciar la aplicación Orionis y crear las tablas correspondientes.

### Consulta de modelo habitual

```python
from orionis.orm import Integer, Model, String


class User(Model):
    id = Integer().primary().autoIncrement()
    name = String()
    timestamps = False


async def active_users():
    return await User.query().where("name", "Ada").orderBy("name").get()
```

### Manejar una fila inexistente

```python
from orionis.orm import Integer, Model, String, ModelNotFoundException


class User(Model):
    id = Integer().primary().autoIncrement()
    name = String()
    timestamps = False


async def load_user(user_id: int):
    try:
        return await User.findOrFail(user_id)
    except ModelNotFoundException:
        return None
```

### Integrar una relación

```python
from orionis.orm import HasManyRelation, Integer, Model, String


class Team(Model):
    id = Integer().primary().autoIncrement()
    name = String()
    timestamps = False

    def members(self) -> HasManyRelation["Member"]:
        return self.hasMany(Member)


class Member(Model):
    id = Integer().primary().autoIncrement()
    team_id = Integer()
    name = String()
    timestamps = False


async def members_for(team_id: int):
    team = await Team.findOrFail(team_id)
    return await team.members().get()
```

## Consideraciones de rendimiento y concurrencia

- Las instancias de modelo usan `__slots__`; `ModelMeta` recopila metadatos comunes una vez, cuando se crea cada clase de modelo.
- `TableDefinition` es un dataclass congelado con slots; las definiciones de columna son objetos fluidos mutables.
- La entrada/salida de base de datos es asíncrona y pasa por las abstracciones de conexión de Orionis. El ORM no define una garantía propia de seguridad entre hilos ni protege con locks su resolver de conexiones compartido.
- Una consulta de modelo devuelve todas las filas seleccionadas en un `Collection`; la paginación limita la página consultada y expone por separado el total informado.
- La carga anticipada agrupa la resolución de relaciones para una lista de modelos. El código fuente no especifica límites explícitos de memoria o CPU a nivel del ORM.

## Notas de compatibilidad

- El paquete declara `requires-python = ">=3.14"` en `pyproject.toml`. El código usa sintaxis de parámetros de tipo genéricos, como `def hasMany[TRelated: "Model"](...)`; los metadatos del paquete establecen la versión mínima admitida.
- Los wrappers de tipos SQL y las descripciones de esquema se traducen mediante el compilador de base de datos de Orionis; este módulo no garantiza que todos los motores admitan todos los tipos lógicos u operaciones de consulta.
- Los drivers opcionales dependen del motor: MySQL (`orionis[mysql]`), PostgreSQL (`orionis[pgsql]`), Oracle (`orionis[oracle]`) y SQL Server (`orionis[sqlserver]`). Los rangos de dependencias están definidos en los metadatos del paquete.
> ⚠️ No especificado en el código fuente: soporte SQL de cada motor y garantías de concurrencia más allá de las interfaces asíncronas de conexión.

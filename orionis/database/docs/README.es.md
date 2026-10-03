# Base de datos de Orionis

> Conexiones asíncronas, compilación SQL, creación de esquemas, migraciones y seeders para aplicaciones Orionis.

## Tabla de contenidos

- [Requisitos](#requisitos)
- [Descripción funcional](#descripción-funcional)
- [Referencia de API](#referencia-de-api)
- [Ejemplos de uso](#ejemplos-de-uso)
- [Consideraciones de rendimiento y concurrencia](#consideraciones-de-rendimiento-y-concurrencia)
- [Notas de compatibilidad](#notas-de-compatibilidad)

## Requisitos

El subsistema de base de datos se instala con `uv add orionis`. El paquete base declara `sqlalchemy[asyncio]>=2.0.54,<3.0` y `aiosqlite>=0.22.1`; SQLite usa esta última dependencia. Los demás drivers requieren el extra correspondiente: `orionis[mysql]` instala `aiomysql>=0.3.2` y `pymysql>=1.2.3`; `orionis[pgsql]` instala `asyncpg>=0.31.0` y `psycopg2-binary>=2.9.13`; `orionis[oracle]` instala `oracledb>=26.0.0`; `orionis[sqlserver]` instala `aioodbc>=0.5.0` y `pyodbc>=5.3.0`. Estos requisitos y sus límites están declarados en `pyproject.toml`.

Por ejemplo, ejecuta `uv add 'orionis[pgsql]'` para el extra de PostgreSQL, o
`uv add 'orionis[database]'` para todos los drivers opcionales de base de datos.

## Descripción funcional

`orionis.database` carga configuraciones de conexión con nombre desde la aplicación, crea motores SQLAlchemy asíncronos de manera diferida y expone las API de conexión y transacción de Orionis. `SQLCompiler` traduce planes de consulta de `orionis.orm.query` y descripciones de esquema de `orionis.orm.schema` a sentencias SQLAlchemy Core.

El módulo también ofrece declaraciones fluidas de esquema, un ejecutor de migraciones y un ejecutor de seeders. Usa directamente `orionis.foundation.contracts.application`, `orionis.foundation.config.database.entities.database`, `orionis.container.providers.service_provider` y `orionis.introspection.modules` para la configuración de la aplicación, el registro de proveedores y el descubrimiento de módulos. `ConnectionManagerProvider` instala el gestor en `orionis.orm.resolver.ConnectionResolver`; `SchemaProvider` vincula `ISchema` con `Schema`.

## Referencia de API

Los métodos que realizan operaciones de entrada/salida son asíncronos y deben esperarse con `await`. A continuación se listan las importaciones públicas de `orionis.database`; las declaraciones de esquema se reexportan desde `orionis.database.schema`, los contratos desde `orionis.database.contracts` y el resultado de inserción desde `orionis.database.entities`.

### `ConnectionManager`

`__init__(self, app: IApplication) -> None` lee `app.config("database")`, conserva el nombre predeterminado y las configuraciones de conexiones, y almacena cada conexión en caché desde la primera vez que se resuelve. El valor de configuración puede ser la entidad de configuración de base de datos del framework o un diccionario.

| Firma | Comportamiento |
|---|---|
| `connection(self, name: str | None = None) -> IConnection` | Resuelve la conexión indicada o la predeterminada; lanza `ConnectionNotFoundException` si el nombre no está declarado. La `Connection` resuelta queda en caché. |
| `addConnection(self, name: str, config: dict[str, Any]) -> None` | Registra o reemplaza una configuración. Lanza `ValueError` si el nombre está vacío y `TypeError` si `config` no es un `dict`. Una conexión ya almacenada sigue usando la configuración anterior hasta que se desconecta. |
| `hasConnection(self, name: str) -> bool` | Indica si hay una configuración registrada con ese nombre. |
| `getDefaultName(self) -> str` | Devuelve el nombre de la conexión predeterminada. |
| `setDefaultName(self, name: str) -> None` | Cambia la conexión predeterminada; lanza `ConnectionNotFoundException` si el nombre no está registrado. |
| `disconnect(self, name: str | None = None) -> None` | Asíncrono: libera y elimina una conexión en caché, o todas si `name` es `None`. |
| `configFor(self, name: str | None = None) -> dict[str, Any]` | Devuelve una configuración registrada o lanza `ConnectionNotFoundException`. |

`ConnectionManagerProvider.register()` registra el gestor como singleton del contenedor. `ConnectionManagerProvider.boot()` espera a que se resuelva el servicio y llama a `ConnectionResolver.setManager(...)`, efecto que configura globalmente la integración con el ORM.

### `Connection`

`__init__(self, name: str, config: dict[str, Any]) -> None` valida el driver durante la construcción y crea el motor asíncrono de forma diferida, cuando se necesita por primera vez. Aplica el prefijo configurado en `prefix` a los nombres físicos de tabla y usa `SQLCompiler` para compilar los planes de consulta del ORM.

| Firma | Comportamiento |
|---|---|
| `getName(self) -> str` | Devuelve el nombre registrado de la conexión. |
| `select(self, query: SelectPlan | str, bindings: Mapping[str, Any] | None = None) -> list[dict[str, Any]]` | Asíncrono: ejecuta un plan o SQL crudo y materializa las filas como diccionarios. El SQL crudo puede usar parámetros nombrados `:param`. |
| `insert(self, plan: InsertPlan) -> InsertResult` | Asíncrono: ejecuta una inserción; informa la clave generada solo para una inserción de una fila y si el driver la devuelve. |
| `update(self, plan: UpdatePlan) -> int` / `delete(self, plan: DeletePlan) -> int` | Asíncronos: ejecutan un plan y devuelven la cantidad de filas afectadas que informa la conexión. |
| `scalar(self, plan: SelectPlan) -> Any` | Asíncrono: devuelve la primera columna de la primera fila, o `None` si no hay filas. |
| `execute(self, sql: str, bindings: Mapping[str, Any] | None = None) -> int` | Asíncrono: ejecuta SQL crudo que modifica datos y devuelve la cantidad de filas afectadas. |
| `statement(self, sql: str, bindings: Mapping[str, Any] | None = None) -> bool` | Asíncrono: ejecuta SQL crudo, como DDL, y devuelve `True` si termina correctamente. |
| `createTable(self, table: TableDefinition, *, if_not_exists: bool = True) -> bool` | Asíncrono: compila y ejecuta el DDL de creación de tabla. |
| `dropTable(self, name: str, schema: str | None = None, *, if_exists: bool = True) -> bool` | Asíncrono: elimina una tabla lógica aplicando el prefijo de la conexión. |
| `begin(self) -> None` / `commit(self) -> None` / `rollback(self) -> None` | Asíncronos: inician, confirman o revierten el nivel actual de transacción. Si ya hay una transacción, `begin` abre un savepoint. La ausencia de una transacción activa o los fallos de SQLAlchemy al controlar la transacción lanzan `TransactionException`. |
| `transaction(self) -> ITransaction` | Devuelve un administrador de contexto asíncrono que confirma al salir normalmente y revierte si se propaga una excepción. |
| `inTransaction(self) -> bool` | Indica si la tarea actual tiene un nivel de transacción activo en esta conexión. |
| `disconnect(self) -> None` | Asíncrono: libera el motor creado de manera diferida, si existe. |

Los errores de compilación o ejecución de los métodos públicos de consulta se propagan como `QueryException`. Si falta un paquete del driver cuando se crea el motor, se lanza `MissingDatabaseDependencyException`. Un nombre de driver no admitido o ausente lanza `UnsupportedDriverException` al construir `Connection`. El SQL crudo usa sentencias `text()` de SQLAlchemy con parámetros nombrados; la ruta de planes compilados no recibe parámetros crudos. `QueryException` informa la conexión y la clase del error de SQLAlchemy sin incluir el SQL, los valores vinculados ni los detalles del driver encadenados.

### `SQLCompiler`

`__init__(self, prefix: str = "") -> None` inicializa `SQLCompiler`, que traduce planes de consulta de Orionis y objetos `TableDefinition` a sentencias SQLAlchemy Core. Almacena en caché los metadatos y las definiciones de tablas SQLAlchemy por instancia del compilador.

| Firma | Retorno y comportamiento |
|---|---|
| `compileSelect(self, plan: SelectPlan) -> Select[Any] | CompoundSelect` | Compila un plan SELECT, incluidas sus uniones. Lanza `QueryException` ante columnas desconocidas o cláusulas inválidas. |
| `supportsBatchInsert(plan: InsertPlan) -> bool` | Indica si el plan puede usar la ruta de inserción por lotes parametrizada del compilador. |
| `compileInsert(self, plan: InsertPlan, *, parameterized: bool = False) -> Insert` | Compila un plan de inserción. |
| `compileUpdate(self, plan: UpdatePlan) -> Update` | Compila un plan de actualización. |
| `compileDelete(self, plan: DeletePlan) -> Delete` | Compila un plan de eliminación. |
| `compileCreateTable(self, definition: TableDefinition, *, if_not_exists: bool = True) -> Executable` | Compila el DDL para crear una tabla. |
| `compileDropTable(self, name: str, schema: str | None = None, *, if_exists: bool = True) -> Executable` | Compila el DDL para eliminar una tabla. |

El compilador asigna valores `ColumnType` de Orionis a tipos SQLAlchemy, resuelve columnas cualificadas y alias, y traduce cláusulas `where`, joins, agregados, orden, paginación, locks y planes de unión. El SQL exacto depende del dialecto.

### API de esquema: `Schema`, `TableCreation` y `Blueprint`

`__init__(self, conn_manager: IConnectionManager) -> None` inicializa `Schema` para realizar operaciones mediante un gestor de conexiones. `connection(self, name: str | None = None) -> Self` selecciona una conexión para esa instancia de `Schema`; volver a llamarlo lanza `ValueError`. Si no se selecciona explícitamente una conexión, las operaciones de esquema dentro de una migración usan la conexión de esa migración.

| Firma | Comportamiento |
|---|---|
| `create(self, name: str) -> TableCreation` | Devuelve el administrador de contexto asíncrono para declarar una tabla mediante un `Blueprint`; al salir correctamente del contexto se crea la tabla. El nombre cualificado puede ser `schema.table`. |
| `createFromDefinition(self, definition: TableDefinition) -> bool` | Asíncrono: crea una tabla a partir de la definición reutilizable indicada. |
| `createFromModel(self, model: type[Model]) -> bool` | Asíncrono: crea la definición actual de tabla de un modelo concreto. Lanza `TypeError` si el argumento no tiene metadatos de modelo concretos. Una conexión seleccionada explícitamente en el esquema tiene prioridad sobre los metadatos de conexión del modelo. |
| `drop(self, name: str) -> bool` | Asíncrono: elimina una tabla; admite `schema.table` para un esquema distinto del predeterminado. |

`__init__(self, schema: Schema, name: str) -> None` inicializa `TableCreation`, que implementa `__aenter__(self) -> Blueprint` y `__aexit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None) -> bool`. Al salir correctamente del bloque, crea la tabla con las definiciones recopiladas; si ocurre una excepción, no la crea y propaga la excepción. `TableCreation` no es esperable con `await`.

`Blueprint` es un colector mutable con slots. Sus métodos públicos son `timestamps(self, *, timezone: bool = False) -> None`, `comment(self, text: str) -> Comment`, `foreignKey(self, column: str, ref_table: str, ref_column: str, name: str | None = None) -> ForeignKey`, `index(self, *columns: str, name: str | None = None, unique: bool = False) -> Index`, `primaryKey(self, *columns: str) -> PrimaryKey`, `unique(self, *columns: str, name: str | None = None) -> Unique`, `columns(self) -> tuple[ColumnDefinition, ...]` y `definitions(self) -> tuple[ColumnDefinition | Comment | ForeignKey | Index | PrimaryKey | Unique, ...]`. `__getattr__(self, name: str) -> Callable[..., ColumnDefinition]` delega en las fábricas conocidas de `Column` y registra sus definiciones; una fábrica desconocida lanza `AttributeError`. `timestamps` agrega las columnas de fecha y hora anulables `created_at` y `updated_at`.

### Fábricas de `Column` y restricciones

`Column` proporciona fábricas estáticas que devuelven subclases de `ColumnDefinition` del ORM. Cada fábrica recibe el nombre de la columna; los parámetros posteriores configuran su tipo SQL. Sus firmas completas son:

```python
id(name: str = "id") -> BigInteger
bigInteger(name: str) -> BigInteger
boolean(name: str, *, create_constraint: bool = False, constraint_name: str | None = None) -> Boolean
date(name: str) -> Date
dateTime(name: str, *, timezone: bool = False) -> DateTime
double(name: str, precision: int | None = None, *, asdecimal: bool = False, decimal_return_scale: int | None = None) -> Double
enum(name: str, *enums: str, constraint_name: str | None = None, create_constraint: bool = False, native_enum: bool = True, length: int | None = None, validate_strings: bool = False) -> Enum
float(name: str, precision: int | None = None, *, asdecimal: bool = False, decimal_return_scale: int | None = None) -> Float
integer(name: str) -> Integer
interval(name: str, *, native: bool = True, second_precision: int | None = None, day_precision: int | None = None) -> Interval
largeBinary(name: str, length: int | None = None) -> LargeBinary
matchType(name: str) -> MatchType
numeric(name: str, precision: int | None = None, scale: int | None = None, decimal_return_scale: int | None = None, *, asdecimal: bool = True) -> Numeric
numericCommon(name: str) -> NumericCommon
pickleType(name: str, protocol: int = 5, pickler: object | None = None, impl: object | None = None) -> PickleType
schemaType(name: str, schema_name: str | None = None) -> SchemaType
smallInteger(name: str) -> SmallInteger
string(name: str, length: int | None = 255, collation: str | None = None) -> String
text(name: str, length: int | None = None, collation: str | None = None) -> Text
time(name: str) -> Time
unicode(name: str, length: int | None = None, collation: str | None = None) -> Unicode
unicodeText(name: str, length: int | None = None, collation: str | None = None) -> UnicodeText
uuid(name: str, *, as_uuid: bool = True, native_uuid: bool = True) -> Uuid
strictArray(name: str, item_type: ColumnDefinition, *, as_tuple: bool = False, dimensions: int | None = None, zero_indexes: bool = False) -> StrictArray
strictBigInt(name: str) -> StrictBigInt
strictBinary(name: str, length: int | None = None) -> StrictBinary
strictBlob(name: str, length: int | None = None) -> StrictBlob
strictChar(name: str, length: int | None = None, collation: str | None = None) -> StrictChar
strictClob(name: str, length: int | None = None, collation: str | None = None) -> StrictClob
strictDecimal(name: str, precision: int | None = 10, scale: int | None = 2, decimal_return_scale: int | None = None, *, asdecimal: bool = True) -> StrictDecimal
strictDoublePrecision(name: str, precision: int | None = None, *, asdecimal: bool = False, decimal_return_scale: int | None = None) -> StrictDoublePrecision
strictInt(name: str) -> StrictInt
strictJson(name: str, *, none_as_null: bool = False) -> StrictJson
strictNChar(name: str, length: int | None = None, collation: str | None = None) -> StrictNChar
strictNVarChar(name: str, length: int | None = None, collation: str | None = None) -> StrictNVarChar
strictReal(name: str, precision: int | None = None, *, asdecimal: bool = False, decimal_return_scale: int | None = None) -> StrictReal
strictSmallInt(name: str) -> StrictSmallInt
strictTimestamp(name: str, *, timezone: bool = False) -> StrictTimestamp
strictVarBinary(name: str, length: int | None = None) -> StrictVarBinary
strictVarChar(name: str, length: int | None = 255, collation: str | None = None) -> StrictVarChar
```

Significado de los parámetros compartidos por esas firmas: `name` identifica la columna; `length`, `precision` y `scale` son dimensiones que se pasan al tipo; `collation` selecciona la colación de texto; `asdecimal` y `decimal_return_scale` configuran la conversión numérica; `enums` proporciona las etiquetas permitidas; `constraint_name` nombra una restricción generada; `create_constraint` controla la generación de restricciones CHECK; `native_enum` y `validate_strings` son opciones de enumeración; `native`, `second_precision` y `day_precision` configuran intervalos; `protocol`, `pickler` e `impl` configuran valores serializados con pickle; `schema_name` nombra el tipo de esquema; `item_type`, `as_tuple`, `dimensions` y `zero_indexes` configuran arreglos; `as_uuid` y `native_uuid` configuran la representación UUID; `none_as_null` controla el almacenamiento de `None` en JSON; `timezone` configura los metadatos de zona horaria. La implementación pasa estos valores al tipo lógico o a la construcción de tipo SQLAlchemy correspondiente.

`Blueprint` reenvía estas fábricas estáticas de forma dinámica. Las definiciones resultantes heredan de `ColumnDefinition`, en `orionis.orm.schema.column`, los métodos fluidos `primary()`, `nullable()`, `default(value)`, `unique()`, `index()`, `foreign(reference)`, `autoIncrement()` y `comment(text)`. Estos métodos mutan la definición y la devuelven. El clasificador de definiciones de esquema reconoce el marcador `Timestamps`, aunque este no está incluido en el alias de tipo `SchemaDefinition`.

Los objetos de definición a nivel de tabla son `Comment(text: str)`, `ForeignKey(column: str, ref_table: str, ref_column: str, name: str | None = None)`, `Index(*columns: str, name: str | None = None, unique: bool = False)`, `PrimaryKey(*columns: str)`, `Unique(*columns: str, name: str | None = None)` y `Timestamps(*, timezone: bool = True)`. `Schema` los acepta junto con definiciones de columnas. Si se declara una clave primaria más de una vez o de forma conflictiva, la recopilación de definiciones lanza `ValueError`; una definición de esquema de tipo no admitido lanza `TypeError`.

### Migraciones: `Migration`, `Migrator` y `MigrationEvents`

Las subclases del contrato abstracto `Migration` implementan `async def up(self) -> None` y `async def down(self) -> None`. `__init__(self, app: IApplication, conn_manager: IConnectionManager) -> None` inicializa `Migrator`, que descubre migraciones en el directorio `database/migrations` de la aplicación y las aplica en orden de nombre de archivo.

Tanto al aplicar como al revertir, el migrador construye cada migración
descubierta con `await app.build(migration_cls)`. El contenedor de la aplicación
resuelve las dependencias del constructor anotadas con tipos. Después, el
runner espera el método `up()` o `down()` de la migración.

| Firma de `Migrator` | Comportamiento |
|---|---|
| `migrate(self, *, connection: str | None = None, events: MigrationEvents | None = None) -> list[str]` | Asíncrono: aplica las migraciones pendientes y devuelve sus nombres en orden de ejecución. |
| `rollback(self, steps: int = 1, *, connection: str | None = None, events: MigrationEvents | None = None) -> list[str]` | Asíncrono: revierte los batches recientes seleccionados y devuelve los nombres desde el más reciente. Lanza `ValueError` si `steps` no es un entero positivo y `MigrationNotFoundException` si falta un archivo de migración registrada. |
| `reset(self, *, connection: str | None = None, events: MigrationEvents | None = None) -> list[str]` | Asíncrono: revierte las migraciones registradas. |
| `refresh(self, steps: int | None = None, *, connection: str | None = None, events: MigrationEvents | None = None) -> list[str]` | Asíncrono: revierte migraciones y luego las aplica de nuevo; puede limitar la cantidad de pasos a revertir. |
| `fresh(self, *, connection: str | None = None, events: MigrationEvents | None = None) -> list[str]` | Asíncrono: elimina el historial de migraciones y seeders en la conexión seleccionada, y aplica las migraciones desde cero. |
| `status(self, *, connection: str | None = None) -> list[dict[str, Any]]` | Asíncrono: devuelve registros de estado por migración. |

Cada paso de migración y su registro de seguimiento se ejecutan dentro de una transacción. Las excepciones de `up` o `down` se propagan; una migración fallida no se registra como aplicada correctamente. Si durante una reversión no se puede encontrar el módulo o la clase de una migración registrada, se lanza `MigrationNotFoundException`.

Cuando una reversión completa termina correctamente y deja sin registros el
historial de migraciones de la conexión seleccionada, el migrador también
elimina su tabla de seguimiento `seeders`. Así, el siguiente `migrate --seed`
puede ejecutar los seeders sobre el esquema recreado. Una reversión parcial
conserva ese historial, porque los datos sembrados pueden seguir en tablas que
no se revirtieron. El rollback de migraciones no deshace directamente los datos
de los seeders; cada método `down()` determina qué ocurre con sus tablas y datos.
`fresh()` también elimina el historial de seeders aunque una reversión anterior
hubiera dejado la tabla `migrations` sin registros.

`MigrationEvents` es un dataclass congelado con slots y argumentos solo por nombre. Tiene callbacks opcionales `on_start: Callable[[str], None] | None`, `on_success: Callable[[str, float], None] | None` y `on_error: Callable[[str, float], None] | None`. Los métodos `started(name: str) -> None`, `succeeded(name: str, elapsed: float) -> None` y `failed(name: str, elapsed: float) -> None` llaman al callback correspondiente si está definido. Los aceptan `migrate`, `rollback`, `reset`, `refresh` y `fresh`; `status` no los acepta.

`current_migration_connection() -> IConnection | None` devuelve la conexión vinculada al contexto de migración actual. `migration_connection_scope(connection: IConnection) -> Generator[None]` vincula la conexión mientras dura su bloque `with` y restaura la vinculación previa al salir. El migrador usa este ámbito para que las operaciones de esquema y ORM sin conexión explícita dentro de una migración usen la misma conexión que la transacción de migración.

### Seeders: `Seeder`, `SeederRunner` y `SeederEvents`

Cada seeder de aplicación hereda de `orionis.database.seeders.Seeder` e
implementa `async def run(self) -> None`. Debe estar en `database/seeders/`;
el comando `make:database-seeder` genera la subclase. `SeederRunner` descubre
las clases definidas en esos módulos y las ordena lexicográficamente por el
nombre base del archivo. Ese nombre identifica el registro persistente y debe
ser único, incluso entre subdirectorios. Usa prefijos ordenados para expresar
dependencias entre seeders.

El runner construye cada seeder pendiente con `await app.build(seeder_cls)`
antes de esperar `run()`. Un seeder puede declarar dependencias del constructor
anotadas con tipos que el contenedor de la aplicación pueda resolver.

| Firma de `SeederRunner` | Comportamiento |
|---|---|
| `__init__(self, app: IApplication, conn_manager: IConnectionManager) -> None` | Resuelve el directorio de seeders y la conexión configurada. |
| `seed(self, *, connection: str | None = None, events: SeederEvents | None = None) -> list[str]` | Asíncrono: ejecuta seeders pendientes y devuelve los nombres completados por esta llamada en orden de ejecución. |

La conexión seleccionada contiene una tabla de tracking `seeders` con clave
primaria `id`, nombre `seeder` único, `batch` y fecha Unix de finalización
`seeded_at`. El runner usa los
registros para elegir los seeders pendientes. Reserva cada seeder mediante
la clave única antes de llamar a `run()` y confirma el registro junto con los
datos en una sola transacción. Escribe `seeded_at` después de que `run()`
termine; si falla, revierte los datos y la reserva para permitir otro intento.
Una reserva concurrente no puede confirmar una segunda copia del mismo nombre.
Si el registro completado queda visible, el intento concurrente omite ese
seeder; otros errores de base de datos se propagan. El batch de cada llamada
pendiente es el máximo batch previo más uno. El ámbito de la transacción
también vincula las operaciones habituales del ORM de Orionis dentro del seeder
a la conexión elegida. Las garantías transaccionales dependen del motor de
base de datos y de las operaciones que realice el seeder.

`SeederEvents` ofrece los mismos callbacks `on_start`, `on_success` y
`on_error` que `MigrationEvents`. La CLI los presenta con la salida de progreso
existente. Ejecuta `python reactor seed` para seeders pendientes o
`python reactor migrate --seed` para migrar correctamente antes de sembrar; ambos
aceptan `--database/-d` para indicar una conexión configurada.

El seeder de autorización incluido crea un administrador con rol `admin` y
permiso `full_access`. Antes de la primera ejecución, edita los valores
literales de nombre, correo y contraseña directamente en
`database/seeders/s0000000001_create_admin_authorization.py`. El seeder aplica hashing de
Orionis a la contraseña antes de almacenarla. Después de su registro, editar
estos valores no vuelve a ejecutarlo; para cambios posteriores, añade otro
seeder.

### `Transaction`, `InsertResult` y excepciones

`__init__(self, connection: IConnection) -> None` inicializa `Transaction`, que implementa `__aenter__(self) -> ITransaction` y `__aexit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None) -> bool`. Inicia la transacción al entrar, la confirma al salir normalmente y la revierte al salir con una excepción; devuelve `False` para propagarla. Los fallos al iniciar, confirmar o revertir lanzan `TransactionException`.

`InsertResult` es un dataclass congelado con slots y los campos `last_insert_id: Any` y `row_count: int`. El ID generado puede ser `None`, incluso cuando el driver no devuelve un ID para una inserción de varias filas.

Todas las excepciones de base de datos heredan de `DatabaseException`: `ConnectionNotFoundException` (el nombre de conexión no existe), `MigrationNotFoundException` (no se encuentra una migración registrada), `MissingDatabaseDependencyException` (falta un paquete de driver requerido), `QueryException` (falló la compilación o ejecución de una consulta), `TransactionException` (control de transacción inválido o fallido) y `UnsupportedDriverException` (no hay dialecto registrado para el driver configurado).

### Contratos, proveedores y funciones de dialecto

`IConnection`, `IConnectionManager` e `ITransaction` en `orionis.database.contracts` especifican las interfaces de conexión, gestor y transacción que implementan las clases concretas. `ISchema` especifica `connection`, `create`, `createFromDefinition`, `createFromModel` y `drop`.

`ConnectionManagerProvider.register(self) -> None` registra `IConnectionManager` como singleton del contenedor, implementado por `ConnectionManager`; `boot(self) -> None` lo resuelve y lo instala en el resolver del ORM. `SchemaProvider.register(self) -> None` vincula `ISchema` con `Schema` como servicio transitorio, de modo que la selección de conexión pertenece a la instancia de esquema resuelta.

Las siguientes funciones de módulo son públicas en `orionis.database.dialect`:

- `resolve_driver(config: dict[str, Any]) -> str` normaliza y valida el nombre del driver; un valor no admitido o ausente lanza `UnsupportedDriverException`.
- `missing_dependency_error(driver: str, cause: ModuleNotFoundError, *, sync: bool = False) -> MissingDatabaseDependencyException` crea una excepción con indicaciones de instalación para el driver async o DBAPI síncrono ausente.
- `build_engine_url(config: dict[str, Any], *, sync: bool = False) -> URL` construye una URL SQLAlchemy para el dialecto async seleccionado o para el dialecto DBAPI bloqueante cuando `sync=True`.
- `engine_options(config: dict[str, Any], *, sync: bool = False) -> dict[str, Any]` devuelve opciones del motor, incluidas las de pool para SQLite en memoria y los argumentos de conexión específicos del driver, cuando corresponda.
- `configure_engine(engine: AsyncEngine, config: dict[str, Any]) -> None` configura el motor para los ajustes de conexión específicos del driver.

Las claves de driver reconocidas son `sqlite`, `mysql`, `pgsql`, `oracle` y `sqlserver`. El comportamiento de otras funciones auxiliares del dialecto no forma parte de la API orientada al ORM.

## Ejemplos de uso

Cada ejemplo es independiente. Para la conexión SQLite en memoria y el esquema basta la instalación base de `orionis`. Ejecútalos con Python 3.14 o posterior.

### Crear una tabla y ejecutar una consulta

```python
import asyncio

from orionis.database.connection_manager import ConnectionManager
from orionis.database.schema import Column, Schema


class App:
    def config(self, key: str) -> dict:
        return {
            "default": "sqlite",
            "connections": {
                "sqlite": {"driver": "sqlite", "database": ":memory:"},
            },
        }


async def main() -> None:
    manager = ConnectionManager(App())
    schema = Schema(manager)
    async with schema.create("users") as table:
        table.integer("id").primary().autoIncrement()
        table.string("name")
    connection = manager.connection()
    await connection.execute(
        "INSERT INTO users (name) VALUES (:name)", {"name": "Ada"},
    )
    rows = await connection.select("SELECT name FROM users")
    print(rows)
    await manager.disconnect()


asyncio.run(main())
```

### Manejar una conexión inexistente

```python
from orionis.database.connection_manager import ConnectionManager
from orionis.database.exceptions import ConnectionNotFoundException


class App:
    def config(self, key: str) -> dict:
        return {
            "default": "sqlite",
            "connections": {
                "sqlite": {"driver": "sqlite", "database": ":memory:"},
            },
        }


manager = ConnectionManager(App())
try:
    manager.connection("archive")
except ConnectionNotFoundException:
    print("La conexión archive no está configurada.")
```

### Integrar la creación del esquema con el ORM

```python
import asyncio

from orionis.database.connection_manager import ConnectionManager
from orionis.database.schema import Schema
from orionis.orm import Integer, Model, String
from orionis.orm.resolver import ConnectionResolver


class App:
    def config(self, key: str) -> dict:
        return {
            "default": "sqlite",
            "connections": {
                "sqlite": {"driver": "sqlite", "database": ":memory:"},
            },
        }


class User(Model):
    id = Integer().primary().autoIncrement()
    name = String()
    timestamps = False


async def main() -> None:
    manager = ConnectionManager(App())
    ConnectionResolver.setManager(manager)
    try:
        await Schema(manager).createFromModel(User)
        user = await User.create({"name": "Ada"})
        print(user.name)
    finally:
        ConnectionResolver.clear()
        await manager.disconnect()


asyncio.run(main())
```

## Consideraciones de rendimiento y concurrencia

- `ConnectionManager` almacena una `Connection` por nombre resuelto; cada conexión crea de forma diferida y conserva su motor async hasta que `disconnect()` lo libera.
- `Connection`, `ConnectionManager`, `Schema`, `Transaction` y `Blueprint` declaran `__slots__` para su propio estado. `Blueprint` no tiene diccionario de instancia; `InsertResult` y `MigrationEvents` son dataclasses congelados con slots cuyos campos no se pueden reasignar después de construirlos.
- Las sentencias SQL crudas se almacenan en caché por texto SQL en un `lru_cache` limitado a 256 entradas.
- `Connection` usa un `ContextVar` y la tarea asyncio actual para seguir el estado transaccional. Las transacciones anidadas usan savepoints en la misma conexión cruda. Una tarea hija que herede un contexto con una transacción activa no puede usarla: las operaciones de conexión lanzan `TransactionException` y la consulta debe ejecutarse en la tarea que inició la transacción.
- Las opciones del motor SQLite en memoria fijan un pool de tamaño uno y sin desbordamiento. Para las demás configuraciones, las opciones de motor y pool dependen del dialecto seleccionado y de la configuración recibida.
- `select` materializa las filas del resultado como una lista de diccionarios antes de liberar la conexión adquirida. Aquí no se especifica una API de streaming ni un límite explícito de memoria o CPU del módulo.
- Las operaciones de esquema y migración realizan entrada/salida de base de datos de forma asíncrona. Cada migración y su escritura de seguimiento se agrupan en una transacción.

## Notas de compatibilidad

La certificación real reprodujo un fallo aiomysql 0.3.2/PyMySQL 1.2.3 al
escribir payloads binarios de colas. Las conexiones aiomysql nuevas convierten
bytes, bytearray y memoryview en literales hexadecimales binarios independientes
del charset; otros tipos conservan la conversión del driver. El ajuste es local
a cada conexión, sin bajar versiones ni modificar módulos de terceros. Ver la
[evidencia operativa](../../../certification/REVIEW.es.md).

- `pyproject.toml` declara `requires-python = ">=3.14"`. También declara SQLAlchemy `>=2.0.54,<3.0`, `aiosqlite>=0.22.1` y las restricciones de drivers indicadas en [Requisitos](#requisitos).
- Los dialectos SQLAlchemy asíncronos configurados en el código son SQLite (`sqlite+aiosqlite`), MySQL (`mysql+aiomysql`), PostgreSQL (`postgresql+asyncpg`), Oracle (`oracle+oracledb_async`) y SQL Server (`mssql+aioodbc`). `build_engine_url(..., sync=True)` también permite obtener URLs DBAPI síncronas para componentes compatibles del framework.
- La configuración de base de datos debe incluir un `driver` reconocido; los drivers de servidor usan los valores de conexión de la configuración y SQLite usa la ruta `database`. Oracle puede usar los campos DSN/TNS-name configurados. `orionis.database.dialect` implementa otros comportamientos particulares por driver.
> ⚠️ No especificado en el código fuente: compatibilidad SQL exacta por motor y operación. Depende de SQLAlchemy y del servidor configurado; el módulo no declara una matriz de compatibilidad.

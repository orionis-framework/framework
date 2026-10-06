# orionis.database

> `orionis.database` administra conexiones SQL asíncronas nombradas, ejecución parametrizada, transacciones locales a tarea, esquemas, migraciones y seeders de Orionis.

## Descripción general

Este módulo es el runtime bajo query builder y ORM. `ConnectionManager` convierte configuración validada en conexiones reutilizables. Una `Connection` crea diferidamente un motor SQLAlchemy async, compila planes, ejecuta SQL parametrizado, ofrece helpers de esquema y posee transacciones anidadas.

`Migrator` descubre migraciones versionadas y registra lotes; `SeederRunner` descubre seeders y puede reclamar ejecuciones únicas. `Schema` convierte blueprints o definiciones ORM en tablas. Aplicaciones suelen obtener conexiones mediante resolver/builders o fachadas; tooling puede usar clases directamente.

## Requisitos

- Python 3.14 o posterior.
- `sqlalchemy[asyncio]>=2.0.54,<3.0` y `aiosqlite>=0.22.1`.
- Extras `orionis[mysql]`, `[pgsql]`, `[oracle]` o `[sqlserver]` para otros drivers.
- Servidor/credenciales para bases remotas; SQLite admite archivo o `:memory:`.
- Directorios de migraciones/seeders relativos a base path.

## Inicio rápido

Usa SQLite en memoria con parámetros:

```python
import asyncio

from orionis.database import Connection


async def main() -> None:
    connection = Connection(
        "docs",
        {"driver": "sqlite", "database": ":memory:", "prefix": ""},
    )
    try:
        await connection.statement(
            "CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT NOT NULL)"
        )
        await connection.execute(
            "INSERT INTO notes (body) VALUES (:body)",
            {"body": "hello"},
        )
        print(await connection.select("SELECT id, body FROM notes"))
    finally:
        await connection.disconnect()


asyncio.run(main())  # [{'id': 1, 'body': 'hello'}]
```

El motor se crea en la primera sentencia y se dispone explícitamente.

Validación: **Executed successfully** en CPython 3.14.6.

## Conceptos principales

### Manager frente a conexión

`ConnectionManager` posee configuración, nombre predeterminado y caché de objetos. `connection(name=None)` construye/reutiliza. `disconnect` dispone motores sin borrar configuración.

### Planes frente a SQL

ORM/query builder envía planes inmutables a `Connection`; `SQLCompiler` crea statements y aplica prefijos. Strings raw se admiten en `select`, `execute`, `statement` con bindings `:parameter`.

### Propiedad de transacción

Estado vive en `ContextVar` etiquetado con tarea. Primer `begin` abre conexión/transacción raíz; anidado crea savepoint. `transaction()` confirma nivel interno en éxito y revierte al escapar excepción.

### Esquema, migraciones y seeders

`Schema` construye definiciones desde `Blueprint` o modelo. `Migration` aporta `up/down`; migrator registra nombres/lotes. `Seeder` aporta `run`; runner descubre y registra ejecuciones únicas.

## Estructura del módulo

| Área | Responsabilidad |
|---|---|
| `connection.py`, `connection_manager.py` | Motores, ejecución, transacciones y conexiones nombradas. |
| `compiler.py`, `dialect.py` | Compilación, URLs/opciones, sesiones y drivers. |
| `schema/`, `schema_provider.py` | Constraints blueprint y tablas. |
| `migrations/` | Descubrimiento y flujos de migración. |
| `seeders/` | Contrato, descubrimiento, eventos y tracking. |
| `entities/`, `contracts/`, `exceptions.py` | Resultados, interfaces y errores. |
| `provider.py` | Manager singleton y resolver ORM. |

## API pública

### `ConnectionManager`

```text
manager.connection(name=None) -> Connection
manager.addConnection(name, config) -> None
manager.hasConnection(name) -> bool
manager.configFor(name=None) -> dict
manager.getDefaultName() -> str
manager.setDefaultName(name) -> None
await manager.disconnect(name=None)
```

Valida nombres/config y lanza `ConnectionNotFoundException`. Config se copia. `disconnect()` sin nombre desconecta todas; con nombre solo una.

### `Connection`

Se recomienda manager. Construcción directa acepta nombre/config, valida driver y difiere motor.

#### Consultas

| Método | Retorno |
|---|---|
| `select(plan_or_sql, bindings=None)` | `list[dict]` materializada. |
| `insert(plan)` | `InsertResult`; batch omite id generado. |
| `update(plan)`, `delete(plan)` | Filas afectadas. |
| `scalar(select_plan)` | Primera columna/fila o `None`. |
| `execute(sql, bindings=None)` | Filas afectadas. |
| `statement(sql, bindings=None)` | `True` para DDL/mantenimiento. |

#### Esquema y ciclo

`createTable`/`dropTable` aplican prefijos. `disconnect` dispone motor; la siguiente operación crea otro.

#### Transacciones

`begin`, `commit`, `rollback` controlan nivel interno. `transaction()` es context manager preferido. `inTransaction()` solo estado de tarea actual.

### `Schema` y blueprints

Selecciona conexión con `.connection(name)`. `create(name)` devuelve builder; `createFromDefinition`, `createFromModel`, `drop`. `Blueprint` acepta `PrimaryKey`, `Unique`, `Index`, `ForeignKey`, `Timestamps`, `Comment`.

### `Migration` y `Migrator`

Implementa `up/down`. Migrator selecciona la conexión solicitada y expone `migrate`, `rollback`, `reset`, `refresh`, `fresh`, `status`; pasos transaccionales y eventos. Archivos se ordenan por nombre y tracking registra batches.

### `Seeder`, `SeederRunner`, `SeederEvents`

Seeder implementa `run`. Runner ejecuta clase nombrada o descubiertas, puede forzar y emite eventos. Claims persistidos evitan doble ejecución entre workers.

### Excepciones

`DatabaseException` es base de errores de conexión/migración/dependencia/query/transacción/driver.

## Flujos de trabajo comunes

### Ejecutar query parametrizada

Obtén conexión, pasa datos por bindings, consume diccionarios y desconecta solo si posees lifecycle. Nunca interpolar usuario.

### Unidad atómica

Usa `async with connection.transaction():`. Anidación usa savepoints. Mantén queries en tarea propietaria.

### Aplicar migraciones

Crea archivos versionados y usa comandos reactor o `Migrator`. Rollback revierte batches recientes en orden inverso.

### Sembrar datos

Coloca `Seeder` en ruta y usa comandos/runner. Tracking único para seeders idempotentes; fuerza solo si rerun es seguro.

## Ejemplos

### Confirmar una transacción

```python
import asyncio

from orionis.database import Connection


async def main() -> None:
    db = Connection("tx", {"driver": "sqlite", "database": ":memory:"})
    try:
        await db.statement("CREATE TABLE counters (value INTEGER NOT NULL)")
        async with db.transaction():
            await db.execute("INSERT INTO counters (value) VALUES (:value)", {"value": 3})
        print(await db.select("SELECT value FROM counters"))  # [{'value': 3}]
    finally:
        await db.disconnect()


asyncio.run(main())
```

Validación: **Executed successfully** en CPython 3.14.6.

### Revertir al escapar excepción

```python
import asyncio

from orionis.database import Connection


async def main() -> None:
    db = Connection("rollback", {"driver": "sqlite", "database": ":memory:"})
    try:
        await db.statement("CREATE TABLE entries (value TEXT NOT NULL)")
        try:
            async with db.transaction():
                await db.execute("INSERT INTO entries (value) VALUES ('temporary')")
                raise RuntimeError("cancel")
        except RuntimeError:
            pass
        print(await db.select("SELECT value FROM entries"))  # []
    finally:
        await db.disconnect()


asyncio.run(main())
```

Validación: **Executed successfully** en CPython 3.14.6.

### Usar savepoint anidado

```python
import asyncio

from orionis.database import Connection


async def main() -> None:
    db = Connection("nested", {"driver": "sqlite", "database": ":memory:"})
    try:
        await db.statement("CREATE TABLE events (name TEXT NOT NULL)")
        async with db.transaction():
            await db.execute("INSERT INTO events VALUES ('outer')")
            try:
                async with db.transaction():
                    await db.execute("INSERT INTO events VALUES ('inner')")
                    raise ValueError("rollback savepoint")
            except ValueError:
                pass
        print(await db.select("SELECT name FROM events"))  # [{'name': 'outer'}]
    finally:
        await db.disconnect()


asyncio.run(main())
```

Solo revierte savepoint interno; raíz confirma.

Validación: **Executed successfully** en CPython 3.14.6.

### Definir migración y seeder

```python
from orionis.database import Migration, Seeder
from orionis.support.facades import DB, Schema


class CreateFlags(Migration):
    async def up(self) -> None:
        async with Schema.create("flags") as table:
            table.id()
            table.string("name", 80)
            table.unique("name")

    async def down(self) -> None:
        await Schema.drop("flags")


class DefaultFlags(Seeder):
    async def run(self) -> None:
        await DB.table("flags").insert({"name": "enabled"})
```

El migrador vincula la conexión elegida al invocar estas fachadas; el contenedor de aplicación resuelve sus servicios.

Validación: **Import-only** en CPython 3.14.6; ejecutarlo requiere contenedor iniciado y runtime de migración/seeder.

## Configuración

`database.default` usa `DB_CONNECTION`, predeterminado `sqlite`. Comunes: `DB_URL`, `DB_DATABASE`, `DB_PREFIX`, `DB_HOST`, `DB_PORT`, `DB_USERNAME`, `DB_PASSWORD`, `DB_CHARSET`.

| Driver | Ajustes adicionales | Puerto/ruta |
|---|---|---|
| SQLite | `DB_FOREIGN_KEYS`, `DB_BUSY_TIMEOUT`, `DB_JOURNAL_MODE`, `DB_SYNCHRONOUS` | `database/database.sqlite` |
| MySQL | `DB_SOCKET`, `DB_COLLATION`, `DB_PREFIX_INDEXES`, `DB_STRICT`, `DB_ENGINE` | `3306` |
| PostgreSQL | `DB_SEARCH_PATH`, `DB_SSLMODE`, `DB_PREFIX_INDEXES` | `5432` |
| Oracle | service/SID/DSN/TNS/encodings | `1521` |
| SQL Server | encrypt/trust/ODBC | `1433` |

URLs tienen precedencia sobre campos descompuestos al construir dialecto.

## Integración con Orionis

Provider registra manager singleton y lo instala en `ConnectionResolver`. `SchemaProvider` vincula schema/fachada. Builders/modelos crean planes; conexiones compilan/ejecutan. Cache, auth, queues, scheduler, session y migrations comparten manager.

Comandos reactor exponen migrate/rollback/reset/refresh/fresh/status/seed/inspect/wipe. Shutdown desconecta motores.

## Errores y casos límite

- Driver inválido falla al construir. Dependencia opcional ausente falla al crear motor.
- Errores SQLAlchemy se vuelven `QueryException` saneado sin SQL/bindings/credenciales.
- Commit/rollback sin estado lanza `TransactionException`.
- Transacción activa no puede usarse desde tarea hija.
- SQL raw acepta bindings nombrados; mapping vacío equivale a ninguno.
- Filas se materializan antes de liberar conexión; selects grandes ocupan memoria completa.
- Discovery rechaza archivos/clases inválidos/duplicados; flujos destructivos requieren intención.

## Rendimiento y concurrencia

Motores/conexiones son diferidos y almacenados. Operaciones no transaccionales usan `engine.begin`; transacciones retienen conexión hasta cerrar niveles. SQL raw parseado usa LRU 256.

Estado de transacción es local a tarea; anidación usa savepoints. Tareas concurrentes comparten objeto para operaciones independientes, no transacción abierta. Pool/opciones vienen de configuración.

Tracking de migrator/seeder usa transacciones/claims DB, no locks de proceso.

## Compatibilidad

Orionis declara Python 3.14+, SQLAlchemy 2.0.54+ y aiosqlite 0.22.1+; validado en CPython 3.14.6 Windows. Drivers: SQLite, MySQL, PostgreSQL, Oracle, SQL Server. Usa extras declarados para mínimos de drivers.

## Notas de verificación

La validación usó CPython 3.14.6. Se inspeccionaron exports, conexión/manager, compiler/dialectos, transacciones, schema, migrations, seeders, providers, config, integración ORM y `tests/database`. Las 243 pruebas pasaron. Cuatro programas de conexión se ejecutaron; las definiciones de migración/seeder se importaron sin ejecutar operaciones ligadas a la aplicación.

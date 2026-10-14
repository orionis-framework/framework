# Configurar conexiones y ejecutar SQL

## Elegir un motor

La configuración de la aplicación está en `config/database.py`, sección `database`. `BootstrapDatabase` extiende la entidad `Database` y reúne una conexión predeterminada y conexiones con nombre. `DB_CONNECTION` selecciona `sqlite` por defecto. Una conexión se crea al resolver su nombre y su engine se inicializa al ejecutar la primera operación.

| Driver | Instalación adicional | Configuración habitual |
|---|---|---|
| `sqlite` | Ninguna | `DB_DATABASE`, `DB_FOREIGN_KEYS`, `DB_BUSY_TIMEOUT` |
| `mysql` | `uv add 'orionis[mysql]'` | host, puerto 3306, base, usuario, contraseña, charset/collation |
| `pgsql` | `uv add 'orionis[pgsql]'` | puerto 5432, `DB_SEARCH_PATH`, `DB_SSLMODE` |
| `oracle` | `uv add 'orionis[oracle]'` | puerto 1521, servicio/SID/DSN/TNS |
| `sqlserver` | `uv add 'orionis[sqlserver]'` | puerto 1433, driver ODBC y TLS |
| `redshift` | `uv add 'orionis[redshift]'` | puerto 5439, TLS y opciones del conector AWS |

`orionis[database]` reúne los drivers opcionales. En un checkout del framework se puede usar `uv sync --extra pgsql`, por ejemplo. Instalar el paquete no crea un servidor ni instala un driver ODBC del sistema. La ausencia de una dependencia opcional se informa como `MissingDatabaseDependencyException` al inicializar ese backend.

## Primer programa con SQLite

Este programa crea datos únicamente en memoria. Los valores del usuario se enlazan mediante marcadores `:name`.

```python
import asyncio
from orionis.database import Connection


async def main() -> None:
    db = Connection("docs", {"driver": "sqlite", "database": ":memory:"})
    try:
        await db.statement(
            "CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT NOT NULL)"
        )
        affected = await db.execute(
            "INSERT INTO notes (body) VALUES (:body)", {"body": "Hello"}
        )
        rows = await db.select(
            "SELECT id, body FROM notes WHERE body = :body", {"body": "Hello"}
        )
        assert affected == 1
        assert rows == [{"id": 1, "body": "Hello"}]
    finally:
        await db.disconnect()


asyncio.run(main())
```

`select()` materializa `list[dict]`; no devuelve un cursor abierto. `execute()` devuelve filas afectadas y `statement()` devuelve `True` cuando la sentencia finaliza correctamente. Para `insert(plan)`, el resultado es `InsertResult` con `last_insert_id` y `row_count`; un insert por lotes no garantiza una identidad generada. `scalar(plan)` devuelve la primera columna o `None`. Estos últimos métodos reciben planes del query builder, no SQL arbitrario.

## Trabajar dentro de una aplicación

Tras el arranque, utiliza la facade; no construyas y desconectes una conexión en cada petición:

```python
from orionis.support.facades import DB


async def find_note(body: str):
    return await DB.table("notes").where("body", body).first()


async def count_notes():
    return await DB.select("SELECT COUNT(*) AS total FROM notes")
```

`DB.connection("reporting")` devuelve un gateway nuevo. `DB.connection("reporting").table("notes")` dirige esa consulta a la conexión registrada; no cambia la conexión de otros consumidores. El gestor ofrece `connection(name)`, `hasConnection(name)`, `configFor(name)`, `addConnection(name, config)` y `setDefaultName(name)`. Cambiar el predeterminado sí afecta a futuros consumidores sin selección explícita: hazlo durante configuración, no como mecanismo de aislamiento por petición.

## Valores de configuración y fallos frecuentes

SQLite usa `database/database.sqlite`, timeout ocupado de 5000 ms, journal `DELETE`, sincronización `NORMAL` y claves foráneas `OFF` en la plantilla actual. Activa deliberadamente `DB_FOREIGN_KEYS` si tu aplicación depende de referencias. Las conexiones de servidor comparten `DB_HOST`, `DB_PORT`, `DB_DATABASE`, `DB_USERNAME` y `DB_PASSWORD`; MySQL añade `DB_SOCKET`, `DB_COLLATION`, `DB_STRICT` y `DB_ENGINE`. Una URL configurada tiene prioridad en los dialectos que la admiten; revisa la entidad del driver antes de copiar `DB_URL` entre motores.

Otros selectores de la plantilla son `DB_PREFIX` y `DB_PREFIX_INDEXES`; SQLite expone `DB_JOURNAL_MODE` y `DB_SYNCHRONOUS`; Oracle, `DB_SERVICE_NAME`, `DB_SID`, `DB_DSN`, `DB_TNS`, `DB_ENCODING` y `DB_NENCODING`; SQL Server, `DB_ENCRYPT`, `DB_TRUST_SERVER_CERTIFICATE` y `DB_ODBC_DRIVER`. `DB_CHARSET` se aplica según el driver activo; no copies valores de charset incompatibles entre motores.

Un nombre desconocido produce `ConnectionNotFoundException`; un driver inválido, `UnsupportedDriverException`; un fallo SQL, `QueryException`. Los errores de ejecución sanitizan SQL, bindings y credenciales. Registra el contexto de negocio y el nombre de conexión sin registrar secretos. Los nombres de tablas/columnas no son valores enlazables: elige identificadores de una lista controlada. El SQL crudo tampoco añade automáticamente prefijos de tabla.

Continúa con [consultas del ORM](../../../orm/docs/es/querying.md) o [transacciones](transactions.md).

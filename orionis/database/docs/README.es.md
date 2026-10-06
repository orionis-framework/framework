# orionis.database

> Administra conexiones asíncronas con nombre, compila descripciones ORM de consultas y schemas, y ejecuta migraciones y seeders transaccionales.

## Tabla de contenidos

- [Requisitos](#requisitos)
- [Descripción funcional](#descripción-funcional)
- [Estructura del módulo](#estructura-del-módulo)
- [Referencia de API](#referencia-de-api)
- [Ejemplos de uso](#ejemplos-de-uso)
- [Características de diseño](#características-de-diseño)
- [Rendimiento y concurrencia](#rendimiento-y-concurrencia)
- [Notas de compatibilidad](#notas-de-compatibilidad)
- [Verificación y limitaciones](#verificación-y-limitaciones)

## Requisitos

El proyecto declara Python **>=3.14** en [pyproject.toml](../../../pyproject.toml).
La ejecución usa SQLAlchemy **Core async**, no su ORM Session o declarative.
El driver aiosqlite es dependencia core. Configure driver y database en cada
conexión; no se deduce un driver ausente/no soportado desde el nombre o URL.

| Driver Orionis | Dialecto SQLAlchemy async | Dialecto de helpers sync | Paquetes declarados |
| --- | --- | --- | --- |
| sqlite | sqlite+aiosqlite | sqlite | Core aiosqlite>=0.22.1; sqlite3 síncrono es biblioteca estándar. |
| mysql | mysql+aiomysql | mysql+pymysql | Extra mysql: aiomysql>=0.3.2, pymysql>=1.2.3. |
| pgsql | postgresql+asyncpg | postgresql+psycopg2 | Core/extra pgsql: asyncpg>=0.31.0; extra psycopg2-binary>=2.9.13. |
| oracle | oracle+oracledb_async | oracle+oracledb | Extra oracle: oracledb>=26.0.0. |
| sqlserver | mssql+aioodbc | mssql+pyodbc | Extra sqlserver: aioodbc>=0.5.0, pyodbc>=5.3.0; una instalación ODBC utilizable es un requisito separado. |

El extra database agrupa los drivers opcionales. SQLAlchemy core se declara
como sqlalchemy[asyncio]>=2.0.54,<3.0. Los hints de instalación de
[dialect.py](../dialect.py) usan uv add; esta tarea no instaló paquetes o extras.
Véase [compatibilidad](#notas-de-compatibilidad) para versiones del lock e
instaladas: no son mínimos soportados.

[ConnectionManager](../connection_manager.py) necesita app.config("database")
con entidad Database del framework o mapping default/connections. Connection
y compilador independientes no requieren boot. Consultas ORM necesitan la
integración [ConnectionResolver](../../orm/resolver.py), instalada en boot
por el [provider](../provider.py) real. Schema necesita un manager. Los runners
necesitan además paths/build de aplicación y clases importables. Configuración
de red, disponibilidad y privilegios dependen del despliegue/driver; no se
ejercitaron aquí.

Los ejemplos usan solo bases temporales propias. reset, refresh, fresh,
rollback y drop pueden eliminar datos. Describir la integración CLI no
autoriza operar sobre la base configurada del checkout.

## Descripción funcional

`orionis.database` resuelve conexiones con nombre, crea engines async de forma
diferida, traduce planes ORM y schemas a SQLAlchemy Core y ejecuta consultas
con transacciones/savepoints propiedad de una tarea. También recoge declaraciones
de tablas y descubre, registra, aplica o revierte migraciones/seeders.

### Integraciones directas

La implementación responsable es [Connection](../connection.py), con
[SQLCompiler](../compiler.py) y [helpers de dialecto](../dialect.py). Planes y
metadatos de tablas/columnas pertenecen a [orionis.orm](../../orm/docs/README.es.md),
con definiciones reales en [expressions.py](../../orm/query/expressions.py)
y [TableDefinition](../../orm/schema/table.py). Aquí se documenta su consumo,
no toda la API ORM.

[ConnectionManagerProvider](../provider.py) registra IConnectionManager
singleton y establece ConnectionResolver en boot.
[SchemaProvider](../schema_provider.py) registra ISchema transient; su boot
heredado es no-op y no pinea Schema globalmente. Los runners usan
[ModuleInspector](../../introspection/modules/inspector.py) /
[ReflectionModule](../../introspection/modules/reflection.py) y app.build.
El [contexto de migración](../migrations/context.py) permite a operaciones
Schema/ORM no cualificadas compartir la conexión elegida, también en seeders.

### Límites de ejecución

La ejecución SQL pública es async; resolver conexiones, compilar planes,
construir URL/opciones, recoger schemas y descubrir/importar es síncrono.
Un objeto Connection no es una sesión DB abierta: el primer uso crea el engine
y cada operación fuera de transacción explícita usa engine.begin. Este es
un contexto transaccional que confirma al salir correctamente, pese al término
"autocommit" de la docstring privada de _acquire.

El estado transaccional recuerda la asyncio Task que lo inició. Un hijo
hereda la referencia ContextVar, pero no puede usar una transacción paterna
activa. El contexto de migración no tiene un guard propio equivalente; el
guard de Connection sigue aplicando. Ni async ni un pool demuestran seguridad
de todo el módulo entre hilos o loops.

## Estructura del módulo

Se inspeccionaron 39 archivos Python y el stub de Blueprint. No hay plantillas
SQL ni otros recursos de runtime no Python en el módulo.

| Archivos o grupo | Responsabilidad y símbolos principales |
| --- | --- |
| [__init__.py](../__init__.py) | Exports diferidos de conexiones/compilador, Migration/Migrator, seeders, Transaction y excepciones. |
| [connection.py](../connection.py), [connection_manager.py](../connection_manager.py), [transaction.py](../transaction.py) | Connection, ConnectionManager, Transaction. |
| [compiler.py](../compiler.py), [dialect.py](../dialect.py) | SQLCompiler y cinco funciones públicas de driver/configuración. |
| [contracts](../contracts/__init__.py) | Exports IConnection, IConnectionManager, ITransaction; los módulos también contienen ISchema, IMigrator y Migration. |
| [entities/result.py](../entities/result.py), [entities/__init__.py](../entities/__init__.py) | InsertResult y su reexportación. |
| [exceptions.py](../exceptions.py) | DatabaseException y seis subclases. |
| [provider.py](../provider.py), [schema_provider.py](../schema_provider.py) | ConnectionManagerProvider, SchemaProvider. |
| [schema/schema.py](../schema/schema.py), [schema/table_creation.py](../schema/table_creation.py), [schema/blueprint.py](../schema/blueprint.py), [schema/blueprint.pyi](../schema/blueprint.pyi) | Schema, TableCreation pendiente, Blueprint mutable y firmas de factories solo para editor. |
| [schema/column.py](../schema/column.py), [schema/__init__.py](../schema/__init__.py) | Cuarenta factories estáticas de Column y exports de declaraciones. |
| [schema/comment.py](../schema/comment.py), [schema/foreign.py](../schema/foreign.py), [schema/index.py](../schema/index.py), [schema/primary.py](../schema/primary.py), [schema/timestamp.py](../schema/timestamp.py), [schema/unique.py](../schema/unique.py) | Comment, ForeignKey, Index, PrimaryKey, Timestamps, Unique. |
| [schema/definitions.py](../schema/definitions.py), [schema/definition_bucket.py](../schema/definition_bucket.py) | Alias SchemaDefinition y auxiliar DefinitionBucket. |
| [migrations](../migrations/__init__.py) | Reexporta Migrator; migrator.py, events.py y context.py controlan discovery/tracking, MigrationEvents/NO_EVENTS y contexto. |
| [seeders](../seeders/__init__.py) | Seeder, SeederRunner, SeederEvents; events.py reutiliza MigrationEvents, no declara otro dataclass. |

Cada fuente, incluidos los seis inicializadores, tiene owner enlazado en el
[apéndice literal](#declaraciones-literales). No se editó ningún directorio
externo al docs directo del módulo para generar documentación.

## Referencia de API

El comportamiento se agrupa por API responsable. Las
[declaraciones literales](#declaraciones-literales) conservan headers,
decoradores, anotaciones, defaults, campos, exports y alias exactos.
**Headers sin cuerpo y cuerpos del stub son referencia, no ejemplos ejecutables.**
Las operaciones generadas o heredadas se identifican aparte.

### Imports y exports de paquetes

[orionis.database](../__init__.py) resuelve nombres de _EXPORTS en el primer
acceso y los cachea mediante [_resolve_export](../../_exports.py). Leer
__all__ o dir no ejecuta todos los módulos. Resolver un export puede importar
dependencias SQLAlchemy/ORM/configuración; no importe indiscriminadamente
todos los símbolos para descubrir la API.

La raíz no exporta Schema, Column, Blueprint, InsertResult, MigrationEvents
o providers. Use los módulos o subpaquetes selectivos reales. El paquete schema
exporta Blueprint, Column y seis marcadores, no Schema/TableCreation/
DefinitionBucket/SchemaDefinition. Contracts solo exporta IConnection/
IConnectionManager/ITransaction. Migrations solo Migrator; seeders exporta
Seeder/SeederEvents/SeederRunner; entities exporta InsertResult. Un export
diferido desconocido lanza AttributeError.

Imports de bibliotecas y SqlSource/SourceMap solo TYPE_CHECKING de compiler.py
no son API runtime independiente. Helpers/estados privados se describen donde
deciden comportamiento público. DefinitionBucket es auxiliar accesible, no
operación de schema exportada.

### Funciones de dialecto y configuración

Fuente/import: [orionis.database.dialect](../dialect.py).

| Función | Parámetros, resultado, condiciones y efectos |
| --- | --- |
| resolve_driver(config) | Lee driver, convierte a string, strip/lower, exige sqlite/mysql/pgsql/oracle/sqlserver. Retorna nombre normalizado o UnsupportedDriverException, incluido driver ausente. No valida todo el payload. |
| build_engine_url(config, *, sync=False) | Retorna SQLAlchemy URL estructurada con el mapa async/sync. No abre engine ni conexión. Ports no numéricos y mappings malformados pueden propagar errores built-in. |
| engine_options(config, *, sync=False) | Retorna dict nuevo con echo=False, future=True, hide_parameters=True y opciones por driver descritas abajo. Driver no soportado se propaga. |
| configure_engine(engine, config) | Instala listeners síncronos Core para SQLite/MySQL cuando aplican. Retorna None; no conecta explícitamente, pero los listeners se ejecutan al usar el engine. No hay guard de registro repetido idempotente. |
| missing_dependency_error(driver, cause, *, sync=False) | Construye y retorna MissingDatabaseDependencyException con paquete/extra uv; no la lanza. Driver desconocido usa paquete fallback; se incluye texto de cause. |

La configuración es confiable para el engine, no un sanitizador genérico SQL:

- SQLite usa database e ignora url informativo. Ausente/None/vacío se convierte
  en :memory:. Otras cadenas son paths literales; no se activa expresamente
  file: como URI del driver. Los paths relativos dependen del CWD.
- Para SQLite :memory:/vacío, async usa AsyncAdaptedQueuePool y sync QueuePool,
  ambos pool_size=1/max_overflow=0 y check_same_thread=False. Es checkout
  exclusivo, **no el comportamiento StaticPool anterior**. En archivo quedan
  las políticas/opciones de pool predeterminadas de SQLAlchemy.
- Pgsql async reenvía sslmode normalizado como ssl y search_path/charset como
  server_settings search_path/client_encoding. Los helpers sync no aplican
  esos argumentos asyncpg. Username/password/host/database son texto opcional
  normalizado; port truthy se convierte con int. Una URL no prueba el servidor.
- MySQL añade charset/unix_socket al query URL. SET NAMES/COLLATE exigen
  identificadores ASCII-word; valores inválidos se omiten de esos comandos.
  strict no-None elige preset sql_mode estricto/relajado mediante normalización
  boolean-like, no un SQL mode arbitrario del usuario.
- SQL Server añade driver ODBC configurado/default ODBC Driver 18 for SQL Server,
  Encrypt y TrustServerCertificate yes/no. Oracle usa dsn/tns_name en connect_args
  y URL solo de credenciales; en otro caso SID o service_name.
- Los listeners SQLite establecen isolation_level=None, aplican PRAGMAs y emiten
  BEGIN en el evento begin para incluir savepoints y DDL en la raíz.
  foreign_key_constraints se convierte ON/OFF; busy_timeout int positivo se
  reenvía; journal_mode/synchronous usan enum.value o strings.
- MySQL async instala un escaper binario local a conexión si escape es callable.
  Bytes/bytearray/memoryview se convierten en hex _binary; el resto usa el
  original. No se parchea globalmente el driver. No se ejecutó MySQL real aquí.

### ConnectionManager

Fuente/import: [orionis.database.connection_manager.ConnectionManager](../connection_manager.py),
también exportado por raíz. Implementa IConnectionManager con slots. El
constructor llama app.config("database"); ConfigDatabase se convierte con
toDict y otro payload se usa directamente. Aplica lower a str(default),
copia superficialmente connections y comienza con caché de objetos vacío.
Configuración ausente/malformada puede lanzar TypeError/KeyError/AttributeError;
no hay fallback de entidad para sección ausente.

| Método | Resultado, mutabilidad y restricciones verificadas |
| --- | --- |
| connection(name=None) | Usa name or default (vacío también elige default), retorna Connection cacheada o construye/cachea una sin abrir engine. Config ausente/None lanza ConnectionNotFoundException. Nombres explícitos no se normalizan. |
| addConnection(name, config) | Exige string no vacío (ValueError, también para no-string) y dict real (TypeError). Retiene nombre sin modificar y dict por referencia; retorna None. Reemplaza config sin desalojar Connection cacheada. |
| hasConnection(name) | Comprueba nombres configurados incluso con entrada None; sin validación ni engine. |
| getDefaultName() | Retorna default string actual. |
| setDefaultName(name) | Exige pertenencia a nombres configurados o lanza ConnectionNotFoundException; retorna None. No normaliza ni desconecta. |
| configFor(name=None) | Retorna dict almacenado real, no copia; ausente/None lanza ConnectionNotFoundException. Mutar afecta construcciones futuras, no la copia superficial de config del Connection existente. |
| await disconnect(name=None) | Extrae un objeto cacheado y espera disconnect, o toma snapshot/vacía todos y dispone secuencialmente. Retorna None. Config/default persisten. Un fallo puede detener la iteración cuando ya se vació el caché. |

Claves no hashables propagan errores del diccionario. Config/prefix del objeto
se capturan al construirlo; desconectar directamente Connection no lo elimina
del caché del manager. Reemplazar no cierra objetos retenidos por consumidores.
No hay remove connection público, límite de caché ni sincronización entre hilos.

### API de consultas y lifecycle de Connection

Fuente/import: [orionis.database.connection.Connection](../connection.py),
exportada por raíz, implementa IConnection con slots. Constructor(name, config)
valida driver, copia config superficialmente, captura prefix del compilador,
crea ContextVar transaccional y deja engine=None. No valida conectividad,
credenciales ni todas las claves.

| Método | Parámetros y resultado esperado/directo |
| --- | --- |
| getName() | Retorna el nombre capturado. |
| await select(query, bindings=None) | String usa text cacheado y bindings; SelectPlan usa SQLCompiler e ignora bindings raw. Materializa list[dict] antes de liberar conexión. |
| await insert(plan) | Compila InsertPlan y puede usar filas homogéneas como parámetros executemany. Retorna InsertResult; solo una fila obtiene clave si el resultado la proporciona. Multirow last_insert_id es None. |
| await update(plan) / delete(plan) | Compila, ejecuta y retorna int(rowcount or 0), incluido un valor negativo del driver. Ausencia de filtros no añade protección contra mutación de todas las filas. |
| await scalar(plan) | Primera columna de primera fila o None. Recibe SelectPlan, no la variante string de select. |
| await execute(sql, bindings=None) | Ejecuta SQL text con mappings :param opcionales; retorna int(rowcount or 0). |
| await statement(sql, bindings=None) | Ejecuta SQL/DDL, descarta resultado y retorna True al completar. |
| await createTable(table, *, if_not_exists=True) | Compila TableDefinition y usa Table.create via run_sync con checkfirst. También crea índices de metadatos. True incluso si conserva tabla existente. |
| await dropTable(name, schema=None, *, if_exists=True) | Aplica prefix a nombre lógico, compila/borra, retorna True. A diferencia de Schema.drop, no analiza nombre con punto como schema separado. |
| transaction() | Retorna un manager Transaction nuevo; no inicia todavía transacción. |
| inTransaction() | True solo para asyncio Task propietaria con stack no vacío. Sin loop en ejecución, current_task puede lanzar RuntimeError. |
| await disconnect() | Si existe engine, vacía el campo y espera dispose. None. No reinicia compiler/config/contexto transaccional; otro uso puede crear engine nuevo. |

Los parámetros se pasan sin coerción general ni protección de identificadores.
Use bindings para valores y SQL raw confiable. _run suministra parámetros si
son truthy; en otro caso llama execute sin mapping. TextClause se cachea por
SQL, no valores. No hay API de resultados streaming: select materializa todo.

Fuera de transacción explícita, cada operación usa engine.begin; salida
correcta confirma y fallo revierte. Comprobar existencia y crear tabla no
es una declaración atómica de base de datos. Prefix afecta tablas/restricciones
compiladas, no SQL raw arbitrario del consumidor.

El primer engine usa URL/opciones, captura ModuleNotFoundError de paquete
DBAPI ausente y lanza MissingDatabaseDependencyException; después instala
listeners. No traduce universalmente otros fallos de dependencia/URL/adquisición/
configuración. _run y run_sync de createTable capturan SQLAlchemyError y lanzan
QueryException sanitizada from None con nombre de conexión y clase de error,
no SQL/valores/mensaje del driver. Compilación, adquisición, salida de contexto,
conversión de filas y callbacks tienen sus propias rutas de propagación.
Las descripciones amplias de QueryException en docstrings no son wrapper exhaustivo.

### Transacciones y pertenencia a tareas

Fuentes: [Connection](../connection.py),
[orionis.database.transaction.Transaction](../transaction.py).
begin/commit/rollback son async y retornan None:

- begin abre conexión dedicada/transacción raíz sin estado; otro begin de la
  misma tarea añade savepoint begin_nested. Si falla begin raíz, se cierra
  la conexión recién abierta antes de volver a lanzar.
- commit/rollback exigen estado y stack no vacío o TransactionException.
  Extraen el nivel interno antes de esperarlo. En finally, stack vacío limpia
  ContextVar y cierra la conexión raw.
- Errores SQLAlchemy se convierten TransactionException con mensaje/causa de
  driver, distinto de query sanitizada. Fallos de cleanup/cancelación pueden
  propagarse; no hay shield/reintento de nivel ni restauración del extraído.
- Un hijo con estado activo heredado recibe TransactionException al consultar
  o controlar transacción; inTransaction es False. Una vez asentado el estado
  original, el hijo lo descarta y puede adquirir de nuevo.

Transaction(connection) guarda referencia sin validar tipo. __aenter__ espera
begin y retorna **self**, no Connection. Consulte mediante Connection dentro
del bloque. __aexit__ confirma con exc_type None, revierte en otro caso y
retorna False. No hay guard propio de entrada/uso único ni forwarding de query.
Un error de salida/cleanup puede reemplazar la excepción del bloque. Contextos
Transaction anidados operan el stack de savepoints de Connection.

ContextVar conserva stack mutable heredado, protegido por identidad de tarea,
no copia profunda. El pool SQLite memory serializa checkout independiente;
el hijo no se une silenciosamente al padre activo. No demuestra seguridad
cross-loop/thread ni DDL transaccional en cada motor.

### SQLCompiler

Fuente/import: [orionis.database.compiler.SQLCompiler](../compiler.py), exportado
por raíz. Constructor(prefix="") captura prefix o vacío, MetaData y cachés
de tabla/definición. Retorna statements Core, no strings SQL ni resultados.
Compilar no hace I/O DB.

| Método | Resultado y condiciones de control |
| --- | --- |
| compileSelect(plan) | Select o CompoundSelect. Proyección, filtros, joins, group/having, orden/paging, locks/unions. Agregados ignoran distinct/order/limit/offset; COUNT permite *, los demás exigen columna. |
| supportsBatchInsert(plan) | Predicado bool estático: más de una fila, mismos conjuntos de claves, sin valores ClauseElement y guard específico de claves de columnas declaradas. No valida cada fila/columna ni garantiza éxito backend. |
| compileInsert(plan, *, parameterized=False) | values vacío -> QueryException. True retorna Insert sin poblar para grupos de parámetros separados; False incorpora valores single/multirow. El consumidor debe acompañar la ruta parametrizada con parámetros reales. |
| compileUpdate(plan) | values vacío -> QueryException; where opcional, sin exigir filtro. |
| compileDelete(plan) | where opcional, sin exigir filtro. |
| compileCreateTable(definition, *, if_not_exists=True) | CreateTable con metadatos y flag. Connection.createTable usa create de su element, no solo el texto DDL. |
| compileDropTable(name, schema=None, *, if_exists=True) | DropTable con prefix/schema; tabla cacheada o MetaData temporal. No invalida caché. |

Estructuras/enums están en [query expressions](../../orm/query/expressions.py),
no se redefinen aquí. Identificadores cualificados resuelven alias/fuentes
lógicas; fuentes/columnas ausentes, operadores join/comparación o tipos de
cláusula inválidos, BETWEEN sin dos límites, insert/update vacío y tipos no
mapeados lanzan QueryException explícita. Otros errores de toolkit/tipo se propagan.

Joins INNER/LEFT/FULL/CROSS y RIGHT con lados outer intercambiados. Joins
subquery requieren alias; los no-CROSS requieren ON. Predicados anidados usan
agrupación explícita; secuencias AND/OR se combinan de izquierda a derecha.
EXISTS/subquery pueden referenciar fuentes externas. Unions aplanan secuencias
del mismo tipo y agrupan mezclas mediante tablas derivadas. El dialecto decide
si SQL/locking/tipo solicitado puede ejecutarse.

RawExpression usa SQL confiable y valores bound. Fragmento aliased sin bindings
usa literal_column.label; con bindings preserva estos mediante scalar subquery
tipada. No hay validación genérica de SQL raw. Tablas sin columnas se completan
desde nombres referenciados **antes** de crear alias; SELECT * schemaless usa
wildcard literal.

Caché por schema y nombre prefijado. La misma identidad TableDefinition no
vacía reutiliza metadatos; otra definición declarada los reconstruye; una vacía
puede reutilizarlos. Mutar la misma definición no garantiza invalidación. Los
cachés no están acotados y persisten tras drop/disconnect. Placeholders de
foreign references usan nombres prefijados sin manejo cualificado cross-schema.

Restricciones observables de los builders de tipos:

- Primary keys autoincrement BigInteger reciben variante Integer SQLite.
  Primary de columna fuerza no-nullable. Defaults son client y, para valores
  no-None no-callable, también server_default literal.
- Enum compila expresamente native_enum=False/create_constraint=False;
  no reenvía todos los flags/length/validate_strings de factory. PickleType
  reenvía protocol, no pickler/impl custom.
- StrictArray, MatchType, NumericCommon y SchemaType tienen factories, pero
  no _TYPE_BUILDERS; compilar lanza QueryException. Factory disponible no
  certifica DDL soportado. Números/strings/tiempo dependen del dialecto.

### Schema y TableCreation

Fuente/import: [orionis.database.schema.schema.Schema](../schema/schema.py),
[TableCreation](../schema/table_creation.py). Schema implementa ISchema y
retiene manager; no abre conexión en constructor.

| Método | Resultado, reglas de selección y errores |
| --- | --- |
| connection(name=None) | Selecciona una vez y retorna Self; segundo uso lanza ValueError, también tras connection(None). El nombre se valida al resolver. None explícito elige default y desactiva fallback de migración. |
| create(name) | TableCreation inmediato. Solo salida async-with correcta recoge/construye/crea. **No hay __await__**; await schema.create no está soportado. |
| await createFromDefinition(definition) | Resuelve conexión seleccionada/migración/default y delega createTable; bool. Sin guard independiente de tipo. |
| await createFromModel(model) | Exige ModelMeta y __meta__ concreto propio o TypeError, usa metadata.table. Selección explícita prevalece sobre model.connection; si ambas faltan puede usar contexto de migración. Bool delegado. |
| await drop(name) | Analiza tabla lógica o un componente schema.table, delega dropTable; bool. |

partition rechaza schema/nombre vacío, segundo componente vacío o puntos
adicionales con ValueError. No valida todos los identificadores SQL ni aplica
strip arbitrario. Columnas duplicadas se sobreescriben por nombre y gana el
último comentario. PrimaryKey explícitas o de columna múltiples causan
ValueError; PrimaryKey vacía puede llegar a IndexError. Tipo no soportado
de definición lanza TypeError.

TableCreation.__aenter__ crea/guarda Blueprint nuevo y lo retorna. __aexit__
llama Schema._createTable solo sin exc_type y con blueprint; retorna False.
No hay guard de uso único/reentrada, cierre de recursos ni protocolo await.
Entrar de nuevo reemplaza el collector; uso concurrente compartido no se
coordina. Salir antes de entrar no crea tabla.

### Blueprint, Column y marcadores de declaración

Fuente/import: [Blueprint](../schema/blueprint.py), [Column](../schema/column.py)
y marcadores de [schema/__init__.py](../schema/__init__.py). Blueprint usa slots,
listas mutables y caché de factories. __getattr__ obtiene atributo callable
de Column, cachea wrapper por nombre, añade cada columna producida y la
retorna. Nombre ausente/no-callable lanza AttributeError; se propagan fallos
del wrapper. No es whitelist separada y fija de factories SQL válidas.
Las columnas entregadas permanecen mutables.

| Método Blueprint | Efecto/resultado implementado |
| --- | --- |
| timestamps(*, timezone=False) | Añade dateTime created_at/updated_at nullable; None, no Self fluido. |
| comment(text) | Normaliza/guarda Comment en constraints y lo retorna. |
| foreignKey(column, ref_table, ref_column, name=None) | Añade/retorna ForeignKey que envuelve CompositeForeignKey de una columna. |
| index(*columns, name=None, unique=False) | Añade/retorna Index que envuelve TableIndex. |
| primaryKey(*columns) | Añade/retorna PrimaryKey con tuple; no marca inmediatamente columnas ya existentes. |
| unique(*columns, name=None) | Añade/retorna Unique con UniqueConstraint. |
| columns() | Tuple snapshot de referencias en orden de columnas. |
| definitions() | Referencias de columnas y después constraints, no orden global intercalado. |

Los cuarenta métodos estáticos Column construyen subtipo ORM ColumnDefinition
nuevo, asignan name y retornan. id además primary/autoincrement. No escriben
DDL. Incluyen enteros, strings/text, booleans, fechas/tiempo, números,
enum/UUID/binary/pickle y variantes Strict. Defaults, bools keyword-only y
*enums exactos están en el apéndice.

Parámetros comunes: name se asigna como identificador; length/collation,
precision/scale, asdecimal/decimal_return_scale configuran tipos lógicos;
labels y flags constraint/native/validation configuran Enum; timezone configura
dateTime/timestamp; native/second_precision/day_precision interval;
protocol/pickler/impl PickleType; schema_name SchemaType;
item_type/as_tuple/dimensions/zero_indexes StrictArray; as_uuid/native_uuid
UUID; none_as_null StrictJson. Factories reenvían a constructores ORM,
cuyas restricciones y omisiones del compilador no son validación por anotación.

Se heredan de [ColumnDefinition](../../orm/schema/column/definition.py) operaciones
primary/nullable/default/unique/index/foreign/autoIncrement/comment que mutan
la misma definición y la retornan; hasDefault diferencia ausencia de un
default explícito. Esos métodos no se declaran en database.

Los marcadores guardan atributos públicos mutables sin slots/frozen: Comment
normaliza NFC, sustituye controles ASCII, colapsa espacios y guarda text
recortado; entrada no textual puede causar TypeError. ForeignKey.foreign,
Index.constraint y Unique.constraint referencian dataclasses ORM. PrimaryKey.columns
es tuple, incluso vacío. Timestamps.timezone no se valida y default es **True**,
distinto de Blueprint.timestamps. El clasificador acepta Timestamps aunque
la unión SchemaDefinition lo omite. Es alias PEP 695, no constructor validador.

DefinitionBucket es auxiliar mutable con slots, dicts nuevos columns/kwargs y
listas primary_columns/unique_constraints/foreign_keys/indexes. Su constructor
no valida; la clasificación llena esas referencias. No se exporta por schema.

### Superficie de tipado de Blueprint

[blueprint.pyi](../schema/blueprint.pyi) suministra firmas para editor/type-checker
de factories dinámicas y seis métodos explícitos. No se importa/ejecuta en
runtime. El comportamiento pertenece a blueprint.py/column.py, no al cuerpo
Ellipsis del stub. No declara constructor runtime, columns(), definitions()
o __getattr__.

El código literal completo se incluye como bloque de referencia junto a los
owners Python. No se infirieron ni añadieron anotaciones al código instalado.
Un tipo disponible en el stub no demuestra soporte de SQLCompiler.

### Migration, Migrator y tracking

Fuente/import: [Migration](../contracts/migration.py), ABC abstracta exportada
por raíz con async up/down, y [Migrator](../migrations/migrator.py), que
implementa IMigrator. Constructor(app, conn_manager) guarda ambos y caché
de discovery vacío; no abre DB hasta la operación.

| Método Migrator | Resultado esperado y límites |
| --- | --- |
| migrate(*, connection=None, events=None) | Asegura tracking, lee nombres, descubre/ordena pendientes y aplica en orden. Retorna completados; sin pendientes []. Batch máximo actual+1. |
| rollback(steps=1, *, connection=None, events=None) | Int positivo no-bool o ValueError. Revierte batches distintos más recientes, primero id registrado mayor. Más steps que batches selecciona todos; retorna nombres. |
| reset(*, connection=None, events=None) | Revierte todo el historial, primero más recientes; retorna nombres, [] sin historial. |
| refresh(steps=None, *, connection=None, events=None) | reset o rollback validado y luego migrate; retorna reaplicados. No es una transacción de secuencia completa. |
| fresh(*, connection=None, events=None) | reset mediante down, borra tracking migrations y seeders cuando corresponde, luego migrate. No vacía genéricamente todas las tablas ajenas. |
| status(*, connection=None) | Asegura tracking (escritura), lee historial y retorna migration/ran/batch de los descubiertos. Nombres registrados sin fuente descubierta no aparecen como filas aparte. |

Discovery usa app.path("database_migrations"), app.basePath y reflexión.
Admite subclases Migration definidas localmente, no reexports, y ordena por
stem final del módulo/archivo. Directorio ausente cachea {}; cada stem debe
ser único también entre subdirectorios o varias clases, o ValueError. No
filtra subclases abstractas por separado antes de app.build. Cachea clases,
incluido vacío, sin refresh público. ModuleInspector normaliza inicializadores
a nombres de paquete; el guard stem=="__init__" no excluye universalmente
clases definidas localmente en ellos.

Tracking migrations tiene id auto, migration único, batch y migrated_at epoch
entero. Cada paso vincula conexión elegida, inicia transacción, construye con
app.build, espera up/down e inserta/elimina tracking. Fallar detiene pasos
posteriores, no deshace los anteriores confirmados. Antes de cambiar schema,
rollback comprueba las clases de todos los nombres seleccionados y lanza
MigrationNotFoundException si falta alguno.

DDL/data transaccional depende del engine y operaciones. No se garantiza
rollback externo o de motores con commits DDL implícitos. Se propagan
import/build/migración/eventos/query. createTable de tracking no tiene reintento
de creador concurrente en Migrator y no se reclaman pendientes antes de up;
no suponga el comportamiento once-only de seeders bajo migrate concurrente.

Rollback completo elimina tracking seeders durante el último paso; parcial
lo conserva. down define qué datos/schema desaparecen; no hay inversa
independiente de datos seeded. fresh también limpia historial cuando no
quedan migraciones registradas.

**Límite de prefix comprobado:** DDL del tracking aplica prefix de Connection,
pero SELECT/INSERT/DELETE de Migrator usan migrations literal sin prefijo.
Un prefijo no vacío reprodujo QueryException en status tras crear la tabla
prefijada. Se documentó, no corrigió. Tracking de seeders usa planes y una
ruta distinta para prefix.

### Eventos y contexto de conexión de migración

Fuente/import: [MigrationEvents](../migrations/events.py),
[funciones de contexto](../migrations/context.py). MigrationEvents es dataclass
frozen/slotted/keyword-only con on_start/on_success/on_error default None;
constructor/igualdad/hash son generados. started(name), succeeded(name, elapsed)
y failed(name, elapsed) invocan callback no-None y retornan None. No hay
validación de callable, conversión de elapsed, protección de errores ni espera
de resultados callback.

NO_EVENTS es una instancia vacía de módulo. SeederEvents de
[seeders/events.py](../seeders/events.py) es **alias importado de MigrationEvents**,
con el mismo NO_EVENTS, no otra clase/constructor.

started de migración ocurre antes de transacción/try; failed para Exception
capturada tras entrar en el trabajo y luego se relanza; succeeded tras commit.
Cancelación/BaseException no se reporta por ese handler Exception. Fallar
started impide trabajo; fallar failed puede sustituir el original; succeeded
puede fallar después de confirmar datos. Seeders tienen su orden de claim.

current_migration_connection() retorna referencia raw o None. El
@contextmanager síncrono migration_connection_scope(connection) produce None,
establece token y restaura en finally, sin comenzar/cerrar transacción ni
validar referencia. Los scopes anidados restauran el externo; hijos heredan
referencia, y sigue aplicando pertenencia de tarea de Connection.

### Seeder y SeederRunner

Fuente/import: [Seeder](../seeders/seeder.py), [SeederRunner](../seeders/runner.py),
exports de raíz/subpaquete. Seeder es ABC abstracta con async run y slots
vacíos. SeederRunner(app, conn_manager) guarda referencias/caché de discovery.
await seed(*, connection=None, events=None) retorna nombres completados por
esa llamada, no todos los pendientes o previos; sin pendientes [].

Discovery usa app.path("database_seeders"), subclases locales, stems ordenados,
ValueError por duplicado y caché como Migrator. No excluye abstractas en
runtime ni sustituye archivos ausentes arbitrariamente.

La tabla por planes seeders tiene id, seeder único, batch y seeded_at. seed
la asegura, lee registros confirmados, elige máximo batch previo+1 y para
cada clase abre transacción e **inserta primero el claim único**, con timestamp
cero. Tras claim, started, contexto de conexión, app.build, await run,
actualización epoch de finalización y commit de datos/tracking juntos.
succeeded tras commit; Exception reporta failed solo si hubo started.

Tras rollback del claim QueryException, si existe registro confirmado visible,
omite esa clase; si no, llama started/failed y relanza query. Maneja conflicto
correcto, no cada fallo como duplicado. Creador concurrente de tracking se
tolera solo si puede leerse después de createTable QueryException. El claim
único impide dos filas confirmadas, pero motor transaccional, efectos externos
y callbacks limitan el "exactly once" de la docstring.

Editar/añadir fuente no repite stem registrado ni invalida discovery. No
existe unseed o borrado de historial público aquí. El lifecycle Migrator
puede limpiarlo según lo descrito. El módulo no contiene credenciales de
administración integradas; datos de seeders de aplicación quedan fuera de esta API.

### Providers, contratos y jerarquía de excepciones

[ConnectionManagerProvider](../provider.py): register retorna None tras binding
singleton; boot espera IConnectionManager, establece ConnectionResolver global
y retorna None. Hereda el constructor app de ServiceProvider.
[SchemaProvider](../schema_provider.py): register None tras binding transient
ISchema; boot async heredado no hace nada. Duplicados/DI dependen del contenedor
real, no de reintentos propios de provider.

Los seis contratos/bases abstractas declaran __slots__=():

| Contrato | Operaciones declaradas |
| --- | --- |
| [IConnection](../contracts/connection.py) | Dieciséis métodos name/query/schema/transaction/lifecycle de Connection. |
| [IConnectionManager](../contracts/connection_manager.py) | Siete operaciones conexión/config/default/disconnect. |
| [ITransaction](../contracts/transaction.py) | Enter/exit async. |
| [ISchema](../contracts/schema.py) | connection, create, createFromDefinition, createFromModel, drop. |
| [IMigrator](../contracts/migrator.py) | Seis operaciones de migración async. |
| [Migration](../contracts/migration.py) | up/down async. Seeder es base abstracta propia con run, no subclase Migration. |

Declaran contratos, no coerción/validación independiente. La mayoría de cuerpos
abstractos tienen solo docstring; ISchema.connection incluye Ellipsis literal.
Los apéndices conservan decoradores/defaults fuente.

[InsertResult](../entities/result.py) es dataclass frozen/slotted con obligatorios
last_insert_id: Any y row_count: int. Constructor posicional, igualdad/hash/repr
generados no son declaraciones literales; no valida campos. No hereda BaseEntity
ni toDict. ID no hashable puede hacer fallar hash. Keys/counts tienen límites
de driver descritos bajo Connection.

[DatabaseException](../exceptions.py) hereda Exception; subclases
ConnectionNotFoundException, MigrationNotFoundException,
MissingDatabaseDependencyException, QueryException, TransactionException y
UnsupportedDriverException. No declaran constructores custom/status codes;
args/chaining estándar. Sus condiciones dependen de owners anteriores.
Callback, parsing, configuración y toolkit no se envuelven universalmente.

### Declaraciones literales

Los headers conservan declaraciones, no firmas runtime evaluadas. Los campos
describen constructores generados/almacenamiento. Alias importado y stub se
identifican aparte. Exports/paquetes vacíos no son implementaciones adicionales.

#### __init__.py

Fuente: [orionis/database/__init__.py](../__init__.py).

`__all__`

```python
__all__ = [
    "Connection",
    "ConnectionManager",
    "ConnectionNotFoundException",
    "DatabaseException",
    "Migration",
    "MigrationNotFoundException",
    "Migrator",
    "MissingDatabaseDependencyException",
    "QueryException",
    "SQLCompiler",
    "Seeder",
    "SeederEvents",
    "SeederRunner",
    "Transaction",
    "TransactionException",
    "UnsupportedDriverException",
]
```

`__getattr__`

```python
def __getattr__(name: str) -> object:
```

`__dir__`

```python
def __dir__() -> list[str]:
```

#### compiler.py

Fuente: [orionis/database/compiler.py](../compiler.py).

`SQLCompiler`

```python
class SQLCompiler:
```

`SQLCompiler fields`

```python
__slots__ = ("_definitions", "_metadata", "_prefix", "_tables")
```

`SQLCompiler.__init__`

```python
def __init__(self, prefix: str = "") -> None:
```

`SQLCompiler.compileSelect`

```python
def compileSelect(self, plan: SelectPlan) -> Select[Any] | CompoundSelect:
```

`SQLCompiler.supportsBatchInsert`

```python
@staticmethod
def supportsBatchInsert(plan: InsertPlan) -> bool:
```

`SQLCompiler.compileInsert`

```python
def compileInsert(
    self,
    plan: InsertPlan,
    *,
    parameterized: bool = False,
) -> Insert:
```

`SQLCompiler.compileUpdate`

```python
def compileUpdate(self, plan: UpdatePlan) -> Update:
```

`SQLCompiler.compileDelete`

```python
def compileDelete(self, plan: DeletePlan) -> Delete:
```

`SQLCompiler.compileCreateTable`

```python
def compileCreateTable(
    self,
    definition: TableDefinition,
    *,
    if_not_exists: bool = True,
) -> Executable:
```

`SQLCompiler.compileDropTable`

```python
def compileDropTable(
    self,
    name: str,
    schema: str | None = None,
    *,
    if_exists: bool = True,
) -> Executable:
```

#### connection.py

Fuente: [orionis/database/connection.py](../connection.py).

`Connection`

```python
class Connection(IConnection):
```

`Connection fields`

```python
__slots__ = ("_compiler", "_config", "_engine", "_name", "_tx_state")
```

`Connection.__init__`

```python
def __init__(
    self,
    name: str,
    config: dict[str, Any],
) -> None:
```

`Connection.getName`

```python
def getName(self) -> str:
```

`Connection.select`

```python
async def select(
    self,
    query: SelectPlan | str,
    bindings: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
```

`Connection.insert`

```python
async def insert(
    self,
    plan: InsertPlan,
) -> InsertResult:
```

`Connection.update`

```python
async def update(
    self,
    plan: UpdatePlan,
) -> int:
```

`Connection.delete`

```python
async def delete(
    self,
    plan: DeletePlan,
) -> int:
```

`Connection.scalar`

```python
async def scalar(
    self,
    plan: SelectPlan,
) -> Any:
```

`Connection.execute`

```python
async def execute(
    self,
    sql: str,
    bindings: Mapping[str, Any] | None = None,
) -> int:
```

`Connection.statement`

```python
async def statement(
    self,
    sql: str,
    bindings: Mapping[str, Any] | None = None,
) -> bool:
```

`Connection.createTable`

```python
async def createTable(
    self,
    table: TableDefinition,
    *,
    if_not_exists: bool = True,
) -> bool:
```

`Connection.dropTable`

```python
async def dropTable(
    self,
    name: str,
    schema: str | None = None,
    *,
    if_exists: bool = True,
) -> bool:
```

`Connection.begin`

```python
async def begin(self) -> None:
```

`Connection.commit`

```python
async def commit(self) -> None:
```

`Connection.rollback`

```python
async def rollback(self) -> None:
```

`Connection.transaction`

```python
def transaction(self) -> ITransaction:
```

`Connection.inTransaction`

```python
def inTransaction(self) -> bool:
```

`Connection.disconnect`

```python
async def disconnect(self) -> None:
```

#### connection_manager.py

Fuente: [orionis/database/connection_manager.py](../connection_manager.py).

`ConnectionManager`

```python
class ConnectionManager(IConnectionManager):

    # ruff: noqa: TC001
```

`ConnectionManager fields`

```python
__slots__ = ("_cached_connections", "_connections", "_default")
```

`ConnectionManager.__init__`

```python
def __init__(
    self,
    app: IApplication,
) -> None:
```

`ConnectionManager.connection`

```python
def connection(
    self,
    name: str | None = None,
) -> IConnection:
```

`ConnectionManager.addConnection`

```python
def addConnection(self, name: str, config: dict[str, Any]) -> None:
```

`ConnectionManager.hasConnection`

```python
def hasConnection(self, name: str) -> bool:
```

`ConnectionManager.getDefaultName`

```python
def getDefaultName(self) -> str:
```

`ConnectionManager.setDefaultName`

```python
def setDefaultName(self, name: str) -> None:
```

`ConnectionManager.disconnect`

```python
async def disconnect(self, name: str | None = None) -> None:
```

`ConnectionManager.configFor`

```python
def configFor(self, name: str | None = None) -> dict[str, Any]:
```

#### contracts/__init__.py

Fuente: [orionis/database/contracts/__init__.py](../contracts/__init__.py).

`__all__`

```python
__all__ = [
    "IConnection",
    "IConnectionManager",
    "ITransaction",
]
```

#### contracts/connection.py

Fuente: [orionis/database/contracts/connection.py](../contracts/connection.py).

`IConnection`

```python
class IConnection(ABC):
```

`IConnection fields`

```python
__slots__ = ()
```

`IConnection.getName`

```python
@abstractmethod
def getName(self) -> str:
```

`IConnection.select`

```python
@abstractmethod
async def select(
    self,
    query: SelectPlan | str,
    bindings: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
```

`IConnection.insert`

```python
@abstractmethod
async def insert(self, plan: InsertPlan) -> InsertResult:
```

`IConnection.update`

```python
@abstractmethod
async def update(self, plan: UpdatePlan) -> int:
```

`IConnection.delete`

```python
@abstractmethod
async def delete(self, plan: DeletePlan) -> int:
```

`IConnection.scalar`

```python
@abstractmethod
async def scalar(self, plan: SelectPlan) -> Any:
```

`IConnection.execute`

```python
@abstractmethod
async def execute(
    self,
    sql: str,
    bindings: Mapping[str, Any] | None = None,
) -> int:
```

`IConnection.statement`

```python
@abstractmethod
async def statement(
    self,
    sql: str,
    bindings: Mapping[str, Any] | None = None,
) -> bool:
```

`IConnection.createTable`

```python
@abstractmethod
async def createTable(
    self,
    table: TableDefinition,
    *,
    if_not_exists: bool = True,
) -> bool:
```

`IConnection.dropTable`

```python
@abstractmethod
async def dropTable(
    self,
    name: str,
    schema: str | None = None,
    *,
    if_exists: bool = True,
) -> bool:
```

`IConnection.begin`

```python
@abstractmethod
async def begin(self) -> None:
```

`IConnection.commit`

```python
@abstractmethod
async def commit(self) -> None:
```

`IConnection.rollback`

```python
@abstractmethod
async def rollback(self) -> None:
```

`IConnection.transaction`

```python
@abstractmethod
def transaction(self) -> ITransaction:
```

`IConnection.inTransaction`

```python
@abstractmethod
def inTransaction(self) -> bool:
```

`IConnection.disconnect`

```python
@abstractmethod
async def disconnect(self) -> None:
```

#### contracts/connection_manager.py

Fuente: [orionis/database/contracts/connection_manager.py](../contracts/connection_manager.py).

`IConnectionManager`

```python
class IConnectionManager(ABC):
```

`IConnectionManager fields`

```python
__slots__ = ()
```

`IConnectionManager.connection`

```python
@abstractmethod
def connection(self, name: str | None = None) -> IConnection:
```

`IConnectionManager.addConnection`

```python
@abstractmethod
def addConnection(self, name: str, config: dict[str, Any]) -> None:
```

`IConnectionManager.hasConnection`

```python
@abstractmethod
def hasConnection(self, name: str) -> bool:
```

`IConnectionManager.getDefaultName`

```python
@abstractmethod
def getDefaultName(self) -> str:
```

`IConnectionManager.setDefaultName`

```python
@abstractmethod
def setDefaultName(self, name: str) -> None:
```

`IConnectionManager.disconnect`

```python
@abstractmethod
async def disconnect(self, name: str | None = None) -> None:
```

`IConnectionManager.configFor`

```python
@abstractmethod
def configFor(self, name: str | None = None) -> dict[str, Any]:
```

#### contracts/migration.py

Fuente: [orionis/database/contracts/migration.py](../contracts/migration.py).

`Migration`

```python
class Migration(ABC):
```

`Migration fields`

```python
__slots__ = ()
```

`Migration.up`

```python
@abstractmethod
async def up(self) -> None:
```

`Migration.down`

```python
@abstractmethod
async def down(self) -> None:
```

#### contracts/migrator.py

Fuente: [orionis/database/contracts/migrator.py](../contracts/migrator.py).

`IMigrator`

```python
class IMigrator(ABC):
```

`IMigrator fields`

```python
__slots__ = ()
```

`IMigrator.migrate`

```python
@abstractmethod
async def migrate(
    self,
    *,
    connection: str | None = None,
    events: MigrationEvents | None = None,
) -> list[str]:
```

`IMigrator.rollback`

```python
@abstractmethod
async def rollback(
    self,
    steps: int = 1,
    *,
    connection: str | None = None,
    events: MigrationEvents | None = None,
) -> list[str]:
```

`IMigrator.reset`

```python
@abstractmethod
async def reset(
    self,
    *,
    connection: str | None = None,
    events: MigrationEvents | None = None,
) -> list[str]:
```

`IMigrator.refresh`

```python
@abstractmethod
async def refresh(
    self,
    steps: int | None = None,
    *,
    connection: str | None = None,
    events: MigrationEvents | None = None,
) -> list[str]:
```

`IMigrator.fresh`

```python
@abstractmethod
async def fresh(
    self,
    *,
    connection: str | None = None,
    events: MigrationEvents | None = None,
) -> list[str]:
```

`IMigrator.status`

```python
@abstractmethod
async def status(
    self,
    *,
    connection: str | None = None,
) -> list[dict[str, Any]]:
```

#### contracts/schema.py

Fuente: [orionis/database/contracts/schema.py](../contracts/schema.py).

`ISchema`

```python
class ISchema(ABC):
```

`ISchema fields`

```python
__slots__ = ()
```

`ISchema.connection`

```python
@abstractmethod
def connection(self, name: str | None = None) -> Self:
```

`ISchema.create`

```python
@abstractmethod
def create(
    self,
    name: str,
) -> TableCreation:
```

`ISchema.createFromDefinition`

```python
@abstractmethod
async def createFromDefinition(self, definition: TableDefinition) -> bool:
```

`ISchema.createFromModel`

```python
@abstractmethod
async def createFromModel(self, model: type[Model]) -> bool:
```

`ISchema.drop`

```python
@abstractmethod
async def drop(self, name: str) -> bool:
```

#### contracts/transaction.py

Fuente: [orionis/database/contracts/transaction.py](../contracts/transaction.py).

`ITransaction`

```python
class ITransaction(ABC):
```

`ITransaction fields`

```python
__slots__ = ()
```

`ITransaction.__aenter__`

```python
@abstractmethod
async def __aenter__(self) -> ITransaction:
```

`ITransaction.__aexit__`

```python
@abstractmethod
async def __aexit__(
    self,
    exc_type: type[BaseException] | None,
    exc: BaseException | None,
    traceback: TracebackType | None,
) -> bool:
```

#### dialect.py

Fuente: [orionis/database/dialect.py](../dialect.py).

`resolve_driver`

```python
def resolve_driver(config: dict[str, Any]) -> str:
```

`missing_dependency_error`

```python
def missing_dependency_error(
    driver: str,
    cause: ModuleNotFoundError,
    *,
    sync: bool = False,
) -> MissingDatabaseDependencyException:
```

`build_engine_url`

```python
def build_engine_url(
    config: dict[str, Any],
    *,
    sync: bool = False,
) -> URL:
```

`engine_options`

```python
def engine_options(
    config: dict[str, Any],
    *,
    sync: bool = False,
) -> dict[str, Any]:
```

`configure_engine`

```python
def configure_engine(engine: AsyncEngine, config: dict[str, Any]) -> None:
```

#### entities/__init__.py

Fuente: [orionis/database/entities/__init__.py](../entities/__init__.py).

`__all__`

```python
__all__ = [
    "InsertResult",
]
```

#### entities/result.py

Fuente: [orionis/database/entities/result.py](../entities/result.py).

`InsertResult`

```python
@dataclass(frozen=True, slots=True)
class InsertResult:
```

`InsertResult fields`

```python
last_insert_id: Any
row_count: int
```

#### exceptions.py

Fuente: [orionis/database/exceptions.py](../exceptions.py).

`DatabaseException`

```python
class DatabaseException(Exception):
```

`ConnectionNotFoundException`

```python
class ConnectionNotFoundException(DatabaseException):
```

`MigrationNotFoundException`

```python
class MigrationNotFoundException(DatabaseException):
```

`MissingDatabaseDependencyException`

```python
class MissingDatabaseDependencyException(DatabaseException):
```

`QueryException`

```python
class QueryException(DatabaseException):
```

`TransactionException`

```python
class TransactionException(DatabaseException):
```

`UnsupportedDriverException`

```python
class UnsupportedDriverException(DatabaseException):
```

#### migrations/__init__.py

Fuente: [orionis/database/migrations/__init__.py](../migrations/__init__.py).

`__all__`

```python
__all__ = [
    "Migrator",
]
```

#### migrations/context.py

Fuente: [orionis/database/migrations/context.py](../migrations/context.py).

`current_migration_connection`

```python
def current_migration_connection() -> IConnection | None:
```

`migration_connection_scope`

```python
@contextmanager
def migration_connection_scope(connection: IConnection) -> Generator[None]:
```

#### migrations/events.py

Fuente: [orionis/database/migrations/events.py](../migrations/events.py).

`MigrationEvents`

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class MigrationEvents:
```

`MigrationEvents fields`

```python
on_start: Callable[[str], None] | None = None
on_success: Callable[[str, float], None] | None = None
on_error: Callable[[str, float], None] | None = None
```

`MigrationEvents.started`

```python
def started(self, name: str) -> None:
```

`MigrationEvents.succeeded`

```python
def succeeded(self, name: str, elapsed: float) -> None:
```

`MigrationEvents.failed`

```python
def failed(self, name: str, elapsed: float) -> None:
```

`NO_EVENTS`

```python
NO_EVENTS: MigrationEvents = MigrationEvents()
```

#### migrations/migrator.py

Fuente: [orionis/database/migrations/migrator.py](../migrations/migrator.py).

`Migrator`

```python
class Migrator(IMigrator):
```

`Migrator fields`

```python
__slots__ = ("__app", "__conn_manager", "__discovered_cache")
```

`Migrator.__init__`

```python
def __init__(
    self,
    app: IApplication,
    conn_manager: IConnectionManager,
) -> None:
```

`Migrator.migrate`

```python
async def migrate(
    self,
    *,
    connection: str | None = None,
    events: MigrationEvents | None = None,
) -> list[str]:
```

`Migrator.rollback`

```python
async def rollback(
    self,
    steps: int = 1,
    *,
    connection: str | None = None,
    events: MigrationEvents | None = None,
) -> list[str]:
```

`Migrator.reset`

```python
async def reset(
    self,
    *,
    connection: str | None = None,
    events: MigrationEvents | None = None,
) -> list[str]:
```

`Migrator.refresh`

```python
async def refresh(
    self,
    steps: int | None = None,
    *,
    connection: str | None = None,
    events: MigrationEvents | None = None,
) -> list[str]:
```

`Migrator.fresh`

```python
async def fresh(
    self,
    *,
    connection: str | None = None,
    events: MigrationEvents | None = None,
) -> list[str]:
```

`Migrator.status`

```python
async def status(
    self,
    *,
    connection: str | None = None,
) -> list[dict[str, Any]]:
```

#### provider.py

Fuente: [orionis/database/provider.py](../provider.py).

`ConnectionManagerProvider`

```python
class ConnectionManagerProvider(ServiceProvider):
```

`ConnectionManagerProvider.register`

```python
def register(self) -> None:
```

`ConnectionManagerProvider.boot`

```python
async def boot(self) -> None:
```

#### schema/__init__.py

Fuente: [orionis/database/schema/__init__.py](../schema/__init__.py).

`__all__`

```python
__all__ = [
    "Blueprint",
    "Column",
    "Comment",
    "ForeignKey",
    "Index",
    "PrimaryKey",
    "Timestamps",
    "Unique",
]
```

#### schema/blueprint.py

Fuente: [orionis/database/schema/blueprint.py](../schema/blueprint.py).

`Blueprint`

```python
class Blueprint:
```

`Blueprint fields`

```python
__slots__ = ("__columns", "__constraints", "__factory_cache")
```

`Blueprint.__init__`

```python
def __init__(self) -> None:
```

`Blueprint.__getattr__`

```python
def __getattr__(self, name: str) -> Callable[..., ColumnDefinition]:
```

`Blueprint.timestamps`

```python
def timestamps(self, *, timezone: bool = False) -> None:
```

`Blueprint.comment`

```python
def comment(self, text: str) -> Comment:
```

`Blueprint.foreignKey`

```python
def foreignKey(
    self,
    column: str,
    ref_table: str,
    ref_column: str,
    name: str | None = None,
) -> ForeignKey:
```

`Blueprint.index`

```python
def index(
    self,
    *columns: str,
    name: str | None = None,
    unique: bool = False,
) -> Index:
```

`Blueprint.primaryKey`

```python
def primaryKey(self, *columns: str) -> PrimaryKey:
```

`Blueprint.unique`

```python
def unique(self, *columns: str, name: str | None = None) -> Unique:
```

`Blueprint.columns`

```python
def columns(self) -> tuple[ColumnDefinition, ...]:
```

`Blueprint.definitions`

```python
def definitions(
    self,
) -> tuple[
    ColumnDefinition | Comment | ForeignKey | Index | PrimaryKey | Unique, ...,
]:
```

#### schema/column.py

Fuente: [orionis/database/schema/column.py](../schema/column.py).

`Column`

```python
class Column:
```

`Column.id`

```python
@staticmethod
def id(name: str = "id") -> BigInteger:
```

`Column.bigInteger`

```python
@staticmethod
def bigInteger(name: str) -> BigInteger:
```

`Column.boolean`

```python
@staticmethod
def boolean(
    name: str,
    *,
    create_constraint: bool = False,
    constraint_name: str | None = None,
) -> Boolean:
```

`Column.date`

```python
@staticmethod
def date(name: str) -> Date:
```

`Column.dateTime`

```python
@staticmethod
def dateTime(name: str, *, timezone: bool = False) -> DateTime:
```

`Column.double`

```python
@staticmethod
def double(
    name: str,
    precision: int | None = None,
    *,
    asdecimal: bool = False,
    decimal_return_scale: int | None = None,
) -> Double:
```

`Column.enum`

```python
@staticmethod
def enum(  # noqa: PLR0913
    name: str,
    *enums: str,
    constraint_name: str | None = None,
    create_constraint: bool = False,
    native_enum: bool = True,
    length: int | None = None,
    validate_strings: bool = False,
) -> Enum:
```

`Column.float`

```python
@staticmethod
def float(
    name: str,
    precision: int | None = None,
    *,
    asdecimal: bool = False,
    decimal_return_scale: int | None = None,
) -> Float:
```

`Column.integer`

```python
@staticmethod
def integer(name: str) -> Integer:
```

`Column.interval`

```python
@staticmethod
def interval(
    name: str,
    *,
    native: bool = True,
    second_precision: int | None = None,
    day_precision: int | None = None,
) -> Interval:
```

`Column.largeBinary`

```python
@staticmethod
def largeBinary(name: str, length: int | None = None) -> LargeBinary:
```

`Column.matchType`

```python
@staticmethod
def matchType(name: str) -> MatchType:
```

`Column.numeric`

```python
@staticmethod
def numeric(
    name: str,
    precision: int | None = None,
    scale: int | None = None,
    decimal_return_scale: int | None = None,
    *,
    asdecimal: bool = True,
) -> Numeric:
```

`Column.numericCommon`

```python
@staticmethod
def numericCommon(name: str) -> NumericCommon:
```

`Column.pickleType`

```python
@staticmethod
def pickleType(
    name: str,
    protocol: int = 5,
    pickler: object | None = None,
    impl: object | None = None,
) -> PickleType:
```

`Column.schemaType`

```python
@staticmethod
def schemaType(name: str, schema_name: str | None = None) -> SchemaType:
```

`Column.smallInteger`

```python
@staticmethod
def smallInteger(name: str) -> SmallInteger:
```

`Column.string`

```python
@staticmethod
def string(
    name: str,
    length: int | None = 255,
    collation: str | None = None,
) -> String:
```

`Column.text`

```python
@staticmethod
def text(
    name: str,
    length: int | None = None,
    collation: str | None = None,
) -> Text:
```

`Column.time`

```python
@staticmethod
def time(name: str) -> Time:
```

`Column.unicode`

```python
@staticmethod
def unicode(
    name: str,
    length: int | None = None,
    collation: str | None = None,
) -> Unicode:
```

`Column.unicodeText`

```python
@staticmethod
def unicodeText(
    name: str,
    length: int | None = None,
    collation: str | None = None,
) -> UnicodeText:
```

`Column.uuid`

```python
@staticmethod
def uuid(
    name: str,
    *,
    as_uuid: bool = True,
    native_uuid: bool = True,
) -> Uuid:
```

`Column.strictArray`

```python
@staticmethod
def strictArray(
    name: str,
    item_type: ColumnDefinition,
    *,
    as_tuple: bool = False,
    dimensions: int | None = None,
    zero_indexes: bool = False,
) -> StrictArray:
```

`Column.strictBigInt`

```python
@staticmethod
def strictBigInt(name: str) -> StrictBigInt:
```

`Column.strictBinary`

```python
@staticmethod
def strictBinary(name: str, length: int | None = None) -> StrictBinary:
```

`Column.strictBlob`

```python
@staticmethod
def strictBlob(name: str, length: int | None = None) -> StrictBlob:
```

`Column.strictChar`

```python
@staticmethod
def strictChar(
    name: str,
    length: int | None = None,
    collation: str | None = None,
) -> StrictChar:
```

`Column.strictClob`

```python
@staticmethod
def strictClob(
    name: str,
    length: int | None = None,
    collation: str | None = None,
) -> StrictClob:
```

`Column.strictDecimal`

```python
@staticmethod
def strictDecimal(
    name: str,
    precision: int | None = 10,
    scale: int | None = 2,
    decimal_return_scale: int | None = None,
    *,
    asdecimal: bool = True,
) -> StrictDecimal:
```

`Column.strictDoublePrecision`

```python
@staticmethod
def strictDoublePrecision(
    name: str,
    precision: int | None = None,
    *,
    asdecimal: bool = False,
    decimal_return_scale: int | None = None,
) -> StrictDoublePrecision:
```

`Column.strictInt`

```python
@staticmethod
def strictInt(name: str) -> StrictInt:
```

`Column.strictJson`

```python
@staticmethod
def strictJson(name: str, *, none_as_null: bool = False) -> StrictJson:
```

`Column.strictNChar`

```python
@staticmethod
def strictNChar(
    name: str,
    length: int | None = None,
    collation: str | None = None,
) -> StrictNChar:
```

`Column.strictNVarChar`

```python
@staticmethod
def strictNVarChar(
    name: str,
    length: int | None = None,
    collation: str | None = None,
) -> StrictNVarChar:
```

`Column.strictReal`

```python
@staticmethod
def strictReal(
    name: str,
    precision: int | None = None,
    *,
    asdecimal: bool = False,
    decimal_return_scale: int | None = None,
) -> StrictReal:
```

`Column.strictSmallInt`

```python
@staticmethod
def strictSmallInt(name: str) -> StrictSmallInt:
```

`Column.strictTimestamp`

```python
@staticmethod
def strictTimestamp(name: str, *, timezone: bool = False) -> StrictTimestamp:
```

`Column.strictVarBinary`

```python
@staticmethod
def strictVarBinary(name: str, length: int | None = None) -> StrictVarBinary:
```

`Column.strictVarChar`

```python
@staticmethod
def strictVarChar(
    name: str,
    length: int | None = 255,
    collation: str | None = None,
) -> StrictVarChar:
```

#### schema/comment.py

Fuente: [orionis/database/schema/comment.py](../schema/comment.py).

`Comment`

```python
class Comment:
```

`Comment.__init__`

```python
def __init__(self, text: str) -> None:
```

#### schema/definition_bucket.py

Fuente: [orionis/database/schema/definition_bucket.py](../schema/definition_bucket.py).

`DefinitionBucket`

```python
class DefinitionBucket:
```

`DefinitionBucket fields`

```python
__slots__ = (
        "columns",
        "foreign_keys",
        "indexes",
        "kwargs",
        "primary_columns",
        "unique_constraints",
    )
```

`DefinitionBucket.__init__`

```python
def __init__(self) -> None:
```

#### schema/definitions.py

Fuente: [orionis/database/schema/definitions.py](../schema/definitions.py).

`SchemaDefinition`

```python
type SchemaDefinition = (
    ColumnDefinition | Comment | ForeignKey | Index | PrimaryKey | Unique
)
```

#### schema/foreign.py

Fuente: [orionis/database/schema/foreign.py](../schema/foreign.py).

`ForeignKey`

```python
class ForeignKey:
```

`ForeignKey.__init__`

```python
def __init__(
    self,
    column: str,
    ref_table: str,
    ref_column: str,
    name: str | None = None,
) -> None:
```

#### schema/index.py

Fuente: [orionis/database/schema/index.py](../schema/index.py).

`Index`

```python
class Index:
```

`Index.__init__`

```python
def __init__(
    self,
    *columns: str,
    name: str | None = None,
    unique: bool = False,
) -> None:
```

#### schema/primary.py

Fuente: [orionis/database/schema/primary.py](../schema/primary.py).

`PrimaryKey`

```python
class PrimaryKey:
```

`PrimaryKey.__init__`

```python
def __init__(self, *columns: str) -> None:
```

#### schema/schema.py

Fuente: [orionis/database/schema/schema.py](../schema/schema.py).

`Schema`

```python
class Schema(ISchema):

    # ruff: noqa: TC001
```

`Schema fields`

```python
__slots__ = (
        "__conn_manager", "__connection_name", "__connection_selected",
    )
```

`Schema.__init__`

```python
def __init__(self, conn_manager: IConnectionManager) -> None:
```

`Schema.connection`

```python
def connection(self, name: str | None = None) -> Self:
```

`Schema.create`

```python
def create(self, name: str) -> TableCreation:
```

`Schema.createFromDefinition`

```python
async def createFromDefinition(self, definition: TableDefinition) -> bool:
```

`Schema.createFromModel`

```python
async def createFromModel(self, model: type[Model]) -> bool:
```

`Schema.drop`

```python
async def drop(self, name: str) -> bool:
```

#### schema/table_creation.py

Fuente: [orionis/database/schema/table_creation.py](../schema/table_creation.py).

`TableCreation`

```python
class TableCreation:
```

`TableCreation fields`

```python
__slots__ = ("__blueprint", "__name", "__schema")
```

`TableCreation.__init__`

```python
def __init__(
    self,
    schema: Schema,
    name: str,
) -> None:
```

`TableCreation.__aenter__`

```python
async def __aenter__(self) -> Blueprint:
```

`TableCreation.__aexit__`

```python
async def __aexit__(
    self,
    exc_type: type[BaseException] | None,
    exc: BaseException | None,
    traceback: TracebackType | None,
) -> bool:
```

#### schema/timestamp.py

Fuente: [orionis/database/schema/timestamp.py](../schema/timestamp.py).

`Timestamps`

```python
class Timestamps:
```

`Timestamps.__init__`

```python
def __init__(self, *, timezone: bool = True) -> None:
```

#### schema/unique.py

Fuente: [orionis/database/schema/unique.py](../schema/unique.py).

`Unique`

```python
class Unique:
```

`Unique.__init__`

```python
def __init__(self, *columns: str, name: str | None = None) -> None:
```

#### schema_provider.py

Fuente: [orionis/database/schema_provider.py](../schema_provider.py).

`SchemaProvider`

```python
class SchemaProvider(ServiceProvider):
```

`SchemaProvider.register`

```python
def register(self) -> None:
```

#### seeders/__init__.py

Fuente: [orionis/database/seeders/__init__.py](../seeders/__init__.py).

`__all__`

```python
__all__ = ["Seeder", "SeederEvents", "SeederRunner"]
```

#### seeders/events.py

Fuente: [orionis/database/seeders/events.py](../seeders/events.py).

`SeederEvents`

```python
from orionis.database.migrations.events import MigrationEvents as SeederEvents
```

`__all__`

```python
__all__ = ["NO_EVENTS", "SeederEvents"]
```

#### seeders/runner.py

Fuente: [orionis/database/seeders/runner.py](../seeders/runner.py).

`SeederRunner`

```python
class SeederRunner:
```

`SeederRunner fields`

```python
__slots__ = ("__app", "__conn_manager", "__discovered_cache")
```

`SeederRunner.__init__`

```python
def __init__(
    self,
    app: IApplication,
    conn_manager: IConnectionManager,
) -> None:
```

`SeederRunner.seed`

```python
async def seed(
    self,
    *,
    connection: str | None = None,
    events: SeederEvents | None = None,
) -> list[str]:
```

#### seeders/seeder.py

Fuente: [orionis/database/seeders/seeder.py](../seeders/seeder.py).

`Seeder`

```python
class Seeder(ABC):
```

`Seeder fields`

```python
__slots__ = ()
```

`Seeder.run`

```python
@abstractmethod
async def run(self) -> None:
```

#### transaction.py

Fuente: [orionis/database/transaction.py](../transaction.py).

`Transaction`

```python
class Transaction(ITransaction):
```

`Transaction fields`

```python
__slots__ = ("_connection",)
```

`Transaction.__init__`

```python
def __init__(self, connection: IConnection) -> None:
```

`Transaction.__aenter__`

```python
async def __aenter__(self) -> ITransaction:
```

`Transaction.__aexit__`

```python
async def __aexit__(
    self,
    exc_type: type[BaseException] | None,
    exc: BaseException | None,
    traceback: TracebackType | None,
) -> bool:
```

#### schema/blueprint.pyi

Fuente: [orionis/database/schema/blueprint.pyi](../schema/blueprint.pyi). Referencia para editor/type-checker, no código runtime ejecutable.

```python
from orionis.database.schema.comment import Comment
from orionis.database.schema.foreign import ForeignKey
from orionis.database.schema.index import Index
from orionis.database.schema.primary import PrimaryKey
from orionis.database.schema.unique import Unique
from orionis.orm.schema.column import ColumnDefinition
from orionis.orm.schema.types import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Double,
    Enum,
    Float,
    Integer,
    Interval,
    LargeBinary,
    MatchType,
    Numeric,
    NumericCommon,
    PickleType,
    SchemaType,
    SmallInteger,
    String,
    StrictArray,
    StrictBigInt,
    StrictBinary,
    StrictBlob,
    StrictChar,
    StrictClob,
    StrictDecimal,
    StrictDoublePrecision,
    StrictInt,
    StrictJson,
    StrictNChar,
    StrictNVarChar,
    StrictReal,
    StrictSmallInt,
    StrictTimestamp,
    StrictVarBinary,
    StrictVarChar,
    Text,
    Time,
    Unicode,
    UnicodeText,
    Uuid,
)

class Blueprint:

    def id(self, name: str = "id") -> BigInteger:
        ...

    def bigInteger(self, name: str) -> BigInteger:
        ...

    def boolean(
        self,
        name: str,
        *,
        create_constraint: bool = False,
        constraint_name: str | None = None,
    ) -> Boolean:
        ...

    def date(self, name: str) -> Date:
        ...

    def dateTime(self, name: str, *, timezone: bool = False) -> DateTime:
        ...

    def double(
        self,
        name: str,
        precision: int | None = None,
        *,
        asdecimal: bool = False,
        decimal_return_scale: int | None = None,
    ) -> Double:
        ...

    def enum(
        self,
        name: str,
        *enums: str,
        constraint_name: str | None = None,
        create_constraint: bool = False,
        native_enum: bool = True,
        length: int | None = None,
        validate_strings: bool = False,
    ) -> Enum:
        ...

    def float(
        self,
        name: str,
        precision: int | None = None,
        *,
        asdecimal: bool = False,
        decimal_return_scale: int | None = None,
    ) -> Float:
        ...

    def integer(self, name: str) -> Integer:
        ...

    def interval(
        self,
        name: str,
        *,
        native: bool = True,
        second_precision: int | None = None,
        day_precision: int | None = None,
    ) -> Interval:
        ...

    def largeBinary(self, name: str, length: int | None = None) -> LargeBinary:
        ...

    def matchType(self, name: str) -> MatchType:
        ...

    def numeric(
        self,
        name: str,
        precision: int | None = None,
        scale: int | None = None,
        decimal_return_scale: int | None = None,
        *,
        asdecimal: bool = True,
    ) -> Numeric:
        ...

    def numericCommon(self, name: str) -> NumericCommon:
        ...

    def pickleType(
        self,
        name: str,
        protocol: int = 5,
        pickler: object | None = None,
        impl: object | None = None,
    ) -> PickleType:
        ...

    def schemaType(
        self,
        name: str,
        schema_name: str | None = None,
    ) -> SchemaType:
        ...

    def smallInteger(self, name: str) -> SmallInteger:
        ...

    def string(
        self,
        name: str,
        length: int | None = 255,
        collation: str | None = None,
    ) -> String:
        ...

    def text(
        self,
        name: str,
        length: int | None = None,
        collation: str | None = None,
    ) -> Text:
        ...

    def time(self, name: str) -> Time:
        ...

    def unicode(
        self,
        name: str,
        length: int | None = None,
        collation: str | None = None,
    ) -> Unicode:
        ...

    def unicodeText(
        self,
        name: str,
        length: int | None = None,
        collation: str | None = None,
    ) -> UnicodeText:
        ...

    def uuid(
        self,
        name: str,
        *,
        as_uuid: bool = True,
        native_uuid: bool = True,
    ) -> Uuid:
        ...

    def strictArray(
        self,
        name: str,
        item_type: ColumnDefinition,
        *,
        as_tuple: bool = False,
        dimensions: int | None = None,
        zero_indexes: bool = False,
    ) -> StrictArray:
        ...

    def strictBigInt(self, name: str) -> StrictBigInt:
        ...

    def strictBinary(
        self,
        name: str,
        length: int | None = None,
    ) -> StrictBinary:
        ...

    def strictBlob(self, name: str, length: int | None = None) -> StrictBlob:
        ...

    def strictChar(
        self,
        name: str,
        length: int | None = None,
        collation: str | None = None,
    ) -> StrictChar:
        ...

    def strictClob(
        self,
        name: str,
        length: int | None = None,
        collation: str | None = None,
    ) -> StrictClob:
        ...

    def strictDecimal(
        self,
        name: str,
        precision: int | None = 10,
        scale: int | None = 2,
        decimal_return_scale: int | None = None,
        *,
        asdecimal: bool = True,
    ) -> StrictDecimal:
        ...

    def strictDoublePrecision(
        self,
        name: str,
        precision: int | None = None,
        *,
        asdecimal: bool = False,
        decimal_return_scale: int | None = None,
    ) -> StrictDoublePrecision:
        ...

    def strictInt(self, name: str) -> StrictInt:
        ...

    def strictJson(
        self,
        name: str,
        *,
        none_as_null: bool = False,
    ) -> StrictJson:
        ...

    def strictNChar(
        self,
        name: str,
        length: int | None = None,
        collation: str | None = None,
    ) -> StrictNChar:
        ...

    def strictNVarChar(
        self,
        name: str,
        length: int | None = None,
        collation: str | None = None,
    ) -> StrictNVarChar:
        ...
    def strictReal(
        self,
        name: str,
        precision: int | None = None,
        *,
        asdecimal: bool = False,
        decimal_return_scale: int | None = None,
    ) -> StrictReal:
        ...

    def strictSmallInt(self, name: str) -> StrictSmallInt:
        ...

    def strictTimestamp(
        self,
        name: str,
        *,
        timezone: bool = False,
    ) -> StrictTimestamp:
        ...

    def strictVarBinary(
        self,
        name: str,
        length: int | None = None,
    ) -> StrictVarBinary:
        ...

    def strictVarChar(
        self,
        name: str,
        length: int | None = 255,
        collation: str | None = None,
    ) -> StrictVarChar:
        ...

    def timestamps(self, *, timezone: bool = False) -> None:
        ...

    def comment(self, text: str) -> Comment:
        ...

    def foreignKey(
        self,
        column: str,
        ref_table: str,
        ref_column: str,
        name: str | None = None,
    ) -> ForeignKey:
        ...

    def index(
        self,
        *columns: str,
        name: str | None = None,
        unique: bool = False,
    ) -> Index:
        ...

    def primaryKey(self, *columns: str) -> PrimaryKey:
        ...

    def unique(self, *columns: str, name: str | None = None) -> Unique:
        ...
```

## Ejemplos de uso

Ejecute cada bloque independientemente con Orionis/core sobre Python 3.14+.
Las verificaciones usaron checkout local, bytecode desactivado, procesos
separados, cwd/recursos temporales y barreras contra escrituras externas o
conexiones de servicios. No se usó DB/bootstrap del checkout ni servidor externo.
Los bloques de referencia/stub anteriores no son estos scripts.

### 1. Ejecutar SQL raw y planes CRUD en SQLite

Se esperan ID generado de una fila, diccionarios materializados, batch sin
ID único y update/delete/scalar mediante planes.

```python
import asyncio
from orionis.database.connection import Connection
from orionis.database.schema.column import Column
from orionis.orm.query.expressions import (
    AggregateClause,
    AggregateFunction,
    DeletePlan,
    InsertPlan,
    SelectPlan,
    UpdatePlan,
    WhereClause,
)
from orionis.orm.schema.table import TableDefinition

async def main() -> None:
    connection = Connection("local", {"driver": "sqlite", "database": ":memory:"})
    table = TableDefinition("entries", {
        "id": Column.id(), "label": Column.string("label"),
    })
    try:
        assert await connection.createTable(table)
        result = await connection.insert(InsertPlan(table, [{"label": "first"}]))
        assert isinstance(result.last_insert_id, int) and result.row_count == 1
        batch = await connection.insert(InsertPlan(table, [
            {"label": "second"}, {"label": "third"},
        ]))
        assert batch.last_insert_id is None and batch.row_count == 2
        assert await connection.select(
            "SELECT label FROM entries WHERE label=:label", {"label": "first"},
        ) == [{"label": "first"}]
        where = [WhereClause("label", value="second")]
        assert await connection.update(UpdatePlan(table, {"label": "updated"},
                                                   wheres=where)) == 1
        assert await connection.delete(DeletePlan(
            table, wheres=[WhereClause("label", value="third")],
        )) == 1
        count = SelectPlan(table, aggregate=AggregateClause(AggregateFunction.COUNT))
        assert await connection.scalar(count) == 2
    finally:
        await connection.disconnect()

asyncio.run(main())
```

### 2. Administrar configuración y manejar errores reales de query

Se espera identidad cacheada hasta disconnect del manager, mapping vivo sin
reemplazar Connection existente y QueryException sanitizada para SQL ausente.

```python
import asyncio
from orionis.database.connection_manager import ConnectionManager
from orionis.database.exceptions import (
    ConnectionNotFoundException,
    QueryException,
    UnsupportedDriverException,
)

class Settings:
    def config(self, key: str) -> dict:
        assert key == "database"
        return {"default": "sqlite", "connections": {
            "sqlite": {"driver": "sqlite", "database": ":memory:"},
        }}

async def main() -> None:
    manager = ConnectionManager(Settings())
    first = manager.connection()
    assert first is manager.connection("sqlite")
    manager.addConnection("sqlite", {"driver": "sqlite", "database": ":memory:"})
    manager.configFor()["prefix"] = "local_"
    assert manager.connection() is first
    try:
        await first.select("SELECT :value FROM missing_table", {"value": "private"})
    except QueryException as error:
        assert "private" not in str(error) and "missing_table" not in str(error)
        assert error.__suppress_context__
    else:
        raise AssertionError("Missing table query succeeded")
    try:
        manager.connection("absent")
    except ConnectionNotFoundException:
        pass
    else:
        raise AssertionError("Unknown connection was accepted")
    manager.addConnection("bad", {"driver": "unsupported"})
    try:
        manager.connection("bad")
    except UnsupportedDriverException:
        pass
    else:
        raise AssertionError("Unsupported driver was accepted")
    await manager.disconnect("sqlite")
    assert manager.connection() is not first
    await manager.disconnect()

asyncio.run(main())
```

### 3. Anidar savepoints y respetar la tarea propietaria

Se espera rollback solo del savepoint interno al fallar, commit externo y
rechazo de query hija mientras la transacción propietaria está activa.

```python
import asyncio
from orionis.database.connection import Connection
from orionis.database.exceptions import TransactionException
from orionis.database.transaction import Transaction

async def main() -> None:
    connection = Connection("local", {"driver": "sqlite", "database": ":memory:"})
    try:
        await connection.statement("CREATE TABLE entries (label TEXT NOT NULL)")
        async with connection.transaction() as transaction:
            assert isinstance(transaction, Transaction)
            await connection.execute("INSERT INTO entries VALUES (:label)",
                                     {"label": "outer"})
            try:
                async with connection.transaction():
                    await connection.execute("INSERT INTO entries VALUES (:label)",
                                             {"label": "inner"})
                    raise ValueError("rollback inner savepoint")
            except ValueError:
                pass
            try:
                await asyncio.create_task(connection.select("SELECT 1"))
            except TransactionException:
                pass
            else:
                raise AssertionError("A child used its parent's transaction")
            assert connection.inTransaction()
        assert not connection.inTransaction()
        assert await connection.select("SELECT label FROM entries") == [
            {"label": "outer"},
        ]
    finally:
        if connection.inTransaction():
            await connection.rollback()
        await connection.disconnect()

asyncio.run(main())
```

### 4. Inspeccionar dialectos y compilar sin servidor

Se esperan URL/opciones sin conectar, predicados bound y QueryException
para una factory sin mapping de compilador.

```python
from sqlalchemy.dialects import sqlite
from orionis.database.compiler import SQLCompiler
from orionis.database.dialect import (
    build_engine_url,
    engine_options,
    missing_dependency_error,
    resolve_driver,
)
from orionis.database.exceptions import (
    MissingDatabaseDependencyException,
    QueryException,
)
from orionis.database.schema.column import Column
from orionis.orm.query.expressions import SelectPlan, WhereClause
from orionis.orm.schema.table import TableDefinition

config = {"driver": " SQLITE ", "database": ":memory:"}
assert resolve_driver(config) == "sqlite"
assert build_engine_url(config).drivername == "sqlite+aiosqlite"
assert build_engine_url(config, sync=True).drivername == "sqlite"
options = engine_options(config)
assert options["pool_size"] == 1 and options["max_overflow"] == 0
error = missing_dependency_error("mysql", ModuleNotFoundError("local probe"))
assert isinstance(error, MissingDatabaseDependencyException)
table = TableDefinition("entries", {"id": Column.integer("id")})
compiler = SQLCompiler(prefix="local_")
statement = compiler.compileSelect(SelectPlan(
    table, columns=("id",), wheres=[WhereClause("id", value=7)],
))
rendered = statement.compile(dialect=sqlite.dialect())
assert "local_entries" in str(rendered) and 7 in rendered.params.values()
try:
    compiler.compileCreateTable(TableDefinition("unsupported", {
        "value": Column.matchType("value"),
    }))
except QueryException:
    pass
else:
    raise AssertionError("An unmapped logical type compiled successfully")
```

### 5. Recoger un schema y abortar una declaración excepcional

Se espera tabla/índice local, referencias conservadas en Blueprint, ausencia
de tabla tras excepción y rechazo de selección repetida de conexión.

```python
import asyncio
from orionis.database.connection_manager import ConnectionManager
from orionis.database.schema.schema import Schema

class Settings:
    def config(self, key: str) -> dict:
        assert key == "database"
        return {"default": "sqlite", "connections": {
            "sqlite": {"driver": "sqlite", "database": ":memory:"},
        }}

async def main() -> None:
    manager = ConnectionManager(Settings())
    schema = Schema(manager)
    try:
        async with schema.create("entries") as table:
            table.id()
            label = table.string("label").nullable()
            table.index("label", name="entries_label_index")
            table.timestamps()
            assert label is table.columns()[1]
            assert len(table.definitions()) == 5
        await manager.connection().execute(
            "INSERT INTO entries (label) VALUES (:label)", {"label": "created"},
        )
        assert await manager.connection().select("SELECT label FROM entries") == [
            {"label": "created"},
        ]
        try:
            async with schema.create("aborted") as table:
                table.id()
                raise LookupError("abort declaration")
        except LookupError:
            pass
        assert await manager.connection().select(
            "SELECT name FROM sqlite_master WHERE name=:name", {"name": "aborted"},
        ) == []
        schema.connection(None)
        try:
            schema.connection("sqlite")
        except ValueError:
            pass
        else:
            raise AssertionError("Schema connection selection was overwritten")
    finally:
        await manager.disconnect()

asyncio.run(main())
```

### 6. Compartir definición de tabla con un modelo ORM real

Se espera usar la misma definición creada por Schema y la integración real
ConnectionManager/ConnectionResolver. Se restaura el resolver incluso si
inicialmente no había manager.

```python
import asyncio
from typing import ClassVar
from orionis.database.connection_manager import ConnectionManager
from orionis.database.schema.column import Column
from orionis.database.schema.schema import Schema
from orionis.orm.exceptions import OrmConfigurationException
from orionis.orm.model import Model
from orionis.orm.resolver import ConnectionResolver
from orionis.orm.schema.table import TableDefinition

ENTRY_V1 = TableDefinition("entries", {
    "id": Column.id(), "label": Column.string("label"),
})

class Entry(Model):
    table_definition = ENTRY_V1
    timestamps = False
    fillable: ClassVar[list[str]] = ["label"]

class Settings:
    def config(self, key: str) -> dict:
        assert key == "database"
        return {"default": "sqlite", "connections": {
            "sqlite": {"driver": "sqlite", "database": ":memory:"},
        }}

async def main() -> None:
    try:
        previous = ConnectionResolver.manager()
    except OrmConfigurationException:
        previous = None
    manager = ConnectionManager(Settings())
    ConnectionResolver.setManager(manager)
    try:
        schema = Schema(manager)
        assert await schema.createFromDefinition(ENTRY_V1)
        entry = await Entry.create({"label": "integrated"})
        found = await Entry.find(entry.id)
        assert found is not None and found.label == "integrated"
        assert await schema.createFromModel(Entry)
    finally:
        if previous is None:
            ConnectionResolver.clear()
        else:
            ConnectionResolver.setManager(previous)
        await manager.disconnect()

asyncio.run(main())
```

### 7. Descubrir, migrar, seedear y reconstruir una aplicación temporal

Es integración completa de filesystem/contenedor, no migración del checkout.
Se espera una ejecución, sin repetir seed, tracking confirmado y limpieza
del historial seeder tras rollback completo antes de replay.

```python
import asyncio
import logging
import os
import sys
import tempfile
from pathlib import Path

previous = Path.cwd()
old_path = sys.path.copy()
with tempfile.TemporaryDirectory(prefix="database-lifecycle-") as directory:
    root = Path(directory)
    os.chdir(root)
    sys.path.insert(0, str(root))
    try:
        from orionis.database.contracts.connection_manager import IConnectionManager
        from orionis.database.migrations.events import MigrationEvents
        from orionis.database.migrations.migrator import Migrator
        from orionis.database.seeders.runner import SeederRunner
        from orionis.foundation.application import Application

        migrations = root / "local_migrations"
        seeders = root / "local_seeders"
        migrations.mkdir()
        seeders.mkdir()
        migration_source = (
            "from orionis.database.contracts.migration import Migration\n"
            "from orionis.database.contracts.schema import ISchema\n"
            "class CreateEntries(Migration):\n"
            "    def __init__(self, schema: ISchema) -> None:\n"
            "        self.schema = schema\n"
            "    async def up(self) -> None:\n"
            "        async with self.schema.create('entries') as table:\n"
            "            table.id()\n"
            "            table.string('label')\n"
            "    async def down(self) -> None:\n"
            "        await self.schema.drop('entries')\n"
        )
        seeder_source = (
            "from orionis.database.seeders.seeder import Seeder\n"
            "from orionis.orm.resolver import ConnectionResolver\n"
            "class SeedEntries(Seeder):\n"
            "    async def run(self) -> None:\n"
            "        await ConnectionResolver.connection().execute(\n"
            "            'INSERT INTO entries (label) VALUES (:label)',\n"
            "            {'label': 'seeded'},\n"
            "        )\n"
        )
        compile(migration_source, "m001.py", "exec")
        compile(seeder_source, "s001.py", "exec")
        (migrations / "m001.py").write_text(migration_source, encoding="utf-8")
        (seeders / "s001.py").write_text(seeder_source, encoding="utf-8")

        async def main() -> None:
            app = Application(base_path=root)
            app.withConfigPaths(database_migrations=migrations,
                                database_seeders=seeders)
            app.create()
            app.config("database", {"default": "sqlite", "connections": {
                "sqlite": {"driver": "sqlite", "database": str(root / "local.db")},
            }})
            await app.boot()
            manager = await app.make(IConnectionManager)
            try:
                migrator = Migrator(app, manager)
                runner = SeederRunner(app, manager)
                events = []
                reporter = MigrationEvents(on_start=events.append)
                assert await migrator.migrate(events=reporter) == ["m001"]
                assert events == ["m001"]
                assert await runner.seed() == ["s001"]
                assert await runner.seed() == []
                assert (await migrator.status())[0]["ran"]
                rows = await manager.connection().select("SELECT label FROM entries")
                assert rows == [
                    {"label": "seeded"},
                ]
                assert await migrator.rollback() == ["m001"]
                assert not (await migrator.status())[0]["ran"]
                assert await migrator.migrate() == ["m001"]
                assert await runner.seed() == ["s001"]
            finally:
                await manager.disconnect()

        asyncio.run(main())
    finally:
        logging.shutdown()
        sys.path[:] = old_path
        os.chdir(previous)
```

## Características de diseño

| Mecanismo observado | Consecuencia para el consumidor |
| --- | --- |
| Exports raíz y engines diferidos | Importar/construir difiere de resolver exports o conectar servicio. |
| Statements Core e IR del framework | Sin ORM Session; SQL emitido y soporte dependen del dialecto. |
| Slots en conexiones/managers/contextos/contratos | Almacenamiento fijo; marcadores sin slots conservan atributos públicos mutables. |
| InsertResult/MigrationEvents frozen | Guards generados, no validación/inmutabilidad profunda de IDs/callbacks. |
| Stack transaccional mutable de tarea | Savepoints reutilizan conexión; hijos no asumen propietario activo. |
| Blueprint mutable y wrappers cacheados | Snapshots retienen columnas; wrappers capturan collector/factory y efectos. |
| Caché discovery y stems únicos persistidos | Discovery una vez por runner; identidad de filename define tracking/ambigüedad. |
| Contexto de migración y claim seeder | Schema/ORM no cualificado usa conexión elegida; claim precede código seeder y tracking sigue migración. |

## Rendimiento y concurrencia

### Cachés y materialización

Fuentes: [connection.py](../connection.py), [manager](../connection_manager.py),
[compiler](../compiler.py), [Blueprint](../schema/blueprint.py),
[Migrator](../migrations/migrator.py), [SeederRunner](../seeders/runner.py).
Texto raw tiene LRU(256) de módulo por SQL, no cachea bindings/valores.
Connection retiene compiler/engine y manager cachea objetos sin límite público.
Disconnect solo elimina entradas del manager si se llama en este; disponer
engine directo conserva definiciones.

Cachés compiler por instancia no acotados; columnas raw se añaden antes de
alias. La misma identidad puede conservar metadatos obsoletos. Blueprint
retiene listas/wrappers por nombre y entrega tuple snapshots superficiales.
Runners materializan tracking/pendientes y cachean mapas, también discovery
vacío. Callbacks/imports pueden retener estado externo.

select materializa mappings dentro de adquisición. Batch usa executemany
parametrizado solo cuando supportsBatchInsert acepta; expresiones SQL mantienen
VALUES explícito. No se hicieron benchmarks de tiempos, asignaciones,
throughput o complejidad portable para esta tarea.

### Transacciones y límites de concurrencia

SQLite memory usa una conexión pooled sin overflow, conservando una DB y
serializando transacciones independientes. Una tarea con la única conexión
retenida que solicita otro checkout puede esperar timeout del pool; este no
detecta deadlocks. Archivo/otros drivers tienen políticas reales, no esta
garantía especial memory.

Construcción engine, mutación manager/compiler y discovery no declaran
seguridad total cross-thread/loop. Crear engine inicialmente es síncrono antes
del primer await, pero compartirlo/raw connection entre loops no está
certificado. Disconnect/eliminación y callers concurrentes no se coordinan
como un mecanismo de leases.

Transacciones rechazan pertenencia activa heredada; cleanup extrae niveles
antes de commit/rollback y no usa shield. Fallos de cancelación/estado/recursos
se propagan. Vaciar caché/disponer engine no garantiza resolver transacción
activa. Callbacks de plan/default/DDL y drivers tienen límites bloqueantes propios.

Migraciones confirman por paso sin claim previo ni lock de todo el run.
Seeders usan claim único y transacción por paso, más reintento de creación
de tracking. No hacen exactly-once los efectos externos/resultados callback.
Batch concurrente y DDL dependen de DB; callbacks síncronos pueden fallar
antes, durante informe de rollback o después de commit.

## Notas de compatibilidad

El mínimo es Python >=3.14. Usa union/generics built-in, PEP 695 SchemaDefinition,
dataclass slots, ContextVar y contextos async. Anotar no valida en runtime;
nombres solo TYPE_CHECKING pueden no resolverse mediante evaluación arbitraria.
Se ejecutó **CPython 3.14.6 en Windows**, sin certificar otra plataforma/runtime.

| Dependencia | Rango declarado | Resolución lockfile | Versión instalada de validación |
| --- | --- | --- | --- |
| `sqlalchemy` | `>=2.0.54,<3.0` | `2.1.1` | `2.1.1` |
| `aiosqlite` | `>=0.22.1` | `0.22.1` | `0.22.1` |
| `apscheduler` | `>=3.11.3,<4.0` | `3.11.3` | `3.11.3` |
| `asyncpg` | `>=0.31.0` | `0.31.0` | `0.31.0` |
| `aiomysql` | `>=0.3.2` | `0.3.2` | No instalado |
| `pymysql` | `>=1.2.3` | `1.2.3` | No instalado |
| `psycopg2-binary` | `>=2.9.13` | `2.9.13` | No instalado |
| `oracledb` | `>=26.0.0` | `26.0.1` | No instalado |
| `aioodbc` | `>=0.5.0` | `0.5.0` | No instalado |
| `pyodbc` | `>=5.3.0` | `5.3.0` | No instalado |
| `ruff` | `>=0.16.8` | `0.16.9` | `0.16.9` |

Evidencia: [pyproject.toml](../../../pyproject.toml), [uv.lock](../../../uv.lock)
y metadatos instalados de esta ejecución. Paquete ausente puede tener resolución
lock, sin que su driver sea ejecutable. asyncpg está instalado, pero no se
usó PostgreSQL. Helpers sync preparan URL/opciones; Connection sigue async y
no existe scheduleTaskStore/sqlAlchemyJobStore en el manager inspeccionado.

Tipos no mapeados, opciones enum/pickle omitidas, DDL transaccional distinto,
ODBC y tracking prefix son límites explícitos, no portabilidad universal.
SQLite memory y awaitabilidad de TableCreation difieren de instrucciones
antiguas; prevalece la fuente.

## Verificación y limitaciones

### Inventario y pruebas

Se cubren 39 fuentes, 35 clases, 156 métodos públicos/especiales, nueve funciones,
un alias de tipo, 19 bloques de campos, ocho exports/constantes y el alias
importado explícito SeederEvents. Hay 229 bloques de referencia runtime más
el archivo de tipado Blueprint completo. Candidatos públicos se trazan a owners;
toolkit importado y alias TYPE_CHECKING quedan fuera de API runtime independiente.

TestingEngine/TestRunner nativos dieron **243/243 correctas**, sin fallos/errores
crudos ni omisiones, con Application temporal real booteada. Audit barrier
admitió solo temporal propio y socketpair interno asyncio Windows, sin operaciones
bloqueadas en el run correcto. El primero tuvo 242 correctas y un fallo:
discovery admin esperaba Path.cwd()/database/seeders ausente en sandbox.
Se suministró copia temporal y pasó toda la suite. Se conserva el fallo inicial;
no se corrigió fuente/test ni se omitió silenciosamente.

Probes locales verificaron retorno/commit/rollback Transaction, alias
SeederEvents, TableCreation no-awaitable y QueryException con prefix de
migraciones no vacío. Tras la suite, comparación hash/mtime completa encontró
solo el README autorizado, sin artefactos externos.

### Estado de ejemplos y documentos

| Ejemplo | Sintaxis | Imports locales | Ejecución |
| --- | --- | --- | --- |
| 1 | Correcta | Correctos | Ejecutado correctamente. |
| 2 | Correcta | Correctos | Ejecutado correctamente. |
| 3 | Correcta | Correctos | Ejecutado correctamente. |
| 4 | Correcta | Correctos | Ejecutado correctamente. |
| 5 | Correcta | Correctos | Ejecutado correctamente. |
| 6 | Correcta | Correctos | Ejecutado correctamente. |
| 7 | Correcta | Correctos | Ejecutado correctamente. |

Ambos manuales tienen 79 encabezados equivalentes y 237 bloques idénticos byte
a byte. Las 229 referencias runtime y el stub completo coinciden con la fuente;
210 candidatos públicos están mapeados a su grupo. Siete ejemplos por idioma
pasaron sintaxis, imports locales reales y ejecución independiente. Se comprobaron
137 enlaces relativos/anclas por manual y 22 del skill. Su YAML solo tiene
name/description y nombre derivado orionis-database. Ruff acotado a
orionis/database y tests/database pasó sin fixes/caché; el editor no informa
errores en los tres entregables.

La comparación completa del baseline incluye ocultos, ignorados, no versionados,
fuentes/pruebas/configuración/dependencias, directorios, docs previos, índice
Git y HEAD. Las escrituras documentales apuntan solo al docs directo del módulo.
Scripts/resultados/cachés/DB y recursos temporales quedan fuera del repositorio.
No se eliminó contenido adicional; quedan exactamente README.md, README.es.md
y SKILL.md, sin subdirectorios ni artefactos.

### Límites restantes

Sanitizar queries corresponde a errores capturados específicos, no a toda
excepción. Pertenencia de transacción, pool memory, factories no soportadas,
alias de eventos, semántica fresh y tracking prefix se documentan desde sus
owners. DDL/efectos externos no admiten garantía transaccional universal.
Esta tarea no cambió fuentes, formateó automáticamente, instaló dependencias,
hizo benchmarks ni editó índice Git.

> ⚠️ No especificado en el código fuente: seguridad de todo el módulo cross-thread/loop, reemplazo/disposición de conexiones atómico con operaciones en vuelo o rollback universal de efectos externos de migraciones/seeders.

> ⚠️ No ejecutado en este entorno: servidores MySQL/PostgreSQL/Oracle/SQL Server reales, ODBC/permisos/DDL de despliegue, ejecución Linux/macOS/free-threaded o versiones Python distintas de 3.14.6.

# Motores y operación en producción

La API de consultas es común, pero no todos los motores ofrecen las mismas capacidades. Usa tipos y operaciones compatibles con el destino y verifica migraciones contra ese motor. SQLite es útil para ejemplos aislados; no demuestra comportamiento de locks, identidades o DDL de un servidor diferente.

## Conexiones de servidor

PostgreSQL aplica `charset`, `search_path` y `sslmode` a sus rutas async y sync. La primera usa `asyncpg`; la segunda, utilizada también por el job store del scheduler, usa `psycopg2`. El search path no debe perderse al configurar tareas persistentes. MySQL expone charset, collation, modo estricto y engine. Oracle permite servicio, SID, DSN o TNS; SQL Server requiere un driver ODBC disponible en el sistema además del extra Python.

Las opciones TLS tienen consecuencias reales. La plantilla de SQL Server incluye `DB_TRUST_SERVER_CERTIFICATE=True`; adapta ese valor a tu política de validación de certificados antes de producción. No publiques credenciales en manuales de aplicación, logs ni repositorios. Las opciones de pool dependen del dialecto y configuración efectiva; no presupongas variables `DB_POOL_*` inexistentes.

Orionis abre las conexiones MySQL en UTC. Las columnas nuevas de tipo `DateTime` y `StrictTimestamp` se crean como `DATETIME(6)` y `TIMESTAMP(6)` para conservar microsegundos. En tablas existentes que usan precisión de segundos, prepara una migración explícita a precisión 6 conservando nulabilidad, valores predeterminados, claves y cláusulas de actualización. Las fracciones descartadas por el esquema anterior no se pueden recuperar.

En Oracle, `StrictTimestamp(timezone=True)` usa `TIMESTAMP WITH TIME ZONE`. Las inserciones, actualizaciones y condiciones sobre columnas tipadas envían el instante en UTC y conservan los microsegundos. Las lecturas tipadas extraen UTC incluso cuando otro cliente guardó un desplazamiento distinto. El ORM muestra las marcas de tiempo gestionadas y los atributos con conversión a fecha y hora en la zona de la aplicación. En consultas SQL escritas a mano, usa `SYS_EXTRACT_UTC(columna)` cuando necesites obtener el valor UTC.

Una versión anterior de Orionis podía guardar la hora UTC con el desplazamiento de una sesión Oracle configurada en otra zona. Para revisar marcas históricas de esas sesiones, compara el instante UTC almacenado con la hora original del evento antes de corregir las filas afectadas. Otros clientes pueden haber escrito marcas válidas con ese mismo desplazamiento.

Las columnas `DateTime` de Oracle, incluidas las declaradas con `DateTime(timezone=True)`, conservan el tipo `DATE` y su precisión de segundos. En estas columnas las marcas de tiempo gestionadas guardan la hora UTC y las conversiones personalizadas guardan la hora local de la aplicación. Las filas existentes conservan su interpretación.

## Amazon Redshift

Redshift utiliza el conector oficial `redshift-connector` y `sqlalchemy-redshift`; no se trata como PostgreSQL a través de asyncpg. Configuración básica:

```dotenv
DB_CONNECTION=redshift
DB_HOST=warehouse.example.test
DB_PORT=5439
DB_DATABASE=dev
DB_USERNAME=app_user
DB_PASSWORD=replace-with-secret
DB_REDSHIFT_SSL=True
DB_REDSHIFT_SSLMODE=verify-full
DB_REDSHIFT_TIMEOUT=30
```

`verify-full` es el valor predeterminado; también se admite `verify-ca`. `DB_REDSHIFT_TIMEOUT=null` desactiva el timeout de socket. IAM añade `DB_REDSHIFT_IAM`, `DB_REDSHIFT_REGION`, `DB_REDSHIFT_CLUSTER_IDENTIFIER`, `DB_REDSHIFT_DB_USER` y opcionalmente `DB_REDSHIFT_PROFILE`. Sin perfil explícito, el conector usa su cadena de credenciales. Serverless añade `DB_REDSHIFT_IS_SERVERLESS`, `DB_REDSHIFT_SERVERLESS_WORK_GROUP` y `DB_REDSHIFT_SERVERLESS_ACCT_ID`.

El conector es síncrono; Orionis ejecuta conexión, queries, resultados y control transaccional en un worker reservado por conexión Core adquirida. Consultas independientes pueden utilizar distintos workers; una transacción conserva el suyo. Cancelar espera la operación en curso antes de limpiar recursos y no garantiza cancelar trabajo en el servidor.

| Capacidad Redshift | Consecuencia |
|---|---|
| Sin savepoints | No anidar transacciones. |
| Sin locks de fila SELECT | `lockForUpdate()` y `sharedLock()` fallan con `QueryException` al ejecutar, también en planes anidados/agregados. |
| Sin DML `RETURNING` | Una identidad generada omitida no se devuelve en `last_insert_id`. |
| `IDENTITY(1,1)` | `autoIncrement()` puede crear identidad nativa, pero un modelo que necesite conocer su clave debe usar una clave generada por el cliente. |
| Sin índices tradicionales | Evitar declaraciones de índices. |
| PK/unique/FK informativas | No basar exclusión mutua o unicidad en esas declaraciones. |

`supportsUniqueConstraints()` devuelve `False`. Cache database, sesiones database, colas database, seeders registrados y job store database del scheduler rechazan Redshift: necesitan unicidad impuesta y, en el scheduler, índices. Estas restricciones no impiden usar Redshift para consultas analíticas y modelos compatibles.

## Diagnóstico, recursos y volumen

`db:show`, `db:table` y `db:wipe` conocen catálogos de Redshift y nombres calificados. Las métricas de tamaño usan bloques asignados de 1 MB; permisos limitados o tablas vacías pueden dejar tamaño desconocido. Las restricciones mostradas son declaraciones, no garantías de enforcement.

Los engines son perezosos y reutilizables. Cierra una conexión directa cuando termines; deja que el ciclo de aplicación cierre las conexiones administradas. `disconnect(name=None)` del gestor cierra todas las cacheadas; con nombre, solamente la seleccionada. No desconectes un servicio compartido mientras otras tareas lo usan.

Al cerrar todas las conexiones administradas, el gestor intenta cerrar cada conexión cacheada aunque una falle. Conserva la cancelación si existe o, en su ausencia, el primer fallo de cierre, y comunica los adicionales al sistema central. Los cierres concurrentes de una conexión bloqueante adquirida o de su worker comparten la finalización y esperan la limpieza por cancelación antes de volver.

Las lecturas materializan resultados completos. Aplica filtros, selección de columnas y paginación; no diseñes un exportador masivo suponiendo streaming de cursores. Divide escrituras grandes y considera que cada lote ocupa memoria. Para errores, diferencia configuración/driver de SQL fallido; conserva métricas de latencia, número de filas y operación de negocio sin exponer datos enlazados. No hay en esta capa garantía general de reintento automático de transacciones.

Las operaciones independientes usan contextos `engine.begin()` y liberan su conexión después de cada llamada; una transacción conserva la conexión hasta terminar sus niveles. El SQL crudo parseado se reutiliza con una caché LRU de 256 textos, sin convertir valores variables en SQL interpolado. En PostgreSQL, los inserts por lotes cuentan filas devueltas por `RETURNING`, incluidas las diferencias cuando un trigger omite una fila de entrada.

Las campañas con credenciales/servidores reales pertenecen a `tests/real_database`, un área local ignorada por Git, con configuración independiente de `.env`. Su existencia o referencias históricas no demuestran una ejecución actual. Cambiar `DB_CONNECTION` tampoco convierte los tests SQLite en pruebas de todos los motores. Valida por separado driver, SQL, DDL, tipos, cancelación y limpieza en cada destino.

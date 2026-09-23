# Límites de integración de base de datos

La referencia completa de modelos y consultas está en el
[manual ORM](../../orm/README.es.md). Esta nota registra las garantías usadas por
[Auth](../../auth/docs/README.es.md) y Session.

## Arquitectura

Modelos y consultas crudas comparten `QueryBuilderBase` y producen planes IR de
Orionis. `Connection` los pasa a `SQLCompiler` y al motor async de SQLAlchemy Core.
No se usan Session, modelos declarativos ni relaciones del ORM de SQLAlchemy.

Las conexiones vienen del resolver configurado. Transacciones son task-local y
las anidadas usan SAVEPOINT. No ejecutar sentencias concurrentes mediante una
misma conexión transaccional heredada; tareas independientes necesitan sus propias
transacciones. Las pruebas concurrentes SQLite usan archivo, no `:memory:`.

## Persistencia Auth

Nombres de roles y permisos son únicos. Propietarios son pares tipo/clave con
claves textuales canónicas para enteros, strings y UUID. Pivotes tienen claves
primarias compuestas y FK restrictivas hacia roles y permisos. Borrar propietarios
permanentemente exige limpieza de aplicación: una FK polimórfica no puede apuntar
a una única tabla global de propietarios.

Permisos se cargan con un SELECT UNION. El compilador aplana operadores consecutivos
del mismo tipo y usa tablas derivadas para operadores mixtos, conservando el orden
sin paréntesis inválidos en SQLite. El aislamiento depende del motor configurado;
esto no es una caché de permisos entre peticiones.

Las constraints únicas deciden duplicados del registrar. Los INSERT fallidos se
revierten localmente antes de recuperarlos para no dejar transacciones PostgreSQL
abortadas. Un INSERT schemaless puede no devolver su ID; Auth lo recupera mediante
el nombre o digest único cuando hace falta.

PAT almacena digest SHA-256, propietario, abilities y fechas. Uso y revocación son
UPDATE condicionales. Session SQL usa planes IR con prefijos y quoting del dialecto;
su `update()` condicional no recrea una sesión eliminada.

## Errores y migraciones

Los errores SQL exponen conexión y clase del error, no valores ni detalles del
driver. Se ocultan parámetros del motor y la cadena de excepción en el límite
público de consulta para reducir exposición de credenciales.

Modificar el código de una migración aplicada no la reejecuta. Tablas Auth existentes
requieren una migración revisada, o reconstrucción solo con datos desechables.
Respaldar datos antes de cambiar claves, restricciones o índices. Las pruebas de
auditoría aplican y revierten migraciones reales solo en bases temporales.

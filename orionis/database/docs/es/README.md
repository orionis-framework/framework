# Bases de datos

Orionis separa la construcción de consultas de su ejecución. El módulo `database` administra conexiones SQL con nombre, compila los planes del [ORM](../../../orm/docs/es/README.md), ejecuta SQL parametrizado y controla transacciones, esquemas, migraciones y seeders. No es necesario utilizar modelos para consultar una tabla.

Empieza con SQLite, incluido en la instalación base. Las operaciones que acceden a la base de datos son asíncronas; declarar columnas, elegir una conexión y construir una consulta son operaciones síncronas. Python 3.14 o posterior es obligatorio.

1. [Configurar conexiones y ejecutar SQL](connections.md): instalación de drivers, selección de conexión, parámetros y resultados.
2. [Transacciones y concurrencia](transactions.md): atomicidad, savepoints, propiedad de tareas y cancelación.
3. [Crear esquemas](schema.md): blueprints, restricciones y definiciones versionadas.
4. [Evolucionar y poblar la base de datos](migrations-and-seeders.md): migraciones, lotes, reversión y ejecución registrada de seeders.
5. [Motores y operación en producción](dialects-and-production.md): diferencias de dialecto, Redshift, seguridad y diagnóstico.

Una aplicación inicializada recibe los servicios mediante providers y puede usar las facades `DB` y `Schema`. Los ejemplos que construyen `Connection` directamente son programas independientes y cierran sus propios recursos. Los fragmentos con facades necesitan el arranque de [Foundation](../../../foundation/docs/es/README.md).

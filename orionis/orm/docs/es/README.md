# ORM y consultas

El ORM de Orionis combina modelos Active Record, consultas fluidas, relaciones y factories. Los modelos describen atributos y comportamiento; [Database](../../../database/docs/es/README.md) administra conexiones, compilación SQL y transacciones. El engine no forma parte de la API del modelo.

Las declaraciones y los builders son síncronos. Las operaciones que leen o escriben datos necesitan `await`. Antes de consultar, inicializa la aplicación y crea las tablas mediante migraciones; definir una clase no crea su tabla.

1. [Modelos, atributos y persistencia](models-and-attributes.md): definir una entidad, proteger entrada y guardar cambios.
2. [Consultar, actualizar y paginar](querying.md): modelos frente a tablas, filtros, joins, agregados y escrituras masivas.
3. [Relacionar y cargar modelos](relationships.md): relaciones simples, eager loading y tablas pivot.
4. [Eventos, scopes y soft deletes](events-and-scopes.md): comportamiento de dominio, políticas de consulta y eliminación lógica.
5. [Factories y pruebas](factories-and-testing.md): datos reproducibles, estados, secuencias y persistencia controlada.
6. [Tipos y restricciones del esquema](schema-and-type-reference.md): catálogo de tipos, modificadores, claves compuestas y definiciones compartidas.

Los ejemplos que solo declaran modelos o construyen planes no acceden a una base. Los ejemplos async con facades requieren bootstrap y tablas compatibles; cada capítulo explica esas condiciones. Python 3.14 o posterior es obligatorio.

El provider database instala un gestor en `ConnectionResolver`; consultar sin ese puente produce `OrmConfigurationException`. El ORM consume la configuración `database`, sin un archivo de configuración separado. `QueryBuilderProvider` registra el gateway singleton de `DB`; cada llamada de consulta crea su propio builder.

## Ejecución acotada y rendimiento

Usa `async for batch in Model.query().orderBy("id").chunks(1000): ...` para hidratar por lotes, o el mismo método en `DB.table(...)`. Cada lote recorre el `get()` habitual, incluidos scopes globales, eventos retrieved, casts y carga anticipada de relaciones. Respeta limit/offset existentes y no modifica la consulta original. `get()` sigue materializando el resultado completo por diseño.

Indica un orden determinista, preferiblemente único. La API pagina con LIMIT/OFFSET, por lo que las páginas profundas pueden costar más; las escrituras concurrentes pueden desplazar filas si la transacción envolvente no ofrece una instantánea consistente. No es un cursor de servidor. Cada lote libera el cursor/conexión antes de producirse, salvo una conexión perteneciente a la transacción del consumidor. Cierra el iterador al salir antes; retener lotes o relaciones numerosas sigue consumiendo memoria del consumidor.

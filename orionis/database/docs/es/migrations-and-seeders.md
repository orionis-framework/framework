# Evolucionar y poblar la base de datos

Las migraciones describen cambios ordenados de esquema. Los seeders insertan datos iniciales mediante clases independientes. Ambos se descubren en las rutas de aplicación `database_migrations` y `database_seeders`, normalmente `database/migrations` y `database/seeders`.

## Escribir una migración reversible

Cada archivo debe contener su subclase local de `Migration`; usa prefijos secuenciales con ceros para conservar orden lexicográfico. Los generadores de [consola](../../../console/docs/es/built-in-commands.md) crean archivos siguiendo las convenciones de la aplicación.

```python
from orionis.database import Migration
from orionis.support.facades import Schema


class CreateFlags(Migration):
    async def up(self) -> None:
        async with Schema.create("flags") as table:
            table.id()
            table.string("name", 80)
            table.unique("name")

    async def down(self) -> None:
        await Schema.drop("flags")
```

El migrador fija una conexión contextual durante cada operación; `Schema` y `DB` la respetan si no se selecciona otra explícitamente. Cada migración y su registro se ejecutan dentro de una transacción propia. La tabla `migrations` guarda nombre, lote y fecha. La atomicidad efectiva del DDL depende del motor; un fallo no debe interpretarse como garantía universal de reversión del esquema.

## Aplicar, inspeccionar y revertir

Ejecuta los comandos desde la raíz de la aplicación inicializada:

```shell
python reactor migrate:status
python reactor migrate
python reactor migrate:rollback --step 1
```

`--step` cuenta **lotes**, no archivos. Una invocación de `migrate` agrupa las migraciones pendientes en un nuevo lote; rollback revierte los últimos lotes y los archivos de cada lote en orden inverso.

| Operación | Comportamiento |
|---|---|
| `migrate` | Aplica pendientes en orden de nombre. |
| `migrate:status` | Muestra el estado de las migraciones descubiertas. |
| `migrate:rollback --step N` | Revierte los últimos N lotes. |
| `migrate:reset` | Revierte todas las aplicadas mediante `down`. |
| `migrate:refresh` | Revierte y vuelve a aplicar; admite selección de lotes. |
| `migrate:fresh` | Ejecuta reset mediante `down`, elimina los historiales y migra otra vez como primer lote. |

Los servicios equivalentes son `Migrator(app, manager).migrate(...)`, `.rollback(steps=1, ...)`, `.reset(...)`, `.refresh(steps=None, ...)`, `.fresh(...)` y `.status(...)`; todas son operaciones async. La selección `connection=` y `events=` se pasa por palabra clave donde corresponde. No ejecutes reset/fresh/refresh sobre datos que deban conservarse sin un plan de recuperación probado.

`fresh` no es una orden universal para borrar todas las tablas: revierte las migraciones registradas mediante sus propios `down`, elimina `migrations` y el historial `seeders`, y vuelve a aplicar. Tablas ajenas a ese flujo no se eliminan automáticamente. Una reversión que agota todas las migraciones aplicadas limpia también el historial de seeders; una reversión parcial lo conserva. Después de reconstruir por completo, `seed` puede volver a poblar los datos. El migrador no ejecuta seeders automáticamente.

## Añadir datos iniciales registrados

```python
from orionis.database import Seeder
from orionis.support.facades import DB


class DefaultFlags(Seeder):
    async def run(self) -> None:
        await DB.table("flags").insert({"name": "enabled"})
```

`python reactor seed` y `python reactor db:seed` ejecutan los seeders pendientes. El contenedor construye cada clase, permitiendo dependencias en su constructor. `SeederRunner.seed(*, connection=None, events=None)` devuelve los nombres completados en esta invocación.

El runner registra una identidad única por seeder en `seeders`, reclama su ejecución y confirma datos y registro en la misma transacción. Dos procesos concurrentes no deben ejecutar el mismo seeder registrado. La API actual no recibe un nombre de clase ni un parámetro `force`: no traslades esas opciones desde otros frameworks o documentación histórica. Para datos adicionales escribe un nuevo seeder; para regenerar datos de desarrollo estudia primero el efecto de reconstruir el esquema y su historial.

La identidad registrada es el nombre de archivo sin extensión, no el nombre de clase. Los archivos se ordenan lexicográficamente y cada uno debe definir una subclase local inequívoca. Renombrar un archivo ya ejecutado puede convertirlo en un seeder aparentemente nuevo: conserva las identidades desplegadas.

## Fallos y despliegue

La detección valida clases locales, duplicados y archivos; una migración registrada que falta puede producir `MigrationNotFoundException` al revertir. No renombres archivos ya aplicados. `MigrationEvents` y `SeederEvents` permiten informar inicio, éxito y fallo sin mezclar salida de consola con la lógica de datos.

El registro transaccional no convierte un envío de correo o una llamada externa en reversible. Mantén esos efectos fuera de los seeders registrados o diséñalos idempotentes. Redshift rechaza `SeederRunner.seed()` antes del acceso porque no impone restricciones únicas. Las [factories](../../../orm/docs/es/factories-and-testing.md) generan modelos; no sustituyen el historial de seeders ni abren una transacción para un lote.

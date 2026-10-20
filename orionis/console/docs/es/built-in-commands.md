# Comandos incluidos

El registro incluido se define en `orionis/console/core/commands.py`; la aplicación puede añadir comandos propios. Consulta `python reactor list` y la ayuda de cada firma antes de operaciones con efectos persistentes. Esta guía organiza el catálogo por tarea, no reemplaza los argumentos específicos de cada ayuda.

## Crear componentes

Los generadores `make:console-command`, `make:model`, `make:factory`, `make:job`, `make:mail`, generadores HTTP, providers, facades, servicios, contratos, tests y MCP utilizan stubs y rutas de aplicación. La firma de cada generador se puede consultar en `list`; no deduzcas opciones de comandos con nombres similares de otro framework.

```shell
python reactor make:job SendWelcomeEmail --help
python reactor make:factory ProductFactory --help
```

Generar un modelo no migra su tabla; generar un job no inicia workers. Revisa los imports, dependencias y configuración del componente generado antes de usarlo.

### Sockets y hubs de realtime

```shell
python -B reactor make:realtime-socket chat
python -B reactor make:realtime-hub chat
```

El primer comando crea `ChatSocket` en `app/realtime/sockets/chat_socket.py`; el segundo crea `ChatHub` en `app/realtime/hubs/chat_hub.py`. El socket es invocable, acepta la conexión, devuelve los mensajes de texto y gestiona desconexiones. El hub hereda de `Hub` e incluye un método `echo(message: str) -> str` expuesto con `@remote`.

Los generadores respetan las rutas configuradas `app_realtime_sockets` y `app_realtime_hubs`, crean subcarpetas, añaden el sufijo una sola vez y no sobrescriben archivos existentes. Por ejemplo, `make:realtime-hub rooms/chat_hub.py` crea `rooms/chat_hub.py` dentro de la ruta de hubs.

La generación no modifica rutas ni inicia conexiones. Registra las clases con `Route.websocket("/ws/chat", ChatSocket)` o `Route.hub("/realtime/chat", ChatHub)` en tus rutas WebSocket. Consulta [WebSocket](../../../http/docs/es/websockets.md) y [hubs](../../../realtime/docs/es/hubs-and-methods.md) para la integración y autorización.

## Restaurar configuración

`bootstrap:config [file]` restaura configuración faltante desde la rama `master` del skeleton oficial.

```shell
orionis bootstrap:config
orionis bootstrap:config app
```

Omite `file` para restaurar todos los archivos faltantes, o pasa el nombre de una configuración sin `.py` para restaurar solo ese archivo. Los nombres disponibles se consultan en el árbol remoto de `master`; un nombre desconocido produce un error con esas opciones. Los archivos existentes se conservan sin sobrescribirlos.

## Evolucionar datos

`migrate`, `migrate:status`, `migrate:rollback`, `migrate:reset`, `migrate:refresh`, `migrate:fresh`, `seed` y `db:seed` se explican en [migraciones y seeders](../../../database/docs/es/migrations-and-seeders.md). Comparten `--database`/`-d` para seleccionar conexión. Rollback `--step` cuenta lotes. `db:show` muestra información de la base; `db:table` inspecciona tablas; `db:wipe` elimina datos estructurales según su flujo y exige cuidado operativo.

```shell
python reactor migrate:status --database sqlite
python reactor db:show --help
python reactor db:table --help
```

No programes `migrate:fresh`, `db:wipe` ni `queue:clear` como mantenimiento rutinario de producción. Borran datos o trabajo pendiente; no equivalen a limpieza de registros completados.

## Servir, inspeccionar y probar

`serve` inicia el servidor de desarrollo según los argumentos disponibles; revisa [HTTP](../../../http/docs/es/README.md) para el ciclo web. `route:list` inspecciona rutas registradas. `test` ejecuta el sistema de pruebas de Orionis; su modo y selección pertenecen a [Testing](../../../test/docs/es/README.md). Las tareas de desarrollo y workers son procesos de larga duración: necesitan supervisión si se usan en un entorno operativo.

`schedule:list` y `schedule:work` pertenecen al [scheduler](task-scheduling.md). `queue:work`, `queue:failed`, `queue:retry`, `queue:forget` y `queue:clear` operan [colas](../../../queues/docs/es/workers-and-failures.md). Los comandos MCP se documentan en [MCP](../../../mcp/docs/es/README.md).

## Optimizar y mantener

El catálogo también incluye optimización y su limpieza, estado de entorno/aplicación, generación de clave, mantenimiento y limpieza de caché, logs, vistas y artefactos de pruebas. Consulta sus firmas/ayuda reales. Generar una nueva clave en una aplicación con datos cifrados tiene efectos sobre esos datos: coordina ese cambio con [cifrado](../../../encrypter/docs/es/README.md). Limpiar caches de compilación invalida metadatos y puede cambiar el tiempo del siguiente arranque.

## Instalar extras desde el catálogo

La firma pública es `packages`, aunque la clase de implementación se llame `InstallCommand`:

```shell
orionis packages --list
orionis packages s3 redshift --yes
orionis packages group:dev --yes
```

`--list` solo muestra el catálogo; los otros ejemplos instalan paquetes con `uv` para el intérprete que ejecuta Orionis. `--yes` suprime confirmación interactiva. No ejecutarlos equivale a revisar el catálogo, no a instalar dependencias automáticamente durante lectura de este manual.

El comando usa primero el manifiesto empaquetado `orionis/pyproject.toml`, después el manifiesto raíz del framework en instalaciones source/editable y, como fallback, el manifiesto raíz de la aplicación. Los textos de propósito provienen de `[tool.orionis.packages]`, con claves `extra:s3` o `group:dev`. Respeta extras, marcadores, grupos y deduplicación; no reescribe el manifiesto ni lockfile de la aplicación. Si falta un catálogo esperado, verifica qué manifiesto está disponible y el entorno Python activo.

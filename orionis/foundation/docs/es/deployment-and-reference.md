# Despliegue, diagnóstico y referencia de Application

## API pública

### `Application(base_path=Path.cwd())`

`orionis.Application` es singleton thread-safe por subclase concreta. `Application.current()` devuelve instancia existente sin crear. Propiedades exponen rutas, inicio, caché compilada, health, readiness, debug/producción y mantenimiento.

### Métodos de bootstrap

- `compile(path=None, invalidation_paths=None)` activa caché de bootstrap.
- `withRouting(api, web, console, health, ai, websocket=...)` registra archivos validados.
- `withProviders(*classes)` y `withMiddleware(*classes)` registran extensiones.
- `withExceptionHandler(cls)` y `withScheduler(cls)` reemplazan defaults.
- `withConfigApp/Auth/Cache/Http/Database/Filesystems/Logging/Mail/Mcp/Queue/Session/Testing(**values)` aporta overrides.
- `withConfigPaths(**paths)` resuelve el mapa completo.
- `on(lifespan, *callbacks, runtime=None)` registra hooks globales o específicos.

`with...` y `on(...)` retornan la aplicación para encadenar y rechazan cambios tras creación. `compile(...)` devuelve `None` y requiere una instrucción independiente. En hit válido de caché compilada, la metadata cacheada prevalece y registros/configuraciones se vuelven no-op intencionalmente.

### Métodos runtime

`create()` registra/configura síncronamente. `boot()` prepara providers async para procesos headless. `handleCommand(args=None)` ejecuta kernel CLI dentro de hooks. `config()`, `path()` y `routingPaths()` exponen config runtime, rutas bootstrap inmutables y listas descongeladas.

`getExceptionHandler()` y `getScheduler()` construyen perezosamente clases configuradas tras creación. Métodos heredados del contenedor aportan binding, resolución, scopes e invocación.

### `Directory`

`Directory(app)` toma una instantánea de `app.path()` y ofrece métodos como `root()`, `appModels()`, `databaseMigrations()`, `resourcesViews()` y `storageLogs()`. Reemplazar luego el mapa no cambia el snapshot.

## Errores y casos límite

- `config`, `path`, flags, handler y scheduler rechazan uso previo a creación donde corresponde.
- Mutar bootstrap tras creación lanza `RuntimeError`; clases provider/middleware/handler/scheduler inválidas lanzan `TypeError`.
- Routing rechaza archivos faltantes, tipos inválidos y archivos sin import de fachada permitido.
- Entidades inválidas detienen creación con su error original, envuelto solo cuando discovery lo requiere.
- La aplicación es singleton por subclase: argumentos posteriores no reinicializan una instancia existente.
- Config runtime es mutable y mappings retornados están vivos; `resetRuntimeConfig()` restaura baseline.
- Claves de path/routing desconocidas retornan `None`; health predeterminado es `/up`.
- Marcador de mantenimiento corrupto/ilegible activa mantenimiento deliberadamente.

## Rendimiento y concurrencia

Modo compilado guarda bootstrap en `FileBasedCache` e invalida por archivos/directorios. Providers y entidades core usan imports lazy. Claves dot notation usan LRU de 256; flags producción/debug se precalculan.

Boot de providers e inicialización de kernels CLI/HTTP usan locks async para compartir un startup. Mantenimiento usa lock de hilo. Scopes/resolución son context-local, pero no hay garantía sobre estado mutable entre loops o hilos arbitrarios.

Monitoreo opcional de desconexión HTTP usa cola ASGI limitada —ocho mensajes y uno retenido por productor— o watcher RSGI, cancelando trabajo al desconectar. WebSockets omiten ese monitoreo de body.

## Compatibilidad

Foundation apunta a Python 3.14+ e implementa ASGI HTTP/WebSocket/lifespan, Granian RSGI y Reactor CLI.

## Estructura del módulo

| Área | Responsabilidad |
|---|---|
| `application.py` | Bootstrap, protocolos, kernels, providers, routing, config, rutas, mantenimiento. |
| `contracts/` | Interfaces `IApplication` e `IDirectory`. |
| `directory.py`, `core_paths.py` | Snapshot de rutas y árbol predeterminado. |
| `config/` | Entidades congeladas, enums, normalización y helpers de entorno. |
| `core_config.py` | Defaults core independientes construidos perezosamente. |
| `core_providers.py`, `core_kernels.py` | Clases provider lazy y metadata de kernels. |
| `core_exception_handler.py`, `core_scheduler.py` | Metadata de extensiones predeterminadas. |
| `enums/` | `Lifespan` y `Runtime`. |
| `lifespan/` | Paneles debug y resumen de uptime. |

## Fuentes y siguientes pasos

[application.py](../../application.py) · [application.py](../../contracts/application.py) · [core_providers.py](../../core_providers.py)

[Volver al índice del módulo](README.md).

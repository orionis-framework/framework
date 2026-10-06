# orionis.foundation

> `orionis.foundation` es el runtime de aplicación Orionis: ensambla configuración validada, rutas, providers, kernels, routing, ciclo de vida y protocolos de despliegue.

## Descripción general

`Application` extiende el `Container` de inyección y es el objeto exportado desde `orionis`. Coordina bootstrap, sirve como entrada ASGI/RSGI, despacha CLI, guarda configuración y rutas, carga providers y posee el ciclo de vida.

Foundation también define entidades congeladas para cada subsistema, metadata core inmutable, el servicio de rutas `Directory`, enums y presentación de startup/shutdown. Las aplicaciones lo configuran en `bootstrap/app.py`, llaman `create()` y dejan que servidor HTTP o Reactor dirijan el runtime.

## Requisitos

- Python 3.14 o posterior; la construcción rechaza intérpretes anteriores.
- Raíz de aplicación como `str` o `pathlib.Path`.
- Módulos de configuración dataclass congelados válidos bajo `config`.
- Archivos de rutas existentes y con la fachada requerida al registrarlos.
- Un event loop por worker; el estado mutable no está diseñado para compartirse entre loops o hilos.

## Inicio rápido

```python
import base64
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis import Application
from orionis.environment import Env


class DocsApplication(Application):
    pass


key = "base64:" + base64.b64encode(b"k" * 32).decode()
Env.set("APP_KEY", key, only_os=True)
try:
    with TemporaryDirectory() as directory:
        app = DocsApplication(Path(directory))
        app.withConfigApp(
            name="Docs",
            env="testing",
            debug=False,
            key=key,
            cipher="AES-256-CBC",
        ).withConfigPaths(storage="var")
        app.create()
        assert app.isCreated and DocsApplication.current() is app
        assert app.config("app.name") == "Docs"
        assert app.path("storage") == (Path(directory) / "var").resolve()
        app.config("app.name", "Runtime Docs")
        assert app.config("app.name") == "Runtime Docs"
        app.resetRuntimeConfig()
        assert app.config("app.name") == "Docs"
        print(app.config("app.name"), app.routeHealthCheck)
finally:
    Env.unset("APP_KEY", only_os=True)
```

Validación: **Executed successfully** en CPython 3.14.6 dentro de una raíz temporal; produjo `Docs /up`.

## Conceptos principales

### Bootstrap frente a runtime

Antes de `create()`, métodos `with...` construyen metadata mutable. La creación carga config/providers, congela el snapshot, registra aplicación y expone una copia runtime mutable. `config(key, value)` cambia solo runtime; `resetRuntimeConfig()` restaura desde el snapshot.

### Etapas de creación y readiness

`create()` completa config y registro de providers. `boot()` además espera boots de providers eager para uso headless, sin ejecutar hooks ni kernels HTTP/CLI. `isCreated`/`isBooted`, `areProvidersBooted` e `isHttpReady` distinguen etapas.

### Propiedad del runtime

Scopes ASGI `http`, `websocket` y `lifespan` se despachan por `Application.__call__`; RSGI usa sus hooks. `handleCommand()` posee startup CLI, comando y shutdown garantizado. Startup HTTP publica handlers ASGI y RSGI antes de readiness.

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

Retornan la aplicación para encadenar y rechazan cambios tras creación. En hit válido de caché compilada, la metadata cacheada prevalece y registros/configuraciones se vuelven no-op intencionalmente.

### Métodos runtime

`create()` registra/configura síncronamente. `boot()` prepara providers async para procesos headless. `handleCommand(args=None)` ejecuta kernel CLI dentro de hooks. `config()`, `path()` y `routingPaths()` exponen config runtime, rutas bootstrap inmutables y listas descongeladas.

`getExceptionHandler()` y `getScheduler()` construyen perezosamente clases configuradas tras creación. Métodos heredados del contenedor aportan binding, resolución, scopes e invocación.

### `Directory`

`Directory(app)` toma una instantánea de `app.path()` y ofrece métodos como `root()`, `appModels()`, `databaseMigrations()`, `resourcesViews()` y `storageLogs()`. Reemplazar luego el mapa no cambia el snapshot.

## Flujos de trabajo comunes

### Iniciar aplicación web

Construye `Application`, opcionalmente activa compilación, registra callbacks, rutas, scheduler, handler, providers y middleware, llama `create()` y expórtala desde `bootstrap.app`; el servidor la invoca por ASGI/RSGI.

### Ejecutar servicios headless

Usa `await app.boot()` para providers eager registrados e iniciados sin kernel. Llamadas concurrentes comparten lock; un provider fallido queda pendiente para reintento.

### Cambiar configuración runtime

Lee con puntos (`app.config("http.cors.allowed_origins")`) y escribe con segundo argumento. Claves ausentes/inaccesibles retornan `None`; escrituras crean diccionarios intermedios. Reinicia para descartar overrides.

### Entrar en mantenimiento

`app.maintenance` es fallback. El marcador compartido `storage/framework/maintenance` sobrescribe con `down` o `up`; cada worker refresca máximo cada 100 ms y falla cerrado ante errores de lectura/decodificación.

## Ejemplos

### Validar configuración nativa

```python
from orionis.foundation.config.app import App, Cipher, Environments

config = App(
    name="Docs",
    env=Environments.TESTING,
    debug=False,
    cipher=Cipher.AES_256_GCM,
    key=b"k" * 32,
)
assert config.env == "testing"
assert config.cipher == "AES-256-GCM"
assert config.key == b"k" * 32
print(config.name, config.env, config.cipher)
```

Validación: **Executed successfully** en CPython 3.14.6.

### Tomar snapshot de directorios

```python
from pathlib import Path
from orionis.foundation.directory import Directory


class App:
    def path(self, key=None):
        paths = {
            "root": Path("project").resolve(),
            "storage_logs": Path("project/storage/logs").resolve(),
        }
        return paths if key is None else paths.get(key)


directory = Directory(App())
assert directory.root() == Path("project").resolve()
assert directory.storageLogs() == Path("project/storage/logs").resolve()
print(directory.storageLogs().as_posix())
```

Validación: **Executed successfully** en CPython 3.14.6.

### Configurar bootstrap compilado

```python
import base64
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis import Application
from orionis.environment import Env


class CachedApplication(Application):
    pass


key = "base64:" + base64.b64encode(b"c" * 32).decode()
Env.set("APP_KEY", key, only_os=True)
try:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "config").mkdir()
        (root / ".env").touch()
        app = CachedApplication(root)
        app.compile("bootstrap/cache", ["config", ".env"])
        app.withConfigApp(key=key)
        app.create()
        assert app.compiled
        assert app.compiledPath == (root / "bootstrap/cache").resolve()
        assert (root / "config").resolve() in app.compiledInvalidationPathsDirs
        assert (root / ".env").resolve() in app.compiledInvalidationPathsFiles
        print("compiled cache configured")
finally:
    Env.unset("APP_KEY", only_os=True)
```

Validación: **Executed successfully** en CPython 3.14.6; todos los archivos fueron temporales.

### Registrar callbacks de ciclo de vida

```python
from orionis.foundation.enums import Lifespan, Runtime


async def open_resources() -> None:
    pass


async def close_resources() -> None:
    pass


app.on(Lifespan.STARTUP, open_resources, runtime=Runtime.HTTP)
app.on(Lifespan.SHUTDOWN, close_resources, runtime=Runtime.HTTP)
```

Validación: **Syntax-validated only** en CPython 3.14.6; `app` pertenece al bootstrap y los callbacks corren bajo ciclo HTTP.

## Configuración

Foundation construye defaults nativos independientes, mezcla datos `withConfig...` y luego dataclasses congeladas descubiertas. Así, entidades `config/*.py` son la fuente final normal. Tras validar, el snapshot se congela profundamente.

Secciones core:

| Sección | Responsabilidad principal |
|---|---|
| `app`, `auth`, `session` | Identidad, entorno, cifrado, guards, cookies y sesiones. |
| `http`, `mcp`, `realtime` | HTTP/seguridad, orígenes y límites realtime. |
| `database`, `cache`, `queue`, `scheduler` | Conexiones, stores, workers y estado programado. |
| `filesystems`, `mail`, `logging`, `view` | Storage, entrega, canales y templates. |
| `hashing`, `testing` | Passwords y test runner. |

Las entidades son dataclasses congeladas que normalizan dicts/enums anidados. Variables de entorno se leen en default factories; consulta cada subsistema para todas las opciones.

## Integración con Orionis

Foundation carga 20 providers core en orden determinista, descubre providers concretos en `app/providers`, registra eager y publica metadata deferred antes del registro eager. `boot` síncrono corre en creación; async durante `boot()` o startup runtime.

Resuelve kernels CLI/HTTP desde metadata, valida imports de fachadas en rutas, inyecta scheduler/handler y se expone como `IApplication` con alias `x-orionis-IApplication`. Todos los módulos consumen su config, contenedor, rutas, scopes o lifecycle.

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

Foundation apunta a Python 3.14+ e implementa ASGI HTTP/WebSocket/lifespan, Granian RSGI y Reactor CLI. La validación usó CPython 3.14.6 en Windows. Rutas usan `pathlib`; aplicar locale/timezone depende de plataforma y locales no soportados se ignoran tras validación.

## Notas de verificación

La validación usó CPython 3.14.6. Se inspeccionaron protocolos, readiness, carga/congelación de config, familias nativas, discovery, compilación, rutas/directory, mantenimiento, lifecycle, contratos, imports lazy y `tests/foundation`. Las 178 pruebas pasaron con el runner Orionis. Cuatro programas independientes se ejecutaron correctamente; lifecycle solo se validó sintácticamente.

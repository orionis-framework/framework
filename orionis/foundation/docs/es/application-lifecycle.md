# Ciclo de vida y recursos de aplicación

## Conceptos principales

### Bootstrap frente a runtime

Antes de `create()`, métodos `with...` construyen metadata mutable. La creación carga config/providers, congela el snapshot, registra aplicación y expone una copia runtime mutable. `config(key, value)` cambia solo runtime; `resetRuntimeConfig()` restaura desde el snapshot.

### Etapas de creación y readiness

`create()` completa config y registro de providers. `boot()` además espera boots de providers eager para uso headless, sin ejecutar hooks ni kernels HTTP/CLI. `isCreated`/`isBooted`, `areProvidersBooted` e `isHttpReady` distinguen etapas.

### Propiedad del runtime

Scopes ASGI `http`, `websocket` y `lifespan` se despachan por `Application.__call__`; RSGI usa sus hooks. `handleCommand()` posee startup CLI, comando y shutdown garantizado. Startup HTTP publica handlers ASGI y RSGI antes de readiness.

## Flujos de trabajo comunes

### Iniciar aplicación web

Construye `Application`, opcionalmente activa compilación, registra callbacks, rutas, scheduler, handler, providers y middleware, llama `create()` y expórtala desde `bootstrap.app`; el servidor la invoca por ASGI/RSGI.

### Ejecutar servicios headless

Usa `await app.boot()` para providers eager registrados e iniciados sin kernel. Llamadas concurrentes comparten lock; un provider fallido queda pendiente para reintento.

### Cambiar configuración runtime

Lee con puntos (`app.config("http.cors.allowed_origins")`) y escribe con segundo argumento. Claves ausentes/inaccesibles retornan `None`; escrituras crean diccionarios intermedios. Reinicia para descartar overrides.

### Entrar en mantenimiento

`app.maintenance` es fallback. El marcador compartido `storage/framework/maintenance` sobrescribe con `down` o `up`; cada worker refresca máximo cada 100 ms y falla cerrado ante errores de lectura/decodificación.

## Integración con Orionis

Foundation carga 20 providers core en orden determinista, descubre providers concretos en `app/providers`, registra eager y publica metadata deferred antes del registro eager. `boot` síncrono corre en creación; async durante `boot()` o startup runtime.

Resuelve kernels CLI/HTTP desde metadata, valida imports de fachadas en rutas, inyecta scheduler/handler y se expone como `IApplication` con alias `x-orionis-IApplication`. Todos los módulos consumen su config, contenedor, rutas, scopes o lifecycle.

## Ejemplos

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

## Elegir la fase correcta

| Operación | Qué prepara | Qué debes esperar después |
|---|---|---|
| `Application(root)` | Identidad del contenedor y raíz | Aún no se puede leer configuración con `config()`. |
| `app.create()` | Configuración y registro de providers | `isCreated` y el alias histórico `isBooted` son verdaderos. |
| `await app.boot()` | También completa el boot de providers eager | `areProvidersBooted` es verdadero; no inicia hooks ni kernels. |
| Inicio HTTP del servidor | Hooks y kernel de HTTP | `isHttpReady` indica handlers publicados, no sockets ni salud de dependencias externas. |
| `await app.handleCommand(args)` | Kernel y hooks CLI | Ejecuta shutdown en `finally` después de entrar en la ejecución del kernel. |

Los hooks globales y los de runtime se guardan en conjuntos. No dependas del orden de registro para inicializar dos recursos dependientes: agrupa esa secuencia en un callback que haga ambos pasos. Un provider deferred se registra y arranca al resolver uno de sus servicios; `areProvidersBooted` solo describe los eager.

## Recursos en un proceso sin servidor

Guarda este ejemplo como programa independiente. El provider registra una dependencia y su `boot` añade la inicialización que requiere un event loop. La aplicación temporal no descubre los providers del checkout. Al terminar, cierra tus propios recursos: `boot()` por sí solo no ejecuta shutdown de un kernel.

```python
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis import Application
from orionis.environment.core.dot_env import DotEnv
from orionis.container.providers import ServiceProvider

class Catalog:
    def __init__(self) -> None:
        self.ready = False

class CatalogProvider(ServiceProvider):
    def register(self) -> None:
        self.app.singleton(None, Catalog)

    async def boot(self) -> None:
        catalog = await self.app.make(Catalog)
        catalog.ready = True

async def main() -> None:
    with TemporaryDirectory() as directory:
        DotEnv(str(Path(directory) / ".env"))
        app = Application(Path(directory))
        app.withConfigApp(key=b"x" * 32, debug=False, env="testing")
        app.withProviders(CatalogProvider)
        app.create()
        assert app.isCreated
        await app.boot()
        assert app.areProvidersBooted
        assert not app.isHttpReady
        assert (await app.make(Catalog)).ready

asyncio.run(main())
```

## Fuentes y siguientes pasos

[application.py](../../application.py) · [lifespan.py](../../enums/lifespan.py) · [runtimes.py](../../enums/runtimes.py)

[Volver al índice del módulo](README.md).

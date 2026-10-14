# Crear y arrancar una aplicación

Orionis reúne un contenedor de servicios, configuración tipada y kernels HTTP y CLI sobre un runtime asíncrono. El punto de entrada es una instancia de `Application`: construirla no inicia un servidor. El ejemplo usa una raíz temporal para mostrar la configuración sin depender del esqueleto de una aplicación. La clave fija es exclusivamente de prueba; utiliza una clave aleatoria privada en una aplicación real.

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

## Fuentes y siguientes pasos

[application.py](../../application.py) · [pyproject.toml](../../../../pyproject.toml)

[Volver al índice del módulo](README.md).

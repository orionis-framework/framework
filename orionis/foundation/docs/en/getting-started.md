# Creating and starting an application

Orionis combines a service container, typed configuration, and HTTP and CLI kernels around an asynchronous runtime. Its entry point is an `Application` instance: constructing it does not start a server. This example uses a temporary root to demonstrate configuration independently of an application skeleton. Its fixed key is only for testing; use a private random key in an actual application.

## Quick start

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

## Evidence and next steps

[application.py](../../application.py) · [pyproject.toml](../../../../pyproject.toml)

[Return to the module index](README.md).

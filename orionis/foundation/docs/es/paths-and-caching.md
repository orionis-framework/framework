# Directorios y caché de arranque

Usa el registro de rutas para que un servicio no dependa del directorio actual del proceso. `Directory` ofrece nombres de métodos para ese mismo registro. La compilación guarda metadatos de arranque: no compila Python ni reemplaza la gestión de despliegues. `compile(...)` devuelve `None`; debe llamarse en una instrucción independiente antes de `create()`.

## Ejemplos

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

## Fuentes y siguientes pasos

[directory.py](../../directory.py) · [core_paths.py](../../core_paths.py) · [application.py](../../application.py)

[Volver al índice del módulo](README.md).

# Directories and bootstrap caching

Use the path registry so that services do not depend on the process working directory. `Directory` provides named methods for that same registry. Compilation stores bootstrap metadata: it does not compile Python or replace deployment management. `compile(...)` returns `None`; call it in a separate statement before `create()`.

## Examples

### Snapshot configured directories

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

### Configure compiled bootstrap state

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

## Evidence and next steps

[directory.py](../../directory.py) · [core_paths.py](../../core_paths.py) · [application.py](../../application.py)

[Return to the module index](README.md).

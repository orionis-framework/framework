# Reading and writing environment configuration

Each block on this page is a separate program. Run the `DotEnv` example in a fresh process: the singleton's first construction selects its file for the whole process.

## Quick start

```python
from orionis.environment import Env, env

Env.set("ORIONIS_DOC_SAMPLE", 7, "int", only_os=True)
assert Env.get("ORIONIS_DOC_SAMPLE") == 7
assert env("MISSING_DOC_KEY", "fallback") == "fallback"
Env.unset("ORIONIS_DOC_SAMPLE", only_os=True)
print("7 fallback")
```

## Core concepts

### Process environment and file cache

`get()` reads `os.environ`, the current process source of truth. Persistent writes update both the file/cache and process environment. `all()` returns only cached entries originating from the selected `.env`; it is not a dump of every operating-system variable.

### Typed values

Supported hints are `str`, `int`, `float`, `bool`, `list`, `dict`, `tuple`, `set`, `path`, and `base64`. Typed storage has the form `<hint>:<payload>`. Container payloads use safe literal parsing; paths normalize to POSIX form; Base64 parses to UTF-8 text when possible and otherwise bytes.

### Singleton path

`DotEnv` uses a singleton metaclass. The path supplied to the first construction in a process determines the backing file for later facade calls. Normal applications rely on the default working-directory `.env`; tests that need another path should isolate the singleton in a fresh process or reset it with the test utilities.

## Common workflows

### Read configuration defaults

Call `env("NAME", fallback)` inside configuration factories. Returned values may already be booleans, numbers, collections, paths, or decoded Base64 content, so do not assume every value is a string.

### Persist a typed value

Use `Env.set("WORKERS", 4, "int")`; the file stores `int:4` and later reads return integer `4`. Use `EnvironmentValueType.INT` instead of a string when enum-based code is clearer.

### Apply an external file edit

Call `Env.reload()` after changing the selected `.env` outside the process. It overrides matching process values and refreshes `all()`. A key removed from the file is removed from the cache, but `python-dotenv` does not automatically delete an already-existing process variable.

## Examples

### Serialize and parse a typed dictionary

```python
from orionis.environment.dynamic.caster import EnvironmentCaster

stored = EnvironmentCaster({"workers": 4}).to("dict")
assert stored == "dict:{'workers': 4}"
assert EnvironmentCaster.parseTyped(stored) == {"workers": 4}
print(stored)
```


### Work with an isolated `.env`

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.environment.core.dot_env import DotEnv

with TemporaryDirectory() as directory:
    path = Path(directory) / ".env"
    values = DotEnv(str(path))
    values.set("FEATURES", ["mail", "queue"], "list")
    assert values.get("FEATURES") == ["mail", "queue"]
    assert values.all() == {"FEATURES": ["mail", "queue"]}
    values.unset("FEATURES")

print("temporary .env ok")
```


### Generate an AES application key

```python
import base64
from orionis.environment.key.key_generator import SecureKeyGenerator

key = SecureKeyGenerator.generate("AES-256-GCM")
raw = base64.b64decode(key.removeprefix("base64:"), validate=True)
assert len(raw) == 32
print("key bytes:", len(raw))
```

## Configuration

The subsystem itself selects `.env` at `Path.cwd() / ".env"` unless the first direct `DotEnv(path)` construction supplies another path. There is no separate Orionis config file for this module.

File values support plain dotenv syntax and these typed prefixes:

| Prefix | Parsed value |
|---|---|
| `str:` | String with leading value whitespace removed. |
| `int:`, `float:` | Python number. |
| `bool:` | `true/1/yes/on/enabled` or `false/0/no/off/disabled`. |
| `list:`, `dict:`, `tuple:`, `set:` | Matching Python literal container. |
| `path:` | Normalized POSIX path string. |
| `base64:` | Decoded UTF-8 string or raw bytes. |

Unprefixed `none`, `null`, `nan`, and `nil` map to `None`; unprefixed safe literals are parsed with `ast.literal_eval`.

## Evidence and next steps

[dot_env.py](../../core/dot_env.py) · [caster.py](../../dynamic/caster.py) · [facade.py](../../facade.py)

[Return to the module index](README.md).

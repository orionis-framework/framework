# Caching source-derived artifacts

Use an artifact cache when a computed dictionary depends on source files.

## Rebuild when sources change

`FileBasedCache` is synchronous and stores one complete dictionary, suitable for compiled metadata. During startup call `get()`; when it returns `None`, rebuild the result, call `save(data)`, and use that dictionary. It supplies no TTL, independent keys, or distributed locks.

The fingerprint uses absolute paths, `st_mtime_ns`, and file size. It does not hash complete file contents: a change preserving those metadata can go unnoticed. Monitored directories add only `*.py`; `monitored_files` lets you name other individual files. Fingerprint lookup is memoized for 0.5 seconds; changes may remain unseen during that interval. This interval is distinct from an artifact TTL.

`save()` accepts only a `dict`, retains version and fingerprint, and skips rewriting when all values match. Publication uses a sibling temporary file and replacement. Two producers can compute and store different results: construction is not mutually exclusive and the final replacement wins. Coordinate compilation if that race matters.

### Serialize framework types

`from orionis.cache.serializer import Serializer` exposes `dumps`, `loads`, `dumpToFile`, and `loadFromFile`. Beyond containers and primitives it supports bytes, Path, dates/times, timedelta, Decimal, UUID, complex values, tuples, sets, frozensets, enums, types, and the `MISSING` sentinel. It uses `__type__` and `__value__` markers; avoid these names in business mappings that must round-trip unchanged.

This format is for trusted local artifacts. Restoring enums and types can import modules by name: do not deserialize client-supplied payloads or files writable by untrusted users. It includes no signature or encryption. `loadFromFile` returns `None` for absent, empty, or unreadable files; corrupt JSON or an unknown marker can propagate an error. Treat the cache as regenerable and decide whether startup should discard it or fail.


### Invalidate a file artifact when source changes

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import time

from orionis.cache import FileBasedCache


with TemporaryDirectory() as directory:
    root = Path(directory)
    source = root / "feature.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")

    cache = FileBasedCache(root, "compiled.cache", monitored_files=[source])
    cache.save({"routes": ["/"]})
    print(cache.get())  # {'routes': ['/']}

    source.write_text("VALUE = 2\n", encoding="utf-8")
    time.sleep(0.6)  # FileBasedCache refreshes its source hash every 0.5 s.
    print(cache.get())  # None
```

### `FileBasedCache`

```text
FileBasedCache(
    path: Path,
    filename: str,
    monitored_dirs: list[Path] | None = None,
    monitored_files: list[Path] | None = None,
)
```

`save(data)` writes a versioned payload and returns `(CACHE_VERSION, sources_hash)`; identical data and source hash skip the rewrite. `get()` returns the dictionary only when version and source hash still match, otherwise `None`. `clear()` reports whether the cache file existed. Only Python files from monitored directories participate, and the cache file itself is excluded.

---

[Index](README.md) · [foundation](../../../foundation/docs/en/README.md)

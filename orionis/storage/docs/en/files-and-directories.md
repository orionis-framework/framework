# Saving files and listing directories

Storage lets you save content and work with files through the same async contract on local, ephemeral, and cloud disks.

## Requirements

- Python 3.14 or newer.
- A booted Orionis application and `filesystems` configuration for the `Storage` facade.
- A writable application directory for local disks.
- Optional official SDKs and credentials for S3 (`boto3`), Azure (`azure-storage-blob`), or GCS (`google-cloud-storage`).



## Quick start

```python
import asyncio
from orionis.storage import Disk, MemoryStorageDriver


async def example() -> None:
    disk = Disk("memory", MemoryStorageDriver(base_url="https://cdn.example.test"))
    file = await disk.put("notes/hello.txt", "Hello, Orionis")
    assert await file.read() == b"Hello, Orionis"
    assert await disk.exists("notes/hello.txt")
    assert await file.url() == "https://cdn.example.test/notes/hello.txt"


asyncio.run(example())
```




## Save a business result

After generating a report, choose a disk and a stable logical path. In a booted application, use `await Storage.disk("local").put("reports/42.txt", content)`. `disk()` is synchronous; `put()` is async and returns a `File`. Retain the object or its `path()` for later operations. The logical path contains neither physical directories nor provider credentials.

`disk.file(path)` and `disk.directory(path)` only create references; they do not check existence. `await file.exists()` helps presentation, but checking then reading can race: catch `StorageFileNotFoundException` around the read that matters. No transaction spans database and storage. When publishing a row and a file, design cleanup or compensation if either operation fails.

`write()` and `put()` replace content. `copyTo()` and `moveTo()` operate within the same disk. They return a new object; after a move, the original object still points to its previous path. `rename(name)` keeps the directory and rejects separators. To copy across disks, pass chunks between their file references: another disk name is not a destination path.

### Read metadata and delete

| Goal | Operation |
|---|---|
| Read complete bytes | `await file.read()` |
| Size / MIME / time | `await file.size()`, `await file.mimeType()`, `await file.lastModified()` |
| Snapshot | `await file.info()` |
| Inspect/change visibility | `await file.visibility()`, `await file.setVisibility("private")` |
| Content checksum | `await file.hash("sha256")` |
| Copy to the server filesystem | `await file.download(destination)` |
| Delete one file | `await file.delete()` → whether it existed |
| Delete a tree | `await disk.directory("reports").delete()` |

`download()` writes to the server filesystem; it does not create an HTTP download response. Its destination is a local path and must be application-controlled. `Directory.delete()` is recursive: an empty path means the disk root. Do not derive it from unvalidated input.

`FileInfo` contains `path`, `size`, `lastModified`, `visibility`, `mimeType`, `createdAt`, `etag`, `checksum`, and `url`. Optional fields may be `None`; a cloud ETag is not guaranteed to be an MD5 of complete content. `info()` may read content to compute checksums: request only size when that is all you need.


### Disks, files, and directories

A disk is a named driver boundary. `disk.file(path)` and `disk.directory(path)` normalize paths immediately but perform no I/O. Disk convenience methods delegate to those domain objects, so behavior remains consistent whether using `put`, `file(...).write`, or directory traversal.

### Safe root-relative paths

Paths use `/`, ignore empty/`.` components, resolve internal `..`, and reject traversal above the disk root, null bytes, colons, and an empty file target. Local drivers additionally resolve filesystem paths beneath their configured root and defend against symlink escapes.

### Work with directory listings

```python
import asyncio
from orionis.storage import Disk, MemoryStorageDriver


async def example() -> None:
    disk = Disk("memory", MemoryStorageDriver())
    await disk.put("reports/2026/january.txt", b"one")
    await disk.put("reports/summary.txt", b"two")
    reports = disk.directory("reports")
    assert [item.path() for item in await reports.files()] == ["reports/summary.txt"]
    assert sorted(item.path() for item in await reports.allFiles()) == [
        "reports/2026/january.txt", "reports/summary.txt",
    ]


asyncio.run(example())
```

### Inspect metadata and visibility

```python
import asyncio
from orionis.storage import Disk, MemoryStorageDriver, Visibility


async def example() -> None:
    file = await Disk("memory", MemoryStorageDriver()).put(
        "assets/app.css", "body{}", Visibility.PUBLIC,
    )
    info = await file.info()
    assert info.size == 6
    assert info.visibility == "public"
    assert len(await file.hash("sha256")) == 64


asyncio.run(example())
```

### Normalize paths without filesystem access

```python
from orionis.storage.exceptions import StoragePathException
from orionis.storage.paths import normalize_file_path, normalize_path

assert normalize_path(r"reports\.\2026\..\summary") == "reports/summary"
assert normalize_file_path("/images/logo.svg") == "images/logo.svg"

try:
    normalize_path("../../secret")
except StoragePathException:
    pass
else:
    raise AssertionError("root escape was accepted")
```

## List and create directories

`directory.path()` returns the logical path. `await directory.create()` creates a directory and returns the same object; object storage may represent it through a marker. `await directory.exists()` checks existence according to its driver. `files()` and `directories()` return lists of direct-child references; `allFiles()` and `allDirectories()` include descendants. Await every listing; returned `File`/`Directory` references remain bound to the same disk.

The root is represented by `disk.directory()` and may exist before any file has been stored. Object storage can derive directories from implicit prefixes: do not assume empty directories are identical persistent entities across providers. Listings materialize as lists, not public paginated cursors. Account for memory and SDK request counts when traversing large trees.

`lastModified` is a timezone-aware UTC timestamp; `createdAt` may be `None` when a provider exposes no creation time. A snapshot does not update after a write: request another `info()` for later state.

---

[Index](README.md) · [foundation](../../../foundation/docs/en/README.md)

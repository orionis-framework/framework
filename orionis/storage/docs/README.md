# orionis.storage

> `orionis.storage` offers one async file/directory API across local, memory, Amazon S3, Azure Blob Storage, and Google Cloud Storage disks.

## Overview

`StorageManager` resolves configured disks lazily and caches each `Disk`. A disk creates lightweight `File` and `Directory` objects that normalize root-relative paths and delegate to an `IStorageDriver`. Built-in drivers share read/write, streaming, metadata, visibility, URL, download, copy/move, and directory-listing contracts.

The abstraction keeps application code independent of vendor SDKs. Cloud clients are imported lazily, local blocking operations run in worker threads, and large payloads can move through async streams without loading a complete object into memory.

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

Validation: **Executed successfully** on CPython 3.14.6.

## Core concepts

### Disks, files, and directories

A disk is a named driver boundary. `disk.file(path)` and `disk.directory(path)` normalize paths immediately but perform no I/O. Disk convenience methods delegate to those domain objects, so behavior remains consistent whether using `put`, `file(...).write`, or directory traversal.

### Safe root-relative paths

Paths use `/`, ignore empty/`.` components, resolve internal `..`, and reject traversal above the disk root, null bytes, colons, and an empty file target. Local drivers additionally resolve filesystem paths beneath their configured root and defend against symlink escapes.

### Streaming

`readStream()` yields bounded byte chunks; `writeStream()` consumes async iterables. `open()` returns `AsyncStream`, whose `read`, `write`, `seek`, and `close` move blocking binary handle operations to worker threads. Use `async with` so buffers close and driver-specific flush callbacks run.

### Visibility and URLs

Visibility is `public` or `private`. On local storage it maps to permissions; on cloud storage it maps to provider access controls where supported. `url()` builds a public location only when configured; `temporaryUrl()` creates signed URLs on capable cloud drivers and is unsupported by local/memory drivers.

### Metadata snapshots

`FileInfo` is an immutable snapshot with path, size, UTC modification/creation times, visibility, MIME type, ETag, SHA-256 checksum, and URL where the driver provides them. Individual metadata calls may be cheaper if only one field is needed.

## Module structure

| Path | Responsibility |
|---|---|
| `manager.py`, `provider.py` | Config validation, lazy disk construction, custom drivers, facade lifecycle. |
| `disk.py`, `file.py`, `directory.py` | High-level backend-neutral domain API. |
| `stream.py`, `uploaded_file.py` | Async binary handles and HTTP upload adaptation. |
| `paths.py` | Canonical root-relative path normalization and traversal rejection. |
| `drivers/local.py`, `drivers/memory.py` | Built-in local and ephemeral implementations. |
| `drivers/s3.py`, `drivers/azure.py`, `drivers/gcs.py` | Lazy optional cloud integrations. |
| `entities/file_info.py`, `enums/visibility.py` | Metadata snapshot and visibility values. |
| `contracts/`, `exceptions.py` | Replaceable interfaces and typed storage failures. |

## Public API

The package root lazily exports `StorageManager`, `Disk`, `File`, `Directory`, `AsyncStream`, `UploadedFile`, `FileInfo`, `Visibility`, and all five built-in driver classes.

### `File`

Provides `path`, `read`, `readStream`, `write`, `writeStream`, `open`, `exists`, `delete`, `copyTo`, `moveTo`, `rename`, `size`, `mimeType`, `lastModified`, `visibility`, `setVisibility`, `hash`, `info`, `url`, `temporaryUrl`, and `download`.

### `Directory`

Provides `path`, `create`, `exists`, `delete`, `files`, `allFiles`, `directories`, and `allDirectories`. Non-recursive methods return direct children; `all*` traverses recursively according to the driver contract.

### Manager and facade

`disk(name=None)` resolves a configured disk; `default()` is shorthand; `extend(driver, factory)` installs a custom driver factory and clears cached disks; `uploaded(http_file)` adapts a multipart upload. `orionis.support.facades.Storage` exposes the same singleton.

### Uploaded files

`UploadedFile` exposes sanitized `originalName`, extension, size, client-declared MIME, and a cached random `hashName`. `store`/`copy` keep the upload buffer usable; `move` stores then closes it. The declared MIME and original name are untrusted metadata.

## Common workflows

### Store generated content

Use `await Storage.disk().put(path, bytes_or_text, visibility)`. Strings are UTF-8 encoded. Retain the returned `File` for later metadata or URL operations.

### Stream large objects

Pass an async byte iterable to `writeStream` or iterate `readStream`. Do not concatenate chunks unless the final size is known and safe.

### Save an HTTP upload

Adapt the HTTP payload with `Storage.uploaded(source)`, validate size/content with schema rules, then call `store`, `storeAs`, `copy`, or `move`. Prefer `hashName()` over client names for collision/path safety.

### Add a custom backend

Implement `IStorageDriver`, register a factory with `StorageManager.extend`, and reference that driver name in configuration. The factory receives the validated disk configuration object.

## Examples

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

Validation: **Executed successfully** on CPython 3.14.6.

### Stream writes and reads

```python
import asyncio
from orionis.storage import Disk, MemoryStorageDriver


async def chunks():
    for value in (b"alpha", b"-", b"beta"):
        yield value


async def example() -> None:
    file = Disk("memory", MemoryStorageDriver()).file("stream.bin")
    await file.writeStream(chunks())
    received = b"".join([part async for part in file.readStream(chunk_size=3)])
    assert received == b"alpha-beta"


asyncio.run(example())
```

Validation: **Executed successfully** on CPython 3.14.6.

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

Validation: **Executed successfully** on CPython 3.14.6.

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

Validation: **Executed successfully** on CPython 3.14.6.

### Use the application facade

```python
from orionis.support.facades import Storage


async def publish_manifest() -> str:
    file = await Storage.disk("public").put(
        "build/manifest.json", '{"version": 1}', visibility="public",
    )
    return await file.url()
```

Validation: **Import and syntax validated** on CPython 3.14.6; execution requires a booted application and configured disk.

## Configuration

`config/filesystems.py` selects `FILESYSTEM_DISK` (default `local`) and defines conventional disks:

- Local: `LOCAL_PATH` defaults to `storage/app/private`.
- Public local: `PUBLIC_PATH` defaults to `storage/app/public`; `PUBLIC_URL` defaults to `/static`.
- S3: `S3_KEY`, `S3_SECRET`, `S3_REGION` (`us-east-1`), `S3_BUCKET`, `S3_URL`, `S3_ENDPOINT`, `S3_USE_PATH_STYLE_ENDPOINT`.
- Azure: `AZURE_CONNECTION_STRING` or account credentials (`AZURE_ACCOUNT_NAME`, `AZURE_ACCOUNT_KEY`), plus `AZURE_CONTAINER` and `AZURE_URL`.
- GCS: `GCS_PROJECT_ID`, optional `GCS_KEY_FILE`, `GCS_BUCKET`, and `GCS_URL`.

Relative local paths are anchored below the application base path. Empty cloud credentials are placeholders, not usable deployments; configuration entities validate shapes while provider SDKs validate credentials on use.

## Integration with Orionis

`StorageProvider` is deferrable, binds `IStorageManager` to a singleton, and pins the `Storage` facade. The HTTP layer buffers/spools multipart files; `StorageManager.uploaded()` wraps them without coupling storage drivers to requests. Schema file/image rules understand the uploaded-file contract.

Public local disks normally pair `PUBLIC_URL=/static` with the application's static-file routing. Storage configuration does not create a public route automatically in isolation; routing and deployment must expose the matching directory intentionally.

## Errors and edge cases

- Invalid or escaping paths raise `StoragePathException`; missing files raise `StorageFileNotFoundException` where the operation requires existence.
- Unsupported features such as local signed URLs raise `UnsupportedStorageOperationException` instead of returning misleading data.
- Unknown disks and drivers raise `DiskNotFoundException` and `DriverNotSupportedException`.
- Copy/move targets are normalized; overwrite semantics follow the driver contract and backend behavior.
- `mimeType()` is inference/provider metadata, not content validation. Hash/checksum support and ETag meaning vary by provider.
- Cloud listing is eventually subject to provider consistency, pagination, credentials, and network failures.
- Open streams must be closed; write streams may publish data during close/flush.

## Performance and concurrency

Disks are built once per manager; file/directory wrappers are cheap. Local file operations and cloud SDK calls are moved off the event loop where blocking. Streaming uses 64 KiB defaults and preserves backpressure.

Memory driver mutations are atomic only within one event-loop turn and are not thread-safe for competing writes. Local driver protects path resolution and uses thread-backed I/O, but application-level concurrent writes to one file still need ownership rules. Cloud throughput and multipart behavior depend on provider SDKs.

## Compatibility

All built-in drivers implement `IStorageDriver`, but provider capabilities differ: public ACLs, signed URLs, creation times, ETags, checksums, and directory semantics are not universally equivalent. Paths are always canonical POSIX-style relative strings at the Orionis API boundary, including on Windows.

Legacy `normalizePath` and `normalizeFilePath` remain lazy aliases; new code should use snake_case names.

## Verification notes

- `tests/storage`: **245 test methods passed** with the Orionis runner on CPython 3.14.6.
- Six bilingual documentation programs were compiled; five standalone memory/path programs were executed successfully.
- The facade program was import/syntax validated because it requires application configuration.
- Cloud drivers were verified through mocked official SDK behavior; no live cloud credentials or network writes were used.
- Evidence covered path/symlink safety, local and memory parity, streams, uploads, metadata, visibility, URLs, manager/provider behavior, optional imports, and S3/Azure/GCS adapters.


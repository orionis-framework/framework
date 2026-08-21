# Orionis Storage (`orionis.storage`)

> Async, driver-agnostic file storage: a single API for local disks, in-memory disks, Amazon S3, Azure Blob Storage, and Google Cloud Storage.

## Table of contents

- [Requirements](#requirements)
- [Functional description](#functional-description)
  - [Where it fits in the framework](#where-it-fits-in-the-framework)
  - [Component pipeline](#component-pipeline)
  - [File map](#file-map)
  - [Design decisions](#design-decisions)
- [API reference](#api-reference)
  - [`StorageManager`](#storagemanager)
  - [`Disk`](#disk)
  - [`File`](#file)
  - [`Directory`](#directory)
  - [`UploadedFile`](#uploadedfile)
  - [`AsyncStream`](#asyncstream)
  - [`IStorageDriver`](#istoragedriver)
  - [`LocalStorageDriver`](#localstoragedriver)
  - [`MemoryStorageDriver`](#memorystoragedriver)
  - [`S3StorageDriver`](#s3storagedriver)
  - [`AzureStorageDriver`](#azurestoragedriver)
  - [`GoogleStorageDriver`](#googlestoragedriver)
  - [Driver helper functions](#driver-helper-functions)
  - [`FileInfo`](#fileinfo)
  - [`Visibility`](#visibility)
  - [Path normalization](#path-normalization)
  - [Exceptions](#exceptions)
  - [`StorageProvider` and the `Storage` facade](#storageprovider-and-the-storage-facade)
  - [Configuration keys](#configuration-keys)
- [Usage examples](#usage-examples)
  - [Resolving a disk through the facade](#resolving-a-disk-through-the-facade)
  - [Handling errors](#handling-errors)
  - [Streaming large files](#streaming-large-files)
  - [Storing an HTTP upload](#storing-an-http-upload)
  - [Running standalone with the memory driver](#running-standalone-with-the-memory-driver)
  - [Registering a custom driver](#registering-a-custom-driver)
- [Performance and concurrency considerations](#performance-and-concurrency-considerations)
- [Compatibility notes](#compatibility-notes)

## Requirements

The `local` and `memory` drivers require nothing beyond `pip install orionis`: they
only use the standard library (`asyncio`, `hashlib`, `mimetypes`, `shutil`,
`pathlib`, `secrets`, `io`, `urllib.parse`).

The cloud drivers rely on the official SDK of each platform, declared as **optional
dependencies** in `pyproject.toml`:

| Driver | PyPI package | Minimum version | Install |
| --- | --- | --- | --- |
| `S3StorageDriver` | `boto3` | `>=1.35` | `pip install orionis[s3]` |
| `AzureStorageDriver` | `azure-storage-blob` | `>=12.24` | `pip install orionis[azure]` |
| `GoogleStorageDriver` | `google-cloud-storage` | `>=2.18` | `pip install orionis[gcs]` |
| All three at once | — | — | `pip install orionis[storage]` |

The SDK is never imported at construction time: each driver bootstraps its client on
the first operation through `importDriverDependency()`, so a missing package raises
`MissingStorageDependencyException` with the exact install command instead of an
`ImportError` at startup.

## Functional description

### Where it fits in the framework

`orionis.storage` provides uniform, fully asynchronous access to file storage,
independently of the physical medium behind it. Application code always talks to the
same objects (`Disk`, `File`, `Directory`); swapping a local disk for an S3 bucket is
a configuration change, not a code change.

Direct relationships with other modules:

- `orionis.foundation.config.filesystems` — supplies the `Filesystems` / `Disks`
  configuration entities that `StorageManager` reads through `app.config("filesystems")`.
- `orionis.foundation` (`core_providers.py`) — registers `StorageProvider`.
- `orionis.container` — resolves `IStorageManager` and powers the `Storage` facade.
- `orionis.http.payload` — produces the multipart payload that `UploadedFile` adapts.
  The HTTP contract is imported only under `TYPE_CHECKING`, so the storage module never
  depends on the HTTP layer at runtime.

### Component pipeline

```text
Storage (facade)  ->  IStorageManager
                        |
                        |  disk(name) / default()          cached per name
                        v
                      Disk  ------------------------------ IStorageDriver
                        |                                   (local | memory |
                        |  file(path) / directory(path)      s3 | azure | gcs |
                        v                                    custom via extend)
              File            Directory
                |                 |
                |  open()         |  files() / directories()
                v                 v
           AsyncStream        list[File] / list[Directory]

UploadedFile  ->  manager.disk(disk).file(target).writeStream(chunks)
```

Every operation on `Disk`, `File`, and `Directory` is delegated to the driver, and the
driver only speaks in canonical root-relative paths produced by
`normalizePath()` / `normalizeFilePath()`.

### File map

| File | Content |
| --- | --- |
| `manager.py` | `StorageManager`: reads the configuration, builds and caches disks, registers custom drivers, adapts HTTP uploads. |
| `disk.py` | `Disk`: factory of `File` / `Directory` objects plus shortcut methods that always delegate to them. |
| `file.py` | `File`: every single-file operation (content, metadata, relocation, URLs). |
| `directory.py` | `Directory`: creation, deletion, existence, and listings that return objects, never strings. |
| `uploaded_file.py` | `UploadedFile`: adapts an HTTP multipart payload so it can be persisted onto any disk. |
| `stream.py` | `AsyncStream`: async wrapper over a lazily opened binary handle. |
| `paths.py` | `normalizePath()` / `normalizeFilePath()`: canonical form and traversal protection. |
| `exceptions.py` | Exception hierarchy rooted at `StorageException`. |
| `provider.py` | `StorageProvider`: binds `IStorageManager` and pins the `Storage` facade. |
| `contracts/` | ABCs: `IStorageManager`, `IDisk`, `IFile`, `IDirectory`, `IUploadedFile`, `IStorageStream`, `IStorageDriver`. |
| `drivers/local.py` | `LocalStorageDriver` (filesystem, atomic writes, POSIX permissions). |
| `drivers/memory.py` | `MemoryStorageDriver` (in-process dictionaries, for tests/ephemeral use). |
| `drivers/s3.py` | `S3StorageDriver` (Amazon S3 and S3-compatible services). |
| `drivers/azure.py` | `AzureStorageDriver` (Azure Blob Storage). |
| `drivers/gcs.py` | `GoogleStorageDriver` (Google Cloud Storage). |
| `drivers/functions.py` | Helpers shared by drivers: lazy import, mode validation, download target, key filtering. |
| `entities/file_info.py` | `FileInfo`: immutable metadata snapshot. |
| `enums/visibility.py` | `Visibility`: `PUBLIC` / `PRIVATE`. |

### Design decisions

- **Driver pattern** — `IStorageDriver` isolates the medium; `File` / `Directory` /
  `Disk` never know which backend they run on, so the same code works on every disk.
- **No duplicated logic** — `Disk.put/exists/delete/copy/move` delegate to `File`, and
  `Directory.files()` builds `File` objects; there is a single implementation per behavior.
- **`__slots__` on every concrete class** (`StorageManager`, `Disk`, `File`, `Directory`,
  `UploadedFile`, `AsyncStream`, all drivers) **and `__slots__ = ()` on every contract** —
  instances carry no attribute dictionary, which bounds per-object memory.
- **Immutable metadata** — `FileInfo` is a `@dataclass(frozen=True, kw_only=True, slots=True)`,
  so a snapshot can be passed around without risk of mutation.
- **Lazy SDK import** — cloud driver constructors perform no I/O and no import, which makes
  them constructible (and testable) without the SDK installed.
- **Path normalization at the boundary** — `File` and `Directory` normalize in `__init__`,
  so drivers can assume paths are already safe.
- **Deferrable provider** — `StorageProvider` implements `DeferrableProvider`, so nothing
  in the storage stack is built until `IStorageManager` is first resolved.

## API reference

### `StorageManager`

`orionis.storage.manager.StorageManager` — implements
`orionis.storage.contracts.manager.IStorageManager`.

`__slots__ = ("_app", "_base_path", "_config", "_custom", "_default", "_disks")`

```python
def __init__(self, app: IApplication) -> None
```

Reads `app.config("filesystems")` and, when it is a `dict`, converts it into the
validated `Filesystems` entity. Stores `app.basePath` as the anchor for relative local
roots, and the configured `default` disk name.

| Method | Signature | Description |
| --- | --- | --- |
| `disk` | `disk(name: str \| None = None) -> IDisk` | Resolves the disk declared under `name` (or the default one). Built on first access and cached in `_disks`. Raises `DiskNotFoundException` when the disk is not declared, and `DriverNotSupportedException` when its `driver` has no implementation. |
| `default` | `default() -> IDisk` | Shortcut for `disk()`. |
| `extend` | `extend(driver: str, factory: Callable[[object], IStorageDriver]) -> None` | Registers a factory for a driver name. The factory receives the disk configuration entity and must return a ready driver. **Side effect:** clears the disk cache so subsequent resolutions pick the factory up. |
| `uploaded` | `uploaded(source: IHttpUploadedFile) -> IUploadedFile` | Wraps an HTTP multipart payload in an `UploadedFile` bound to this manager. |

Driver resolution order inside the private `__buildDriver()`:

1. Factory registered with `extend()` for the disk's `driver` value (always wins).
2. `"local"` → `LocalStorageDriver`, rooted at `config.path`; relative paths are
   anchored to `app.basePath`, and `config.url` becomes the public base URL.
3. `"memory"` → `MemoryStorageDriver(base_url=config.url)`.
4. `"aws"` or `"s3"` → `S3StorageDriver(config)`.
5. `"azure"` → `AzureStorageDriver(config)`.
6. `"gcs"` or `"google"` → `GoogleStorageDriver(config)`.
7. Anything else → `DriverNotSupportedException`.

### `Disk`

`orionis.storage.disk.Disk` — implements `orionis.storage.contracts.disk.IDisk`.

`__slots__ = ("_driver", "_name")`

```python
def __init__(self, name: str, driver: IStorageDriver) -> None
```

| Method | Signature | Description |
| --- | --- | --- |
| `name` | `name() -> str` | Configuration name of the disk. |
| `file` | `file(path: str) -> IFile` | Builds a `File` bound to this driver. Raises `StoragePathException` for an invalid path or one that resolves to the root. |
| `directory` | `directory(path: str = "") -> IDirectory` | Builds a `Directory`; the empty string is the disk root. Raises `StoragePathException` on escape attempts. |
| `put` | `async put(path: str, contents: bytes \| str, visibility: str \| None = None) -> IFile` | `self.file(path).write(contents, visibility)`. |
| `exists` | `async exists(path: str) -> bool` | `self.file(path).exists()`. |
| `delete` | `async delete(path: str) -> bool` | `self.file(path).delete()`. |
| `copy` | `async copy(source: str, target: str) -> IFile` | `self.file(source).copyTo(target)`. |
| `move` | `async move(source: str, target: str) -> IFile` | `self.file(source).moveTo(target)`. |

### `File`

`orionis.storage.file.File` — implements `orionis.storage.contracts.file.IFile`.

`__slots__ = ("_driver", "_path")`

```python
def __init__(self, driver: IStorageDriver, path: str) -> None
```

The path is normalized with `normalizeFilePath()` at construction time, so an invalid
path fails immediately with `StoragePathException` and never reaches the driver.

| Method | Signature | Notes |
| --- | --- | --- |
| `path` | `path() -> str` | Canonical root-relative path. |
| `read` | `async read() -> bytes` | Raises `StorageFileNotFoundException`. |
| `readStream` | `readStream(chunk_size: int = 65536) -> AsyncIterator[bytes]` | Not a coroutine: returns the driver's async iterator, consume it with `async for`. |
| `write` | `async write(contents: bytes \| str, visibility: str \| None = None) -> IFile` | `str` is encoded as UTF-8. Returns `self` (fluent). |
| `writeStream` | `async writeStream(stream: AsyncIterable[bytes], visibility: str \| None = None) -> IFile` | Returns `self`. |
| `open` | `open(mode: str = "rb") -> IStorageStream` | Sync call returning a lazily opened stream. Accepted modes: `rb`, `wb`, `ab`, `rb+`, `wb+`, `ab+`; anything else raises `UnsupportedStorageOperationException`. |
| `delete` | `async delete() -> bool` | `True` when the file existed. |
| `exists` | `async exists() -> bool` | — |
| `copyTo` | `async copyTo(target: str) -> IFile` | Returns a **new** `File` pointing at the copy. |
| `moveTo` | `async moveTo(target: str) -> IFile` | Returns a new `File`; the current object keeps pointing at the old path. |
| `rename` | `async rename(name: str) -> IFile` | Renames within the same directory. Raises `StoragePathException` if `name` is empty or contains `/` or `\`. |
| `size` | `async size() -> int` | Bytes. |
| `mimeType` | `async mimeType() -> str \| None` | — |
| `lastModified` | `async lastModified() -> datetime` | Timezone-aware (UTC). |
| `url` | `async url() -> str` | Raises `UnsupportedStorageOperationException` when the disk exposes no public URLs. |
| `temporaryUrl` | `async temporaryUrl(expires_in: int = 3600) -> str` | Signed URL; unsupported by `local` and `memory`. |
| `visibility` | `async visibility() -> str` | `'public'` or `'private'`. |
| `setVisibility` | `async setVisibility(visibility: str) -> IFile` | Returns `self`. |
| `download` | `async download(destination: str \| Path) -> Path` | Copies to the local filesystem; when `destination` is an existing directory the original name is kept. Returns the absolute path. |
| `hash` | `async hash(algorithm: str = "sha256") -> str` | Any algorithm accepted by `hashlib.new`. |
| `info` | `async info() -> FileInfo` | Metadata snapshot. |

### `Directory`

`orionis.storage.directory.Directory` — implements
`orionis.storage.contracts.directory.IDirectory`.

`__slots__ = ("_driver", "_path")`

```python
def __init__(self, driver: IStorageDriver, path: str = "") -> None
```

The path is normalized with `normalizePath()`; the empty string denotes the disk root.

| Method | Signature | Notes |
| --- | --- | --- |
| `path` | `path() -> str` | Empty string means the disk root. |
| `create` | `async create() -> IDirectory` | Creates missing parents. Returns `self`. |
| `delete` | `async delete() -> bool` | Recursive. `True` when it existed. |
| `exists` | `async exists() -> bool` | — |
| `files` | `async files() -> list[IFile]` | Direct children only, sorted by path. |
| `allFiles` | `async allFiles() -> list[IFile]` | Whole subtree. |
| `directories` | `async directories() -> list[IDirectory]` | Direct children only. |
| `allDirectories` | `async allDirectories() -> list[IDirectory]` | Whole subtree. |

Listing methods return `File` / `Directory` objects, never strings: the driver returns
paths and `Directory` wraps them.

### `UploadedFile`

`orionis.storage.uploaded_file.UploadedFile` — implements
`orionis.storage.contracts.uploaded_file.IUploadedFile`.

`__slots__ = ("_hash_name", "_manager", "_source")`

```python
def __init__(self, source: IHttpUploadedFile, manager: IStorageManager) -> None
```

| Method | Signature | Notes |
| --- | --- | --- |
| `originalName` | `originalName() -> str` | `source.filename` (already sanitized by the HTTP layer). |
| `extension` | `extension() -> str` | Lowercase, dot included; empty string when there is none. |
| `size` | `size() -> int` | Payload bytes. |
| `mimeType` | `mimeType() -> str \| None` | MIME type declared by the client. |
| `hashName` | `hashName() -> str` | `secrets.token_hex(20)` plus the original extension. Generated once and cached per instance. |
| `read` | `async read() -> bytes` | Reads the whole payload on a worker thread. |
| `store` | `async store(directory: str = "", disk: str \| None = None, visibility: str \| None = None) -> IFile` | Persists under the generated hash name. |
| `storeAs` | `async storeAs(directory: str, name: str, disk: str \| None = None, visibility: str \| None = None) -> IFile` | Explicit name. Raises `StoragePathException` if `name` is empty or contains a separator. |
| `move` | `async move(directory: str, name: str \| None = None, disk: str \| None = None) -> IFile` | Persists and then closes the upload buffer. |
| `copy` | `async copy(directory: str, name: str \| None = None, disk: str \| None = None) -> IFile` | Persists and keeps the buffer usable. |

Persistence always goes through `manager.disk(disk).file(target).writeStream(...)`, and
the payload is streamed chunk by chunk (the blocking iterator is advanced with
`asyncio.to_thread`), so an upload spooled to a temporary file is never fully loaded
into memory.

### `AsyncStream`

`orionis.storage.stream.AsyncStream` — implements
`orionis.storage.contracts.stream.IStorageStream`.

`__slots__ = ("_handle", "_on_close", "_opener")`

```python
def __init__(
    self,
    opener: Callable[[], BinaryIO],
    on_close: Callable[[BinaryIO], None] | None = None,
) -> None
```

The handle is created by `opener` on first use (or on `__aenter__`) and every blocking
operation runs on a worker thread.

| Method | Signature | Notes |
| --- | --- | --- |
| `read` | `async read(size: int = -1) -> bytes` | `-1` reads to EOF. |
| `write` | `async write(data: bytes) -> int` | Bytes written. |
| `seek` | `async seek(offset: int, whence: int = 0) -> int` | New absolute position. |
| `close` | `async close() -> None` | Invokes `on_close` with the open handle, then closes it. Detaches the handle first, so a double close is a no-op. |
| `__aenter__` | `async __aenter__() -> IStorageStream` | Opens the handle and returns the stream. |
| `__aexit__` | `async __aexit__(exc_type, exc, traceback) -> None` | Always closes. |

The `on_close` callback is what lets the memory driver flush the buffer back into its
store when a writable stream is closed.

### `IStorageDriver`

`orionis.storage.contracts.driver.IStorageDriver` — ABC with 24 abstract methods.
Application code never touches a driver directly.

| Group | Methods |
| --- | --- |
| Content | `read`, `readStream`, `write`, `writeStream`, `delete`, `exists`, `open` |
| Relocation | `copy`, `move`, `download` |
| Metadata | `size`, `mimeType`, `lastModified`, `visibility`, `setVisibility`, `hash`, `info` |
| Directories | `createDirectory`, `deleteDirectory`, `directoryExists`, `files`, `directories` |
| URLs | `url`, `temporaryUrl` |

`readStream` and `open` are the only non-`async def` members: `readStream` is
implemented as an async generator (call it and iterate with `async for`) and `open`
returns the stream object synchronously.

`files()` and `directories()` take `recursive` as a keyword-only argument
(`files(path="", *, recursive=False)`).

Capability matrix of the five built-in drivers:

| Capability | `local` | `memory` | `s3` | `azure` | `gcs` |
| --- | --- | --- | --- | --- | --- |
| `url()` | Requires configured `url`, otherwise `UnsupportedStorageOperationException` | Same as local | Configured `url`, custom `endpoint`, or virtual-host address | Configured `url` or the Azure blob endpoint | Configured `url` or `storage.googleapis.com` |
| `temporaryUrl()` | Always raises `UnsupportedStorageOperationException` | Always raises `UnsupportedStorageOperationException` | `generate_presigned_url` | SAS token; requires the account key | V4 signed URL; requires a signing key |
| `visibility()` | Derived from permission bits (`st_mode & 0o044`) | Value stored with the entry | Object ACL grants for `AllUsers` | Container access policy | `allUsers` entry in the blob ACL |
| `setVisibility()` | `chmod` `0o644` / `0o600` | Updates the stored value | `put_object_acl` | Always raises `UnsupportedStorageOperationException` | Predefined ACL |
| Directories | Real filesystem directories | Explicit set plus prefixes implied by keys | Zero-byte `path/` markers plus implied prefixes | Same as S3 | Same as S3 |

### `LocalStorageDriver`

`orionis.storage.drivers.local.LocalStorageDriver`

`__slots__ = ("_base_url", "_root")`

```python
def __init__(self, root: Path, base_url: str | None = None) -> None
```

- `root` is resolved with `Path.resolve()` and created with `mkdir(parents=True, exist_ok=True)`
  in the constructor.
- `base_url` has its trailing `/` stripped; when it is `None`, `url()` raises and
  `FileInfo.url` is `None`.
- **Atomic writes:** `write()` and `writeStream()` write to a sibling
  `<name>.<random>.tmp` file and then `Path.replace()` it over the destination. The
  random infix gives every call its own staging file, so writers racing on the same path
  never mix payloads; a failed write removes only its own temporary file and leaves the
  destination untouched.
- Because of that, `files()` skips entries whose name ends in `.tmp`.
- Visibility maps onto POSIX bits: files `0o644` (public) / `0o600` (private),
  directories `0o755` / `0o700`. An unknown level raises `UnsupportedStorageOperationException`.
- `info()` reads the file once and computes MD5 (`etag`) and SHA-256 (`checksum`) in the
  same pass; `createdAt` uses `st_birthtime` when the platform provides it, otherwise `None`.
- `mimeType()` is derived from the extension via `mimetypes.guess_type()` and performs no
  disk access.
- Every blocking call runs through `asyncio.to_thread`.

### `MemoryStorageDriver`

`orionis.storage.drivers.memory.MemoryStorageDriver`

`__slots__ = ("_base_url", "_directories", "_files")`

```python
def __init__(self, base_url: str | None = None) -> None
```

Keeps every object in process memory: `_files` maps paths to `_MemoryEntry`
(`content`, `visibility`, `created_at`, `modified_at`) and `_directories` holds the
directories created explicitly. Designed for tests and ephemeral workloads.

- A new entry defaults to `Visibility.PRIVATE` when `write()` receives `visibility=None`;
  on an overwrite the previous visibility is preserved and `created_at` is kept.
- `open()` works over `io.BytesIO`: read modes require an existing file, append modes
  seek to the end, and every writable mode flushes back into the store on close.
- `download()` does touch the filesystem — it writes the in-memory content to the local
  destination.
- Concurrency: the store is a plain dictionary mutated without locks. Every operation
  completes without awaiting midway, so concurrent tasks on a single event loop never
  observe a partial mutation; no guarantee is offered when the same path is mutated from
  several threads at once, which streams opened with `open()` do because they flush their
  buffer on a worker thread.

### `S3StorageDriver`

`orionis.storage.drivers.s3.S3StorageDriver`

`__slots__ = ("_base_url", "_bucket", "_client", "_client_error", "_endpoint", "_key", "_region", "_secret", "_use_path_style")`

```python
def __init__(self, config: object) -> None
```

Reads `bucket`, `region`, `key`, `secret`, `url`, `endpoint`, and
`use_path_style_endpoint` from the configuration entity. The constructor performs no
import and no network call.

- The `boto3` client is built on first use: explicit credentials win, and when they are
  absent boto3 falls back to its own credential chain. `use_path_style_endpoint=True`
  switches the addressing style to `path`.
- Error codes `404`, `NoSuchKey`, and `NotFound` are translated into
  `StorageFileNotFoundException`; any other SDK error propagates unchanged.
- Visibility maps to canned ACLs `public-read` / `private`; `visibility()` inspects the
  object grants looking for a read permission for the anonymous-users group.
- `deleteDirectory()` batch-deletes in groups of up to 1000 keys.
- Streams are buffered into a spooled temporary file that spills to disk beyond 8 MiB.

### `AzureStorageDriver`

`orionis.storage.drivers.azure.AzureStorageDriver`

`__slots__ = ("_account_key", "_account_name", "_base_url", "_connection_string", "_container", "_container_name", "_http_error", "_not_found", "_sdk")`

```python
def __init__(self, config: object) -> None
```

Reads `connection_string`, `account_name`, `account_key`, `container`, and `url`. When a
connection string is supplied, `AccountName` and `AccountKey` are parsed out of it so
URLs and SAS tokens can be produced.

- Azure has no per-blob visibility: `visibility()` reflects the container access policy
  and `setVisibility()` **always** raises `UnsupportedStorageOperationException`.
- `temporaryUrl()` produces a read-only SAS URL and requires the account key; without it,
  the call raises `UnsupportedStorageOperationException`.
- `info()` fills `checksum` from the `Content-MD5` stored by Azure (hex-encoded) when
  available, and `etag` from the blob ETag with quotes stripped.
- `directoryExists("")` returns `True` (the root always exists).

### `GoogleStorageDriver`

`orionis.storage.drivers.gcs.GoogleStorageDriver`

`__slots__ = ("_base_url", "_bucket", "_bucket_name", "_cloud_error", "_key_file", "_not_found", "_project")`

```python
def __init__(self, config: object) -> None
```

Reads `project_id`, `key_file`, `bucket`, and `url`. Authentication uses the
service-account key file when configured, otherwise Application Default Credentials.

- `temporaryUrl()` builds a V4 signed URL; signing requires credentials with a private
  key (a key file), which plain ADC does not provide.
- `visibility()` returns `'private'` when ACLs cannot be inspected — for example under
  uniform bucket-level access.
- Visibility maps to GCS predefined ACLs; an unknown level raises
  `UnsupportedStorageOperationException`.

### Driver helper functions

`orionis.storage.drivers.functions` — module-level helpers shared by the cloud drivers.

| Function | Signature | Description |
| --- | --- | --- |
| `importDriverDependency` | `importDriverDependency(module: str, package: str, extra: str) -> ModuleType` | Imports an optional SDK module and converts `ImportError` into `MissingStorageDependencyException` carrying the install command. |
| `assertBinaryMode` | `assertBinaryMode(mode: str) -> None` | Validates a stream mode against `rb`, `wb`, `ab`, `rb+`, `wb+`, `ab+`. |
| `resolveDownloadTarget` | `resolveDownloadTarget(normalized: str, destination: str \| Path) -> Path` | Resolves the local target of a download, keeping the original name when the destination is an existing directory, and creating missing parents. |
| `filterFiles` | `filterFiles(keys: Iterable[str], base: str, *, recursive: bool) -> list[str]` | Selects the keys that are files under `base`; keys ending in `/` are directory markers and are always excluded. Returns a sorted list. |
| `deriveDirectories` | `deriveDirectories(keys: Iterable[str], base: str, *, recursive: bool) -> list[str]` | Infers directory paths from object keys (object stores have no physical directories). Returns a sorted list. |

### `FileInfo`

`orionis.storage.entities.file_info.FileInfo` —
`@dataclass(frozen=True, kw_only=True, slots=True)`. Returned by `await file.info()`.

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `path` | `str` | — | Canonical root-relative path. |
| `size` | `int` | — | Size in bytes. |
| `lastModified` | `datetime` | — | Timezone-aware modification timestamp. |
| `visibility` | `str` | — | `'public'` or `'private'`. |
| `mimeType` | `str \| None` | `None` | Guessed MIME type. |
| `createdAt` | `datetime \| None` | `None` | Creation timestamp when the driver can supply it. |
| `etag` | `str \| None` | `None` | Entity tag (MD5 hex digest in the built-in drivers). |
| `checksum` | `str \| None` | `None` | SHA-256 hex digest when available. |
| `url` | `str \| None` | `None` | Public URL when the disk exposes one. |

Field names are camelCase on purpose, to match the public API naming of the framework.

### `Visibility`

`orionis.storage.enums.visibility.Visibility` — `StrEnum` with `PUBLIC = "public"` and
`PRIVATE = "private"`. Since members inherit from `str`, they can be passed anywhere a
plain visibility string is accepted.

### Path normalization

`orionis.storage.paths` — two module-level functions applied at every boundary.

```python
def normalizePath(path: str) -> str
def normalizeFilePath(path: str) -> str
```

`normalizePath()` converts `\` into `/`, drops empty and `.` segments, resolves `..`
logically (without touching the filesystem), and returns a path with no leading or
trailing slash. The empty string represents the disk root. It raises
`StoragePathException` when the path contains a null byte, when a segment contains `:`
(blocking drive letters and stream separators), or when a `..` escapes the root.

`normalizeFilePath()` applies the same rules and additionally rejects an empty result,
because the disk root can never be treated as a file.

### Exceptions

`orionis.storage.exceptions` — all inherit from `StorageException`, which inherits from
`Exception`.

| Exception | Raised when |
| --- | --- |
| `StorageException` | Base class for the module. |
| `DiskNotFoundException` | The disk is not declared in the `filesystems` configuration. |
| `DriverNotSupportedException` | The disk references a driver with no implementation. |
| `MissingStorageDependencyException` | A driver needs an optional package that is not installed. |
| `StoragePathException` | The path is malformed or escapes the disk root. |
| `StorageFileNotFoundException` | The file does not exist on the target disk. |
| `UnsupportedStorageOperationException` | The driver cannot perform the requested operation (temporary URL, visibility, stream mode, hash algorithm). |

### `StorageProvider` and the `Storage` facade

`orionis.storage.provider.StorageProvider` extends `ServiceProvider` and
`DeferrableProvider`, and is listed in `orionis/foundation/core_providers.py`.

| Member | Behavior |
| --- | --- |
| `provides()` | `[IStorageManager]` |
| `register()` | `self.app.singleton(IStorageManager, StorageManager)` |
| `boot()` | `await Storage.pin()` (async) |

`orionis.support.facades.storage.Storage` only overrides `getFacadeAccessor()`, which
returns `IStorageManager`. The sibling `storage.pyi` file exists purely for editor
autocompletion and is never executed.

Because the provider is **deferrable**, register and boot only run the first time
`IStorageManager` is resolved through the container. That has a concrete consequence for
the facade:

- Before that first resolution, `Storage.disk("public")` returns a deferred dispatcher
  that must be awaited: `disk = await Storage.disk("public")`. That call resolves the
  service, boots the provider, and pins the facade.
- Once pinned, attribute access is a direct passthrough: `Storage.disk("public")` returns
  the `Disk` synchronously, and awaiting it would fail because a `Disk` is not awaitable.

Injecting `IStorageManager` (constructor or controller-method parameter) avoids that
distinction altogether: the container resolves the deferred provider and hands over the
real manager.

### Configuration keys

`StorageManager` reads `app.config("filesystems")`, backed by the entities in
`orionis.foundation.config.filesystems` and, in the application, by `config/filesystems.py`.

| Key | Type | Description |
| --- | --- | --- |
| `default` | `DiskName \| str` | Disk used by `Storage.default()` / `disk(None)`. Validated against `DiskName` (`local`, `public`, `s3`, `azure`, `gcs`). |
| `disks.local` | `Local` | `driver` (default `"local"`), `path` (default `"storage/app/private"`). |
| `disks.public` | `Public` | `driver` (default `"local"`), `path`, `url`. |
| `disks.s3` | `S3` | `driver` (default `"aws"`), `key`, `secret`, `region`, `bucket`, `url`, `endpoint`, `use_path_style_endpoint`. |
| `disks.azure` | `Azure` | `driver` (default `"azure"`), `connection_string`, `account_name`, `account_key`, `container`, `url`. |
| `disks.gcs` | `GCS` | `driver` (default `"gcs"`), `project_id`, `key_file`, `bucket`, `url`. |

`Disks` is a frozen dataclass with exactly those five fields, so disk **names** are fixed;
what is configurable per disk is the `driver` it points at, which is also the key used by
`StorageManager.extend()`.

## Usage examples

### Resolving a disk through the facade

```python
from orionis.storage.contracts.file import IFile
from orionis.support.facades.storage import Storage


async def store_report(payload: bytes) -> IFile:
    """Persist a report on the public disk and return the stored file."""
    # First facade access: awaiting it boots the deferred provider and pins
    # the facade, so later accesses can be used directly.
    disk = await Storage.disk("public")

    report = await disk.put("reports/2026-q1.pdf", payload, "public")
    print(report.path(), await report.size(), await report.url())

    for entry in await disk.directory("reports").files():
        print(entry.path())

    return report
```

### Handling errors

```python
import asyncio

from orionis.storage.disk import Disk
from orionis.storage.drivers.memory import MemoryStorageDriver
from orionis.storage.exceptions import (
    StorageFileNotFoundException,
    StoragePathException,
    UnsupportedStorageOperationException,
)


async def main() -> None:
    disk = Disk(name="memory", driver=MemoryStorageDriver())

    try:
        await disk.file("missing.txt").read()
    except StorageFileNotFoundException as exc:
        print("not found:", exc)

    try:
        disk.file("../../etc/passwd")
    except StoragePathException as exc:
        print("rejected path:", exc)

    await disk.put("notes.txt", "hello")
    try:
        await disk.file("notes.txt").temporaryUrl(60)
    except UnsupportedStorageOperationException as exc:
        print("unsupported:", exc)


asyncio.run(main())
```

### Streaming large files

```python
import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

from orionis.storage.disk import Disk
from orionis.storage.drivers.local import LocalStorageDriver


async def rows() -> AsyncIterator[bytes]:
    """Produce the export contents chunk by chunk."""
    for index in range(3):
        yield f"row-{index}\n".encode()


async def main() -> None:
    driver = LocalStorageDriver(root=Path("storage/app/private"))
    disk = Disk(name="local", driver=driver)

    # Nothing is fully materialized in memory, neither on write nor on read.
    export = await disk.file("exports/report.csv").writeStream(rows())

    async for chunk in export.readStream(chunk_size=8):
        print(chunk)

    async with export.open("rb") as stream:
        print(await stream.read(5))

    await export.delete()


asyncio.run(main())
```

### Storing an HTTP upload

```python
from orionis.http import HttpResponse, response
from orionis.http.base import BaseController
from orionis.http.request import Request
from orionis.storage.contracts.manager import IStorageManager


class AvatarController(BaseController):

    async def store(
        self,
        request: Request,
        storage: IStorageManager,
    ) -> HttpResponse:
        """
        Persist the uploaded avatar on the public disk.

        Parameters
        ----------
        request : Request
            Incoming HTTP request carrying the multipart form.
        storage : IStorageManager
            Storage manager injected by the container.

        Returns
        -------
        HttpResponse
            JSON payload with the stored path and its public URL.
        """
        form = await request.form()
        upload = storage.uploaded(form.files["avatar"][0])

        # store() uses a random hash name; storeAs() takes an explicit one.
        stored = await upload.store("avatars", disk="public", visibility="public")

        return response.json({
            "path": stored.path(),
            "url": await stored.url(),
        })
```

### Running standalone with the memory driver

```python
import asyncio

from orionis.storage.disk import Disk
from orionis.storage.drivers.memory import MemoryStorageDriver


async def main() -> None:
    disk = Disk(name="fake", driver=MemoryStorageDriver(base_url="https://cdn.test"))

    await disk.put("invoices/2026/001.txt", "total: 120", "public")
    await disk.put("invoices/2026/002.txt", "total: 340")

    invoices = disk.directory("invoices")
    print([entry.path() for entry in await invoices.allFiles()])
    print([entry.path() for entry in await invoices.directories()])

    first = disk.file("invoices/2026/001.txt")
    print(await first.visibility())
    print(await first.url())
    print(await first.hash("md5"))
    print(await first.info())


asyncio.run(main())
```

### Registering a custom driver

```python
from orionis.storage.contracts.driver import IStorageDriver
from orionis.storage.contracts.manager import IStorageManager
from orionis.storage.drivers.memory import MemoryStorageDriver


def register_fake_driver(manager: IStorageManager) -> None:
    """Bind the driver name 'fake' to an in-memory implementation."""

    def factory(config: object) -> IStorageDriver:
        # config is the disk configuration entity declared in config/filesystems.py.
        return MemoryStorageDriver(base_url=getattr(config, "url", None))

    # Any disk whose `driver` field is "fake" now resolves to this factory,
    # which also takes precedence over the built-in drivers.
    manager.extend("fake", factory)
```

## Performance and concurrency considerations

- **Non-blocking I/O:** every blocking operation (filesystem access, SDK calls, spooled
  upload buffers) runs through `asyncio.to_thread`, so the event loop stays responsive.
  There is no truly asynchronous native client involved; the model is "worker threads
  behind an async API".
- **Bounded memory:** `readStream`, `writeStream`, `hash`, and `info` process 64 KiB
  chunks; cloud drivers spool incoming streams into a temporary file that spills to disk
  beyond 8 MiB. `read()` is the only operation that materializes the whole file.
- **Disk cache:** `StorageManager` builds each `Disk` once and caches it in `_disks`;
  `extend()` clears the cache. Cloud clients are also built once per driver instance and
  reused.
- **Atomic local writes:** the temporary-file plus `Path.replace()` sequence means a
  reader never observes a half-written file, and a failed transfer leaves no partial
  destination behind. Each call stages into its own randomly named temporary file, so
  concurrent writers on the same path publish one complete payload or nothing.
- **`__slots__` everywhere** in concrete classes and empty `__slots__` in the contracts,
  which removes the attribute dictionary from the many short-lived `File` / `Directory`
  instances a listing creates.
- **Cheap objects:** `Disk.file()`, `Disk.directory()`, and `File.open()` perform no I/O;
  they only build objects. Cost is incurred when awaiting or entering them.
- **Independent state:** `File` and `Directory` hold only a driver reference and a string,
  so they can be created and used freely from multiple tasks. `AsyncStream`, on the other
  hand, wraps a single handle with a mutable position, so a stream should be used by one
  task at a time.

## Compatibility notes

- **Python `>= 3.14`** (`requires-python` in `pyproject.toml`). The module uses
  `Path.walk()` (3.12+), `datetime.UTC` (3.11+), `StrEnum` (3.11+),
  `hashlib.new(..., usedforsecurity=False)` (3.9+), and `X | Y` type syntax.
- **Windows:** visibility relies on POSIX permission bits. Windows does not implement the
  full POSIX model, so `chmod` degrades gracefully and `visibility()` can report `'public'`
  for files created with the default mode.
- **`createdAt`** depends on `st_birthtime`, which not every platform/filesystem exposes;
  it is `None` when unavailable.
- **`Path.replace()`** cannot cross devices; the local driver falls back to `shutil.move()`
  for cross-device moves. On Windows it can also raise `PermissionError` when another
  writer is replacing the same destination at that very instant, an operating system
  restriction that POSIX does not have.
- **Optional SDKs:** cloud drivers can be instantiated without their SDK installed; the
  failure surfaces on the first operation as `MissingStorageDependencyException`.
- **The `storage` module never imports the HTTP layer at runtime**: the multipart payload
  contract is imported only under `TYPE_CHECKING` and consumed duck-typed
  (`filename`, `extension`, `size`, `content_type`, `read()`, `chunks()`, `close()`).

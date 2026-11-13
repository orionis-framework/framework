# Configuring disks, publication, and drivers

Storage lets you save content and work with files through the same async contract on local, ephemeral, and cloud disks.

## Configure disks and credentials

The shipped configuration supports names `local`, `public`, `s3`, `azure`, and `gcs`. A disk name selects an entry; its `driver` attribute selects the implementation. `local` and `public` use the same local driver with different roots. You can also assign the `memory` driver to an existing entry for an isolated environment.

`Filesystems` and `Disks` validate known fields: arbitrarily adding `private` or `archive` to a dict does not automatically create a disk. The manager can read attributes from an extended configuration object, but new names require compatible entities/configuration and validation. For a small integration, changing an existing entry's driver is simpler.

| Provider | Orionis extra | Consumed settings / defaults |
|---|---|---|
| Local | none | `LOCAL_PATH=storage/app/private`; public uses `PUBLIC_PATH=storage/app/public`, `PUBLIC_URL=/static`. |
| S3 | `s3` (`boto3>=1.43.99`) | `S3_KEY`, `S3_SECRET`, `S3_REGION=us-east-1`, `S3_BUCKET`, optional URL/endpoint, path style disabled. |
| Azure Blob | `azure` (`azure-storage-blob>=12.30.2`) | Connection string or account/key; `AZURE_CONTAINER`; optional URL. |
| GCS | `gcs` (`google-cloud-storage>=3.14.1`) | Project, bucket, optional key file or SDK default credentials. |

The aggregate `storage` extra installs all three SDKs. Driver construction is lazy and does not validate a network connection. Concurrent first accesses publish a single SDK client per driver; first I/O may raise `MissingStorageDependencyException` with installation guidance or an SDK exception. Credentials and permissions follow provider policies. `StorageManager` has no common failover or retry policy.

### Visibility and publication

`url()` builds a location: it neither grants permission nor creates a server static route. Local/memory require `base_url`; cloud can derive URLs from provider settings or a configured base. Keep confidential files on private storage and authorize every download.

`temporaryUrl(expires_in=3600)` supports signing on S3, Azure, and GCS, subject to credentials. Local and memory raise `UnsupportedStorageOperationException`. Azure requires an account key for SAS and has no per-blob ACL: writes ignore visibility and `setVisibility()` explicitly fails; configure container access. S3/GCS require bucket policies that permit the requested ACL. A valid URL does not prove existence, application-user authorization, or public access.

### Register a driver

Implement `IStorageDriver` and register a synchronous `factory(config)` during boot before first use. `extend()` can override built-in names and clears cached disks; retained disk references continue to use the previous driver. Do not mutate the registry during concurrent requests. The factory receives no application argument and is not awaited: explicitly capture dependencies when needed.

This example registers a custom-named memory driver for the existing `local` entry without creating files:

```python
import asyncio
from pathlib import Path
from orionis.storage import MemoryStorageDriver, StorageManager


class App:
    basePath = Path.cwd()

    def config(self, name: str) -> dict:
        return {
            "default": "local",
            "disks": {"local": {"driver": "scratch", "path": "unused"}},
        }


async def main() -> None:
    manager = StorageManager(App())
    manager.extend("scratch", lambda config: MemoryStorageDriver())
    file = await manager.disk().put("check.txt", "ok")
    assert await file.read() == b"ok"


asyncio.run(main())
```

## Configuration

`config/filesystems.py` selects `FILESYSTEM_DISK` (default `local`) and defines conventional disks:

- Local: `LOCAL_PATH` defaults to `storage/app/private`.
- Public local: `PUBLIC_PATH` defaults to `storage/app/public`; `PUBLIC_URL` defaults to `/static`.
- S3: `S3_KEY`, `S3_SECRET`, `S3_REGION` (`us-east-1`), `S3_BUCKET`, `S3_URL`, `S3_ENDPOINT`, `S3_USE_PATH_STYLE_ENDPOINT`.
- Azure: `AZURE_CONNECTION_STRING` or account credentials (`AZURE_ACCOUNT_NAME`, `AZURE_ACCOUNT_KEY`), plus `AZURE_CONTAINER` and `AZURE_URL`.
- GCS: `GCS_PROJECT_ID`, optional `GCS_KEY_FILE`, `GCS_BUCKET`, and `GCS_URL`.

Relative local paths are anchored below the application base path. Empty cloud credentials are placeholders, not usable deployments; configuration entities validate shapes while provider SDKs validate credentials on use.



## Integration with Orionis

When the deferrable `StorageProvider` boots, it binds `IStorageManager` as a singleton and pins the `Storage` facade. Application boot alone need not load a deferred provider; call `await Storage.pin()` before the first synchronous `Storage.disk()` access. The HTTP layer buffers/spools multipart files; `StorageManager.uploaded()` wraps them without coupling storage drivers to requests. Schema file/image rules understand the uploaded-file contract.

Public local disks normally pair `PUBLIC_URL=/static` with the application's static-file routing. Storage configuration does not create a public route automatically in isolation; routing and deployment must expose the matching directory intentionally.



### Use the application facade

```python
from orionis.support.facades import Storage


async def publish_manifest() -> str:
    await Storage.pin()
    file = await Storage.disk("public").put(
        "build/manifest.json",
        '{"version": 1}',
        visibility="public",
    )
    return await file.url()
```

## Errors and edge cases

- Invalid or escaping paths raise `StoragePathException`; missing files raise `StorageFileNotFoundException` where the operation requires existence.
- Local permission and I/O failures propagate as their original `PermissionError`/`OSError`, including in existence checks and listings. Only absent or non-directory paths use the operation's documented missing-path result, such as `False`, an empty list, or `StorageFileNotFoundException`.
- Unsupported features such as local signed URLs raise `UnsupportedStorageOperationException` instead of returning misleading data.
- Unknown disks and drivers raise `DiskNotFoundException` and `DriverNotSupportedException`.
- Copy/move targets are normalized; overwrite semantics follow the driver contract and backend behavior.
- `mimeType()` is inference/provider metadata, not content validation. Hash/checksum support and ETag meaning vary by provider.
- Cloud listing is subject to provider consistency, pagination, credentials, and network failures. S3 batch deletion checks per-object failures and raises the SDK's `ClientError`; some objects may already have been deleted.
- Open streams must be closed; write streams may publish data during close/flush.



## Concurrency and limits

Each manager constructs and publishes one disk instance per name, including concurrent calls from threads. This does not make an async driver usable across event loops. Local `write()` and `writeStream()` publish with unique temporary files and replacement: readers do not observe mixed bytes, but concurrent writers follow final-replacement semantics. An `exists()` then `write()` sequence does not guarantee create-if-absent. Memory is ephemeral and does not synchronize threads or processes. Cloud drivers depend on their SDK, network, and service consistency.

There are no multi-file transactions, business locks, or common compare-and-swap operation. Coordinate same-key work in application code. Bound size, temporary disk use, and concurrency: spooling protects RAM at the cost of local I/O and does not make work unlimited.


## Compatibility

All built-in drivers implement `IStorageDriver`, but provider capabilities differ: public ACLs, signed URLs, creation times, ETags, checksums, and directory semantics are not universally equivalent. Storage input paths and `file.path()` use canonical POSIX-style strings relative to the disk root, including on Windows. Local files also expose `absolutePath()` with native filesystem separators and `relativePath()` relative to `app.basePath` with `/` separators. Custom drivers inherit unsupported-operation errors for these optional methods until they provide an implementation.

Legacy `normalizePath` and `normalizeFilePath` remain lazy aliases; new code should use snake_case names.

## Implementation reference for extensions

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

---

[Index](README.md) · [http](../../../http/docs/en/README.md) · [container](../../../container/docs/en/README.md) · [mail](../../../mail/docs/en/README.md)

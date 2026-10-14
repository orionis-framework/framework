# Streaming content and saving uploads

Understand memory use, closure, and publication before streaming large files.

## Choose bytes, chunks, or handles

`read()` materializes the complete object. For incremental consumption, use `async for chunk in file.readStream(chunk_size=65536)`. `writeStream()` consumes an async iterable of bytes and requests the next chunk after the corresponding work. Implementations have different memory costs: memory accumulates all chunks; cloud spools input to a temporary file before calling its SDK; local stages writes and publishes on completion.

Cloud drivers use `SpooledTemporaryFile` for `open()`, so opening for reading may download the complete object before reads begin. `readStream()` is the incremental path. Azure delegates chunk sizing to its SDK and ignores `chunk_size`; do not assume identical bounds across providers.

`open()` is synchronous and returns a lazy handle with async operations. Supported modes are `rb`, `wb`, `ab`, `rb+`, `wb+`, and `ab+`; text modes are unsupported. Always use `async with` for closure. Memory/cloud writing modes publish on close: closing after an exception can also flush. A handle is not a transaction and provides no rollback. Local `open("wb")` opens the target directly; use `write()`/`writeStream()` when complete-content atomic publication is required.

### Open and close an isolated local file

```python
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.storage import Disk, LocalStorageDriver


async def main() -> None:
    with TemporaryDirectory() as root:
        disk = Disk("local", LocalStorageDriver(Path(root)))
        file = disk.file("reports/export.bin")
        async with file.open("wb+") as stream:
            assert await stream.write(b"report") == 6
            await stream.seek(0)
            assert await stream.read(3) == b"rep"
        assert await file.read() == b"report"


asyncio.run(main())
```

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

## Persist an HTTP upload

The HTTP type `orionis.http.payload.uploaded_file.UploadedFile` holds buffered multipart data. The storage adapter `orionis.storage.uploaded_file.UploadedFile` references it and provides disk-saving methods. Use `Storage.uploaded(source)` to obtain the latter. You do not need to copy everything to bytes first.

Validate size and content before publishing. Apply Schema file/image rules to the original HTTP payload: they expect `filename`, `size`, and synchronous `read()`. The storage adapter has async methods and does not replace that validation protocol. `originalName()` and `mimeType()` reflect client metadata; even though the HTTP payload sanitizes names, an extension does not prove file format. `hashName()` generates 40 hex characters plus the extension once; repeated calls on the same upload keep that name. This reduces collisions, but a write can still replace an existing path according to backend semantics.

`store(directory="", disk=None, visibility=None)` uses that random name. `storeAs(directory, name, disk=None, visibility=None)` allows an explicit name without separators. `copy(directory, name=None, disk=None)` saves while keeping the source open; `move(...)` saves then closes the HTTP buffer. Neither creates a transaction with your model. Store the returned `stored.path()` and retain the original name only as display metadata.

This example creates a small payload to exercise the flow without a server; a controller receives `source` from the HTTP parser.

```python
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.http.payload.uploaded_file import UploadedFile as HttpUpload
from orionis.storage import StorageManager


class App:
    def __init__(self, root: Path) -> None:
        self.basePath = root

    def config(self, name: str) -> dict:
        assert name == "filesystems"
        return {"default": "local", "disks": {"local": {"path": "private"}}}


async def main() -> None:
    with TemporaryDirectory() as root:
        manager = StorageManager(App(Path(root)))
        source = HttpUpload("report.txt", "text/plain")
        try:
            source.write(b"approved content")
            upload = manager.uploaded(source)
            stored = await upload.store("incoming", visibility="private")
            assert stored.path().startswith("incoming/")
            assert await stored.read() == b"approved content"
            assert await upload.read() == b"approved content"
        finally:
            source.close()


asyncio.run(main())
```

---

[Index](README.md) · [http](../../../http/docs/en/README.md) · [schemas](../../../schemas/docs/en/README.md)

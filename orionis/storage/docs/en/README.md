# Storage

Storage lets you save content and work with files through the same async contract on local, ephemeral, and cloud disks.

## Learning path

1. [Files and directories](files-and-directories.md): reading, writing, paths, metadata, and deletion.
2. [Streams and uploads](streaming-and-uploads.md): memory, handles, publication, and HTTP uploads.
3. [Disks and drivers](disks-and-drivers.md): local/cloud configuration, visibility, and extensions.

Memory and temporary-file examples require no credentials. Facade examples require the application and `StorageProvider`; cloud operations need their SDK and permissions.

## Bounded execution and performance

Local, S3 and GCS `readStream` preserve the requested logical chunk size, read one chunk first, then group native reads within a 1 MiB budget (at least one requested chunk). Azure batches at most 16 SDK chunks, stopping at 1 MiB; one SDK chunk can exceed that budget. No producer keeps reading while the consumer is paused. Cancellation waits for the in-progress native read before closing its handle.

`async with file.open("rb") as stream: ...` also supports `async for chunk in stream.chunks(65536, buffer_size=1048576): ...`. Do not interleave chunk iteration with seek/write/other reads. The surrounding async context owns close. Early exit from driver streams should use `contextlib.aclosing`; SDK requests still need finite network timeouts because cancelling Python cannot forcibly stop native I/O.

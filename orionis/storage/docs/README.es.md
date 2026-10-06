# orionis.storage

> `orionis.storage` ofrece una API async de archivos/directorios para discos local, memory, Amazon S3, Azure Blob y Google Cloud Storage.

## Descripción general

`StorageManager` resuelve discos configurados perezosamente y cachea cada `Disk`. Un disco crea objetos ligeros `File`/`Directory` que normalizan rutas relativas y delegan a `IStorageDriver`. Los drivers comparten contratos de lectura/escritura, streaming, metadata, visibilidad, URL, descarga, copy/move y listados.

La abstracción independiza la aplicación de SDKs. Clientes cloud se importan perezosamente, I/O local bloqueante corre en threads y payloads grandes usan streams async.

## Requisitos

- Python 3.14 o posterior.
- Aplicación iniciada y configuración `filesystems` para la fachada.
- Directorio escribible para local.
- SDK/credenciales opcionales para S3 (`boto3`), Azure (`azure-storage-blob`) o GCS (`google-cloud-storage`).

## Inicio rápido

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

Validación: **Ejecutado correctamente** en CPython 3.14.6.

## Conceptos principales

### Discos, archivos y directorios

Un disco es un límite de driver nombrado. `file`/`directory` normalizan de inmediato sin I/O. Las conveniencias delegan a objetos de dominio para mantener comportamiento consistente.

### Rutas relativas seguras

Las rutas usan `/`, ignoran vacío/`.` y resuelven `..` internos; rechazan escape de raíz, null, dos puntos y target file vacío. Local además impide escapes por symlink.

### Streaming

`readStream()` produce chunks; `writeStream()` consume iterables async. `open()` devuelve `AsyncStream` con operaciones en worker threads. Use `async with` para cerrar y ejecutar flush.

### Visibilidad y URL

Visibilidad es `public`/`private`. Local la mapea a permisos y cloud a controles del proveedor. `url()` requiere base configurada; `temporaryUrl()` firma en cloud compatible y no se soporta en local/memory.

### Metadata

`FileInfo` es snapshot inmutable con ruta, tamaño, fechas UTC, visibilidad, MIME, ETag, SHA-256 y URL cuando existen. Consultas individuales pueden ser más baratas.

## Estructura del módulo

| Ruta | Responsabilidad |
|---|---|
| `manager.py`, `provider.py` | Config, discos lazy, drivers custom y fachada. |
| `disk.py`, `file.py`, `directory.py` | API neutral. |
| `stream.py`, `uploaded_file.py` | Handles async y uploads HTTP. |
| `paths.py` | Normalización y rechazo de traversal. |
| `drivers/local.py`, `drivers/memory.py` | Implementaciones local/efímera. |
| `drivers/s3.py`, `drivers/azure.py`, `drivers/gcs.py` | Cloud opcional. |
| `entities/file_info.py`, `enums/visibility.py` | Metadata y visibilidad. |
| `contracts/`, `exceptions.py` | Interfaces y fallos tipados. |

## API pública

La raíz exporta perezosamente `StorageManager`, `Disk`, `File`, `Directory`, `AsyncStream`, `UploadedFile`, `FileInfo`, `Visibility` y cinco drivers.

### `File`

Ofrece `path`, read/write/streams/open, exists/delete, copy/move/rename, tamaño/MIME/fecha/visibilidad/hash/info/URL/temporary URL/download.

### `Directory`

Ofrece `path`, `create`, `exists`, `delete`, `files`, `allFiles`, `directories`, `allDirectories`. Los métodos `all*` son recursivos.

### Manager y fachada

`disk(name=None)`, `default()`, `extend(driver, factory)` y `uploaded(http_file)`. `orionis.support.facades.Storage` expone el mismo singleton.

### Uploads

`UploadedFile` expone nombre sanitizado, extensión, tamaño, MIME declarado y `hashName` aleatorio cacheado. `store`/`copy` mantienen buffer; `move` lo cierra. MIME/nombre del cliente no son confiables.

## Flujos de trabajo comunes

### Guardar contenido

Use `await Storage.disk().put(path, bytes_or_text, visibility)`. Strings usan UTF-8. Retenga `File` para metadata/URL.

### Transmitir objetos grandes

Pase iterable async a `writeStream` o itere `readStream`. No concatene sin tamaño seguro.

### Guardar upload HTTP

Adapte con `Storage.uploaded`, valide tamaño/contenido y llame `store`, `storeAs`, `copy` o `move`. Prefiera `hashName`.

### Añadir backend

Implemente `IStorageDriver`, registre factory con `extend` y use ese nombre en config.

## Ejemplos

### Listar directorios

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

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Escribir y leer streaming

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

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Inspeccionar metadata/visibilidad

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

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Normalizar rutas sin filesystem

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

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Usar fachada

```python
from orionis.support.facades import Storage


async def publish_manifest() -> str:
    file = await Storage.disk("public").put(
        "build/manifest.json", '{"version": 1}', visibility="public",
    )
    return await file.url()
```

Validación: **Importación y sintaxis validadas** en CPython 3.14.6; requiere aplicación/disco configurado.

## Configuración

`config/filesystems.py` selecciona `FILESYSTEM_DISK` (`local`) y define:

- Local: `LOCAL_PATH` (`storage/app/private`).
- Public: `PUBLIC_PATH` (`storage/app/public`) y `PUBLIC_URL` (`/static`).
- S3: `S3_KEY`, `S3_SECRET`, `S3_REGION`, `S3_BUCKET`, `S3_URL`, `S3_ENDPOINT`, `S3_USE_PATH_STYLE_ENDPOINT`.
- Azure: `AZURE_CONNECTION_STRING` o `AZURE_ACCOUNT_NAME`/`AZURE_ACCOUNT_KEY`, `AZURE_CONTAINER`, `AZURE_URL`.
- GCS: `GCS_PROJECT_ID`, `GCS_KEY_FILE`, `GCS_BUCKET`, `GCS_URL`.

Rutas relativas se anclan al base path. Credenciales vacías son placeholders; entities validan forma y SDK valida credenciales al usar.

## Integración con Orionis

`StorageProvider` deferrable enlaza singleton y fachada. HTTP bufferiza uploads; manager los adapta sin acoplar drivers. Reglas Schema de archivo/imagen entienden el contrato.

Discos public suelen emparejar `PUBLIC_URL=/static` con routing estático. La configuración por sí sola no publica el directorio.

## Errores y casos límite

- Rutas inválidas producen `StoragePathException`; archivos requeridos ausentes, `StorageFileNotFoundException`.
- Features no soportadas producen `UnsupportedStorageOperationException`.
- Disco/driver desconocido producen `DiskNotFoundException`/`DriverNotSupportedException`.
- Overwrite sigue contrato/semántica del backend.
- MIME no valida contenido; hash/ETag varían.
- Cloud depende de consistencia, paginación, credenciales y red.
- Streams abiertos deben cerrarse; close/flush puede publicar writes.

## Rendimiento y concurrencia

Discos se construyen una vez; wrappers son baratos. I/O bloqueante va fuera del loop. Streaming usa 64 KiB y backpressure.

Memory solo es atómico dentro de un turno del loop, no entre threads. Local protege resolución, pero writes concurrentes al mismo archivo requieren ownership. Cloud depende del SDK.

## Compatibilidad

Todos implementan `IStorageDriver`, pero ACL, URL firmada, timestamps, ETag, checksum y directorios no son equivalentes. La API usa rutas POSIX relativas incluso en Windows.

`normalizePath`/`normalizeFilePath` siguen como aliases legacy; código nuevo debe usar snake_case.

## Notas de verificación

- `tests/storage`: **245 métodos de prueba aprobados** con el runner de Orionis en CPython 3.14.6.
- Se compilaron seis programas bilingües; cinco programas memory/path se ejecutaron correctamente.
- La fachada se validó por importación/sintaxis porque requiere configuración.
- Cloud se verificó con mocks de SDK oficiales; no hubo credenciales ni writes de red.
- La evidencia cubrió rutas/symlinks, paridad local-memory, streams, uploads, metadata, visibilidad, URL, manager/provider, imports opcionales y adaptadores cloud.


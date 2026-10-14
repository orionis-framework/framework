# Transmitir contenido y guardar uploads

Controla memoria, cierre y publicación antes de aplicar streaming a archivos grandes.

## Elegir entre bytes, chunks y handles

`read()` materializa el objeto completo. Para un consumidor incremental utiliza `async for chunk in file.readStream(chunk_size=65536)`. `writeStream()` consume un iterable async de bytes y solo pide el siguiente chunk después del trabajo correspondiente. No todas las implementaciones usan la misma cantidad de memoria: memory acumula todos los chunks; cloud spolea la entrada a un temporal antes de invocar el SDK; local escribe a un temporal y publica al finalizar.

Los drivers cloud usan `SpooledTemporaryFile` para `open()`, de modo que abrir para lectura puede descargar el objeto completo antes de que puedas leerlo. `readStream()` es el camino incremental. Azure delega el tamaño de chunks al SDK e ignora `chunk_size`; no supongas límites idénticos en todos los proveedores.

`open()` es síncrono y devuelve un handle lazy con operaciones async. Los modos son `rb`, `wb`, `ab`, `rb+`, `wb+` y `ab+`; los modos de texto no están admitidos. Usa siempre `async with` para cerrar. En memory/cloud los modos de escritura publican al cerrar: cerrar después de una excepción también puede ejecutar flush. Un handle no es una transacción ni ofrece rollback. En local `open("wb")` utiliza el archivo directamente; si necesitas publicación atómica de contenido completo, utiliza `write()`/`writeStream()`.

### Abrir y cerrar un archivo local aislado

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

## Persistir una carga HTTP

El tipo HTTP `orionis.http.payload.uploaded_file.UploadedFile` mantiene el multipart en un buffer. El adaptador storage `orionis.storage.uploaded_file.UploadedFile` lo referencia y entrega métodos para guardar en un disco. Usa `Storage.uploaded(source)` para obtener este último. No necesitas copiar todo a bytes antes de guardarlo.

Valida tamaño y contenido antes de publicar. Aplica las reglas Schema de archivo/imagen al payload HTTP original: esperan `filename`, `size` y un `read()` síncrono. El adaptador storage tiene métodos async y no sustituye ese protocolo de validación. `originalName()` y `mimeType()` reflejan metadatos del cliente; aun cuando el payload HTTP sanitiza el nombre, la extensión no demuestra el formato del archivo. `hashName()` genera una vez 40 caracteres hex más la extensión; llamar nuevamente al mismo upload conserva el nombre. Esto reduce colisiones, pero una escritura puede reemplazar una ruta existente según el backend.

`store(directory="", disk=None, visibility=None)` usa ese nombre aleatorio. `storeAs(directory, name, disk=None, visibility=None)` permite uno explícito sin separadores. `copy(directory, name=None, disk=None)` guarda y mantiene abierto el origen; `move(...)` guarda y después cierra el buffer HTTP. Ninguno convierte la operación en una transacción con tu modelo. Guarda la ruta que devuelve `stored.path()` y conserva el nombre original solo como metadata de presentación.

El ejemplo crea un payload pequeño para ejecutar el recorrido sin servidor; en un controlador `source` procede del parser HTTP.

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

[Índice](README.md) · [http](../../../http/docs/es/README.md) · [schemas](../../../schemas/docs/es/README.md)

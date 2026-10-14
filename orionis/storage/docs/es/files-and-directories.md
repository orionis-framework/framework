# Guardar archivos y recorrer directorios

Storage permite guardar contenido y trabajar con archivos mediante el mismo contrato async en discos locales, efímeros o cloud.

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




## Guardar un resultado de negocio

Después de generar un reporte, decide un disco y una ruta lógica estable. En una aplicación iniciada puedes usar `await Storage.disk("local").put("reports/42.txt", content)`. `disk()` es síncrono; `put()` es async y devuelve un `File`. Conserva ese objeto o su `path()` para futuras operaciones. La ruta no contiene el directorio físico ni credenciales del proveedor.

`disk.file(path)` y `disk.directory(path)` solo crean referencias; no verifican existencia. `await file.exists()` sirve para presentación, pero una comprobación seguida de lectura puede tener carreras: captura `StorageFileNotFoundException` en la lectura que importa. No se incluye una transacción que englobe base de datos y almacenamiento. Si publicas una fila y un archivo, diseña limpieza/compensación cuando una operación falle.

`write()` y `put()` reemplazan contenido. `copyTo()` y `moveTo()` operan dentro del mismo disco. Devuelven un objeto nuevo; después de mover, el objeto original sigue apuntando a la ruta anterior. `rename(name)` conserva el directorio y rechaza separadores. Para copiar entre discos, transmite chunks entre sus referencias: no pases el nombre de otro disco como ruta de destino.

### Leer metadatos y eliminar

| Objetivo | Operación |
|---|---|
| Leer bytes completos | `await file.read()` |
| Tamaño / MIME / fecha | `await file.size()`, `await file.mimeType()`, `await file.lastModified()` |
| Snapshot | `await file.info()` |
| Ver o cambiar visibilidad | `await file.visibility()`, `await file.setVisibility("private")` |
| Checksum del contenido | `await file.hash("sha256")` |
| Copiar al filesystem del servidor | `await file.download(destination)` |
| Borrar un archivo | `await file.delete()` → si existía |
| Borrar árbol | `await disk.directory("reports").delete()` |

`download()` escribe en el filesystem del servidor; no crea por sí mismo una respuesta HTTP de descarga. El destino es una ruta local y debe ser controlado por la aplicación. `Directory.delete()` elimina recursivamente: una ruta vacía representa la raíz del disco. No la construyas a partir de entrada no validada.

`FileInfo` incluye `path`, `size`, `lastModified`, `visibility`, `mimeType`, `createdAt`, `etag`, `checksum` y `url`. Los campos opcionales pueden ser `None`; el ETag cloud no garantiza ser un MD5 del contenido completo. Consultar `info()` puede requerir leer contenido para calcular checksums: si solo necesitas tamaño, pide ese dato.


### Discos, archivos y directorios

Un disco es un límite de driver nombrado. `file`/`directory` normalizan de inmediato sin I/O. Las conveniencias delegan a objetos de dominio para mantener comportamiento consistente.

### Rutas relativas seguras

Las rutas usan `/`, ignoran vacío/`.` y resuelven `..` internos; rechazan escape de raíz, null, dos puntos y target file vacío. Local además impide escapes por symlink.

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

## Recorrer y crear directorios

`directory.path()` devuelve la ruta lógica. `await directory.create()` crea un directorio y devuelve el mismo objeto; en object storage puede representarse mediante un marcador. `await directory.exists()` comprueba existencia según el driver. `files()` y `directories()` devuelven listas de referencias de hijos directos; `allFiles()` y `allDirectories()` incluyen descendientes. Todos esos listados se esperan con `await`; las referencias `File`/`Directory` resultantes siguen ligadas al mismo disco.

La raíz se representa con `disk.directory()` y puede existir aunque aún no hayas guardado archivos. En object storage los directorios también pueden derivarse de prefijos implícitos: no dependas de que un directorio vacío sea una entidad persistente idéntica en todos los proveedores. Los listados se materializan como listas, no como cursores paginados públicos. Para árboles grandes considera su memoria y el número de peticiones del SDK.

`lastModified` contiene una fecha consciente de zona horaria en UTC; `createdAt` puede ser `None` cuando el proveedor no expone una fecha de creación. Un snapshot no se actualiza después de escribir: solicita otro `info()` si necesitas el estado posterior.

---

[Índice](README.md) · [foundation](../../../foundation/docs/es/README.md)
